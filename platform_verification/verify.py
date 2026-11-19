"""End-to-end verification of the calling platform against a running service.

Two new users sign up. One is a dental clinic that saves rules for its phone
number. The other asks its assistant to book an appointment there. The
assistant's call is a real Twilio call between the two platform numbers, so one
run exercises an outbound call, an inbound call answered by saved rules, the
separation of the two accounts, and the free-allowance block.

Only the two accounts' own platform numbers are dialled. See README.md.
"""

import argparse
import asyncio
import json
import os
import random
import re
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import httpx
from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport

EXPECTED_TOOLS = {
    "place_call",
    "get_call_result",
    "list_calls",
    "set_inbound_rules",
    "get_inbound_rules",
    "get_account_status",
}
# A number in the reserved fictional range: never assigned to a subscriber.
UNAPPROVED_NUMBER = "+12025550143"
_DIGIT_WORDS = {
    "zero": "0", "oh": "0", "one": "1", "two": "2", "three": "3", "four": "4",
    "five": "5", "six": "6", "seven": "7", "eight": "8", "nine": "9",
}  # fmt: skip


def spoken_digits(text: str) -> str:
    """Reduce speech-to-text output to its digits, in order.

    A code read aloud comes back as "four eight two one", "4 8 2 1", or "4821"
    depending on the recognizer; all three reduce to the same string.
    """
    words = re.findall(r"[a-z]+|\d", text.lower())
    return "".join(_DIGIT_WORDS.get(w, w if w.isdigit() else "") for w in words)


def transcript_turns(transcript: str) -> list[tuple[str, str]]:
    turns = []
    for line in transcript.splitlines():
        match = re.match(r"^\[[^\]]+\]\s+(user|assistant):\s*(.*)$", line)
        if match:
            turns.append((match.group(1), match.group(2)))
        elif turns and line.strip():
            # One turn can span several lines.
            turns[-1] = (turns[-1][0], turns[-1][1] + " " + line.strip())
    return turns


class Report:
    def __init__(self) -> None:
        self.checks: list[dict] = []
        self.evidence: dict = {}

    def check(self, name: str, passed: bool, detail: str = "") -> bool:
        self.checks.append({"name": name, "passed": bool(passed), "detail": detail})
        print(
            f"[{'PASS' if passed else 'FAIL'}] {name}"
            + (f" — {detail}" if detail else "")
        )
        return bool(passed)

    @property
    def passed(self) -> bool:
        return bool(self.checks) and all(c["passed"] for c in self.checks)


class ToolRefused(Exception):
    pass


class Assistant:
    """An AI assistant's connection: a standard MCP client plus one API key."""

    def __init__(self, mcp_url: str, api_key: str) -> None:
        self.mcp_url = mcp_url
        self.api_key = api_key

    def session(self) -> Client:
        return Client(
            StreamableHttpTransport(
                self.mcp_url, headers={"Authorization": f"Bearer {self.api_key}"}
            )
        )

    async def tool_names(self) -> set[str]:
        async with self.session() as session:
            return {tool.name for tool in await session.list_tools()}

    async def tool_schema(self, name: str) -> dict:
        async with self.session() as session:
            return next(
                t.input_schema for t in await session.list_tools() if t.name == name
            )

    async def call(self, name: str, **arguments):
        async with self.session() as session:
            result = await session.call_tool(name, arguments, raise_on_error=False)
        text = "".join(getattr(block, "text", "") for block in result.content)
        if result.is_error:
            raise ToolRefused(text)
        content = result.structured_content
        if content is not None:
            return content["result"] if set(content) == {"result"} else content
        return json.loads(text)

    async def refusal(self, name: str, **arguments) -> str | None:
        try:
            await self.call(name, **arguments)
        except ToolRefused as exc:
            return str(exc)
        return None


