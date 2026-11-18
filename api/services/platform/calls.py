"""What a platform account can do: place a call, read results, set inbound rules.

The MCP tools and the account REST route are thin wrappers over this module.
Every function takes the caller's ``organization_id`` and reads or writes only
through it; ids that arrive from a client are never trusted on their own.
"""

from typing import Any

from api.db import db_client
from api.services.platform.agent_definitions import (
    DEFAULT_INBOUND_RULES,
    inbound_agent_definition,
    inbound_rules_from_definition,
)
from api.services.platform.allowance import get_allowance_status
from api.services.platform.destinations import assert_destination_allowed
from api.services.platform.provisioning import (
    ensure_platform_account,
    get_platform_account,
    update_platform_account,
)
from api.services.platform.settings import get_platform_settings
from api.services.workflow_run_artifacts import (
    TranscriptDownloadError,
    download_run_transcript_text,
)
from fastapi import HTTPException
from loguru import logger

MAX_TASK_CHARS = 4000
MAX_BACKGROUND_CHARS = 6000
MAX_RULES_CHARS = 6000
MAX_NAME_CHARS = 120
MAX_GREETING_CHARS = 300


async def _ready_account(organization_id: int) -> dict[str, Any]:
    account = await get_platform_account(organization_id)
    if not account.get("outbound_workflow_id") or not account.get(
        "inbound_workflow_id"
    ):
        await ensure_platform_account(organization_id)
        account = await get_platform_account(organization_id)
    if not account.get("outbound_workflow_id") or not account.get(
        "inbound_workflow_id"
    ):
        raise HTTPException(
            status_code=503,
            detail="This account is still being set up. Try again in a minute.",
        )
    return account


async def get_account_status(organization_id: int) -> dict[str, Any]:
    account = await _ready_account(organization_id)
    allowance = await get_allowance_status(organization_id)
    settings = get_platform_settings()
    phone_number = account.get("phone_number")
    return {
        "phone_number": phone_number,
        "phone_number_status": (
            "ready"
            if phone_number and account.get("inbound_routed")
            else "No phone number is available yet. Outbound and inbound calls "
            "start to work when the operator adds numbers."
        ),
        "free_minutes_total": round(allowance.free_seconds / 60, 1),
        "free_minutes_used": round(allowance.used_seconds / 60, 1),
        "free_minutes_remaining": round(allowance.remaining_seconds / 60, 1),
        "calls_in_last_24_hours": allowance.calls_last_24h,
        "daily_call_limit": allowance.daily_call_limit,
        "max_call_minutes": round(settings.max_call_seconds / 60, 1),
        "can_call": allowance.blocked_code is None and bool(phone_number),
        "blocked_reason": allowance.blocked_message,
        "test_period": bool(settings.destination_allowlist),
    }


async def place_call(
    organization_id: int,
    *,
    phone_number: str,
    task: str,
    background: str | None = None,
    on_behalf_of: str | None = None,
    api_key_id: int | None = None,
    api_key_created_by: int | None = None,
) -> dict[str, Any]:
    task = (task or "").strip()
    if not task:
        raise HTTPException(status_code=400, detail="Give a task for the call.")
    if len(task) > MAX_TASK_CHARS:
        raise HTTPException(
            status_code=400,
            detail=f"The task is too long. The limit is {MAX_TASK_CHARS} characters.",
        )
    if background and len(background) > MAX_BACKGROUND_CHARS:
        raise HTTPException(
            status_code=400,
            detail=(
                f"The background is too long. The limit is "
                f"{MAX_BACKGROUND_CHARS} characters."
            ),
        )
    phone_number = (phone_number or "").strip()
    assert_destination_allowed(phone_number)

    account = await _ready_account(organization_id)
    if not account.get("phone_number_id"):
        raise HTTPException(
            status_code=503,
            detail=(
                "This account has no phone number yet, so it cannot place "
                "calls. The operator must add numbers."
            ),
        )
    if phone_number == account.get("phone_number"):
        raise HTTPException(
            status_code=400, detail="An account cannot call its own number."
        )

    # Checked again inside start_outbound_call; this early check refuses
    # without leaving a failed call record behind.
    allowance = await get_allowance_status(organization_id)
    if allowance.blocked_code is not None:
        raise HTTPException(status_code=402, detail=allowance.blocked_message)

    workflow = await db_client.get_workflow(
        account["outbound_workflow_id"], organization_id=organization_id
    )
    if workflow is None:
        raise HTTPException(status_code=503, detail="Calling is not set up yet.")

    context = {
        "task": task,
        "platform_call": True,
    }
    if background and background.strip():
        context["background"] = background.strip()
    if on_behalf_of and on_behalf_of.strip():
        context["principal_name"] = on_behalf_of.strip()[:MAX_NAME_CHARS]

    # The public agent route owns Dograh's one outbound dial path (concurrency
    # slot, quota, provider call). It is reused as-is so platform calls cannot
    # drift from it; the import is local because routes sit above services.
    from api.routes.public_agent import (
        ResolvedAgentTarget,
        TriggerCallRequest,
        _execute_resolved_target,
    )

    response = await _execute_resolved_target(
        ResolvedAgentTarget(
            workflow=workflow,
            organization_id=organization_id,
            identifier_type="workflow_uuid",
            identifier_value=workflow.workflow_uuid,
        ),
        TriggerCallRequest(
            phone_number=phone_number,
            initial_context=context,
            telephony_configuration_id=account["telephony_configuration_id"],
            from_phone_number_id=account["phone_number_id"],
        ),
        use_draft=False,
        api_key_id=api_key_id,
        api_key_created_by=api_key_created_by,
    )
    return {
        "call_id": response.workflow_run_id,
        "status": "ringing",
        "to": phone_number,
        "from": account.get("phone_number"),
        "next_step": (
            "The call is in progress. Call get_call_result with this call_id "
            "after about 30 seconds, and again until status is 'completed'."
        ),
    }


