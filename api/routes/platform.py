"""Account endpoints for the shared calling platform (platform mode only)."""

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import AwareDatetime, BaseModel, Field, model_validator

from api.constants import ENABLE_SIGNUP
from api.db.models import UserModel
from api.services.auth.depends import get_user_with_selected_organization
from api.services.platform import caller_id, calls, operator
from api.services.platform.settings import get_platform_settings

router = APIRouter(prefix="/platform")


def _require_platform_mode() -> None:
    if not get_platform_settings().enabled:
        raise HTTPException(status_code=404, detail="Not found")


@router.get("/info", dependencies=[Depends(_require_platform_mode)])
async def get_service_info() -> dict:
    """Public facts the sign-in page needs. No account data."""
    settings = get_platform_settings()
    return {
        "signup_open": ENABLE_SIGNUP,
        "free_minutes": settings.free_seconds / 60,
        "test_period": bool(settings.destination_allowlist),
        "mcp_url": settings.public_mcp_url,
    }


@router.get("/account", dependencies=[Depends(_require_platform_mode)])
async def get_account(
    user: UserModel = Depends(get_user_with_selected_organization),
) -> dict:
    """The signed-in user's number, allowance, and MCP connection details."""
    status = await calls.get_account_status(user.selected_organization_id)
    status["mcp_url"] = get_platform_settings().public_mcp_url
    return status


class CallerIdRequest(BaseModel):
    phone_number: str = Field(max_length=20)


@router.post("/caller-id", dependencies=[Depends(_require_platform_mode)])
async def start_caller_id_verification(
    request: CallerIdRequest,
    user: UserModel = Depends(get_user_with_selected_organization),
) -> dict:
    """Phone the user's own number with a code so calls can show that number."""
    return await caller_id.start_verification(
        user.selected_organization_id, request.phone_number
    )


@router.get("/calls", dependencies=[Depends(_require_platform_mode)])
async def get_calls(
    limit: int = 20,
    user: UserModel = Depends(get_user_with_selected_organization),
) -> list[dict]:
    return await calls.list_calls(user.selected_organization_id, limit)


@router.get("/calls/{call_id}", dependencies=[Depends(_require_platform_mode)])
async def get_call(
    call_id: int,
    user: UserModel = Depends(get_user_with_selected_organization),
) -> dict:
    return await calls.get_call_result(user.selected_organization_id, call_id)


@router.get("/inbound-rules", dependencies=[Depends(_require_platform_mode)])
async def get_inbound_rules(
    user: UserModel = Depends(get_user_with_selected_organization),
) -> dict:
    return await calls.get_inbound_rules(user.selected_organization_id)


def _require_operator(x_operator_token: str = Header(default="")) -> None:
    """Operator endpoints answer 404 unless the shared secret matches.

    With no secret configured they are closed to everyone.
    """
    if not operator.is_operator_token(x_operator_token):
        raise HTTPException(status_code=404, detail="Not found")


class AllowanceRequest(BaseModel):
    free_seconds: int | None = Field(
        default=None,
        ge=0,
        le=360_000,
        description="Allowance for this account in seconds. Null restores the default.",
    )


@router.put(
    "/operator/accounts/{organization_id}/allowance",
    dependencies=[Depends(_require_operator)],
)
async def set_account_allowance(
    organization_id: int, request: AllowanceRequest
) -> dict:
    return await operator.set_account_allowance(organization_id, request.free_seconds)


class PlanRequest(BaseModel):
    name: str = Field(min_length=1, max_length=60)
    included_seconds: int = Field(ge=0)
    period_start: AwareDatetime
    period_end: AwareDatetime

    @model_validator(mode="after")
    def _period_has_length(self) -> "PlanRequest":
        if self.period_end <= self.period_start:
            raise ValueError("period_end must be after period_start")
        return self


@router.put(
    "/operator/accounts/{organization_id}/plan",
    dependencies=[Depends(_require_operator)],
)
async def set_account_plan(organization_id: int, request: PlanRequest) -> dict:
    """Billing calls this for the first payment and for each renewal."""
    return await operator.set_account_plan(
        organization_id,
        request.name,
        request.included_seconds,
        request.period_start,
        request.period_end,
    )


@router.delete(
    "/operator/accounts/{organization_id}/plan",
    dependencies=[Depends(_require_operator)],
)
async def clear_account_plan(organization_id: int) -> dict:
    return await operator.clear_account_plan(organization_id)


@router.post(
    "/operator/accounts/{organization_id}/release-number",
    dependencies=[Depends(_require_operator)],
)
async def release_account_number(organization_id: int) -> dict:
    return await operator.release_account_number(organization_id)


@router.post(
    "/operator/accounts/{organization_id}/assign-number",
    dependencies=[Depends(_require_operator)],
)
async def assign_account_number(organization_id: int) -> dict:
    return await operator.assign_account_number(organization_id)


class SuspendRequest(BaseModel):
    suspended: bool


@router.put(
    "/operator/accounts/{organization_id}/suspended",
    dependencies=[Depends(_require_operator)],
)
async def set_account_suspended(organization_id: int, request: SuspendRequest) -> dict:
    return await operator.set_account_suspended(organization_id, request.suspended)


@router.post(
    "/operator/accounts/{organization_id}/close",
    dependencies=[Depends(_require_operator)],
)
async def close_account(organization_id: int) -> dict:
    return await operator.close_account(organization_id)
