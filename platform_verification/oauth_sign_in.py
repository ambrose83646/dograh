"""Sign-up through an assistant with OAuth, tested from the outside.

The run does what a plugin host (Grok Bot) does: it has only the MCP address.
It finds the OAuth server, registers itself with an app callback, sends a
person to the consent page, and uses the tokens with a standard MCP client.
It makes no phone calls.

How this can fail (written before the code):

 1. A client with no token gets HTTP 401 with no pointer to the discovery
    document, so it cannot start the sign-in.
 2. `/mcp` answers with a redirect to `/mcp/`. A host that does not follow a
    redirect on POST cannot connect.
 3. The discovery documents give addresses on a different host or with
    `http`, because the service is behind a proxy.
 4. Registration refuses the app callback `cursor://...`.
 5. The service gives a code with no action of the person.
 6. "Cancel" creates an account, or does not tell the client.
 7. The consent step can be used two times.
 8. A callback that the client did not register gets the code.
 9. The consent page shows the client's name as HTML.
10. A code works with a wrong PKCE verifier, or works two times.
11. The token of one person reads the account of a different person.
16. One network address makes accounts with no limit. Each account has a
    Twilio subaccount, so this costs the operator.
17. The limit also stops "Cancel", or a refused "Allow" makes an account.
12. A new account with no phone can place a call, or the refusal does not
    tell the assistant what to do.
13. A refresh does not give a token that works, or the old refresh token
    works for a long time.
14. After a revoke, a token of that authorization still works.
15. A made-up token is accepted, or an API key stops working.
"""

import argparse
import asyncio
import base64
import hashlib
import json
import re
import secrets
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import httpx
from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport

sys.path.insert(0, str(Path(__file__).parent))
from verify import Report

GROK_BOT_CALLBACK = "cursor://anysphere.cursor-mcp/oauth/callback"
EVIL_NAME = "Grok Bot <script>alert(1)</script>"


def pkce() -> tuple[str, str]:
    verifier = secrets.token_urlsafe(48)
    digest = hashlib.sha256(verifier.encode()).digest()
    return verifier, base64.urlsafe_b64encode(digest).rstrip(b"=").decode()


def session(mcp_url: str, token: str) -> Client:
    return Client(
        StreamableHttpTransport(mcp_url, headers={"Authorization": f"Bearer {token}"})
    )


async def tool(mcp_url: str, token: str, name: str, **arguments) -> dict:
    async with session(mcp_url, token) as client:
        result = await client.call_tool(name, arguments, raise_on_error=False)
        text = result.content[0].text if result.content else ""
        if result.is_error:
            return {"refused": text}
        return json.loads(text)


async def connects(mcp_url: str, token: str) -> bool:
    try:
        async with session(mcp_url, token) as client:
            return bool(await client.list_tools())
    except Exception:  # noqa: BLE001
        return False


class Host:
    """The plugin host: one registered client that can authorize people."""

    def __init__(self, http: httpx.AsyncClient, server: dict, callback: str) -> None:
        self.http = http
        self.server = server
        self.callback = callback
        self.client_id = ""

    async def register(self, name: str) -> httpx.Response:
        response = await self.http.post(
            self.server["registration_endpoint"],
            json={
                "client_name": name,
                "redirect_uris": [self.callback],
                "grant_types": ["authorization_code", "refresh_token"],
                "response_types": ["code"],
                "token_endpoint_auth_method": "none",
            },
        )
        if response.status_code in (200, 201):
            self.client_id = response.json()["client_id"]
        return response

    async def start(self, challenge: str, state: str, callback: str | None = None):
        return await self.http.get(
            self.server["authorization_endpoint"],
            params={
                "response_type": "code",
                "client_id": self.client_id,
                "redirect_uri": callback or self.callback,
                "code_challenge": challenge,
                "code_challenge_method": "S256",
                "state": state,
            },
        )

    async def form(self, consent_url: str) -> tuple[str, dict]:
        """What the person's browser gets: the address and fields of the form."""
        page = await self.http.get(consent_url)
        fields = dict(
            re.findall(r'type="hidden" name="(\w+)" value="([^"]*)"', page.text)
        )
        action = re.search(r'<form[^>]* action="([^"]+)"', page.text).group(1)
        return str(httpx.URL(consent_url).join(action)), fields

    async def decide(
        self, consent_url: str, decision: str, form: tuple[str, dict] | None = None
    ) -> httpx.Response:
        action, fields = form or await self.form(consent_url)
        return await self.http.post(action, data={**fields, "decision": decision})

    async def token(self, **form) -> httpx.Response:
        return await self.http.post(
            self.server["token_endpoint"], data={"client_id": self.client_id, **form}
        )

    async def authorize(self) -> dict:
        """One person selects "Allow". Returns the tokens."""
        verifier, challenge = pkce()
        state = secrets.token_urlsafe(8)
        first = await self.start(challenge, state)
        back = await self.decide(first.headers["location"], "allow")
        query = parse_qs(urlsplit(back.headers["location"]).query)
        assert query["state"] == [state], query
        tokens = await self.token(
            grant_type="authorization_code",
            code=query["code"][0],
            redirect_uri=self.callback,
            code_verifier=verifier,
        )
        tokens.raise_for_status()
        return tokens.json()


