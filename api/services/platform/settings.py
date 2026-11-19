"""Operator configuration for the shared-platform calling service.

Read from the environment on each access so a restart is the only step needed
to change a value. No value here is ever returned to a tenant.
"""

import os
from dataclasses import dataclass


def _csv(name: str) -> tuple[str, ...]:
    return tuple(v.strip() for v in os.getenv(name, "").split(",") if v.strip())


@dataclass(frozen=True)
class PlatformSettings:
    enabled: bool
    twilio_account_sid: str
    twilio_auth_token: str
    # Phone numbers owned by the platform Twilio account. Each organization is
    # assigned at most one; a number is never shared.
    number_pool: tuple[str, ...]
    openai_api_key: str
    deepgram_api_key: str
    free_seconds: int
    max_call_seconds: int
    daily_call_limit: int
    # E.164 prefixes users may dial, e.g. "+1". Empty means no restriction.
    allowed_prefixes: tuple[str, ...]
    # When set, only these exact numbers (plus the platform's own pool) can be
    # dialled. Used before public launch to keep calls to approved test lines.
    destination_allowlist: tuple[str, ...]
    public_mcp_url: str
    # Shared secret for the operator endpoints. Empty closes them.
    operator_token: str

    @property
    def missing(self) -> list[str]:
        required = {
            "PLATFORM_TWILIO_ACCOUNT_SID": self.twilio_account_sid,
            "PLATFORM_TWILIO_AUTH_TOKEN": self.twilio_auth_token,
            "PLATFORM_OPENAI_API_KEY": self.openai_api_key,
            "PLATFORM_DEEPGRAM_API_KEY": self.deepgram_api_key,
        }
        return [name for name, value in required.items() if not value]


def get_platform_settings() -> PlatformSettings:
    from api.constants import BACKEND_API_ENDPOINT

    return PlatformSettings(
        enabled=os.getenv("PLATFORM_MODE", "false").lower() == "true",
        twilio_account_sid=os.getenv("PLATFORM_TWILIO_ACCOUNT_SID", ""),
        twilio_auth_token=os.getenv("PLATFORM_TWILIO_AUTH_TOKEN", ""),
        number_pool=_csv("PLATFORM_TWILIO_NUMBER_POOL"),
        openai_api_key=os.getenv("PLATFORM_OPENAI_API_KEY", ""),
        deepgram_api_key=os.getenv("PLATFORM_DEEPGRAM_API_KEY", ""),
        free_seconds=int(os.getenv("PLATFORM_FREE_SECONDS", "600")),
        max_call_seconds=int(os.getenv("PLATFORM_MAX_CALL_SECONDS", "600")),
        daily_call_limit=int(os.getenv("PLATFORM_DAILY_CALL_LIMIT", "20")),
        allowed_prefixes=_csv("PLATFORM_ALLOWED_PREFIXES"),
        destination_allowlist=_csv("PLATFORM_DESTINATION_ALLOWLIST"),
        public_mcp_url=os.getenv("PLATFORM_PUBLIC_MCP_URL")
        or f"{BACKEND_API_ENDPOINT.rstrip('/')}/mcp",
        operator_token=os.getenv("PLATFORM_OPERATOR_TOKEN", ""),
    )
