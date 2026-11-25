"""OAuth sign-in for assistants, so that a plugin host needs no API key.

A plugin host (Grok Bot, Claude, ChatGPT) registers itself, sends the person
to the consent page of this service, and keeps the tokens. The person selects
"Allow" one time. That creates an account with no phone number: it can do
nothing but start the phone check.

The tokens are random strings. Only their hashes are stored, so a copy of the
database gives no access.
"""

import hashlib
import json
import secrets
import time
from datetime import UTC, datetime, timedelta
from typing import Any

from fastmcp.server.auth.auth import (
    ClientRegistrationOptions,
    OAuthProvider,
    RevocationOptions,
)
from loguru import logger
from mcp.server.auth.provider import (
    AccessToken,
    AuthorizationCode,
    AuthorizationParams,
    RefreshToken,
    TokenError,
    construct_redirect_uri,
)
from mcp.server.auth.routes import build_metadata
from mcp.shared.auth import OAuthClientInformationFull, OAuthToken
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from api.db import db_client
from api.db.models import PlatformOAuthTokenModel, UserModel
from api.services.platform import phone_auth
from api.services.platform.settings import get_platform_settings

ACCESS_PREFIX = "ddo_at_"
REFRESH_PREFIX = "ddo_rt_"
ACCOUNT_PREFIX = "oauth_"

CONSENT_SECONDS = 600
CODE_SECONDS = 300
ACCESS_SECONDS = 3600
REFRESH_SECONDS = 180 * 86400
# A host can lose the answer to a refresh and send the old token again. The
# old token works for this time after its first use, then it ends.
REFRESH_GRACE_SECONDS = 60


def public_base_url() -> str:
    """The public address of this service, without the /mcp path."""
    return get_platform_settings().public_mcp_url.rstrip("/").removesuffix("/mcp")


def resource_metadata_url() -> str:
    return public_base_url() + "/.well-known/oauth-protected-resource/mcp"


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


class TooManyAccounts(Exception):
    """The limit of new accounts was reached."""


async def reset_account_limits() -> int:
    """Operator only: let all addresses make new accounts again."""
    store = phone_auth._store()
    keys = [key async for key in store.scan_iter("oauth:day:*")] + ["oauth:hour"]
    return await store.delete(*keys)


class _Code(AuthorizationCode):
    user_id: int


class _Refresh(RefreshToken):
    row_id: int
    user_id: int
    grant_id: str


async def _issue(
    client_id: str, user_id: int, grant_id: str, scopes: list[str]
) -> OAuthToken:
    access = ACCESS_PREFIX + secrets.token_urlsafe(32)
    refresh = REFRESH_PREFIX + secrets.token_urlsafe(32)
    now = datetime.now(UTC)
    await db_client.add_platform_oauth_tokens(
        [
            PlatformOAuthTokenModel(
                token_hash=_hash(token),
                kind=kind,
                client_id=client_id,
                user_id=user_id,
                grant_id=grant_id,
                scopes=scopes,
                expires_at=now + timedelta(seconds=seconds),
            )
            for token, kind, seconds in (
                (access, "access", ACCESS_SECONDS),
                (refresh, "refresh", REFRESH_SECONDS),
            )
        ]
    )
    return OAuthToken(
        access_token=access,
        token_type="Bearer",
        expires_in=ACCESS_SECONDS,
        refresh_token=refresh,
        scope=" ".join(scopes) or None,
    )


