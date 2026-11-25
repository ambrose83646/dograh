"""Let a user place calls from a phone number they own.

Twilio's Verified Caller ID: Twilio phones the number, the person keys in a
code, and the user's subaccount may then show that number on outbound calls.
No number is bought. A verified caller ID cannot receive calls through Twilio.
"""

from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import HTTPException
from loguru import logger

from api.db import db_client
from api.services.platform import oauth_accounts, twilio_accounts
from api.services.platform.destinations import assert_destination_allowed
from api.services.platform.provisioning import (
    get_platform_account,
    update_platform_account,
)
from api.services.platform.settings import get_platform_settings

# Twilio keeps a validation call open for about a minute.
_PENDING_FOR = timedelta(minutes=3)


def _recent_attempts(account: dict[str, Any], now: datetime) -> list[str]:
    cutoff = now - timedelta(hours=24)
    return [
        stamp
        for stamp in account.get("caller_id_attempts") or []
        if datetime.fromisoformat(stamp) > cutoff
    ]


async def start_verification(organization_id: int, phone_number: str) -> dict[str, Any]:
    """Make Twilio phone ``phone_number`` and return the code to key in."""
    phone_number = (phone_number or "").strip()
    # A verification is a real phone call to the number, so it follows the
    # same destination rules as any other call.
    assert_destination_allowed(phone_number)

    account = await get_platform_account(organization_id)
    subaccount_sid = account.get("twilio_subaccount_sid")
    if not subaccount_sid:
        raise HTTPException(
            status_code=503,
            detail="This account is still being set up. Try again in a minute.",
        )
    if phone_number == account.get("caller_id"):
        return {
            "status": "verified",
            "phone_number": phone_number,
            "note": "This number is already your caller ID.",
        }
    if phone_number == account.get("phone_number"):
        raise HTTPException(
            status_code=400,
            detail="This is the service number of this account. Give a phone you own.",
        )

    # Another account has this number. A new account from an assistant can
    # join that account when the person passes the check; all others stop here.
    join_to = await db_client.get_platform_number_owner(phone_number, organization_id)
    proof_in_target = False
    if join_to is not None:
        if not await oauth_accounts.is_new_oauth_account(organization_id, account):
            raise HTTPException(
                status_code=409,
                detail=(
                    "This phone number belongs to another account. One phone "
                    "number can be used on one account only."
                ),
            )
        target_sid = await oauth_accounts.proof_subaccount(join_to)
        # A number that Twilio lists there already would pass with no call.
        if target_sid and not await _listed(target_sid, phone_number):
            subaccount_sid, proof_in_target = target_sid, True

    now = datetime.now(UTC)
    attempts = _recent_attempts(account, now)
    limit = get_platform_settings().caller_id_daily_attempts
    if len(attempts) >= limit:
        raise HTTPException(
            status_code=429,
            detail=(
                f"This account started {limit} phone number checks in the last "
                "24 hours. Try again tomorrow."
            ),
        )
    # Recorded before the call so a failed attempt still counts.
    await update_platform_account(
        organization_id, caller_id_attempts=[*attempts, now.isoformat()]
    )

    try:
        code = await twilio_accounts.start_caller_id_validation(
            subaccount_sid, phone_number, f"org-{organization_id}"
        )
    except twilio_accounts.TwilioAccountError as exc:
        logger.warning(
            f"Caller ID validation for organization {organization_id} was refused: {exc}"
        )
        raise HTTPException(
            status_code=400,
            detail=(
                "The phone company did not accept this number for a check. "
                "Make sure it is a number you own that can receive calls."
            ),
        ) from exc

    await update_platform_account(
        organization_id,
        caller_id_pending={
            "phone_number": phone_number,
            "started_at": now.isoformat(),
            **(
                {"join_to": join_to, "proof_in_target": proof_in_target}
                if join_to is not None
                else {}
            ),
        },
    )
    return {
        "status": "calling",
        "phone_number": phone_number,
        "validation_code": code,
        "next_step": (
            f"The phone {phone_number} rings in a few seconds. The person must "
            f"answer and enter the code {code} on the keypad. Then call "
            "get_account_status: caller_id shows the number when the check passed."
        ),
    }


async def _listed(subaccount_sid: str, phone_number: str) -> bool:
    try:
        return (
            await twilio_accounts.find_caller_id(subaccount_sid, phone_number)
            is not None
        )
    except twilio_accounts.TwilioAccountError as exc:
        raise HTTPException(
            status_code=502, detail="The phone company did not answer. Try again."
        ) from exc


async def refresh(organization_id: int, account: dict[str, Any]) -> dict[str, Any]:
    """Complete a pending verification when Twilio reports it passed.

    Twilio, not the client, is the source of truth: the number becomes the
    caller ID only when the subaccount that ran the check lists it. After a
    join, the returned account has ``joined_to``: the organization that the
    caller's tokens work for from now on.
    """
    pending = account.get("caller_id_pending")
    if not pending:
        return account
    phone_number = pending["phone_number"]
    join_to = pending.get("join_to")
    checked_id, checked = organization_id, account
    if join_to is not None and pending.get("proof_in_target"):
        checked_id, checked = join_to, await get_platform_account(join_to)
    try:
        caller_id_sid = await twilio_accounts.find_caller_id(
            checked["twilio_subaccount_sid"], phone_number
        )
    except twilio_accounts.TwilioAccountError as exc:
        logger.warning(f"Caller ID lookup failed for {organization_id}: {exc}")
        return account

    if caller_id_sid is None:
        started = datetime.fromisoformat(pending["started_at"])
        if datetime.now(UTC) - started > _PENDING_FOR:
            return await update_platform_account(
                organization_id, caller_id_pending=None
            )
        return account

    if join_to is None:
        return await _record(organization_id, account, phone_number, caller_id_sid)
    if checked_id == join_to:
        await _record(join_to, checked, phone_number, caller_id_sid)
    return await oauth_accounts.join(organization_id, join_to)


async def _record(
    organization_id: int, account: dict[str, Any], phone_number: str, caller_id_sid: str
) -> dict[str, Any]:
    """Make a number that Twilio verified the caller ID of the account."""
    previous_sid = account.get("caller_id_sid")
    row = await db_client.set_platform_caller_id(
        organization_id, account["telephony_configuration_id"], phone_number
    )
    account = await update_platform_account(
        organization_id,
        caller_id=phone_number,
        caller_id_sid=caller_id_sid,
        caller_id_phone_number_id=row.id,
        caller_id_pending=None,
    )
    if previous_sid and previous_sid != caller_id_sid:
        try:
            await twilio_accounts.delete_caller_id(
                account["twilio_subaccount_sid"], previous_sid
            )
        except twilio_accounts.TwilioAccountError as exc:
            logger.warning(f"Old caller ID {previous_sid} was not removed: {exc}")
    return account
