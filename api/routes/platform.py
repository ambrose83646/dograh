"""Account endpoints for the shared calling platform (platform mode only)."""

from fastapi import APIRouter, Depends, HTTPException

from api.db.models import UserModel
from api.services.auth.depends import get_user_with_selected_organization
from api.services.platform import calls
from api.services.platform.settings import get_platform_settings

router = APIRouter(prefix="/platform")


def _require_platform_mode() -> None:
    if not get_platform_settings().enabled:
        raise HTTPException(status_code=404, detail="Not found")


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
