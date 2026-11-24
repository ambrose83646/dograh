"""One person, one account: join and clean-up of accounts from an assistant.

The run does what people and a plugin host do. Maria has a DanaDial account
from the web site (phone sign-in) with a paid plan. She then connects two
assistants with OAuth. Each "Allow" makes a new, empty account. The phone
check must bring each assistant to her first account. Omar and Priya select
"Allow" and never prove a phone. The run makes real phone calls: Twilio's
check calls to the test phone, which keys the code.

How this can fail (written before the code):

 1. The start of a check gives access to the other account before the person
    keys the code.
 2. A wrong code on the phone joins the accounts.
 3. An account that is not new (it has its own sign-in) takes the phone
    number of a different account by this path.
 4. After the join, the assistant still reads the empty account: no plan,
    no caller ID.
 5. The person gets two phone calls: one for the join and one to give the
    first account its caller ID.
 6. The Twilio subaccount of the empty account stays open (the operator pays
    for nothing, and the count of subaccounts grows).
 7. A refresh after the join gives a token of the empty account, or fails.
 8. A second assistant cannot join when the first account has its caller ID
    already, or the join replaces that caller ID.
 9. The join of the second assistant stops the tokens of the first.
10. The clean-up removes an account that is new, an account with a verified
    phone, or an account that a person paid for.
11. The clean-up leaves an old account with no phone: its token still works
    or its subaccount stays open.
"""

import argparse
import asyncio
import json
import os
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).parent))
from oauth_sign_in import Host, connects, tool
from verify import Report, TestPhone

CALLBACK = "cursor://anysphere.cursor-mcp/oauth/callback"
PLAN = "Join check plan"


def other_code(code: str) -> str:
    return f"{(int(code) + 1) % 1000000:06d}"