async def run(args, report: Report) -> None:
    base = args.base_url.rstrip("/")
    mcp_url = base + "/mcp"
    # The operator API is not always open to the internet.
    operator_base = (args.operator_url or base).rstrip("/")
    operator = {"X-Operator-Token": args.operator_token}
    async with httpx.AsyncClient(timeout=30, follow_redirects=False) as http:
        summary_url = operator_base + "/api/v1/platform/operator/oauth/summary"
        reset_url = operator_base + "/api/v1/platform/operator/oauth/reset-limits"
        (await http.post(reset_url, headers=operator)).raise_for_status()

        # --- The host has only the MCP address ---------------------------------
        hello = {
            "jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {"protocolVersion": "2025-06-18", "capabilities": {},
                       "clientInfo": {"name": "host", "version": "1"}},
        }  # fmt: skip
        headers = {"Accept": "application/json, text/event-stream"}
        bare = await http.post(mcp_url, json=hello, headers=headers)
        challenge_header = bare.headers.get("www-authenticate", "")
        pointer = re.search(r'resource_metadata="([^"]+)"', challenge_header)
        report.check(
            "With no token, /mcp answers 401 at once (no redirect) and gives "
            "the address of the discovery document",
            bare.status_code == 401 and pointer is not None,
            f"HTTP {bare.status_code}; WWW-Authenticate: {challenge_header[:160]}",
        )
        resource = (await http.get(pointer.group(1))).json()
        issuer = resource["authorization_servers"][0].rstrip("/")
        server = (
            await http.get(issuer + "/.well-known/oauth-authorization-server")
        ).json()
        addresses = [
            resource["resource"], issuer, server["authorization_endpoint"],
            server["token_endpoint"], server["registration_endpoint"],
            server["revocation_endpoint"],
        ]  # fmt: skip
        report.check(
            "The discovery documents give public addresses of this service, "
            "and permit a client with no secret and PKCE",
            all(a.startswith(base) for a in addresses)
            and resource["resource"].rstrip("/") == mcp_url
            and "S256" in server["code_challenge_methods_supported"]
            and "none" in server["token_endpoint_auth_methods_supported"],
            f"{addresses}",
        )
        report.evidence["discovery"] = {"resource": resource, "server": server}

        # --- Registration with the app callback of Grok Bot --------------------
        host = Host(http, server, GROK_BOT_CALLBACK)
        registered = await host.register(EVIL_NAME)
        report.check(
            "A client can register with the app callback of Grok Bot",
            registered.status_code in (200, 201) and bool(host.client_id),
            f"HTTP {registered.status_code} {registered.text[:160]}",
        )

        # --- The person must act ------------------------------------------------
        verifier, challenge = pkce()
        first = await host.start(challenge, "state-1")
        consent_url = first.headers.get("location", "")
        page = await http.get(consent_url)
        report.check(
            "The authorization does not give a code before the person acts: "
            "it shows a page of this service",
            first.status_code in (302, 303, 307)
            and consent_url.startswith(base)
            and "code=" not in consent_url
            and page.status_code == 200
            and "Allow" in page.text,
            f"HTTP {first.status_code} -> {consent_url[:90]}",
        )
        report.check(
            "The consent page shows the client's name as text, and cannot be "
            "put in a frame",
            "<script>alert(1)</script>" not in page.text
            and "&lt;script&gt;" in page.text
            and page.headers.get("x-frame-options", "").upper() == "DENY",
            f"X-Frame-Options: {page.headers.get('x-frame-options')}",
        )

        accounts_before = (
            await http.get(
                operator_base + "/api/v1/platform/operator/oauth/summary",
                headers=operator,
            )
        ).json()
        form = await host.form(consent_url)
        cancelled = await host.decide(consent_url, "cancel", form)
        accounts_after = (
            await http.get(
                operator_base + "/api/v1/platform/operator/oauth/summary",
                headers=operator,
            )
        ).json()
        cancel_to = cancelled.headers.get("location", "")
        report.check(
            '"Cancel" tells the client and makes no account',
            cancel_to.startswith(GROK_BOT_CALLBACK)
            and parse_qs(urlsplit(cancel_to).query).get("error") == ["access_denied"]
            and accounts_after["accounts"] == accounts_before["accounts"],
            f"{cancel_to[:120]}; accounts {accounts_before['accounts']} -> "
            f"{accounts_after['accounts']}",
        )
        again = await host.decide(consent_url, "allow", form)
        report.check(
            "A consent step that was used cannot be used again",
            again.status_code == 400 and "location" not in again.headers,
            f"HTTP {again.status_code}",
        )

        stranger = await host.start(challenge, "s", "https://attacker.example/cb")
        report.check(
            "A callback that the client did not register gets nothing",
            stranger.status_code == 400 and "location" not in stranger.headers,
            f"HTTP {stranger.status_code} {stranger.text[:120]}",
        )

        # --- Allow, then the code ------------------------------------------------
        first = await host.start(challenge, "state-2")
        allowed = await host.decide(first.headers["location"], "allow")
        back = allowed.headers.get("location", "")
        code = parse_qs(urlsplit(back).query).get("code", [""])[0]
        wrong = await host.token(
            grant_type="authorization_code", code=code,
            redirect_uri=GROK_BOT_CALLBACK, code_verifier=pkce()[0],
        )  # fmt: skip
        good = await host.token(
            grant_type="authorization_code", code=code,
            redirect_uri=GROK_BOT_CALLBACK, code_verifier=verifier,
        )  # fmt: skip
        second_use = await host.token(
            grant_type="authorization_code", code=code,
            redirect_uri=GROK_BOT_CALLBACK, code_verifier=verifier,
        )  # fmt: skip
        maria = good.json() if good.status_code == 200 else {}
        report.check(
            '"Allow" sends the code to the app callback. The code needs the '
            "correct PKCE verifier and works one time",
            back.startswith(GROK_BOT_CALLBACK + "?")
            and parse_qs(urlsplit(back).query).get("state") == ["state-2"]
            and wrong.json().get("error") == "invalid_grant"
            and good.status_code == 200
            and second_use.json().get("error") == "invalid_grant"
            and bool(maria.get("refresh_token")),
            f"wrong verifier HTTP {wrong.status_code}, correct HTTP "
            f"{good.status_code}, second use HTTP {second_use.status_code}, "
            f"expires_in {maria.get('expires_in')}",
        )

        # --- The assistant works with the token ---------------------------------
        status = await tool(mcp_url, maria["access_token"], "get_account_status")
        refused = await tool(
            mcp_url, maria["access_token"], "place_call",
            phone_number=args.dial, task="Ask what time they close today.",
        )  # fmt: skip
        report.check(
            "The new account has no phone and cannot call. The refusal tells "
            "the assistant to do the phone check",
            status.get("caller_id") is None
            and status.get("can_call") is False
            and "start_caller_id_verification" in refused.get("refused", ""),
            f"can_call {status.get('can_call')}; refusal: "
            f"{refused.get('refused', refused)!s:.160}",
        )

        # --- A second person, same host -----------------------------------------
        omar = await host.authorize()
        word = "code word " + secrets.token_hex(4)
        await tool(
            mcp_url, maria["access_token"], "set_inbound_rules",
            rules=f"Take a message. The {word}.", answer_as="Maria Lopez",
        )  # fmt: skip
        maria_rules = await tool(mcp_url, maria["access_token"], "get_inbound_rules")
        omar_rules = await tool(mcp_url, omar["access_token"], "get_inbound_rules")
        report.check(
            "Each authorization is a separate account: one person's rules are "
            "not in the other person's account",
            word in maria_rules.get("rules", "")
            and word not in json.dumps(omar_rules)
            and omar_rules.get("is_default") is True,
            f"Maria: {maria_rules.get('rules', '')[:60]!r}; Omar default: "
            f"{omar_rules.get('is_default')}",
        )

        # --- Refresh ---------------------------------------------------------------
        fresh = await host.token(
            grant_type="refresh_token", refresh_token=maria["refresh_token"]
        )
        fresh_tokens = fresh.json() if fresh.status_code == 200 else {}
        still_maria = await tool(
            mcp_url, fresh_tokens.get("access_token", "x"), "get_inbound_rules"
        )
        report.check(
            "A refresh gives new tokens for the same account",
            fresh.status_code == 200
            and fresh_tokens["access_token"] != maria["access_token"]
            and fresh_tokens["refresh_token"] != maria["refresh_token"]
            and word in still_maria.get("rules", ""),
            f"HTTP {fresh.status_code}",
        )
        print(f"    waiting {args.grace + 5} s for the old refresh token to end")
        await asyncio.sleep(args.grace + 5)
        stale = await host.token(
            grant_type="refresh_token", refresh_token=maria["refresh_token"]
        )
        report.check(
            "The old refresh token stops soon after it was used",
            stale.json().get("error") == "invalid_grant",
            f"HTTP {stale.status_code} after {args.grace + 5} s",
        )

        # --- Revoke ------------------------------------------------------------------
        revoked = await http.post(
            server["revocation_endpoint"],
            data={"client_id": host.client_id, "token": fresh_tokens["refresh_token"]},
        )
        after_revoke = [
            await connects(mcp_url, maria["access_token"]),
            await connects(mcp_url, fresh_tokens["access_token"]),
        ]
        refresh_after = await host.token(
            grant_type="refresh_token", refresh_token=fresh_tokens["refresh_token"]
        )
        report.check(
            "After a revoke, no token of that authorization works, and the "
            "other person's token still works",
            revoked.status_code == 200
            and after_revoke == [False, False]
            and refresh_after.json().get("error") == "invalid_grant"
            and await connects(mcp_url, omar["access_token"]),
            f"revoke HTTP {revoked.status_code}; old tokens connect: {after_revoke}",
        )

        # --- Other credentials ------------------------------------------------------
        made_up = await connects(mcp_url, "ddo_at_" + secrets.token_urlsafe(32))
        key_ok = None
        if args.api_key:
            key_ok = await connects(mcp_url, args.api_key)
        report.check(
            "A made-up token is refused"
            + (
                ", and an API key of an existing account still works"
                if args.api_key
                else ""
            ),
            made_up is False and key_ok in (None, True),
            f"made-up token connects: {made_up}; API key connects: {key_ok}",
        )

        # --- The limit of new accounts for one network address ------------------
        # Maria and Omar are two accounts. Make more until the service refuses.
        made_now = 2
        refusal = None
        for _ in range(args.limit):
            first = await host.start(pkce()[1], "limit")
            answer = await host.decide(first.headers["location"], "allow")
            if answer.status_code != 303:
                refusal = answer
                refused_form = await host.form(first.headers["location"])
                break
            made_now += 1
        count = (await http.get(summary_url, headers=operator)).json()["accounts"]
        cancel_still = (
            await host.decide("", "cancel", refused_form) if refusal else None
        )
        report.check(
            f"One network address can make {args.limit} accounts in a day and "
            'no more. The refused "Allow" makes no account, and "Cancel" '
            "still works",
            refusal is not None
            and refusal.status_code == 429
            and "Too many new accounts" in refusal.text
            and made_now == args.limit
            and count - accounts_before["accounts"] == args.limit
            and cancel_still.status_code == 303,
            f"accounts made: {made_now}; then HTTP "
            f"{refusal.status_code if refusal else 'no refusal'}; accounts in the "
            f"service: +{count - accounts_before['accounts']}",
        )

        # --- Clean up: the accounts that this run made -----------------------------
        await http.post(reset_url, headers=operator)
        now = (await http.get(summary_url, headers=operator)).json()
        made = set(now["organization_ids"]) - set(accounts_before["organization_ids"])
        for organization_id in sorted(made):
            closed = await http.post(
                f"{operator_base}/api/v1/platform/operator/accounts/{organization_id}/close",
                headers=operator,
            )
            print(f"closed account {organization_id}: HTTP {closed.status_code}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--operator-token", required=True)
    parser.add_argument("--operator-url", default="")
    parser.add_argument("--api-key", default="")
    parser.add_argument("--dial", default="+12085050523")
    parser.add_argument("--grace", type=int, default=60)
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    report = Report()
    try:
        asyncio.run(run(args, report))
    finally:
        out = Path(args.out)
        out.mkdir(parents=True, exist_ok=True)
        (out / "results.json").write_text(
            json.dumps({"checks": report.checks, "evidence": report.evidence}, indent=2)
        )
        lines = ["# OAuth sign-in check", "", f"Service: `{args.base_url}`", ""]
        lines += [
            f"- **{'PASS' if c['passed'] else 'FAIL'}** {c['name']}  \n  {c['detail']}"
            for c in report.checks
        ]
        (out / "report.md").write_text("\n".join(lines) + "\n")
    return 0 if report.passed else 1


if __name__ == "__main__":
    sys.exit(main())
