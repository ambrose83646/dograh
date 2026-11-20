"""Call allowance and abuse limits for platform accounts.

An account starts with free minutes that never renew. A monthly plan, set by
the operator's billing system, gives minutes for one period; only calls that
started in the period count against it. When the period is over and no new
one is set, the account is measured against its free minutes again, which its
earlier calls have normally used.

Usage is measured, not ledgered: the seconds an organization has used are the
recorded durations of its own runs, so there is no counter that can drift from
what actually happened and nothing a tenant can reset.
"""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from api.db import db_client
from api.services.platform.settings import get_platform_settings

ALLOWANCE_EXHAUSTED_CODE = "free_allowance_used"
PLAN_EXHAUSTED_CODE = "plan_allowance_used"
DAILY_LIMIT_CODE = "daily_call_limit_reached"
# The assistant gets a warning below one fifth of the minutes.
LOW_MINUTES_DIVISOR = 5


@dataclass(frozen=True)
class AllowanceStatus:
    allowed_seconds: int
    used_seconds: int
    calls_last_24h: int
    daily_call_limit: int
    plan_name: str | None = None
    period_end: datetime | None = None

    @property
    def remaining_seconds(self) -> int:
        return max(0, self.allowed_seconds - self.used_seconds)

    @property
    def blocked_code(self) -> str | None:
        if self.remaining_seconds <= 0:
            return PLAN_EXHAUSTED_CODE if self.plan_name else ALLOWANCE_EXHAUSTED_CODE
        if self.calls_last_24h >= self.daily_call_limit:
            return DAILY_LIMIT_CODE
        return None

    @property
    def blocked_message(self) -> str | None:
        code = self.blocked_code
        if code == ALLOWANCE_EXHAUSTED_CODE:
            billing_url = get_platform_settings().billing_url
            where = f" at {billing_url}" if billing_url else ""
            return (
                f"The {self.allowed_seconds // 60} free call minutes are used. "
                f"The user must choose a monthly plan{where} before this "
                f"account can make or answer more calls."
            )
        if code == PLAN_EXHAUSTED_CODE:
            billing_url = get_platform_settings().billing_url
            where = f" at {billing_url}" if billing_url else ""
            return (
                f"The {self.allowed_seconds // 60} call minutes of the "
                f"{self.plan_name} plan are used for this period. The minutes "
                f"renew on {self.period_end:%B %-d, %Y}. To call before that "
                f"date, the user can change to a larger plan{where}; the "
                f"larger plan gives its minutes immediately. Until then this "
                f"account cannot make or answer calls."
            )
        if code == DAILY_LIMIT_CODE:
            return (
                f"This account reached its limit of {self.daily_call_limit} "
                f"calls in 24 hours. Try again later."
            )
        return None

    @property
    def low_minutes_note(self) -> str | None:
        """Words for the assistant when under 20% of the minutes remain."""
        if self.remaining_seconds <= 0:
            return None
        if self.remaining_seconds * LOW_MINUTES_DIVISOR >= self.allowed_seconds:
            return None
        billing_url = get_platform_settings().billing_url
        where = f" at {billing_url}" if billing_url else ""
        left = f"{self.remaining_seconds / 60:.1f} of {self.allowed_seconds // 60}"
        if self.plan_name:
            return (
                f"Less than 20% of the call minutes of this period remain: "
                f"{left}. Tell the user. A call ends when the minutes are "
                f"used. The minutes renew on {self.period_end:%B %-d, %Y}; a "
                f"larger plan{where} gives its minutes immediately."
            )
        return (
            f"Less than 20% of the free call minutes remain: {left}. Tell the "
            f"user. A call ends when the minutes are used. They do not renew; "
            f"after them the user must choose a monthly plan{where}."
        )


def active_plan(account: dict[str, Any]) -> dict[str, Any] | None:
    """The account's plan when the current time is inside its period."""
    plan = account.get("plan")
    if not isinstance(plan, dict):
        return None
    start = datetime.fromisoformat(plan["period_start"])
    end = datetime.fromisoformat(plan["period_end"])
    if not start <= datetime.now(UTC) < end:
        return None
    return {**plan, "period_start": start, "period_end": end}


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
    plan = active_plan(account)
    if plan:
        allowed_seconds = plan["included_seconds"]
        used = await db_client.get_platform_call_seconds(
            organization_id, since=plan["period_start"]
        )
    else:
        # The operator can grant or reduce one account's free allowance.
        allowed_seconds = account.get("free_seconds")
        if not isinstance(allowed_seconds, int) or allowed_seconds < 0:
            allowed_seconds = settings.free_seconds
        used = await db_client.get_platform_call_seconds(organization_id)
    recent = await db_client.count_platform_runs_since(
        organization_id, datetime.now(UTC) - timedelta(hours=24)
    )
    if exclude_current_run:
        recent = max(0, recent - 1)
    return AllowanceStatus(
        allowed_seconds=allowed_seconds,
        used_seconds=int(round(used)),
        calls_last_24h=recent,
        daily_call_limit=settings.daily_call_limit,
        plan_name=plan["name"] if plan else None,
        period_end=plan["period_end"] if plan else None,
    )
