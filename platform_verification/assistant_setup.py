"""The assistant leads the setup, and can stop a call and name the billing page.

The run does what a plugin host and its assistant do. Lena adds DanaDial in
her assistant: "Allow", nothing else. The assistant knows only what the
server says: the instructions, the tool list, and `setup` in
get_account_status. It then makes a real call to a shop phone that puts the
call on hold, and stops that call. Omar is a second person with his own
assistant. The run makes real phone calls.

How this can fail (written before the code):

 1. A new account shows `setup` as complete, or the service makes a call
    before the phone check.
 2. `setup` still says "ask for the number" while the phone rings, so the
    assistant starts a second check and the person gets two calls.
 3. After the right code, `setup` does not become complete.
 4. The instructions still tell the assistant to get a key, or do not name
    `setup`, end_call, or get_billing_link.
 5. An assistant of a different person ends Lena's call.
 6. end_call says "ended" but the phone call continues, and the minutes
    continue.
 7. end_call loses the words that were said before the end.
 8. A second end_call fails, or changes the record of the call.
 9. end_call on a call that still rings leaves the phone ringing, or leaves
    the call "ringing" in the record with no end.
10. A call that was stopped while it rang uses call minutes.
11. get_billing_link gives no address, or the address is not the billing
    page of the service.
12. With the free minutes used, `setup` still says "ready", so the assistant
    tries calls and does not tell the person about the plan.
"""

import argparse
import asyncio
import json
import os
import sys
import time
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).parent))
from oauth_sign_in import Host, session, tool
from verify import HOLD_SCRIPT, HOLD_TASK, Report, TestPhone

CALLBACK = "cursor://anysphere.cursor-mcp/oauth/callback"
LIVE = ("ringing", "in_progress")