async def sign_up(http: httpx.AsyncClient, name: str, run_id: str) -> dict:
    email = f"verify-{run_id}-{name.split()[0].lower()}@example.com"
    response = await http.post(
        "/api/v1/auth/signup",
        json={
            "email": email,
            "password": f"Verify-{run_id}-{random.random()}",
            "name": name,
        },
    )
    response.raise_for_status()
    body = response.json()
    auth = {"Authorization": f"Bearer {body['token']}"}
    key = await http.post(
        "/api/v1/user/api-keys", json={"name": "assistant"}, headers=auth
    )
    key.raise_for_status()
    return {
        "name": name,
        "email": email,
        "organization_id": body["user"]["organization_id"],
        "auth": auth,
        "api_key": key.json()["api_key"],
        "api_key_id": key.json()["id"],
    }


async def wait_for_call(assistant: Assistant, call_id: int, timeout: float) -> dict:
    """Poll the way the tool description tells an assistant to."""
    deadline = time.monotonic() + timeout
    result: dict = {}
    while time.monotonic() < deadline:
        await asyncio.sleep(15)
        result = await assistant.call("get_call_result", call_id=call_id)
        print(
            f"    call {call_id}: {result['status']} {result.get('duration_seconds')}s"
        )
        if result["status"] in ("completed", "failed") and (
            result.get("transcript") or result["status"] == "failed"
        ):
            return result
    return result


