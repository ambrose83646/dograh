"""Prepaid minute packs: extra minutes that the billing system sells.

The plan gives minutes for one period. When they run low, this service asks
the billing system for a pack; the billing system charges the user and
reports the pack here. Pack minutes are used after the plan minutes and stay
on the account until they are used.

This service never charges anyone. A request is only a signal; the minutes
exist when the billing system reports a payment.
"""

import asyncio
import hashlib
import hmac
import json
import uuid
from datetime import UTC, datetime
from typing import Any

import httpx
from loguru import logger

from api.db import db_client
from api.enums import WorkflowRunState
from api.services.platform.allowance import (
    AllowanceStatus,
    active_plan,
    get_allowance_status,
)
from api.services.platform.provisioning import (
    get_platform_account,
    update_platform_account,
)
from api.services.platform.settings import get_platform_settings

# Ask for a pack below this, so that a call is not cut off.
REQUEST_BELOW_SECONDS = 300
# A request with no pack after this time is sent again at the next occasion.
REQUEST_RETRY_SECONDS = 600
SIGNATURE_HEADER = "X-Platform-Signature"
_REMEMBERED_REFERENCES = 100

# Account changes are read-modify-write. The service runs one web worker.
_locks: dict[int, asyncio.Lock] = {}


def _lock(organization_id: int) -> asyncio.Lock:
    return _locks.setdefault(organization_id, asyncio.Lock())


async def settled_pack_seconds(organization_id: int, account: dict) -> int:
    """The pack minutes left when the account's recorded plan period closes.

    Calls above the plan minutes of that period were made on pack minutes.
    """
    balance = int(account.get("pack_seconds") or 0)
    plan = account.get("plan")
    if not balance or not isinstance(plan, dict):
        return balance
    used = await db_client.get_platform_call_seconds(
        organization_id,
        since=datetime.fromisoformat(plan["period_start"]),
        until=datetime.fromisoformat(plan["period_end"]),
    )
    over = max(0, int(round(used)) - int(plan["included_seconds"]))
    return max(0, balance - over)


async def set_plan(
    organization_id: int,
    name: str,
    included_seconds: int,
    period_start: datetime,
    period_end: datetime,
    pack_limit: int,
) -> None:
    async with _lock(organization_id):
        account = await get_platform_account(organization_id)
        old = account.get("plan") if isinstance(account.get("plan"), dict) else None
        same_period = bool(
            old and datetime.fromisoformat(old["period_start"]) == period_start
        )
        changes: dict[str, Any] = {}
        if not same_period:
            changes["pack_seconds"] = await settled_pack_seconds(
                organization_id, account
            )
        await update_platform_account(
            organization_id,
            plan={
                "name": name,
                "included_seconds": included_seconds,
                "period_start": period_start.isoformat(),
                "period_end": period_end.isoformat(),
                "pack_limit": pack_limit,
                # A repeat for the same period must not give more packs.
                "packs_added": old.get("packs_added", 0) if same_period else 0,
            },
            **changes,
        )


async def clear_plan(organization_id: int) -> None:
    async with _lock(organization_id):
        account = await get_platform_account(organization_id)
        await update_platform_account(
            organization_id,
            plan=None,
            pack_seconds=await settled_pack_seconds(organization_id, account),
        )


async def add_pack(organization_id: int, seconds: int, reference: str) -> bool:
    """Record a paid pack. Returns False when this payment is already recorded."""
    async with _lock(organization_id):
        account = await get_platform_account(organization_id)
        references = list(account.get("pack_references") or [])
        if reference in references:
            return False
        changes: dict[str, Any] = {
            "pack_seconds": int(account.get("pack_seconds") or 0) + seconds,
            "pack_references": (references + [reference])[-_REMEMBERED_REFERENCES:],
            "pack_request": None,
        }
        plan = account.get("plan")
        if isinstance(plan, dict):
            changes["plan"] = {**plan, "packs_added": plan.get("packs_added", 0) + 1}
        await update_platform_account(organization_id, **changes)
        logger.info(f"Pack of {seconds} s added to organization {organization_id}")
        return True