class PlatformOAuthProvider(OAuthProvider):
    def __init__(self) -> None:
        super().__init__(
            base_url=public_base_url(),
            client_registration_options=ClientRegistrationOptions(enabled=True),
            revocation_options=RevocationOptions(enabled=True),
        )

    def get_routes(self, mcp_path: str | None = None) -> list[Route]:
        """The library routes, with a discovery document that tells the truth.

        A plugin host is a public client: it has no secret and proves itself
        with PKCE. The token route accepts that, but the library's document
        does not say so, and a host can refuse to continue.
        """
        metadata = build_metadata(
            self.base_url,
            self.service_documentation_url,
            self.client_registration_options,
            self.revocation_options,
        )
        metadata.token_endpoint_auth_methods_supported.append("none")
        metadata.revocation_endpoint_auth_methods_supported.append("none")
        document = metadata.model_dump(mode="json", exclude_none=True)

        async def discovery(request: Request) -> JSONResponse:
            return JSONResponse(
                document,
                headers={
                    "Cache-Control": "public, max-age=3600",
                    "Access-Control-Allow-Origin": "*",
                },
            )

        async def revoke(request: Request) -> JSONResponse:
            """End all tokens of the consent that this token came from.

            The library's route refuses a client that has no secret, and a
            plugin host has none. Possession of the token is the proof here.
            An unknown token gets the same answer (RFC 7009).
            """
            form = await request.form()
            token = str(form.get("token") or "")
            if not token:
                return JSONResponse({"error": "invalid_request"}, status_code=400)
            for kind in ("refresh", "access"):
                row = await db_client.get_platform_oauth_token(_hash(token), kind)
                if row is not None and row.client_id == form.get("client_id"):
                    await db_client.delete_platform_oauth_grant(row.grant_id)
            return JSONResponse({}, headers={"Cache-Control": "no-store"})

        replaced = {
            "/.well-known/oauth-authorization-server": Route(
                "/.well-known/oauth-authorization-server",
                discovery,
                methods=["GET", "OPTIONS"],
            ),
            "/revoke": Route("/revoke", revoke, methods=["POST"]),
        }
        return [
            replaced.get(getattr(route, "path", ""), route)
            for route in super().get_routes(mcp_path)
        ]

    # --- Clients ---------------------------------------------------------------

    async def get_client(self, client_id: str) -> OAuthClientInformationFull | None:
        info = await db_client.get_platform_oauth_client(client_id)
        return OAuthClientInformationFull.model_validate(info) if info else None

    async def register_client(self, client_info: OAuthClientInformationFull) -> None:
        await db_client.save_platform_oauth_client(
            client_info.client_id, client_info.model_dump(mode="json")
        )

    # --- The person's consent -----------------------------------------------------

    async def authorize(
        self, client: OAuthClientInformationFull, params: AuthorizationParams
    ) -> str:
        """Keep the request and send the person to the consent page."""
        request_id = secrets.token_urlsafe(32)
        await phone_auth._store().set(
            f"oauth:consent:{request_id}",
            json.dumps(
                {
                    "client_id": client.client_id,
                    "client_name": client.client_name or "",
                    "redirect_uri": str(params.redirect_uri),
                    "explicit": params.redirect_uri_provided_explicitly,
                    "scopes": params.scopes or [],
                    "code_challenge": params.code_challenge,
                    "state": params.state,
                    "resource": params.resource,
                }
            ),
            ex=CONSENT_SECONDS,
        )
        return f"{public_base_url()}/oauth/consent?request={request_id}"

    async def consent_request(self, request_id: str) -> dict[str, Any] | None:
        raw = await phone_auth._store().get(f"oauth:consent:{request_id}")
        return json.loads(raw) if raw else None

    async def decide(
        self, request_id: str, allow: bool, client_address: str
    ) -> str | None:
        """Use the consent request one time. Returns where to send the person.

        Each "Allow" makes an account and a Twilio subaccount, and the person
        has not proved who they are. Thus the number of new accounts has a
        limit for each network address and a limit for the full service.
        Raises TooManyAccounts before the consent request is used.
        """
        store = phone_auth._store()
        if allow:
            if not await store.exists(f"oauth:consent:{request_id}"):
                return None
            settings = get_platform_settings()
            if (
                await phone_auth._count(f"oauth:day:{client_address}", 86400)
                > settings.oauth_daily_per_address
            ):
                raise TooManyAccounts
            if (
                await phone_auth._count("oauth:hour", 3600)
                > settings.oauth_hourly_total
            ):
                logger.error(
                    "More than {} new OAuth accounts in one hour. New accounts "
                    "are refused until the hour ends.",
                    settings.oauth_hourly_total,
                )
                raise TooManyAccounts
        raw = await store.getdel(f"oauth:consent:{request_id}")
        if not raw:
            return None
        request = json.loads(raw)
        if not allow:
            return construct_redirect_uri(
                request["redirect_uri"],
                error="access_denied",
                error_description="The person did not allow access.",
                state=request["state"],
            )
        user, _ = await db_client.get_or_create_user_by_provider_id(
            ACCOUNT_PREFIX + secrets.token_hex(12)
        )
        await phone_auth._ensure_organization(user)
        code = secrets.token_urlsafe(32)
        await phone_auth._store().set(
            f"oauth:code:{_hash(code)}",
            json.dumps(
                {
                    "client_id": request["client_id"],
                    "user_id": user.id,
                    "redirect_uri": request["redirect_uri"],
                    "explicit": request["explicit"],
                    "scopes": request["scopes"],
                    "code_challenge": request["code_challenge"],
                    "resource": request["resource"],
                    "expires_at": time.time() + CODE_SECONDS,
                }
            ),
            ex=CODE_SECONDS,
        )
        return construct_redirect_uri(
            request["redirect_uri"], code=code, state=request["state"]
        )

    # --- Code to tokens -------------------------------------------------------------

    async def load_authorization_code(
        self, client: OAuthClientInformationFull, authorization_code: str
    ) -> _Code | None:
        raw = await phone_auth._store().get(f"oauth:code:{_hash(authorization_code)}")
        if not raw:
            return None
        saved = json.loads(raw)
        if saved["client_id"] != client.client_id:
            return None
        return _Code(
            code=authorization_code,
            client_id=saved["client_id"],
            user_id=saved["user_id"],
            redirect_uri=saved["redirect_uri"],
            redirect_uri_provided_explicitly=saved["explicit"],
            scopes=saved["scopes"],
            code_challenge=saved["code_challenge"],
            resource=saved["resource"],
            expires_at=saved["expires_at"],
        )

    async def exchange_authorization_code(
        self, client: OAuthClientInformationFull, authorization_code: _Code
    ) -> OAuthToken:
        # The delete is the one-time gate: two requests with one code race here.
        if not await phone_auth._store().delete(
            f"oauth:code:{_hash(authorization_code.code)}"
        ):
            raise TokenError("invalid_grant", "The code was used already.")
        return await _issue(
            client.client_id,
            authorization_code.user_id,
            secrets.token_hex(16),
            authorization_code.scopes,
        )

    # --- Refresh ----------------------------------------------------------------------

    async def load_refresh_token(
        self, client: OAuthClientInformationFull, refresh_token: str
    ) -> _Refresh | None:
        row = await db_client.get_platform_oauth_token(_hash(refresh_token), "refresh")
        if row is None or row.client_id != client.client_id:
            return None
        return _Refresh(
            token=refresh_token,
            client_id=row.client_id,
            scopes=row.scopes or [],
            expires_at=int(row.expires_at.timestamp()),
            row_id=row.id,
            user_id=row.user_id,
            grant_id=row.grant_id,
        )

    async def exchange_refresh_token(
        self,
        client: OAuthClientInformationFull,
        refresh_token: _Refresh,
        scopes: list[str],
    ) -> OAuthToken:
        if not set(scopes).issubset(refresh_token.scopes):
            raise TokenError("invalid_scope", "The scopes are more than were given.")
        await db_client.end_platform_oauth_token(
            refresh_token.row_id,
            datetime.now(UTC) + timedelta(seconds=REFRESH_GRACE_SECONDS),
        )
        return await _issue(
            client.client_id, refresh_token.user_id, refresh_token.grant_id, scopes
        )

    # --- Use and revoke ------------------------------------------------------------------

    async def load_access_token(self, token: str) -> AccessToken | None:
        row = await db_client.get_platform_oauth_token(_hash(token), "access")
        if row is None:
            return None
        return AccessToken(
            token=token,
            client_id=row.client_id,
            scopes=row.scopes or [],
            expires_at=int(row.expires_at.timestamp()),
        )

    async def revoke_token(self, token: AccessToken | RefreshToken) -> None:
        kind = "refresh" if isinstance(token, RefreshToken) else "access"
        row = await db_client.get_platform_oauth_token(_hash(token.token), kind)
        if row is not None:
            await db_client.delete_platform_oauth_grant(row.grant_id)


async def user_for_access_token(token: str) -> UserModel | None:
    """The account that an access token works for."""
    row = await db_client.get_platform_oauth_token(_hash(token), "access")
    if row is None:
        return None
    return await db_client.get_user_by_id(row.user_id)
