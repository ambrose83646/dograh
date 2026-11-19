"""Operator actions on platform accounts: change an allowance, reclaim a number.

These are the controls the operator needs to run a free service on its own
provider accounts. Tenants never reach them.
"""

from typing import Any

from fastapi import HTTPException

from api.db import db_client
from api.services.platform.allowance import get_allowance_status
from api.services.platform.provisioning import (
    get_platform_account,
    update_platform_account,
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
    allowance = await get_allowance_status(organization_id)
    return {
        "organization_id": organization_id,
        "free_seconds": allowance.free_seconds,
        "used_seconds": allowance.used_seconds,
        "remaining_seconds": allowance.remaining_seconds,
    }


async def release_account_number(organization_id: int) -> dict[str, Any]:
    """Return the account's phone number to the pool.

    The account keeps its call records and rules but can no longer place or
    receive calls. ``number_released`` stops provisioning from handing it a
    new number on its next request.
    """
    account = await _existing_account(organization_id)
    number = account.get("phone_number")
    if account.get("phone_number_id"):
        await db_client.release_platform_phone_number(
            organization_id, account["phone_number_id"]
        )
    await update_platform_account(
        organization_id,
        phone_number_id=None,
        phone_number=None,
        inbound_routed=False,
        number_released=True,
    )
    return {"organization_id": organization_id, "released": number}