async def request_pack_if_low(
    organization_id: int,
    allowance: AllowanceStatus | None = None,
    *,
    in_call_seconds: int = 0,
) -> bool:
    """Ask the billing system for a pack when few minutes remain.

    ``in_call_seconds`` is the length so far of a call in progress, which is
    not in the measured usage until the call ends. Returns whether a request
    was sent. Never raises: billing trouble must not break a call.
    """
    try:
        return await _request_pack_if_low(organization_id, allowance, in_call_seconds)
    except Exception as e:
        logger.warning(f"Pack request for organization {organization_id} failed: {e}")
        return False


async def _request_pack_if_low(
    organization_id: int, allowance: AllowanceStatus | None, in_call_seconds: int
) -> bool:
    settings = get_platform_settings()
    if allowance is None:
        allowance = await get_allowance_status(organization_id)
    if not allowance.pack_available:
        return False
    remaining = allowance.remaining_seconds - in_call_seconds
    if remaining >= REQUEST_BELOW_SECONDS:
        return False
    now = datetime.now(UTC)
    async with _lock(organization_id):
        account = await get_platform_account(organization_id)
        plan = active_plan(account)
        if not plan or plan.get("packs_added", 0) >= plan.get("pack_limit", 0):
            return False
        pending = account.get("pack_request")
        if (
            isinstance(pending, dict)
            and pending.get("after_packs") == plan.get("packs_added", 0)
            and pending.get("period_start") == plan["period_start"].isoformat()
            and (now - datetime.fromisoformat(pending["requested_at"])).total_seconds()
            < REQUEST_RETRY_SECONDS
        ):
            return False
        request = {
            # The same id for each repeat of one request: the billing system
            # must charge one time for one id.
            "id": (
                pending["id"]
                if isinstance(pending, dict)
                and pending.get("after_packs") == plan.get("packs_added", 0)
                and pending.get("period_start") == plan["period_start"].isoformat()
                else uuid.uuid4().hex
            ),
            "requested_at": now.isoformat(),
            "after_packs": plan.get("packs_added", 0),
            "period_start": plan["period_start"].isoformat(),
            "delivered": False,
        }
        await update_platform_account(organization_id, pack_request=request)
    if not settings.billing_webhook_url:
        return False
    body = json.dumps(
        {
            "event": "pack_needed",
            "request_id": request["id"],
            "organization_id": organization_id,
            "remaining_seconds": max(0, remaining),
            "packs_added_this_period": request["after_packs"],
            "pack_limit": plan.get("pack_limit", 0),
            "period_start": request["period_start"],
        }
    ).encode()
    signature = hmac.new(
        settings.billing_webhook_secret.encode(), body, hashlib.sha256
    ).hexdigest()
    async with httpx.AsyncClient(timeout=10) as http:
        response = await http.post(
            settings.billing_webhook_url,
            content=body,
            headers={
                "Content-Type": "application/json",
                SIGNATURE_HEADER: f"sha256={signature}",
            },
        )
    if response.status_code >= 300:
        # Not delivered: forget the time, so that the next occasion sends again.
        async with _lock(organization_id):
            await update_platform_account(
                organization_id,
                pack_request={
                    **request,
                    "requested_at": datetime.fromtimestamp(0, UTC).isoformat(),
                },
            )
        raise RuntimeError(f"billing system answered HTTP {response.status_code}")
    async with _lock(organization_id):
        account = await get_platform_account(organization_id)
        current = account.get("pack_request")
        if isinstance(current, dict) and current.get("id") == request["id"]:
            await update_platform_account(
                organization_id, pack_request={**current, "delivered": True}
            )
    logger.info(f"Pack requested for organization {organization_id}")
    return True


async def watch_call(organization_id: int, workflow_run_id: int, delay: int) -> None:
    """During a call, ask for a pack at the moment the minutes become low."""
    try:
        await asyncio.sleep(delay)
        run = await db_client.get_workflow_run_by_id(workflow_run_id)
        running = run is not None and run.state == WorkflowRunState.RUNNING.value
        await request_pack_if_low(
            organization_id, in_call_seconds=delay if running else 0
        )
    except Exception as e:
        logger.warning(f"Pack watch for run {workflow_run_id} failed: {e}")
