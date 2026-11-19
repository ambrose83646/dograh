"""Give a self-signed-up organization its managed calling setup.

Platform mode replaces Dograh's hosted bootstrap. Each organization gets:

* model connections on the operator's provider keys, set as its default
* its own Twilio subaccount under the operator's account
* an outbound agent and an inbound agent

It gets no phone number. The user verifies a phone number they own as a caller
ID for outbound calls (``caller_id``). A number for inbound calls is a paid
resource the operator assigns (``operator.assign_account_number``).

Every step keys on recorded state, so a failed attempt resumes where it
stopped and a completed account costs one indexed read.
"""

from datetime import timedelta
from typing import Any

from loguru import logger

from api.db import db_client
from api.enums import OrganizationConfigurationKey
from api.services.platform import twilio_accounts
from api.services.platform.agent_definitions import (
    DEFAULT_INBOUND_RULES,
    INBOUND_AGENT_NAME,
    OUTBOUND_AGENT_NAME,
    inbound_agent_definition,
    outbound_agent_definition,
)
from api.services.platform.settings import PlatformSettings, get_platform_settings

_ACCOUNT_KEY = OrganizationConfigurationKey.PLATFORM_ACCOUNT.value
_LEASE_KEY = OrganizationConfigurationKey.PLATFORM_ACCOUNT_BOOTSTRAP.value
_LEASE_STALE_AFTER = timedelta(seconds=60)

MODEL_CONFIGURATION_NAME = "Platform default"
TELEPHONY_CONFIGURATION_NAME = "Platform calling"


async def get_platform_account(organization_id: int) -> dict[str, Any]:
    """The organization's recorded managed-setup ids; empty when none yet."""
    value = await db_client.get_configuration_value(organization_id, _ACCOUNT_KEY)
    return dict(value) if isinstance(value, dict) else {}


async def update_platform_account(organization_id: int, **changes: Any) -> dict:
    account = await get_platform_account(organization_id)
    account.update(changes)
    await db_client.upsert_configuration(organization_id, _ACCOUNT_KEY, account)
    return account


def _is_complete(account: dict[str, Any]) -> bool:
    return all(
        account.get(key)
        for key in (
            "model_configuration_uuid",
            "telephony_configuration_id",
            "outbound_workflow_id",
            "inbound_workflow_id",
        )
    )


async def ensure_platform_account(organization_id: int) -> bool:
    """Provision whatever the organization is still missing.

    Returns True when the account is set up. A caller ID or a phone number is
    a later step and is not part of this.
    Never raises: the caller is an authenticated user whatever happens here.
    """
    settings = get_platform_settings()
    try:
        account = await get_platform_account(organization_id)
        if _is_complete(account):
            return True
        if settings.missing:
            logger.error(
                "Platform mode is on but {} is not set; cannot provision "
                "organization {}",
                ", ".join(settings.missing),
                organization_id,
            )
            return False

        owner_token = await db_client.claim_configuration_lease(
            organization_id, _LEASE_KEY, _LEASE_STALE_AFTER
        )
        if owner_token is None:
            return False
        try:
            account = await _provision(organization_id, settings)
        finally:
            # State, not the lease, records completion; drop the lease so an
            # incomplete account retries next time.
            await db_client.release_configuration_lease(
                organization_id, _LEASE_KEY, owner_token
            )
        return _is_complete(account)
    except Exception:
        logger.opt(exception=True).warning(
            "Failed to provision platform account for organization {}; will "
            "retry on a later request",
            organization_id,
        )
        return False


async def _provision(organization_id: int, settings: PlatformSettings) -> dict:
    account = await get_platform_account(organization_id)

    if not account.get("model_configuration_uuid"):
        uuid = await _provision_models(organization_id, settings)
        account = await update_platform_account(
            organization_id, model_configuration_uuid=uuid
        )

    if not account.get("telephony_configuration_id"):
        subaccount_sid, subaccount_token = await twilio_accounts.create_subaccount(
            f"platform-org-{organization_id}"
        )
        row = await db_client.create_telephony_configuration(
            organization_id=organization_id,
            name=TELEPHONY_CONFIGURATION_NAME,
            provider="twilio",
            credentials={
                "account_sid": subaccount_sid,
                "auth_token": subaccount_token,
            },
            is_default_outbound=True,
        )
        account = await update_platform_account(
            organization_id,
            telephony_configuration_id=row.id,
            twilio_subaccount_sid=subaccount_sid,
        )

    if not (account.get("outbound_workflow_id") and account.get("inbound_workflow_id")):
        owner_id = await db_client.get_platform_owner_user_id(organization_id)
        if owner_id is None:
            raise RuntimeError(f"Organization {organization_id} has no owner user")
        if not account.get("outbound_workflow_id"):
            workflow = await _create_agent(
                OUTBOUND_AGENT_NAME,
                outbound_agent_definition(),
                owner_id,
                organization_id,
                settings,
            )
            account = await update_platform_account(
                organization_id, outbound_workflow_id=workflow.id
            )
        if not account.get("inbound_workflow_id"):
            workflow = await _create_agent(
                INBOUND_AGENT_NAME,
                inbound_agent_definition(
                    DEFAULT_INBOUND_RULES, principal_name="", greeting=None
                ),
                owner_id,
                organization_id,
                settings,
            )
            account = await update_platform_account(
                organization_id, inbound_workflow_id=workflow.id
            )

    return account


async def _provision_models(organization_id: int, settings: PlatformSettings) -> str:
    openai = await db_client.create_provider_connection(
        organization_id,
        name="Platform OpenAI",
        provider="openai",
        credentials={"api_key": settings.openai_api_key},
        connection_settings={},
    )
    deepgram = await db_client.create_provider_connection(
        organization_id,
        name="Platform Deepgram",
        provider="deepgram",
        credentials={"api_key": settings.deepgram_api_key},
        connection_settings={},
    )

    def _on(connection, **model_settings) -> dict:
        return {
            "provider_connection_uuid": str(connection.uuid),
            "settings": model_settings,
        }

    if settings.xai_api_key:
        xai = await db_client.create_provider_connection(
            organization_id,
            name="Platform xAI",
            provider="xai",
            credentials={"api_key": settings.xai_api_key},
            connection_settings={},
        )
        # "auto" lets one voice answer in the language the other party speaks.
        tts = _on(xai, voice=settings.tts_voice or "eve", language="auto")
    else:
        tts = _on(deepgram)

    configuration = await db_client.create_named_model_configuration(
        organization_id,
        name=MODEL_CONFIGURATION_NAME,
        configuration={
            "version": 3,
            "mode": "pipeline",
            "llm": _on(openai),
            "stt": _on(deepgram, model=settings.stt_model, language="multi"),
            "tts": tts,
            "embeddings": _on(openai),
        },
    )
    await db_client.set_default_named_model_configuration(
        organization_id, configuration.uuid
    )
    return str(configuration.uuid)


async def _create_agent(
    name: str,
    definition: dict,
    owner_id: int,
    organization_id: int,
    settings: PlatformSettings,
):
    workflow = await db_client.create_workflow(
        name, definition, owner_id, organization_id
    )
    # The per-call ceiling is a cost control the tenant cannot raise.
    await db_client.save_workflow_draft(
        workflow.id,
        workflow_definition=definition,
        workflow_configurations={"max_call_duration": settings.max_call_seconds},
    )
    await db_client.publish_workflow_draft(
        workflow.id, change_description="Platform defaults"
    )
    return workflow
