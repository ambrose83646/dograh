"""Operator actions on platform accounts: allowance, inbound number, suspension.

These are the controls the operator needs to run a free service on its own
provider accounts. Tenants never reach them.
"""

import hmac
from datetime import datetime
from typing import Any

from fastapi import HTTPException

from api.db import db_client
from api.services.platform import packs, twilio_accounts
from api.services.platform.allowance import get_allowance_status
from api.services.platform.provisioning import (
    get_platform_account,
    update_platform_account,
)
from api.services.platform.settings import get_platform_settings
from api.services.telephony.factory import get_telephony_provider_by_id
from api.utils.common import get_backend_endpoints


def is_operator_token(token: str) -> bool:
    """True only in platform mode, with a secret configured, and a match."""
    settings = get_platform_settings()
    return bool(
        settings.enabled
        and settings.operator_token
        and hmac.compare_digest(token.encode(), settings.operator_token.encode())
    )


async def _existing_account(organization_id: int) -> dict[str, Any]:
    account = await get_platform_account(organization_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    return account


async def set_account_allowance(
    organization_id: int, free_seconds: int | None
) -> dict[str, Any]:
    """Set one account's allowance in seconds; None returns it to the default."""
    await _existing_account(organization_id)
    await update_platform_account(organization_id, free_seconds=free_seconds)
    return await _allowance_summary(organization_id)


async def set_account_plan(
    organization_id: int,
    name: str,
    included_seconds: int,
    period_start: datetime,
    period_end: datetime,
    pack_limit: int = 0,
) -> dict[str, Any]:
    """Give the account a plan for one paid period.

    The billing system calls this for the first payment and for each renewal.
    Only calls that start in the period count against ``included_seconds``.
    """
    await _existing_account(organization_id)
    await packs.set_plan(
        organization_id, name, included_seconds, period_start, period_end, pack_limit
    )
    return await _allowance_summary(organization_id)


async def add_account_pack(
    organization_id: int, seconds: int, reference: str
) -> dict[str, Any]:
    """Record a pack that the user paid for. ``reference`` names the payment;
    a repeat with the same reference adds nothing."""
    await _existing_account(organization_id)
    added = await packs.add_pack(organization_id, seconds, reference)
    return {**await _allowance_summary(organization_id), "added": added}


async def clear_account_plan(organization_id: int) -> dict[str, Any]:
    """End the account's plan now. The free allowance applies again."""
    await _existing_account(organization_id)
    await packs.clear_plan(organization_id)
    return await _allowance_summary(organization_id)


async def _allowance_summary(organization_id: int) -> dict[str, Any]:
    allowance = await get_allowance_status(organization_id)
    return {
        "organization_id": organization_id,
        "plan": allowance.plan_name,
        "plan_period_end": allowance.period_end,
        "allowed_seconds": allowance.allowed_seconds,
        "used_seconds": allowance.used_seconds,
        "remaining_seconds": allowance.remaining_seconds,
        "pack_seconds": allowance.pack_seconds,
        "pack_limit": allowance.pack_limit,
        "packs_added": allowance.packs_added,
        # The open request to the billing system for a pack, if any.
        "pack_request": (await get_platform_account(organization_id)).get(
            "pack_request"
        ),
    }


async def assign_account_number(organization_id: int) -> dict[str, Any]:
    """Give the account a number for inbound calls from the operator's pool.

    The number moves into the account's Twilio subaccount and is routed to the
    account's inbound agent. Numbers cost money, so only the operator does this.
    """
    account = await _existing_account(organization_id)
    subaccount_sid = account.get("twilio_subaccount_sid")
    if not (subaccount_sid and account.get("inbound_workflow_id")):
        raise HTTPException(status_code=409, detail="Account is not set up yet")
    settings = get_platform_settings()

    if not account.get("phone_number_id"):
        number = await db_client.assign_platform_pool_number(
            organization_id,
            account["telephony_configuration_id"],
            settings.number_pool,
        )
        if number is None:
            raise HTTPException(status_code=409, detail="No free number in the pool")
        account = await update_platform_account(
            organization_id,
            phone_number_id=number.id,
            phone_number=number.address_normalized,
            inbound_routed=False,
            number_in_subaccount=False,
        )

    if not account.get("number_in_subaccount"):
        await twilio_accounts.move_number(
            account["phone_number"],
            from_sid=settings.twilio_account_sid,
            to_sid=subaccount_sid,
        )
        account = await update_platform_account(
            organization_id, number_in_subaccount=True
        )

    if not account.get("inbound_routed"):
        await db_client.set_platform_inbound_workflow(
            organization_id,
            account["phone_number_id"],
            account["inbound_workflow_id"],
        )
        provider = await get_telephony_provider_by_id(
            account["telephony_configuration_id"], organization_id
        )
        backend_endpoint, _ = await get_backend_endpoints()
        result = await provider.configure_inbound(
            account["phone_number"],
            f"{backend_endpoint}/api/v1/telephony/inbound/run",
        )
        if not result.ok:
            raise HTTPException(
                status_code=502,
                detail=f"Could not route {account['phone_number']}: {result.message}",
            )
        account = await update_platform_account(organization_id, inbound_routed=True)

    return {"organization_id": organization_id, "assigned": account["phone_number"]}


async def release_account_number(organization_id: int) -> dict[str, Any]:
    """Return the account's inbound number to the pool.

    The account keeps its call records, rules, and caller ID but no longer
    receives calls.
    """
    account = await _existing_account(organization_id)
    number = account.get("phone_number")
    if number and account.get("number_in_subaccount"):
        await twilio_accounts.move_number(
            number,
            from_sid=account["twilio_subaccount_sid"],
            to_sid=get_platform_settings().twilio_account_sid,
        )
        await update_platform_account(organization_id, number_in_subaccount=False)
    if account.get("phone_number_id"):
        await db_client.release_platform_phone_number(
            organization_id, account["phone_number_id"]
        )
    await update_platform_account(
        organization_id,
        phone_number_id=None,
        phone_number=None,
        inbound_routed=False,
    )
    return {"organization_id": organization_id, "released": number}


async def set_account_suspended(
    organization_id: int, suspended: bool
) -> dict[str, Any]:
    """Suspend or restore one account's Twilio subaccount.

    A suspended subaccount cannot place or receive calls. Other accounts are
    not affected.
    """
    account = await _existing_account(organization_id)
    subaccount_sid = account.get("twilio_subaccount_sid")
    if not subaccount_sid:
        raise HTTPException(status_code=409, detail="Account is not set up yet")
    await twilio_accounts.set_subaccount_status(
        subaccount_sid, "suspended" if suspended else "active"
    )
    await update_platform_account(organization_id, suspended=suspended)
    return {"organization_id": organization_id, "suspended": suspended}


async def close_account(organization_id: int) -> dict[str, Any]:
    """Close the account's Twilio subaccount for good and take back its number.

    Twilio cannot reopen a closed subaccount. The call records stay.
    """
    await release_account_number(organization_id)
    account = await _existing_account(organization_id)
    subaccount_sid = account.get("twilio_subaccount_sid")
    if subaccount_sid and not account.get("closed"):
        await twilio_accounts.set_subaccount_status(subaccount_sid, "closed")
    await db_client.clear_platform_caller_id(organization_id)
    await update_platform_account(
        organization_id,
        closed=True,
        caller_id=None,
        caller_id_sid=None,
        caller_id_phone_number_id=None,
        caller_id_pending=None,
    )
    return {"organization_id": organization_id, "closed": True}
