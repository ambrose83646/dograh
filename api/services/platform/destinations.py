"""Which numbers a platform account may dial.

The operator pays for every call, so the destination is policy, not user
preference. Applied on every outbound path through ``start_outbound_call``.
"""

import re

from api.services.platform.settings import get_platform_settings
from fastapi import HTTPException

_E164 = re.compile(r"^\+[1-9]\d{7,14}$")


def assert_destination_allowed(phone_number: str) -> None:
    settings = get_platform_settings()
    if not settings.enabled:
        return
    if not _E164.match(phone_number):
        raise HTTPException(
            status_code=400,
            detail=(
                "Give the phone number in international format: a plus sign, "
                "the country code, then the number, with no spaces. "
                "Example: +14155550123."
            ),
        )
    if settings.destination_allowlist:
        permitted = set(settings.destination_allowlist) | set(settings.number_pool)
        if phone_number not in permitted:
            raise HTTPException(
                status_code=403,
                detail=(
                    "This service is in a test period and can call approved "
                    "test numbers only."
                ),
            )
        return
    if settings.allowed_prefixes and not phone_number.startswith(
        settings.allowed_prefixes
    ):
        raise HTTPException(
            status_code=403,
            detail=(
                "Calls to this country are not available. Allowed prefixes: "
                + ", ".join(settings.allowed_prefixes)
                + "."
            ),
        )