async def run(args, report: Report) -> None:
    base = args.base_url.rstrip("/")
    mcp_url = base + "/mcp"
    local = (args.operator_url or base).rstrip("/")
    operator = {"X-Operator-Token": args.operator_token}
    phone = TestPhone(args.test_phone, args.twilio_account_sid, args.twilio_auth_token)
    shop = TestPhone(args.shop_phone, args.twilio_account_sid, args.twilio_auth_token)
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

        async def new_assistant(host: Host) -> tuple[str, int]:
            before = await oauth_organizations()
            tokens = await host.authorize()
            await tool(mcp_url, tokens["access_token"], "get_account_status")
            (organization_id,) = await oauth_organizations() - before
            made.append(organization_id)
            return tokens["access_token"], organization_id

        async def twilio_call(organization_id: int, to: str, since: float) -> dict:
            """The newest call of the account to ``to``, as Twilio has it."""
            (subaccount,) = await phone.subaccounts(organization_id)
            calls = [
                c
                for c in await phone.calls_in(subaccount["sid"])
                if c["to"] == to and c["direction"].startswith("outbound")
            ]
            return calls[0] if calls else {}

        try:
            (await op("POST", "oauth/reset-limits")).raise_for_status()
            (await op("POST", "phone-identities/release", **me)).raise_for_status()

            server = (
                await http.get(base + "/.well-known/oauth-authorization-server")
            ).json()
            host = Host(http, server, CALLBACK)
            (await host.register("Grok Bot")).raise_for_status()

            # --- Lena selects "Allow". The assistant reads what the server says.
            lena, lena_org = await new_assistant(host)

            async def lena_tool(name: str, **arguments) -> dict:
                return await tool(mcp_url, lena, name, **arguments)

            async with session(mcp_url, lena) as client:
                instructions = client.instructions or ""
                tools = {t.name for t in await client.list_tools()}
            report.evidence["instructions"] = instructions
            report.check(
                "The instructions name the setup state and the new tools, and "
                "do not ask for a key",
                "`setup`" in instructions
                and "end_call" in instructions
                and "get_billing_link" in instructions
                and "Do not ask the user for a key" in instructions
                and {"end_call", "get_billing_link"} <= tools,
                f"{len(tools)} tools: {sorted(tools)}",
            )

            first = await lena_tool("get_account_status")
            early = await lena_tool(
                "place_call", phone_number=shop.number, task="Say hello."
            )
            report.evidence["setup_new_account"] = first.get("setup")
            report.check(
                "A new account: setup is not complete, the next step is the "
                "phone check, and a call is refused",
                first.get("setup", {}).get("state") == "verify_phone"
                and first["setup"]["done"] is False
                and "start_caller_id_verification" in first["setup"]["next_step"]
                and first["can_call"] is False
                and "refused" in early,
                f"state {first.get('setup', {}).get('state')!r}; early call: "
                f"{str(early)[:110]}",
            )

            # --- The phone check, the way `setup` tells the assistant ---------
            await phone.answer_with_code("000000")  # replaced when the code is known
            started = await lena_tool("start_caller_id_verification", **me)
            await phone.answer_with_code(started["validation_code"])
            during = await lena_tool("get_account_status")
            report.evidence["setup_during_check"] = during.get("setup")
            report.check(
                "While the phone rings, setup says to wait for the code and "
                "not to start a new check",
                during["setup"]["state"] == "waiting_for_code"
                and during["setup"]["done"] is False
                and phone.number in during["setup"]["next_step"],
                during["setup"]["next_step"][:120],
            )
            status: dict = {}
            for _ in range(14):
                await asyncio.sleep(5)
                status = await lena_tool("get_account_status")
                if status["setup"]["done"]:
                    break
            await phone.hang_up()
            report.evidence["setup_after_check"] = status.get("setup")
            report.check(
                "After the code, setup is complete with one phone call: the "
                "caller ID is her phone and the account can call",
                status["setup"]["state"] == "ready"
                and status["caller_id"] == phone.number
                and status["can_call"] is True,
                f"state {status['setup']['state']!r}; caller ID "
                f"{status['caller_id']}; minutes {status['minutes_remaining']}",
            )

            # --- A real call on hold; the assistant stops it ------------------
            omar, _ = await new_assistant(host)
            await shop.answer_with_script(HOLD_SCRIPT)
            placed_at = time.time()
            call = await lena_tool(
                "place_call",
                phone_number=shop.number,
                task=HOLD_TASK,
                on_behalf_of="Lena Fischer",
                call_reason="to ask about opening hours",
            )
            call_id = call["call_id"]
            progress: dict = {}
            for _ in range(20):
                await asyncio.sleep(4)
                progress = await lena_tool("get_call_result", call_id=call_id)
                if "Bright Bikes" in (progress.get("transcript") or ""):
                    break
            other = await tool(mcp_url, omar, "end_call", call_id=call_id)
            await asyncio.sleep(6)
            still = await lena_tool("get_call_result", call_id=call_id)
            report.check(
                "The assistant of a different person cannot end her call",
                "not found" in str(other.get("refused", "")).lower()
                and still["status"] == "in_progress",
                f"his end_call: {str(other)[:90]}; her call after 6 s: "
                f"{still['status']}, {still['duration_seconds']} s",
            )

            ended = await lena_tool("end_call", call_id=call_id)
            ended_at = time.time()
            twilio_state = {}
            for _ in range(10):
                await asyncio.sleep(2)
                twilio_state = await twilio_call(lena_org, shop.number, placed_at)
                if twilio_state.get("status") == "completed":
                    break
            seconds_to_end = round(time.time() - ended_at)
            report.check(
                "end_call ends the phone call itself in a few seconds "
                "(Twilio's own record)",
                ended.get("ended_now") is True
                and twilio_state.get("status") == "completed"
                and seconds_to_end <= 20,
                f"Twilio status {twilio_state.get('status')!r} after "
                f"{seconds_to_end} s; Twilio duration "
                f"{twilio_state.get('duration')} s",
            )

            record: dict = {}
            for _ in range(12):
                await asyncio.sleep(5)
                record = await lena_tool("get_call_result", call_id=call_id)
                if record["status"] not in LIVE and record.get("transcript"):
                    break
            report.evidence["stopped_call"] = record
            report.check(
                "The record keeps the words said before the end, and says "
                "that the assistant ended the call",
                record["status"] == "completed"
                and "Bright Bikes" in record.get("transcript", "")
                and record.get("ended_by") == "assistant",
                f"status {record['status']}; ended_by {record.get('ended_by')!r}; "
                f"{len(record.get('transcript', ''))} characters of transcript",
            )
            used = (await lena_tool("get_account_status"))["minutes_used"]
            await asyncio.sleep(25)
            used_later = (await lena_tool("get_account_status"))["minutes_used"]
            talk_seconds = ended_at - placed_at
            report.check(
                "The minutes stop at the end of the call",
                0 < used <= round(talk_seconds / 60 + 0.2, 1) and used_later == used,
                f"{used} minutes used for a call that was stopped "
                f"{round(talk_seconds)} s after the request; 25 s later: "
                f"{used_later}",
            )

            again = await lena_tool("end_call", call_id=call_id)
            same = await lena_tool("get_call_result", call_id=call_id)
            report.check(
                "A second end_call changes nothing",
                again.get("ended_now") is False
                and same["duration_seconds"] == record["duration_seconds"]
                and same["transcript"] == record["transcript"],
                str(again)[:140],
            )

            # --- Stop a call while it rings ------------------------------------
            await shop.answer_with_script(HOLD_SCRIPT)
            ring_at = time.time()
            ringing = await lena_tool(
                "place_call", phone_number=shop.number, task=HOLD_TASK
            )
            stopped: dict = {}
            for _ in range(10):
                stopped = await lena_tool("end_call", call_id=ringing["call_id"])
                if "refused" not in stopped:
                    break
                await asyncio.sleep(0.5)
            stop_seconds = round(time.time() - ring_at, 1)
            ring_record: dict = {}
            for _ in range(12):
                await asyncio.sleep(5)
                ring_record = await lena_tool(
                    "get_call_result", call_id=ringing["call_id"]
                )
                if ring_record["status"] not in LIVE:
                    break
            ring_twilio = await twilio_call(lena_org, shop.number, ring_at)
            used_after_ring = (await lena_tool("get_account_status"))["minutes_used"]
            report.evidence["stopped_while_ringing"] = ring_record
            report.check(
                "end_call on a call that was just started: the phone call "
                "ends and the record gets an end",
                stopped.get("ended_now") is True
                and ring_record["status"] not in LIVE
                and ring_twilio.get("status") in ("canceled", "completed", "no-answer")
                and int(ring_twilio.get("duration") or 0) <= 5,
                f"end_call {stop_seconds} s after place_call; record "
                f"{ring_record['status']!r}; Twilio {ring_twilio.get('status')!r}, "
                f"{ring_twilio.get('duration')} s",
            )
            report.check(
                "That stopped call uses no more than 0.1 call minutes",
                used_after_ring - used_later <= 0.1,
                f"minutes used before {used_later}, after {used_after_ring}",
            )

            # --- Payment: the page address, and setup when the minutes are used
            link = await lena_tool("get_billing_link")
            (
                await op("PUT", f"accounts/{lena_org}/allowance", free_seconds=0)
            ).raise_for_status()
            empty = await lena_tool("get_account_status")
            refused = await lena_tool(
                "place_call", phone_number=shop.number, task="Say hello."
            )
            link_empty = await lena_tool("get_billing_link")
            report.evidence["billing_link"] = link
            report.evidence["setup_minutes_used"] = empty.get("setup")
            report.check(
                "get_billing_link gives the billing page and how she signs in",
                link.get("url") == args.billing_url
                and phone.number in link.get("sign_in", "")
                and link_empty.get("url") == args.billing_url,
                f"{link.get('url')}; {link.get('sign_in', '')[:90]}",
            )
            report.check(
                "With the free minutes used, setup says that calls are "
                "blocked and that she needs the plan; a call is refused",
                empty["setup"]["state"] == "blocked"
                and "monthly plan" in empty["setup"]["next_step"]
                and empty["can_call"] is False
                and "refused" in refused,
                empty["setup"]["next_step"][:150],
            )
        finally:
            await phone.hang_up()
            await shop.hang_up()
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
    parser.add_argument("--shop-phone", required=True)
    parser.add_argument("--billing-url", required=True)
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
    lines = [
        "# Assistant-led setup, end_call and billing link check",
        "",
        f"Service: `{args.base_url}`",
        "",
    ]
    lines += [
        f"- **{'PASS' if c['passed'] else 'FAIL'}** {c['name']}  \n  {c['detail']}"
        for c in report.checks
    ]
    (out / "report.md").write_text("\n".join(lines) + "\n")
    return 0 if report.passed else 1


if __name__ == "__main__":
    sys.exit(main())
