"""Which numbers a platform account may dial.

The operator pays for every call, so the destination is policy, not user
preference. Applied on every outbound path through ``start_outbound_call``.
"""

import re

from fastapi import HTTPException

from api.services.platform.settings import get_platform_settings

_E164 = re.compile(r"^\+[1-9]\d{7,14}$")
_NANP = re.compile(r"^\+1[2-9]\d{2}[2-9]\d{6}$")
# "+1" is shared by the US, Canada, and about 20 other countries. Calls to
# those and to premium-rate codes cost far more than a domestic call, and are
# the usual target of toll fraud, so "+1" here means the US and Canada only.
_NANP_BLOCKED_AREA_CODES = frozenset(
    {
        "242", "246", "264", "268", "284", "345", "441", "473", "649", "658",
        "664", "721", "758", "767", "784", "809", "829", "849", "868", "869",
        "876",  # Caribbean countries and Bermuda
        "900", "976",  # premium rate
    }
)  # fmt: skip


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
    if phone_number.startswith("+1") and (
        not _NANP.match(phone_number) or phone_number[2:5] in _NANP_BLOCKED_AREA_CODES
    ):
        raise HTTPException(
            status_code=403,
            detail=(
                "This service calls numbers in the United States and Canada "
                "only. This number is not a valid number there, or it is in a "
                "different country or a premium-rate range."
            ),
        )
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
    # After the country rules: a number the service never calls gets the
    # lasting reason, not the reason of the test period.
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
