"""Accounts that came from an OAuth consent: join them or remove them.

An "Allow" on the consent page makes a new account before the person proves
a phone. Two things follow:

* A person who has an account already gets a second one. When they prove
  the phone of the first account, the assistant's tokens move to the first
  account and the new account is closed. The phone check is the proof that
  the two accounts are one person.
* A person who never proves a phone leaves an account and a Twilio
  subaccount that nobody uses. The clean-up closes them.
"""

from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import HTTPException
from loguru import logger

from api.db import db_client
from api.services.platform import operator
from api.services.platform.allowance import get_allowance_status
from api.services.platform.oauth import ACCOUNT_PREFIX
from api.services.platform.provisioning import (
    ensure_platform_account,
    get_platform_account,
    update_platform_account,
)

# A phone check that started less than this long ago can still pass.
_CHECK_WINDOW = timedelta(minutes=10)


async def is_new_oauth_account(organization_id: int, account: dict[str, Any]) -> bool:
    """True for an account from a consent that has no caller ID yet."""
    if account.get("caller_id"):
        return False
    owner_id = await db_client.get_platform_owner_user_id(organization_id)
    owner = await db_client.get_user_by_id(owner_id) if owner_id else None
    return bool(owner and owner.provider_id.startswith(ACCOUNT_PREFIX))


async def proof_subaccount(target_organization_id: int) -> str | None:
    """Where the phone check runs for a join to this account.

    Returns the Twilio subaccount of the target when the target has no caller
    ID: the check then gives the target its caller ID, and the person gets one
    phone call, not two. Returns None when the check must run in the new
    account as proof only.
    """
    await ensure_platform_account(target_organization_id)
    target = await get_platform_account(target_organization_id)
    if target.get("closed") or target.get("suspended"):
        raise HTTPException(
            status_code=403,
            detail=(
                "The account of this phone number is closed. Tell the user to "
                "contact DanaDial support."
            ),
        )
    if target.get("caller_id"):
        return None
    if not target.get("twilio_subaccount_sid"):
        raise HTTPException(
            status_code=503,
            detail="This account is still being set up. Try again in a minute.",
        )
    return target["twilio_subaccount_sid"]


async def join(organization_id: int, target_organization_id: int) -> dict[str, Any]:
    """Move the assistant's tokens to the target account; close this account.

    The caller has confirmed with Twilio that the person holds the phone of
    the target account.
    """
    user_id = await db_client.get_platform_owner_user_id(organization_id)
    target_user_id = await db_client.get_platform_owner_user_id(target_organization_id)
    if user_id is None or target_user_id is None:
        raise RuntimeError(
            f"Cannot join organization {organization_id} to "
            f"{target_organization_id}: an owner is missing"
        )
    moved = await db_client.move_platform_oauth_tokens(user_id, target_user_id)
    account = await update_platform_account(
        organization_id, joined_to=target_organization_id, caller_id_pending=None
    )
    logger.info(
        "OAuth account {} joined account {} ({} tokens moved)",
        organization_id,
        target_organization_id,
        moved,
    )
    await _retire(organization_id, user_id, account)
    return account


async def _retire(
    organization_id: int | None, user_id: int, account: dict[str, Any]
) -> bool:
    """Close the Twilio subaccount and take the user out of the OAuth list.

    When Twilio fails, the user stays in the list and the clean-up tries again.
    """
    if organization_id and account and not account.get("closed"):
        try:
            await operator.close_account(organization_id)
        except Exception:
            logger.opt(exception=True).warning(
                "OAuth account {} was not closed; the clean-up will try again",
                organization_id,
            )
            return False
    await db_client.retire_platform_oauth_user(user_id)
    return True


async def clean_up(older_than: timedelta) -> dict[str, Any]:
    """Close OAuth accounts that joined an account or never proved a phone."""
    now = datetime.now(UTC)
    removed: list[int] = []
    for user in await db_client.list_platform_oauth_users():
        organization_id = user.selected_organization_id
        account = await get_platform_account(organization_id) if organization_id else {}
        if not account.get("joined_to"):
            if account.get("caller_id") or user.created_at > now - older_than:
                continue
            pending = account.get("caller_id_pending")
            if pending and (
                now - datetime.fromisoformat(pending["started_at"]) < _CHECK_WINDOW
            ):
                continue
            if account and (await get_allowance_status(organization_id)).plan_name:
                # Paid for, so a person uses it. Never remove it here.
                continue
            await db_client.delete_platform_oauth_tokens_of_user(user.id)
        if await _retire(organization_id, user.id, account):
            removed.append(organization_id or 0)
    if removed:
        logger.info("OAuth clean-up closed accounts {}", removed)
    return {"removed": len(removed), "organization_ids": removed}
