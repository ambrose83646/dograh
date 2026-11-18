"""Close every Dograh surface a platform tenant must not reach.

Dograh trusts a signed-in user with their own provider keys, campaigns, and
workflow builder. On the shared platform the provider accounts are the
operator's, so a tenant gets only the calling tools. The rule is deny by
default: a new upstream route is closed until it is listed here.
"""

import re

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

_API = "/api/v1"

# (methods or None for any, path pattern). Patterns match the whole path.
_ALLOWED: tuple[tuple[frozenset[str] | None, re.Pattern[str]], ...] = tuple(
    (frozenset(methods) if methods else None, re.compile(pattern))
    for methods, pattern in (
        (None, r"/mcp(/.*)?"),
        ({"GET"}, rf"{_API}/health"),
        (None, rf"{_API}/auth/.*"),
        ({"GET"}, rf"{_API}/user/auth/user"),
        (None, rf"{_API}/user/api-keys(/.*)?"),
        (None, rf"{_API}/platform/.*"),
        # Twilio's own webhooks. They carry no tenant session and are
        # verified by signature inside the handlers.
        ({"POST"}, rf"{_API}/telephony/twiml"),
        ({"POST"}, rf"{_API}/telephony/twilio/status-callback/\d+"),
        ({"GET", "POST"}, rf"{_API}/telephony/inbound/run"),
        ({"POST"}, rf"{_API}/telephony/inbound/fallback"),
    )
)
_ALLOWED_WEBSOCKETS = re.compile(rf"{_API}/telephony/ws/\d+/\d+/\d+(/[^/]+)?")


def is_platform_path_allowed(scope_type: str, method: str, path: str) -> bool:
    if scope_type == "websocket":
        return bool(_ALLOWED_WEBSOCKETS.fullmatch(path))
    if method == "OPTIONS":
        return True
    return any(
        (methods is None or method in methods) and pattern.fullmatch(path)
        for methods, pattern in _ALLOWED
    )


class PlatformSurfaceMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] not in ("http", "websocket") or is_platform_path_allowed(
            scope["type"], scope.get("method", ""), scope["path"]
        ):
            await self.app(scope, receive, send)
            return
        if scope["type"] == "websocket":
            await send({"type": "websocket.close", "code": 1008})
            return
        response = JSONResponse(
            status_code=404,
            content={"detail": "This endpoint is not available on this service."},
        )
        await response(scope, receive, send)
