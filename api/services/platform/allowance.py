"""Call allowance and abuse limits for platform accounts.

An account starts with free minutes that never renew. A monthly plan, set by
the operator's billing system, gives minutes for one period; only calls that
started in the period count against it. Prepaid packs add minutes that are
used after the plan minutes and stay until they are used (``packs.py``). When the period is over and no new
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
    # Plan (or free) seconds plus pack seconds.
    allowed_seconds: int
    used_seconds: int
    calls_last_24h: int
    daily_call_limit: int
    plan_name: str | None = None
    period_end: datetime | None = None
    # Prepaid pack seconds in ``allowed_seconds``; they are used last.
    pack_seconds: int = 0
    # Packs that the billing system may add automatically in this period.
    pack_limit: int = 0
    packs_added: int = 0

    @property
    def remaining_seconds(self) -> int:
        return max(0, self.allowed_seconds - self.used_seconds)

    @property
    def pack_available(self) -> bool:
        """The billing system can still add a pack in this period."""
        return bool(self.plan_name) and self.packs_added < self.pack_limit

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
        billing_url = get_platform_settings().billing_url
        where = f" at {billing_url}" if billing_url else ""
        if code == ALLOWANCE_EXHAUSTED_CODE:
            return (
                f"The {self.allowed_seconds // 60} free call minutes are used. "
                f"The user must start the monthly plan{where} before this "
                f"account can make or answer more calls."
            )
        if code == PLAN_EXHAUSTED_CODE and self.pack_available:
            return (
                "The call minutes of this account are used. A paid pack of "
                "more minutes is added automatically, and that payment is "
                "not complete. Try again in one minute. If the call is "
                f"refused again, the user must check the payment method{where}."
            )
        if code == PLAN_EXHAUSTED_CODE:
            packs = (
                f"The limit of {self.pack_limit} automatic minute packs for "
                f"this period is also reached. "
                if self.pack_limit
                else ""
            )
            more = (
                f"the user can raise the limit of automatic minute packs{where}"
                if self.pack_limit
                else f"the user can get more minutes{where}"
            )
            return (
                f"The call minutes of the {self.plan_name} plan are used for "
                f"this period. {packs}The minutes renew on "
                f"{self.period_end:%B %-d, %Y}. To call before that date, "
                f"{more}. Until then this account cannot make or answer calls."
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
        if self.pack_available:
            return (
                f"Less than 20% of the call minutes remain: {left}. Tell the "
                f"user that a paid pack of more minutes is added "
                f"automatically when fewer than 5 minutes remain. "
                f"{self.packs_added} of {self.pack_limit} automatic packs are "
                f"used in this period. The price and the limit are on the "
                f"billing page{where}."
            )
        if self.plan_name:
            more = (
                f"the limit of {self.pack_limit} automatic minute packs is "
                f"reached; the user can raise it{where}"
                if self.pack_limit
                else f"the user can get more minutes{where}"
            )
            return (
                f"Less than 20% of the call minutes of this period remain: "
                f"{left}. Tell the user. A call ends when the minutes are "
                f"used. The minutes renew on {self.period_end:%B %-d, %Y}; "
                f"{more}."
            )
        return (
            f"Less than 20% of the free call minutes remain: {left}. Tell the "
            f"user. A call ends when the minutes are used. They do not renew; "
            f"after them the user must start the monthly plan{where}."
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
    pack_seconds = 0
    if plan:
        # Pack minutes need an active plan. Without one they wait.
        pack_seconds = int(account.get("pack_seconds") or 0)
        allowed_seconds = plan["included_seconds"] + pack_seconds
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
        pack_seconds=pack_seconds,
        pack_limit=int(plan.get("pack_limit", 0)) if plan else 0,
        packs_added=int(plan.get("packs_added", 0)) if plan else 0,
    )
