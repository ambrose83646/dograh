"""Account endpoints for the shared calling platform (platform mode only)."""

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field

from api.constants import ENABLE_SIGNUP
from api.db.models import UserModel
from api.services.auth.depends import get_user_with_selected_organization
from api.services.platform import calls, operator
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


@router.post(
    "/operator/accounts/{organization_id}/release-number",
    dependencies=[Depends(_require_operator)],
)
async def release_account_number(organization_id: int) -> dict:
    return await operator.release_account_number(organization_id)
