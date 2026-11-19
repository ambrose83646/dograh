"""Free call allowance and abuse limits for platform accounts.

Usage is measured, not ledgered: the seconds an organization has used are the
recorded durations of its own runs, so there is no counter that can drift from
what actually happened and nothing a tenant can reset.
"""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from api.db import db_client
from api.services.platform.settings import get_platform_settings

ALLOWANCE_EXHAUSTED_CODE = "free_allowance_used"
DAILY_LIMIT_CODE = "daily_call_limit_reached"


@dataclass(frozen=True)
class AllowanceStatus:
    free_seconds: int
    used_seconds: int
    calls_last_24h: int
    daily_call_limit: int

    @property
    def remaining_seconds(self) -> int:
        return max(0, self.free_seconds - self.used_seconds)

    @property
    def blocked_code(self) -> str | None:
        if self.remaining_seconds <= 0:
            return ALLOWANCE_EXHAUSTED_CODE
        if self.calls_last_24h >= self.daily_call_limit:
            return DAILY_LIMIT_CODE
        return None

    @property
    def blocked_message(self) -> str | None:
        code = self.blocked_code
        if code == ALLOWANCE_EXHAUSTED_CODE:
            return (
                f"The free allowance of {self.free_seconds // 60} call minutes "
                f"is used. No more calls can be made or answered on this account."
            )
        if code == DAILY_LIMIT_CODE:
            return (
                f"This account reached its limit of {self.daily_call_limit} "
                f"calls in 24 hours. Try again later."
            )
        return None


async def get_allowance_status(
    organization_id: int, *, exclude_current_run: bool = False
) -> AllowanceStatus:
    """Measure the organization's usage.

    ``exclude_current_run`` is for the start-of-call check, which runs after
    the run row for that very call exists: that row must not count against the
    daily limit of the call it belongs to.
    """
    settings = get_platform_settings()
    # Local import: provisioning sits above this module's other callers.
    from api.services.platform.provisioning import get_platform_account

    account = await get_platform_account(organization_id)
    # The operator can grant or reduce one account's allowance.
    free_seconds = account.get("free_seconds")
    if not isinstance(free_seconds, int) or free_seconds < 0:
        free_seconds = settings.free_seconds
    used = await db_client.get_platform_call_seconds(organization_id)
    recent = await db_client.count_platform_runs_since(
        organization_id, datetime.now(UTC) - timedelta(hours=24)
    )
    if exclude_current_run:
        recent = max(0, recent - 1)
    return AllowanceStatus(
        free_seconds=free_seconds,
        used_seconds=int(round(used)),
        calls_last_24h=recent,
        daily_call_limit=settings.daily_call_limit,
    )