def _direction(run, account: dict[str, Any]) -> str:
    if run.workflow_id == account.get("inbound_workflow_id"):
        return "inbound"
    return "outbound"


def _summarize(run, account: dict[str, Any]) -> dict[str, Any]:
    initial = run.initial_context or {}
    gathered = run.gathered_context or {}
    usage = run.usage_info or {}
    direction = _direction(run, account)
    error = gathered.get("error") or (run.annotations or {}).get("error")
    if run.is_completed:
        status = (
            "failed"
            if error and not usage.get("call_duration_seconds")
            else ("completed")
        )
    elif run.state == "running":
        status = "in_progress"
    else:
        status = "ringing"
    summary = {
        "call_id": run.id,
        "direction": direction,
        "status": status,
        "started_at": run.created_at.isoformat() if run.created_at else None,
        "duration_seconds": round(float(usage.get("call_duration_seconds") or 0)),
        "to": initial.get("called_number"),
        "from": initial.get("caller_number"),
        "disposition": gathered.get("mapped_call_disposition")
        or gathered.get("call_disposition"),
    }
    if direction == "outbound":
        summary["task"] = initial.get("task")
    if error:
        summary["error"] = str(error)
    return summary


async def get_call_result(organization_id: int, call_id: int) -> dict[str, Any]:
    account = await _ready_account(organization_id)
    run = await db_client.get_workflow_run(
        run_id=call_id, organization_id=organization_id
    )
    if run is None:
        # Same answer for "does not exist" and "belongs to someone else".
        raise HTTPException(status_code=404, detail=f"Call {call_id} not found")

    result = _summarize(run, account)
    result["result"] = (run.gathered_context or {}).get("extracted_variables") or {}
    result["transcript"] = ""
    if run.transcript_url:
        try:
            result["transcript"] = await download_run_transcript_text(
                transcript_url=run.transcript_url,
                storage_backend=run.storage_backend,
            )
        except (TranscriptDownloadError, ValueError) as exc:
            logger.warning(f"Transcript for call {call_id} could not be read: {exc}")
            result["transcript_error"] = (
                "The transcript exists but could not be read. Try again."
            )
    if result["status"] in ("ringing", "in_progress"):
        result["next_step"] = "The call has not ended. Ask again in 20 seconds."
    elif not result["transcript"] and "transcript_error" not in result:
        result["next_step"] = (
            "The call ended. If it was answered, the transcript appears within "
            "a minute; ask again once."
        )
    return result


async def list_calls(organization_id: int, limit: int = 20) -> list[dict[str, Any]]:
    account = await _ready_account(organization_id)
    runs = await db_client.list_platform_calls(
        organization_id, limit=max(1, min(limit, 50))
    )
    return [_summarize(run, account) for run in runs]


async def get_inbound_rules(organization_id: int) -> dict[str, Any]:
    account = await _ready_account(organization_id)
    workflow = await db_client.get_workflow(
        account["inbound_workflow_id"], organization_id=organization_id
    )
    rules = None
    if workflow is not None and workflow.released_definition is not None:
        rules = inbound_rules_from_definition(
            workflow.released_definition.workflow_json
        )
    return {
        "phone_number": account.get("phone_number"),
        "rules": rules if rules is not None else DEFAULT_INBOUND_RULES,
        "answer_as": account.get("inbound_answer_as") or "",
        "greeting": account.get("inbound_greeting") or "",
        "is_default": not account.get("inbound_rules_saved"),
    }


async def set_inbound_rules(
    organization_id: int,
    *,
    rules: str,
    answer_as: str | None = None,
    greeting: str | None = None,
) -> dict[str, Any]:
    rules = (rules or "").strip()
    if not rules:
        raise HTTPException(status_code=400, detail="Give the rules text.")
    if len(rules) > MAX_RULES_CHARS:
        raise HTTPException(
            status_code=400,
            detail=f"The rules are too long. The limit is {MAX_RULES_CHARS} characters.",
        )
    answer_as = (answer_as or "").strip()[:MAX_NAME_CHARS]
    greeting = (greeting or "").strip()[:MAX_GREETING_CHARS]

    account = await _ready_account(organization_id)
    workflow = await db_client.get_workflow(
        account["inbound_workflow_id"], organization_id=organization_id
    )
    if workflow is None:
        raise HTTPException(status_code=503, detail="Calling is not set up yet.")

    definition = inbound_agent_definition(
        rules, principal_name=answer_as, greeting=greeting or None
    )
    await db_client.save_workflow_draft(
        workflow.id,
        workflow_definition=definition,
        workflow_configurations={
            "max_call_duration": get_platform_settings().max_call_seconds
        },
    )
    await db_client.publish_workflow_draft(
        workflow.id, change_description="Inbound rules updated"
    )
    await update_platform_account(
        organization_id,
        inbound_rules_saved=True,
        inbound_answer_as=answer_as,
        inbound_greeting=greeting,
    )
    return {
        "saved": True,
        "phone_number": account.get("phone_number"),
        "note": (
            "The next call to this number is answered with these rules. No "
            "assistant has to be connected at that time."
            if account.get("phone_number")
            else "The rules are saved. They apply when this account gets a "
            "phone number."
        ),
    }