async def run(args, report: Report) -> None:
    run_id = datetime.now(UTC).strftime("%m%d%H%M%S")
    code_digits = f"{random.randint(1000, 9999)}"
    fee = random.choice([25, 35, 45])
    mcp_url = args.base_url.rstrip("/") + "/mcp/"
    operator = {"X-Operator-Token": args.operator_token}
    report.evidence.update(
        run_id=run_id, base_url=args.base_url, started_at=datetime.now(UTC).isoformat(),
        confirmation_code=f"RD-{code_digits}", cancellation_fee=fee,
    )  # fmt: skip
    accounts: list[dict] = []

    async with httpx.AsyncClient(base_url=args.base_url, timeout=60) as http:
        try:
            # --- The MCP endpoint refuses clients without credentials -------
            initialize = {
                "jsonrpc": "2.0", "id": 1, "method": "initialize",
                "params": {"protocolVersion": "2025-06-18", "capabilities": {},
                           "clientInfo": {"name": "verify", "version": "1"}},
            }  # fmt: skip
            mcp_headers = {"Accept": "application/json, text/event-stream"}
            anonymous = await http.post("/mcp/", json=initialize, headers=mcp_headers)
            forged = await http.post(
                "/mcp/", json=initialize,
                headers={**mcp_headers, "Authorization": "Bearer dgr_not_a_real_key"},
            )  # fmt: skip
            report.check(
                "MCP refuses a client with no key and a client with a made-up key",
                anonymous.status_code == 401 and forged.status_code == 401,
                f"no key: HTTP {anonymous.status_code}; made-up key: HTTP {forged.status_code}",
            )

            # --- Two people sign up with no operator involved ----------------
            clinic = await sign_up(http, "Riverside Dental", run_id)
            accounts.append(clinic)
            maria = await sign_up(http, "Maria Lopez", run_id)
            accounts.append(maria)
            clinic_ai = Assistant(mcp_url, clinic["api_key"])
            maria_ai = Assistant(mcp_url, maria["api_key"])

            clinic_tools = await clinic_ai.tool_names()
            maria_tools = await maria_ai.tool_names()
            report.check(
                "A standard MCP client connects with a user's key and lists the calling tools",
                clinic_tools == EXPECTED_TOOLS and maria_tools == EXPECTED_TOOLS,
                f"tools: {sorted(maria_tools)}",
            )

            clinic_status = await clinic_ai.call("get_account_status")
            maria_status = await maria_ai.call("get_account_status")
            clinic["phone_number"] = clinic_status["phone_number"]
            maria["phone_number"] = maria_status["phone_number"]
            report.evidence["accounts"] = [
                {k: a[k] for k in ("name", "email", "organization_id", "phone_number")}
                for a in accounts
            ]
            report.check(
                "Each new user gets a separate account with its own phone number and allowance",
                clinic["organization_id"] != maria["organization_id"]
                and bool(clinic["phone_number"])
                and bool(maria["phone_number"])
                and clinic["phone_number"] != maria["phone_number"]
                and clinic_status["can_call"]
                and maria_status["can_call"]
                and maria_status["free_minutes_used"] == 0,
                f"accounts {clinic['organization_id']} and {maria['organization_id']}; "
                f"numbers {clinic['phone_number']} and {maria['phone_number']}; "
                f"{maria_status['free_minutes_total']} free minutes each",
            )
            if not (clinic["phone_number"] and maria["phone_number"]):
                return

            # --- The clinic saves how its number is answered ------------------
            greeting = "Riverside Dental, this is the front desk. How can I help you?"
            rules = (
                "You are the front desk of Riverside Dental, a dental clinic. "
                "The clinic is open Monday to Thursday, 8 am to 5 pm. It is closed on "
                "Wednesday mornings for staff training, so never offer a Wednesday morning. "
                "The only free cleaning appointments this week are Tuesday at 2:30 pm and "
                "Thursday at 9:00 am. "
                "To book, you must first get the patient's full name and date of birth. "
                "New patients must bring a photo ID and their insurance card. "
                f"A cancellation with less than 24 hours' notice costs {fee} dollars. "
                f"After the booking is agreed, give the confirmation code R D {' '.join(code_digits)} "
                "and say it one character at a time. Never give the code before the "
                "booking is agreed. You cannot give medical advice."
            )
            saved = await clinic_ai.call(
                "set_inbound_rules",
                rules=rules,
                answer_as="Riverside Dental",
                greeting=greeting,
            )
            stored = await clinic_ai.call("get_inbound_rules")
            report.check(
                "A user saves inbound rules through MCP and reads them back",
                saved.get("saved") is True
                and stored["rules"] == rules
                and stored["greeting"] == greeting
                and stored["is_default"] is False,
            )

            # --- The platform refuses calls it must not place -----------------
            # Dial-out to a stranger is attempted only while the service says it
            # is in its test period, when the allowlist is what must stop it.
            unapproved = (
                await maria_ai.refusal(
                    "place_call", phone_number=UNAPPROVED_NUMBER, task="Say hello."
                )
                if maria_status["test_period"]
                else "skipped: the service is past its test period"
            )
            own = await maria_ai.refusal(
                "place_call", phone_number=maria["phone_number"], task="Say hello."
            )
            malformed = await maria_ai.refusal(
                "place_call", phone_number="2025550143", task="Say hello."
            )
            after_refusals = await maria_ai.call("list_calls", limit=50)
            report.check(
                "Calls to an unapproved number, the user's own number, and a malformed number are refused and start nothing",
                all([unapproved, own, malformed]) and after_refusals == [],
                f"unapproved: {unapproved!r}",
            )

            # --- Maria's assistant places the call. No clinic assistant is ---
            # --- connected: every clinic MCP session above is closed. --------
            task = (
                "Call Riverside Dental and book a teeth cleaning for Maria Lopez, who is "
                "a new patient. She prefers Wednesday morning. If Wednesday morning is not "
                "possible, take the earliest morning appointment this week; she cannot come "
                "in the afternoon. Before you finish, get these answers: the day and time "
                "booked, the confirmation code, what a new patient must bring, and the fee "
                "for a late cancellation."
            )
            placed = await maria_ai.call(
                "place_call",
                phone_number=clinic["phone_number"],
                task=task,
                background=(
                    "Maria Lopez, date of birth 14 March 1988. Insurance: Delta Dental. "
                    "Callback number: " + maria["phone_number"]
                ),
                on_behalf_of="Maria Lopez",
            )
            report.check(
                "place_call starts a call and returns a call id at once",
                isinstance(placed.get("call_id"), int)
                and placed["from"] == maria["phone_number"]
                and placed["to"] == clinic["phone_number"],
                json.dumps(placed)[:200],
            )
            outbound = await wait_for_call(
                maria_ai, placed["call_id"], args.call_timeout
            )
            report.evidence["outbound_call"] = outbound
            out_turns = transcript_turns(outbound.get("transcript", ""))
            heard = " ".join(text for role, text in out_turns if role == "user").lower()
            report.check(
                "The outbound call completes and the assistant reads a multi-turn transcript",
                outbound.get("status") == "completed"
                and outbound.get("direction") == "outbound"
                and outbound.get("duration_seconds", 0) >= 30
                and len(out_turns) >= 8
                and {role for role, _ in out_turns} == {"user", "assistant"},
                f"{outbound.get('status')}, {outbound.get('duration_seconds')} s, {len(out_turns)} turns",
            )
            report.check(
                "The caller's agent negotiated: Wednesday was refused and Thursday 9 am was booked",
                "thursday" in heard
                and "wednesday" in outbound.get("transcript", "").lower(),
            )
            report.check(
                "The caller's transcript holds the confirmation code that exists only in the clinic's saved rules",
                code_digits in spoken_digits(heard),
                f"code RD-{code_digits}; digits heard: {spoken_digits(heard)[-40:]}",
            )

            # --- The clinic's assistant connects afterwards and finds the call
            clinic_calls = await clinic_ai.call("list_calls", limit=10)
            inbound_summary = next(
                (c for c in clinic_calls if c["direction"] == "inbound"), None
            )
            inbound = (
                await clinic_ai.call(
                    "get_call_result", call_id=inbound_summary["call_id"]
                )
                if inbound_summary
                else {}
            )
            report.evidence["inbound_call"] = inbound
            in_turns = transcript_turns(inbound.get("transcript", ""))
            said = " ".join(text for role, text in in_turns if role == "assistant")
            report.check(
                "The inbound call was answered with the clinic's saved greeting and rules while no assistant was connected",
                bool(inbound_summary)
                and len(clinic_calls) == 1
                and inbound.get("from") == maria["phone_number"]
                and inbound.get("status") == "completed"
                and "front desk" in said.lower()
                and code_digits in spoken_digits(said)
                and "thursday" in said.lower(),
                f"{len(in_turns)} turns; from {inbound.get('from')}",
            )

            # --- Neither user can reach the other's data ----------------------
            maria_call, clinic_call = placed["call_id"], inbound.get("call_id")
            cross_a = await maria_ai.refusal("get_call_result", call_id=clinic_call)
            cross_b = await clinic_ai.refusal("get_call_result", call_id=maria_call)
            maria_calls = await maria_ai.call("list_calls", limit=50)
            report.check(
                "A user cannot read the other user's call record or transcript through MCP",
                bool(cross_a)
                and bool(cross_b)
                and [c["call_id"] for c in maria_calls] == [maria_call]
                and clinic_call not in [c["call_id"] for c in maria_calls],
                f"refusals: {cross_a!r} / {cross_b!r}",
            )
            rest_cross = await http.get(
                f"/api/v1/platform/calls/{clinic_call}", headers=maria["auth"]
            )
            rest_own = await http.get(
                f"/api/v1/platform/calls/{maria_call}", headers=maria["auth"]
            )
            report.check(
                "The same holds on the REST API with a signed-in session",
                rest_cross.status_code == 404 and rest_own.status_code == 200,
                f"other's call: HTTP {rest_cross.status_code}; own call: HTTP {rest_own.status_code}",
            )
            maria_rules = await maria_ai.call("get_inbound_rules")
            report.check(
                "A user cannot read the other user's agent rules",
                code_digits not in spoken_digits(json.dumps(maria_rules))
                and maria_rules["is_default"] is True,
            )
            keys = (
                await http.get("/api/v1/user/api-keys", headers=maria["auth"])
            ).json()
            steal = await http.delete(
                f"/api/v1/user/api-keys/{clinic['api_key_id']}", headers=maria["auth"]
            )
            still_works = (await clinic_ai.call("get_account_status"))["phone_number"]
            report.check(
                "A user cannot list or revoke the other user's access keys",
                maria["api_key_id"] in [k["id"] for k in keys]
                and clinic["api_key_id"] not in [k["id"] for k in keys]
                and not any(
                    k["key_prefix"] == clinic["api_key"][: len(k["key_prefix"])]
                    for k in keys
                )
                and steal.status_code == 404
                and still_works == clinic["phone_number"],
                f"revoke attempt: HTTP {steal.status_code}",
            )
            schema = await maria_ai.tool_schema("place_call")
            closed = {}
            for method, path in [
                ("GET", "/api/v1/workflow/summary"),
                ("GET", "/api/v1/organizations/telephony-config"),
                ("GET", "/api/v1/user/configurations/user"),
                ("GET", "/api/v1/model-connections"),
                ("GET", f"/api/v1/workflow/1/runs/{clinic_call}"),
                (
                    "POST",
                    "/api/v1/public/agent/workflow/00000000-0000-0000-0000-000000000000",
                ),
                ("POST", "/api/v1/mcp/"),
            ]:
                for auth in (maria["auth"], {"X-API-Key": maria["api_key"]}):
                    response = await http.request(method, path, headers=auth, json={})
                    closed[f"{method} {path}"] = response.status_code
            report.check(
                "A user cannot choose a caller number and cannot reach the provider keys, phone numbers, or agents through the underlying Dograh API",
                set(schema["properties"])
                == {"phone_number", "task", "background", "on_behalf_of"}
                and set(closed.values()) == {404},
                json.dumps(closed),
            )
            operator_probe = await http.put(
                f"/api/v1/platform/operator/accounts/{clinic['organization_id']}/allowance",
                headers=maria["auth"], json={"free_seconds": 0},
            )  # fmt: skip
            report.check(
                "A user cannot use the operator controls on another account",
                operator_probe.status_code == 404
                and (await clinic_ai.call("get_account_status"))["can_call"] is True,
                f"HTTP {operator_probe.status_code}",
            )

            # --- The free allowance blocks further calls ----------------------
            # Maria has used real call time. The operator sets her allowance to
            # one minute so the limit is reached without ten minutes of calls.
            before = await maria_ai.call("get_account_status")
            limited = await http.put(
                f"/api/v1/platform/operator/accounts/{maria['organization_id']}/allowance",
                headers=operator, json={"free_seconds": 60},
            )  # fmt: skip
            limited.raise_for_status()
            blocked_status = await maria_ai.call("get_account_status")
            blocked = await maria_ai.refusal(
                "place_call", phone_number=clinic["phone_number"], task=task
            )
            # An account at its limit must not cost the operator inbound minutes either.
            inbound_to_blocked = await clinic_ai.call(
                "place_call",
                phone_number=maria["phone_number"],
                task="Tell Maria Lopez that her appointment is confirmed.",
                on_behalf_of="Riverside Dental",
            )
            callback = await wait_for_call(
                clinic_ai, inbound_to_blocked["call_id"], 120
            )
            after = await maria_ai.call("get_account_status")
            maria_calls_after = await maria_ai.call("list_calls", limit=50)
            answered = [c for c in maria_calls_after if c["duration_seconds"] > 0]
            report.evidence["quota"] = {
                "before": before, "blocked_status": blocked_status, "refusal": blocked,
                "call_to_blocked_account": callback, "after": after,
            }  # fmt: skip
            report.check(
                "A user at the free allowance cannot start another call",
                before["free_minutes_used"] >= 1.0
                and blocked_status["can_call"] is False
                and blocked_status["free_minutes_remaining"] == 0
                and bool(blocked)
                and "allowance" in blocked.lower(),
                f"used {before['free_minutes_used']} min of 1; refusal: {blocked!r}",
            )
            report.check(
                "A call to a user at the free allowance is not answered and uses no call time",
                [c["call_id"] for c in answered] == [maria_call]
                and after["free_minutes_used"] == before["free_minutes_used"]
                and callback.get("duration_seconds", 0) == 0,
                f"caller saw: {callback.get('status')}, {callback.get('duration_seconds')} s",
            )
            restored = await http.put(
                f"/api/v1/platform/operator/accounts/{maria['organization_id']}/allowance",
                headers=operator, json={"free_seconds": None},
            )  # fmt: skip
            report.check(
                "The operator restores the allowance and the user can call again",
                restored.status_code == 200
                and (await maria_ai.call("get_account_status"))["can_call"] is True,
            )

            # --- A revoked key stops working ----------------------------------
            revoke = await http.delete(
                f"/api/v1/user/api-keys/{clinic['api_key_id']}", headers=clinic["auth"]
            )
            revoked = await http.post(
                "/mcp/", json=initialize,
                headers={**mcp_headers, "Authorization": f"Bearer {clinic['api_key']}"},
            )  # fmt: skip
            report.check(
                "A key the user revoked is refused",
                revoke.status_code == 200 and revoked.status_code == 401,
                f"HTTP {revoked.status_code}",
            )
        finally:
            # Return the test numbers to the pool so the run can be repeated.
            for account in accounts:
                released = await http.post(
                    f"/api/v1/platform/operator/accounts/{account['organization_id']}/release-number",
                    headers=operator,
                )
                print(
                    f"released number of account {account['organization_id']}: HTTP {released.status_code}"
                )