async def run(args, report: Report) -> None:
    base = args.base_url.rstrip("/")
    mcp_url = base + "/mcp"
    local = (args.operator_url or base).rstrip("/")
    operator = {"X-Operator-Token": args.operator_token}
    phone = TestPhone(args.test_phone, args.twilio_account_sid, args.twilio_auth_token)
    me = {"phone_number": phone.number}
    made: list[int] = []

    async with (
        httpx.AsyncClient(timeout=30, follow_redirects=False) as http,
        httpx.AsyncClient(base_url=local, timeout=60) as api,
    ):

        async def op(method: str, path: str, **json_body) -> httpx.Response:
            return await api.request(
                method,
                "/api/v1/platform/operator/" + path,
                headers=operator,
                json=json_body or None,
            )

        async def oauth_organizations() -> set[int]:
            return set((await op("GET", "oauth/summary")).json()["organization_ids"])

        async def open_subaccounts(organization_id: int) -> int:
            return len(await phone.subaccounts(organization_id))

        async def new_assistant(host: Host) -> tuple[dict, int]:
            """A person selects "Allow". Returns the tokens and the new account."""
            before = await oauth_organizations()
            tokens = await host.authorize()
            # The first use of the token sets the account up.
            await tool(mcp_url, tokens["access_token"], "get_account_status")
            (organization_id,) = await oauth_organizations() - before
            made.append(organization_id)
            return tokens, organization_id

        async def check_phone(token: str, *, right_code: bool) -> dict:
            """Start the phone check; the phone answers and keys a code."""
            started = await tool(mcp_url, token, "start_caller_id_verification", **me)
            if "validation_code" not in started:
                return {"started": started, "status": {}}
            code = started["validation_code"]
            await phone.answer_with_code(code if right_code else other_code(code))
            status: dict = {}
            for _ in range(14):
                await asyncio.sleep(5)
                status = await tool(mcp_url, token, "get_account_status")
                if right_code and status.get("caller_id"):
                    break
            await phone.hang_up()
            return {"started": started, "status": status}

        try:
            (await op("POST", "oauth/reset-limits")).raise_for_status()
            # A run that stopped early can leave the phone bound to an account.
            (await op("POST", "phone-identities/release", **me)).raise_for_status()
            await op("POST", "phone-identities/reset-code-limit", **me)

            # --- Maria has an account from the web site, with a plan ---------
            seen = set(await phone.texts())
            sent = await api.post("/api/v1/platform/auth/start", json=me)
            codes = await phone.new_codes(seen)
            signed_in = await api.post(
                "/api/v1/platform/auth/verify", json={**me, "code": codes[0]}
            )
            signed_in.raise_for_status()
            maria_auth = {"Authorization": f"Bearer {signed_in.json()['token']}"}
            maria_org = signed_in.json()["user"]["organization_id"]
            made.append(maria_org)

            async def maria_account() -> dict:
                response = await api.get("/api/v1/platform/account", headers=maria_auth)
                response.raise_for_status()
                return response.json()

            first_view = await maria_account()
            now = datetime.now(UTC)
            plan = await op(
                "PUT",
                f"accounts/{maria_org}/plan",
                name=PLAN,
                included_seconds=3000,
                period_start=(now - timedelta(days=1)).isoformat(),
                period_end=(now + timedelta(days=29)).isoformat(),
            )
            report.check(
                "Maria has a web site account with a plan and no caller ID",
                sent.status_code == 200
                and plan.status_code == 200
                and first_view["caller_id"] is None
                and first_view["organization_id"] == maria_org,
                f"account {maria_org}; plan HTTP {plan.status_code}",
            )

            # --- She connects an assistant: a new, empty account --------------
            server = (
                await http.get(base + "/.well-known/oauth-authorization-server")
            ).json()
            host = Host(http, server, CALLBACK)
            (await host.register("Grok Bot")).raise_for_status()
            first, first_org = await new_assistant(host)
            empty = await tool(mcp_url, first["access_token"], "get_account_status")
            report.check(
                '"Allow" makes a new account that does not see her plan',
                first_org != maria_org
                and empty.get("plan") is None
                and empty.get("caller_id") is None
                and await open_subaccounts(first_org) == 1,
                f"new account {first_org}; plan {empty.get('plan')!r}",
            )

            # --- An account with its own sign-in cannot take her number -------
            signup = await api.post(
                "/api/v1/auth/signup",
                json={
                    "email": f"join-{now:%m%d%H%M%S}@example.com",
                    "password": f"Join-{os.urandom(8).hex()}",
                    "name": "Riverside Dental",
                },
                headers=operator,
            )
            signup.raise_for_status()
            clinic_auth = {"Authorization": f"Bearer {signup.json()['token']}"}
            clinic_org = signup.json()["user"]["organization_id"]
            made.append(clinic_org)
            await api.get("/api/v1/platform/account", headers=clinic_auth)
            clinic_try = await api.post(
                "/api/v1/platform/caller-id", json=me, headers=clinic_auth
            )
            report.check(
                "An account with its own sign-in cannot start a check of her "
                "phone number",
                clinic_try.status_code == 409,
                f"HTTP {clinic_try.status_code}: {clinic_try.text[:120]}",
            )

            # --- A wrong code gives nothing -------------------------------------
            wrong = await check_phone(first["access_token"], right_code=False)
            after_wrong = await maria_account()
            report.check(
                "The start of a check and a wrong code on the phone give no "
                "access: the assistant stays on the empty account",
                wrong["started"].get("status") == "calling"
                and wrong["status"].get("plan") is None
                and wrong["status"].get("caller_id") is None
                and after_wrong["caller_id"] is None
                and first_org in await oauth_organizations(),
                f"plan {wrong['status'].get('plan')!r}; caller ID "
                f"{wrong['status'].get('caller_id')!r}",
            )

            # --- The right code joins the accounts: one phone call ---------------
            right = await check_phone(first["access_token"], right_code=True)
            maria_now = await maria_account()
            report.check(
                "After one phone check, the assistant works for her first "
                "account: it reads her plan and her caller ID",
                right["status"].get("plan") == PLAN
                and right["status"].get("caller_id") == phone.number
                and right["status"].get("can_call") is True,
                f"plan {right['status'].get('plan')!r}; caller ID "
                f"{right['status'].get('caller_id')!r}",
            )
            report.check(
                "The same phone call gave her first account its caller ID, so "
                "she is not phoned a second time",
                maria_now["caller_id"] == phone.number
                and maria_now["organization_id"] == maria_org,
                f"web site view: caller ID {maria_now['caller_id']!r}",
            )
            report.check(
                "The empty account is closed: its Twilio subaccount is not "
                "open, and it is not in the list of assistant accounts",
                await open_subaccounts(first_org) == 0
                and await open_subaccounts(maria_org) == 1
                and first_org not in await oauth_organizations(),
                f"open subaccounts of {first_org}: {await open_subaccounts(first_org)}",
            )
            refreshed = await host.token(
                grant_type="refresh_token", refresh_token=first["refresh_token"]
            )
            fresh = refreshed.json().get("access_token", "")
            fresh_status = (
                await tool(mcp_url, fresh, "get_account_status") if fresh else {}
            )
            report.check(
                "A refresh after the join gives a token of her first account",
                refreshed.status_code == 200 and fresh_status.get("plan") == PLAN,
                f"refresh HTTP {refreshed.status_code}; plan "
                f"{fresh_status.get('plan')!r}",
            )

            # --- A second assistant, when the caller ID exists already ----------
            second_host = Host(http, server, CALLBACK)
            (await second_host.register("Claude")).raise_for_status()
            second, second_org = await new_assistant(second_host)
            joined = await check_phone(second["access_token"], right_code=True)
            maria_last = await maria_account()
            report.check(
                "A second assistant joins the same account with one phone "
                "check, and her caller ID stays as it was",
                joined["status"].get("plan") == PLAN
                and joined["status"].get("caller_id") == phone.number
                and maria_last["caller_id"] == phone.number
                and await open_subaccounts(second_org) == 0
                and await open_subaccounts(maria_org) == 1,
                f"second account {second_org}; plan {joined['status'].get('plan')!r}",
            )
            first_still = await tool(mcp_url, fresh, "get_account_status")
            report.check(
                "The first assistant still works after the second one joined",
                first_still.get("plan") == PLAN,
                f"plan {first_still.get('plan')!r}",
            )

            # --- People who never prove a phone ----------------------------------
            omar, omar_org = await new_assistant(host)
            priya, priya_org = await new_assistant(host)
            paid = await op(
                "PUT",
                f"accounts/{priya_org}/plan",
                name=PLAN,
                included_seconds=600,
                period_start=(now - timedelta(days=1)).isoformat(),
                period_end=(now + timedelta(days=29)).isoformat(),
            )
            timed = (await op("POST", "oauth/clean-up")).json()
            kept = await connects(mcp_url, omar["access_token"])
            report.check(
                "The timed clean-up does not remove an account that is new",
                omar_org not in timed["organization_ids"]
                and kept
                and await open_subaccounts(omar_org) == 1,
                f"removed by the timed clean-up: {timed['organization_ids']}",
            )
            forced = (await op("POST", "oauth/clean-up", older_than_hours=0)).json()
            omar_after = await connects(mcp_url, omar["access_token"])
            omar_refresh = await host.token(
                grant_type="refresh_token", refresh_token=omar["refresh_token"]
            )
            report.check(
                "The clean-up removes an old account with no phone: its tokens "
                "stop and its Twilio subaccount is closed",
                omar_org in forced["organization_ids"]
                and omar_after is False
                and omar_refresh.status_code in (400, 401)
                and await open_subaccounts(omar_org) == 0,
                f"removed: {forced['organization_ids']}; Omar's token connects: "
                f"{omar_after}; refresh HTTP {omar_refresh.status_code}",
            )
            maria_kept = await tool(mcp_url, fresh, "get_account_status")
            report.check(
                "The clean-up keeps an account with a verified phone and an "
                "account that a person paid for",
                paid.status_code == 200
                and maria_kept.get("caller_id") == phone.number
                and await connects(mcp_url, second["access_token"])
                and await connects(mcp_url, priya["access_token"])
                and priya_org not in forced["organization_ids"]
                and await open_subaccounts(priya_org) == 1
                and await open_subaccounts(maria_org) == 1,
                f"Maria's caller ID {maria_kept.get('caller_id')!r}; Priya's "
                f"account {priya_org} is open",
            )
            report.evidence.update(
                maria=maria_org,
                first_assistant=first_org,
                second_assistant=second_org,
                omar=omar_org,
                priya=priya_org,
                clinic=clinic_org,
            )
        finally:
            # --- Clean up: the accounts that this run made ------------------------
            await phone.hang_up()
            await op("POST", "oauth/reset-limits")
            await op("POST", "phone-identities/release", **me)
            for organization_id in made:
                closed = await op("POST", f"accounts/{organization_id}/close")
                print(f"closed account {organization_id}: HTTP {closed.status_code}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--operator-url", default="")
    parser.add_argument("--operator-token", required=True)
    parser.add_argument("--test-phone", required=True)
    parser.add_argument(
        "--twilio-account-sid", default=os.getenv("PLATFORM_TWILIO_ACCOUNT_SID", "")
    )
    parser.add_argument(
        "--twilio-auth-token", default=os.getenv("PLATFORM_TWILIO_AUTH_TOKEN", "")
    )
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    report = Report()
    try:
        asyncio.run(run(args, report))
    except Exception as exc:  # noqa: BLE001 - a crash is a failed run with a report
        report.check(
            "The run finished without an unexpected error", False, repr(exc)[:500]
        )
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "results.json").write_text(
        json.dumps({"checks": report.checks, "evidence": report.evidence}, indent=2)
    )
    lines = ["# Account join and clean-up check", "", f"Service: `{args.base_url}`", ""]
    lines += [
        f"- **{'PASS' if c['passed'] else 'FAIL'}** {c['name']}  \n  {c['detail']}"
        for c in report.checks
    ]
    (out / "report.md").write_text("\n".join(lines) + "\n")
    return 0 if report.passed else 1


if __name__ == "__main__":
    sys.exit(main())
