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
from api.services.platform import twilio_accounts
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
        caller_id_pending={"phone_number": phone_number, "started_at": now.isoformat()},
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


async def refresh(organization_id: int, account: dict[str, Any]) -> dict[str, Any]:
    """Complete a pending verification when Twilio reports it passed.

    Twilio, not the client, is the source of truth: the number becomes the
    caller ID only when the organization's own subaccount lists it.
    """
    pending = account.get("caller_id_pending")
    if not pending:
        return account
    phone_number = pending["phone_number"]
    try:
        caller_id_sid = await twilio_accounts.find_caller_id(
            account["twilio_subaccount_sid"], phone_number
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