def write_report(report: Report, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    report.evidence["finished_at"] = datetime.now(UTC).isoformat()
    result = {"passed": report.passed, "checks": report.checks, **report.evidence}
    (out_dir / "results.json").write_text(json.dumps(result, indent=2, default=str))
    lines = [
        "# Calling platform verification",
        "",
        f"- Result: **{'PASS' if report.passed else 'FAIL'}** "
        f"({sum(c['passed'] for c in report.checks)} of {len(report.checks)} checks)",
        f"- Service: {report.evidence.get('base_url')}",
        f"- Run: {report.evidence.get('run_id')} ({report.evidence.get('started_at')})",
        "",
        "| Check | Result | Detail |",
        "| --- | --- | --- |",
    ]
    for c in report.checks:
        detail = c["detail"].replace("|", "\\|").replace("\n", " ")[:300]
        lines.append(
            f"| {c['name']} | {'PASS' if c['passed'] else 'FAIL'} | {detail} |"
        )
    for title, key in (
        ("Outbound call, as the caller's assistant read it", "outbound_call"),
        ("Inbound call, as the clinic's assistant read it afterwards", "inbound_call"),
    ):
        call = report.evidence.get(key) or {}
        lines += ["", f"## {title}", "", f"Call {call.get('call_id')}: {call.get('status')}, "
                  f"{call.get('duration_seconds')} s, {call.get('from')} to {call.get('to')}",
                  "", "```", (call.get("transcript") or "(no transcript)").strip(), "```"]  # fmt: skip
        if call.get("result"):
            lines += [
                "",
                "Agent's own summary:",
                "",
                "```json",
                json.dumps(call["result"], indent=2),
                "```",
            ]
    (out_dir / "report.md").write_text("\n".join(lines) + "\n")
    print(f"\nWrote {out_dir / 'results.json'} and {out_dir / 'report.md'}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--base-url", default=os.getenv("VERIFY_BASE_URL", "http://localhost:8000")
    )
    parser.add_argument(
        "--operator-token", default=os.getenv("PLATFORM_OPERATOR_TOKEN", "")
    )
    parser.add_argument("--out", default="platform_verification/results/latest")
    parser.add_argument("--call-timeout", type=float, default=420)
    args = parser.parse_args()
    if not args.operator_token:
        print(
            "Set PLATFORM_OPERATOR_TOKEN: the run needs it for the allowance step and cleanup."
        )
        return 2
    report = Report()
    try:
        asyncio.run(run(args, report))
    except Exception as exc:  # A crash is a failed run with a written report.
        report.check(
            "The run finished without an unexpected error", False, repr(exc)[:500]
        )
    write_report(report, Path(args.out))
    return 0 if report.passed else 1


if __name__ == "__main__":
    sys.exit(main())
