"""Sign-in with a phone number and a code sent by text message.

The phone number is the account: one number, one account, for good. That is
what keeps a person from taking the free minutes again with a new account.
Only the operator can release a number.

Each text costs the operator money, so requests are limited for each number
and for each client address, and a code dies after a few wrong guesses.
"""

import hashlib
import hmac
import re
import secrets
from typing import Any

import redis.asyncio as aioredis
from fastapi import HTTPException
from loguru import logger

from api.constants import ENABLE_SIGNUP, OSS_JWT_SECRET, REDIS_URL
from api.db import db_client
from api.db.models import UserModel
from api.services.organization_bootstrap import ensure_organization_bootstrapped
from api.services.platform import twilio_accounts
from api.services.platform.destinations import assert_destination_allowed
from api.services.platform.settings import get_platform_settings
from api.utils.auth import create_jwt_token

CODE_TTL_SECONDS = 600
RESEND_AFTER_SECONDS = 60
MAX_GUESSES = 5
_WRONG_CODE = "The code is wrong or is not valid now. Ask for a new code."

_redis: aioredis.Redis | None = None


def _store() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(REDIS_URL, decode_responses=True)
    return _redis


def normalize_phone(phone_number: str) -> str:
    """Accept the ways people write a US or Canada number; return +1XXXXXXXXXX."""
    raw = (phone_number or "").strip()
    digits = re.sub(r"[\s().-]", "", raw)
    if re.fullmatch(r"\d{10}", digits):
        return "+1" + digits
    if re.fullmatch(r"1\d{10}", digits):
        return "+" + digits
    return digits


def provider_id_for(phone_number: str) -> str:
    return f"phone_{phone_number}"


def _digest(phone_number: str, code: str) -> str:
    return hmac.new(
        OSS_JWT_SECRET.encode(), f"{phone_number}:{code}".encode(), hashlib.sha256
    ).hexdigest()


async def _count(key: str, window_seconds: int) -> int:
    store = _store()
    count = await store.incr(key)
    if count == 1:
        await store.expire(key, window_seconds)
    return count


async def start(phone_number: str, client_address: str, *, operator: bool) -> dict:
    """Send a sign-in code to the phone."""
    phone_number = normalize_phone(phone_number)
    assert_destination_allowed(phone_number)
    settings = get_platform_settings()
    if not settings.sms_from:
        raise HTTPException(status_code=503, detail="Phone sign-in is not set up.")

    user = await db_client.get_platform_phone_user(provider_id_for(phone_number))
    if user is None and not (ENABLE_SIGNUP or operator):
        raise HTTPException(status_code=403, detail="Sign-up is not open yet.")

    store = _store()
    if not await store.set(
        f"otp:wait:{phone_number}", "1", nx=True, ex=RESEND_AFTER_SECONDS
    ):
        raise HTTPException(
            status_code=429, detail="A code was sent a moment ago. Wait one minute."
        )
    if (
        await _count(f"otp:day:{phone_number}", 86400) > settings.otp_daily_per_number
        or await _count(f"otp:hour:{client_address}", 3600)
        > settings.otp_hourly_per_address
    ):
        raise HTTPException(
            status_code=429, detail="Too many codes were requested. Try again later."
        )

    code = f"{secrets.randbelow(10**6):06d}"
    key = f"otp:code:{phone_number}"
    await store.hset(key, mapping={"digest": _digest(phone_number, code), "guesses": 0})
    await store.expire(key, CODE_TTL_SECONDS)
    try:
        await twilio_accounts.send_text(
            phone_number,
            f"Your DanaDial code is {code}. It is valid for 10 minutes. "
            "Do not share it.",
        )
    except twilio_accounts.TwilioAccountError as exc:
        await store.delete(key)
        logger.warning(f"Sign-in text was not sent: {exc}")
        raise HTTPException(
            status_code=502,
            detail="The text message was not sent. Check the number and try again.",
        ) from exc
    return {"status": "sent", "valid_for_seconds": CODE_TTL_SECONDS}


async def verify(phone_number: str, code: str, *, operator: bool) -> dict[str, Any]:
    """Check the code. Sign the phone's account in, or create it."""
    phone_number = normalize_phone(phone_number)
    store = _store()
    key = f"otp:code:{phone_number}"
    if not await store.exists(key):
        raise HTTPException(status_code=401, detail=_WRONG_CODE)
    # Counted before the comparison, so parallel guesses cannot pass the limit.
    if await store.hincrby(key, "guesses", 1) > MAX_GUESSES:
        await store.delete(key)
        raise HTTPException(status_code=401, detail=_WRONG_CODE)
    digest = await store.hget(key, "digest")
    if not digest or not hmac.compare_digest(digest, _digest(phone_number, code)):
        raise HTTPException(status_code=401, detail=_WRONG_CODE)
    await store.delete(key)

    provider_id = provider_id_for(phone_number)
    user = await db_client.get_platform_phone_user(provider_id)
    if user is None:
        if not (ENABLE_SIGNUP or operator):
            raise HTTPException(status_code=403, detail="Sign-up is not open yet.")
        # The unique provider id makes this safe when two requests race.
        user, _ = await db_client.get_or_create_user_by_provider_id(provider_id)
    organization_id = await _ensure_organization(user)
    return {
        "token": create_jwt_token(user.id, ""),
        "user": {
            "id": user.id,
            "email": None,
            "phone_number": phone_number,
            "organization_id": organization_id,
            "provider_id": provider_id,
        },
    }


async def _ensure_organization(user: UserModel) -> int:
    if user.selected_organization_id:
        return user.selected_organization_id
    organization, _ = await db_client.get_or_create_organization_by_provider_id(
        org_provider_id=f"org_{user.provider_id}", user_id=user.id
    )
    await db_client.add_user_to_organization(user.id, organization.id)
    await db_client.update_user_selected_organization(user.id, organization.id)
    await ensure_organization_bootstrapped(organization.id, created_by=user.provider_id)
    return organization.id


async def release(phone_number: str) -> dict[str, Any]:
    """Operator only: unbind the phone so that it can sign up again.

    The old account stays, with its call records, but nobody can sign in to it.
    """
    phone_number = normalize_phone(phone_number)
    released = await db_client.release_platform_phone_identity(
        provider_id_for(phone_number)
    )
    await _store().delete(
        f"otp:code:{phone_number}",
        f"otp:wait:{phone_number}",
        f"otp:day:{phone_number}",
    )
    return {"phone_number": phone_number, "released": released}


def sign_in_phone(user: UserModel) -> str | None:
    prefix = provider_id_for("")
    return user.provider_id[len(prefix) :] if user.provider_id.startswith(prefix) else None
