"""End-to-end verification of the calling platform against a running service.

Two new users sign up. One is a dental clinic: the operator gives it a number
for inbound calls and it saves rules for that number. The other, Maria, has no
service number. She verifies a phone of her own as her caller ID, then asks her
assistant to book an appointment at the clinic. The assistant's call is a real
Twilio call, so one run exercises caller ID verification, an outbound call, an
inbound call answered by saved rules, the separation of the two accounts down
to their Twilio subaccounts, and the free-allowance block.

Only two approved test numbers are dialled: the clinic's number and the test
phone that plays Maria's own phone. See README.md.
"""

import argparse
import asyncio
import json
import os
import random
import re
import sys
import time
import urllib.parse
from datetime import UTC, datetime, timedelta
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
    "start_caller_id_verification",
    "update_settings",
}
TWILIO_API = "https://api.twilio.com/2010-04-01"
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


async def sign_up(
    http: httpx.AsyncClient, name: str, run_id: str, operator: dict | None = None
) -> dict:
    email = f"verify-{run_id}-{name.split()[0].lower()}@example.com"
    response = await http.post(
        "/api/v1/auth/signup",
        json={
            "email": email,
            "password": f"Verify-{run_id}-{random.random()}",
            "name": name,
        },
        # Sent only while public signup is closed.
        headers=operator or {},
    )
    response.raise_for_status()
    return await account_from(http, name, response.json(), email)


async def account_from(
    http: httpx.AsyncClient, name: str, body: dict, email: str | None = None
) -> dict:
    """The signed-in user with a new MCP key, from a sign-up or sign-in answer."""
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


class TestPhone:
    """Plays a person's own phone: answers Twilio's check call and keys the code.

    The phone is a Twilio number in the operator's main account. Its voice
    address is set to TwiML that sends the code as keypad tones.
    """

    def __init__(self, number: str, account_sid: str, auth_token: str) -> None:
        self.number = number
        self.account_sid = account_sid
        self.twilio = httpx.AsyncClient(
            base_url=TWILIO_API, auth=(account_sid, auth_token), timeout=30
        )

    async def _set_voice_url(self, url: str, method: str = "GET") -> None:
        found = await self.twilio.get(
            f"/Accounts/{self.account_sid}/IncomingPhoneNumbers.json",
            params={"PhoneNumber": self.number},
        )
        found.raise_for_status()
        sid = found.json()["incoming_phone_numbers"][0]["sid"]
        response = await self.twilio.post(
            f"/Accounts/{self.account_sid}/IncomingPhoneNumbers/{sid}.json",
            data={"VoiceUrl": url, "VoiceMethod": method},
        )
        response.raise_for_status()

    async def answer_with_code(self, code: str) -> None:
        tones = "w".join(code)
        twiml = (
            f'<Response><Pause length="5"/><Play digits="{tones}"/>'
            f'<Pause length="3"/><Play digits="{tones}"/><Pause length="15"/></Response>'
        )
        await self._set_voice_url(
            "https://twimlets.com/echo?Twiml=" + urllib.parse.quote(twiml)
        )

    async def answer_with_script(self, twiml_body: str) -> None:
        """Answer the next call by playing a fixed script, like a machine."""
        await self._set_voice_url(
            "https://twimlets.com/echo?Twiml="
            + urllib.parse.quote(f"<Response>{twiml_body}</Response>")
        )

    async def hang_up(self) -> None:
        await self._set_voice_url("")

    async def texts(self) -> dict[str, str]:
        """Text messages this phone received, newest 20, as sid -> body."""
        response = await self.twilio.get(
            f"/Accounts/{self.account_sid}/Messages.json",
            params={"To": self.number, "PageSize": 20},
        )
        response.raise_for_status()
        return {
            m["sid"]: m["body"]
            for m in response.json()["messages"]
            if m["direction"] == "inbound"
        }

    async def new_codes(self, seen: set[str], wait: float = 45) -> list[str]:
        """Codes in the texts that arrived since ``seen``. Waits for the first."""
        deadline = time.monotonic() + wait
        while True:
            fresh = {s: b for s, b in (await self.texts()).items() if s not in seen}
            codes = [m.group(1) for b in fresh.values() if (m := re.search(r"\b(\d{6})\b", b))]
            if codes or time.monotonic() > deadline:
                return codes
            await asyncio.sleep(3)

    async def subaccounts(self, organization_id: int) -> list[dict]:
        response = await self.twilio.get(
            "/Accounts.json",
            params={
                "FriendlyName": f"platform-org-{organization_id}",
                "Status": "active",
            },
        )
        response.raise_for_status()
        return response.json()["accounts"]

    async def calls_in(self, account_sid: str) -> list[dict]:
        response = await self.twilio.get(f"/Accounts/{account_sid}/Calls.json")
        response.raise_for_status()
        return response.json()["calls"]


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
    phone = TestPhone(args.test_phone, args.twilio_account_sid, args.twilio_auth_token)

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
            info = (await http.get("/api/v1/platform/info")).json()
            report.evidence["signup_open"] = info["signup_open"]
            invite = None if info["signup_open"] else operator
            # An email account costs nothing to make, so each one would be ten
            # more free minutes. Only the operator can make one, at any time.
            stranger = await http.post(
                "/api/v1/auth/signup",
                json={
                    "email": f"verify-{run_id}-stranger@example.com",
                    "password": f"Verify-{run_id}-{random.random()}",
                    "name": "Stranger",
                },
            )
            report.check(
                "A person without the operator secret cannot make an email account",
                stranger.status_code == 403,
                f"HTTP {stranger.status_code}",
            )
            clinic = await sign_up(http, "Riverside Dental", run_id, operator)
            accounts.append(clinic)

            # --- Maria signs up with her phone number and a text code ---------
            # Ways phone sign-in can go wrong:
            # 1. a wrong code, or the code of a different number, signs in
            # 2. a code works two times
            # 3. a person can guess codes without a limit
            # 4. the service sends a text for each request (the operator pays)
            # 5. a number outside the United States and Canada gets a text
            # 6. while signup is closed, a stranger's number gets a text
            # 7. the same phone gets a second account with new free minutes
            start_url = "/api/v1/platform/auth/start"
            check_url = "/api/v1/platform/auth/verify"
            release_url = "/api/v1/platform/operator/phone-identities/release"
            me = {"phone_number": phone.number}

            async def try_code(code: str, number: str = phone.number, headers=None):
                return await http.post(
                    check_url, json={"phone_number": number, "code": code},
                    headers=headers or {},
                )  # fmt: skip

            def other_code(code: str) -> str:
                return f"{(int(code) + 1) % 1000000:06d}"

            # A run that stopped early can leave the phone bound to an account.
            (await http.post(release_url, headers=operator, json=me)).raise_for_status()
            seen = set(await phone.texts())
            abroad_start = await http.post(
                start_url, json={"phone_number": "+442079460958"}, headers=invite or {}
            )
            closed_start = await http.post(start_url, json=me) if invite else None
            first_start = await http.post(start_url, json=me, headers=invite or {})
            second_start = await http.post(start_url, json=me, headers=invite or {})
            codes = await phone.new_codes(seen)
            await asyncio.sleep(10)
            codes = await phone.new_codes(seen, wait=0)
            report.check(
                "A sign-in request sends one text with a code; a second request "
                "in the same minute, a number abroad, and a stranger while "
                "signup is closed get no text",
                first_start.status_code == 200
                and second_start.status_code == 429
                and abroad_start.status_code in (400, 403)
                and (closed_start is None or closed_start.status_code == 403)
                and len(codes) == 1,
                f"first {first_start.status_code}, second {second_start.status_code}, "
                f"abroad {abroad_start.status_code}, closed "
                f"{closed_start.status_code if closed_start else 'n/a'}, texts {len(codes)}",
            )
            code = codes[0] if codes else "000000"
            wrong = await try_code(other_code(code), headers=invite)
            other_number = await try_code(code, UNAPPROVED_NUMBER, headers=invite)
            signed_up = await try_code(code, headers=invite)
            replay = await try_code(code, headers=invite)
            report.check(
                "Only the right code for the right number signs in, and a code "
                "works one time",
                wrong.status_code == 401
                and other_number.status_code in (400, 401)
                and signed_up.status_code == 200
                and replay.status_code == 401,
                f"wrong {wrong.status_code}, other number {other_number.status_code}, "
                f"right {signed_up.status_code}, replay {replay.status_code}",
            )
            signed_up.raise_for_status()
            maria = await account_from(http, "Maria Lopez", signed_up.json())
            accounts.append(maria)

            # A new code, five wrong guesses, then the right code: refused.
            await asyncio.sleep(61)
            seen = set(await phone.texts())
            (await http.post(start_url, json=me)).raise_for_status()
            guess_code = (await phone.new_codes(seen) or ["000000"])[0]
            guesses = [
                (await try_code(other_code(guess_code))).status_code for _ in range(5)
            ]
            after_guesses = await try_code(guess_code)
            # The same phone signs in again: the same account, no new one.
            await asyncio.sleep(61)
            seen = set(await phone.texts())
            (await http.post(start_url, json=me)).raise_for_status()
            again_code = (await phone.new_codes(seen) or ["000000"])[0]
            signed_in = await try_code(again_code)
            same_account = (
                signed_in.status_code == 200
                and signed_in.json()["user"]["organization_id"]
                == maria["organization_id"]
            )
            report.check(
                "After five wrong guesses the code is dead, and the same phone "
                "signs in to the same account, not a new one",
                guesses == [401] * 5
                and after_guesses.status_code == 401
                and same_account
                and len({code, guess_code, again_code}) == 3,
                f"guesses {guesses}, right code after them {after_guesses.status_code}, "
                f"same account {same_account}",
            )
            clinic_ai = Assistant(mcp_url, clinic["api_key"])
            maria_ai = Assistant(mcp_url, maria["api_key"])

            clinic_tools = await clinic_ai.tool_names()
            maria_tools = await maria_ai.tool_names()
            report.check(
                "A standard MCP client connects with a user's key and lists the calling tools",
                clinic_tools == EXPECTED_TOOLS and maria_tools == EXPECTED_TOOLS,
                f"tools: {sorted(maria_tools)}",
            )

            # --- A new account has its own Twilio subaccount and no number ----
            await clinic_ai.call("get_account_status")
            maria_status = await maria_ai.call("get_account_status")
            clinic_subs = await phone.subaccounts(clinic["organization_id"])
            maria_subs = await phone.subaccounts(maria["organization_id"])
            report.check(
                "Each new user gets a separate account with its own Twilio subaccount, its own allowance, and no bought number",
                clinic["organization_id"] != maria["organization_id"]
                and len(clinic_subs) == 1
                and len(maria_subs) == 1
                and clinic_subs[0]["sid"] != maria_subs[0]["sid"]
                and {clinic_subs[0]["status"], maria_subs[0]["status"]} == {"active"}
                and args.twilio_account_sid
                not in (clinic_subs[0]["sid"], maria_subs[0]["sid"])
                and maria_status["phone_number"] is None
                and maria_status["caller_id"] is None
                and maria_status["can_call"] is False
                and maria_status["minutes_used"] == 0,
                f"accounts {clinic['organization_id']} and {maria['organization_id']}; "
                f"subaccounts ...{clinic_subs[0]['sid'][-6:] if clinic_subs else '?'} and "
                f"...{maria_subs[0]['sid'][-6:] if maria_subs else '?'}; "
                f"{maria_status['minutes_total']} free minutes each",
            )
            maria["subaccount_sid"] = maria_subs[0]["sid"]
            clinic["subaccount_sid"] = clinic_subs[0]["sid"]

            # --- The operator gives the clinic a number for inbound calls -----
            assigned = await http.post(
                f"/api/v1/platform/operator/accounts/{clinic['organization_id']}/assign-number",
                headers=operator,
            )
            assigned.raise_for_status()
            clinic["phone_number"] = (await clinic_ai.call("get_account_status"))[
                "phone_number"
            ]
            self_assign = await http.post(
                f"/api/v1/platform/operator/accounts/{maria['organization_id']}/assign-number",
                headers=maria["auth"],
            )
            report.check(
                "Only the operator can give an account a number for inbound calls",
                bool(clinic["phone_number"])
                and clinic["phone_number"] != phone.number
                and self_assign.status_code == 404,
                f"clinic number {clinic['phone_number']}; user attempt: HTTP {self_assign.status_code}",
            )

            # --- Maria verifies her own phone as her caller ID ----------------
            no_caller_id = await maria_ai.refusal(
                "place_call", phone_number=clinic["phone_number"], task="Say hello."
            )
            stranger_phone = (
                await maria_ai.refusal(
                    "start_caller_id_verification", phone_number=UNAPPROVED_NUMBER
                )
                if maria_status["test_period"]
                else "skipped: the service is past its test period"
            )
            started = await maria_ai.call(
                "start_caller_id_verification", phone_number=phone.number
            )
            # Maria's phone rings; she answers and keys in the code.
            await phone.answer_with_code(started["validation_code"])
            verified_status: dict = {}
            for _ in range(18):
                await asyncio.sleep(5)
                verified_status = await maria_ai.call("get_account_status")
                if verified_status["caller_id"]:
                    break
            await phone.hang_up()
            maria["caller_id"] = verified_status.get("caller_id")
            report.check(
                "A user with no caller ID cannot place a call, and cannot make the service phone an unapproved number for a check",
                bool(no_caller_id)
                and "caller id" in no_caller_id.lower()
                and bool(stranger_phone),
                f"no caller ID: {no_caller_id!r}",
            )
            report.check(
                "A user verifies a phone they own with a keypad code and then calls from that number, with no number bought",
                started["status"] == "calling"
                and len(started["validation_code"]) == 6
                and maria["caller_id"] == phone.number
                and verified_status["outbound_calls_from"] == phone.number
                and verified_status["phone_number"] is None
                and verified_status["can_call"] is True,
                f"caller ID {maria['caller_id']}",
            )
            taken = await clinic_ai.refusal(
                "start_caller_id_verification", phone_number=phone.number
            )
            report.check(
                "A phone number that belongs to one account cannot be the "
                "caller ID of a different account",
                bool(taken) and "another account" in taken.lower(),
                f"refusal: {taken!r}",
            )
            clinic_steal = await clinic_ai.call("get_account_status")
            report.check(
                "The other user's account does not gain that caller ID",
                clinic_steal["caller_id"] is None
                and clinic_steal["outbound_calls_from"] == clinic["phone_number"],
            )
            report.evidence["accounts"] = [
                {
                    "name": a["name"],
                    "email": a["email"],
                    "organization_id": a["organization_id"],
                    "phone_number": a.get("phone_number"),
                    "caller_id": a.get("caller_id"),
                }
                for a in accounts
            ]
            if not (clinic["phone_number"] and maria["caller_id"]):
                return

            # --- The clinic saves how its number is answered ------------------
            greeting = "Riverside Dental, this is the front desk. How can I help you?"
            rules = (
                "You are the front desk of Riverside Dental, a dental clinic. "
                "The clinic is open Monday to Thursday, 8 am to 5 pm. It is closed on "
                "Wednesday mornings for staff training, so never offer a Wednesday morning. "
                "The only free cleaning appointments next week are Tuesday at 2:30 pm and "
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
                "place_call", phone_number=maria["caller_id"], task="Say hello."
            )
            malformed = await maria_ai.refusal(
                "place_call", phone_number="2025550143", task="Say hello."
            )
            # Numbers reserved for fiction, in the United Kingdom and in the
            # premium-rate 900 range. The service must refuse both at any time.
            abroad = await maria_ai.refusal(
                "place_call", phone_number="+442079460958", task="Say hello."
            )
            premium = await maria_ai.refusal(
                "place_call", phone_number="+19005550143", task="Say hello."
            )
            after_refusals = await maria_ai.call("list_calls", limit=50)
            report.check(
                "Calls to an unapproved number, the user's own number, and a malformed number are refused and start nothing",
                all([unapproved, own, malformed]) and after_refusals == [],
                f"unapproved: {unapproved!r}",
            )
            report.check(
                "Calls to a number outside the United States and Canada, and to a premium-rate number, are refused and start nothing",
                "+1" in (abroad or "")
                and "United States and Canada" in (premium or "")
                and after_refusals == [],
                f"abroad: {abroad!r}; premium: {premium!r}",
            )

            # --- Maria's assistant places the call. No clinic assistant is ---
            # --- connected: every clinic MCP session above is closed. --------
            task = (
                "Call Riverside Dental and book a teeth cleaning for Maria Lopez, who is "
                "a new patient. She prefers Wednesday morning. If Wednesday morning is not "
                "possible, take the earliest morning appointment next week; she cannot come "
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
                    "Callback number: " + maria["caller_id"]
                ),
                on_behalf_of="Maria Lopez",
            )
            report.check(
                "place_call starts a call and returns a call id at once",
                isinstance(placed.get("call_id"), int)
                and placed["from"] == maria["caller_id"]
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
                and inbound.get("from") == maria["caller_id"]
                and inbound.get("status") == "completed"
                and "front desk" in said.lower()
                and code_digits in spoken_digits(said)
                and "thursday" in said.lower(),
                f"{len(in_turns)} turns; from {inbound.get('from')}",
            )

            # --- Twilio itself keeps the two users' calls apart ---------------
            maria_twilio = await phone.calls_in(maria["subaccount_sid"])
            clinic_twilio = await phone.calls_in(clinic["subaccount_sid"])
            report.check(
                "Twilio recorded the outbound leg in the caller's subaccount and the inbound leg in the clinic's subaccount",
                any(
                    c["direction"] == "outbound-api"
                    and c["to"] == clinic["phone_number"]
                    for c in maria_twilio
                )
                and any(
                    c["direction"] == "inbound" and c["from"] == maria["caller_id"]
                    for c in clinic_twilio
                )
                and not any(c["direction"] == "inbound" for c in maria_twilio),
                f"{len(maria_twilio)} call records in the caller's subaccount, "
                f"{len(clinic_twilio)} in the clinic's",
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
                == {
                    "phone_number",
                    "task",
                    "background",
                    "on_behalf_of",
                    "call_reason",
                    "voicemail_message",
                }
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

            # --- The user changes the voice through MCP -----------------------
            voices = (await clinic_ai.call("get_account_status"))["voice_options"]
            if voices:
                new_voice = next(v for v in voices if v != "eve")
                changed = await clinic_ai.call("update_settings", voice=new_voice)
                bad_voice = await clinic_ai.refusal("update_settings", voice="nobody")
                report.check(
                    "A user changes the agent's voice through MCP, and the other user's voice does not change",
                    changed["voice"] == new_voice
                    and (await clinic_ai.call("get_account_status"))["voice"]
                    == new_voice
                    and (await maria_ai.call("get_account_status"))["voice"] == "eve"
                    and bool(bad_voice),
                    f"clinic voice: {new_voice}; unknown voice: {bad_voice!r}",
                )

            # --- A voicemail box answers --------------------------------------
            # The test phone plays a voicemail greeting. The clinic's agent
            # must leave the message it was given and end the call.
            callback_code = f"{random.randint(100, 999)}"
            await phone.answer_with_script(
                '<Pause length="1"/><Say>Hi, you have reached Sam Carter. I can not '
                "take your call right now. Please leave a message after the tone."
                '</Say><Pause length="40"/>'
            )
            voicemail_call = await clinic_ai.call(
                "place_call",
                phone_number=phone.number,
                task="Remind Sam Carter of the cleaning appointment on Thursday at 9 am.",
                on_behalf_of="Riverside Dental",
                call_reason="about an appointment on Thursday",
                voicemail_message=(
                    "Hello, this is the assistant of Riverside Dental with a reminder "
                    "of your cleaning on Thursday at nine. To change it, call us and "
                    f"give the reference {' '.join(callback_code)}. Goodbye."
                ),
            )
            voicemail = await wait_for_call(clinic_ai, voicemail_call["call_id"], 150)
            report.evidence["voicemail_call"] = voicemail
            vm_said = " ".join(
                text
                for role, text in transcript_turns(voicemail.get("transcript", ""))
                if role == "assistant"
            )
            report.check(
                "When a voicemail box answers, the agent leaves the given message, ends the call, and reports voicemail",
                voicemail.get("answered_by") == "voicemail"
                and voicemail.get("voicemail_message_left") is True
                and callback_code in spoken_digits(vm_said)
                and "thursday" in vm_said.lower()
                and 0 < voicemail.get("duration_seconds", 0) <= 60,
                f"answered_by {voicemail.get('answered_by')}, "
                f"{voicemail.get('duration_seconds')} s; agent said: {vm_said[:160]!r}",
            )

            # --- A call screener answers, then the person picks up ------------
            # The test phone asks for name and reason, holds, and then a
            # "person" comes on the line and gives a price that is random for
            # each run.
            price, price_words = random.choice(
                [(140, "forty"), (160, "sixty"), (180, "eighty")]
            )

            def has_price(text: str) -> bool:
                # Speech-to-text writes "160" or "one hundred sixty".
                return str(price) in text or f"hundred {price_words}" in text.replace(
                    " and ", " "
                )

            await phone.answer_with_script(
                "<Say>Hi. Before I try to connect you, please say your name and the "
                'reason for your call.</Say><Pause length="9"/>'
                '<Say>Thank you. Please stay on the line.</Say><Pause length="4"/>'
                '<Say>Hello, this is Sam Carter speaking. Go ahead.</Say><Pause length="14"/>'
                f"<Say>Yes, the bike is still for sale. The price is {price} dollars. "
                'That is all I can tell you. Goodbye.</Say><Pause length="20"/>'
            )
            screened_call = await clinic_ai.call(
                "place_call",
                phone_number=phone.number,
                task=(
                    "Ask Sam Carter if the bike in his advertisement is still for "
                    "sale, and what the price is. Bring back both answers."
                ),
                on_behalf_of="Dana Reyes",
                call_reason="about the bike you advertised",
            )
            screened = await wait_for_call(clinic_ai, screened_call["call_id"], 180)
            report.evidence["screened_call"] = screened
            screened_turns = transcript_turns(screened.get("transcript", ""))
            sc_said = " ".join(t for r, t in screened_turns if r == "assistant").lower()
            sc_heard = " ".join(t for r, t in screened_turns if r == "user").lower()
            report.check(
                "When a call screener answers, the agent gives the name and reason, waits, and then does the task with the person",
                screened.get("call_screener_detected") is True
                and screened.get("answered_by") == "person"
                and "dana reyes" in sc_said
                and "bike" in sc_said
                and "sam" in sc_said
                and sc_said.index("dana reyes") < sc_said.index("sam")
                and has_price(sc_heard)
                and has_price(sc_said),
                f"answered_by {screened.get('answered_by')}, screener "
                f"{screened.get('call_screener_detected')}, {screened.get('duration_seconds')} s, "
                f"price {price}; agent said: {sc_said[:220]!r}",
            )
            # Sam's side ends the call right after the price. The result must
            # not depend on the agent reaching its own closing step.
            for _ in range(4):
                if (screened.get("result") or {}).get("outcome_summary"):
                    break
                await asyncio.sleep(10)
                screened = await clinic_ai.call(
                    "get_call_result", call_id=screened_call["call_id"]
                )
            sc_summary = str(
                (screened.get("result") or {}).get("outcome_summary") or ""
            )
            report.check(
                "When the other person ends the call first, the assistant still gets a result summary with the answer",
                str(price) in sc_summary.replace(",", "")
                or f"hundred {price_words}" in sc_summary.lower().replace(" and ", " "),
                f"ended by {screened.get('disposition')}; summary: {sc_summary[:200]!r}",
            )
            await phone.hang_up()
            report.check(
                "A call that a person answered reports that a person answered",
                outbound.get("answered_by") == "person"
                and not outbound.get("call_screener_detected"),
                f"answered_by {outbound.get('answered_by')}",
            )

            # --- The free allowance blocks further calls ----------------------
            # Both users have used real call time. The operator sets an
            # allowance of one minute so the limit is reached without ten
            # minutes of calls.
            def allowance_url(account: dict) -> str:
                return f"/api/v1/platform/operator/accounts/{account['organization_id']}/allowance"

            before = await maria_ai.call("get_account_status")
            limited = await http.put(
                allowance_url(maria), headers=operator, json={"free_seconds": 60}
            )
            limited.raise_for_status()
            blocked_status = await maria_ai.call("get_account_status")
            blocked = await maria_ai.refusal(
                "place_call", phone_number=clinic["phone_number"], task=task
            )
            restored = await http.put(
                allowance_url(maria), headers=operator, json={"free_seconds": None}
            )
            restored_status = await maria_ai.call("get_account_status")
            report.check(
                "A user at the free allowance cannot start another call",
                before["minutes_used"] >= 1.0
                and blocked_status["can_call"] is False
                and blocked_status["minutes_remaining"] == 0
                and blocked_status["plan"] is None
                and bool(blocked)
                and "monthly plan" in blocked.lower(),
                f"used {before['minutes_used']} min of 1; refusal: {blocked!r}",
            )
            # --- Monthly plans -------------------------------------------------
            # Maria has used her free minutes (allowance of one minute, more
            # than one minute of calls in this run). Ways a plan can go wrong:
            # 1. a plan does not unblock an account whose free minutes are used
            # 2. calls from before the period count against the period
            # 3. a plan with all its minutes used still allows calls
            # 4. a renewal does not start the count again
            # 5. a plan whose period is over still allows calls
            # 6. an account gets its free minutes again when the plan ends
            # 7. a user gives a plan to their own account
            # 8. a period that ends before it starts is accepted
            (await http.put(
                allowance_url(maria), headers=operator, json={"free_seconds": 60}
            )).raise_for_status()

            def plan_url(account: dict) -> str:
                return f"/api/v1/platform/operator/accounts/{account['organization_id']}/plan"

            async def set_plan(seconds: int, start: datetime, end: datetime):
                return await http.put(
                    plan_url(maria), headers=operator,
                    json={
                        "name": "Starter", "included_seconds": seconds,
                        "period_start": start.isoformat(), "period_end": end.isoformat(),
                    },
                )  # fmt: skip

            now = datetime.now(UTC)
            by_tenant = await http.put(
                plan_url(maria), headers=maria["auth"],
                json={
                    "name": "Starter", "included_seconds": 6000,
                    "period_start": now.isoformat(),
                    "period_end": (now + timedelta(days=30)).isoformat(),
                },
            )  # fmt: skip
            backwards = await set_plan(6000, now, now - timedelta(days=1))
            still_blocked = await maria_ai.call("get_account_status")
            report.check(
                "A user cannot give a plan to their own account, and a period "
                "that ends before it starts is refused",
                by_tenant.status_code == 404
                and backwards.status_code == 422
                and still_blocked["can_call"] is False
                and still_blocked["plan"] is None,
                f"tenant {by_tenant.status_code}, backwards {backwards.status_code}",
            )

            # The period starts now: the calls from before it must not count.
            (await set_plan(6000, now, now + timedelta(days=30))).raise_for_status()
            on_plan = await maria_ai.call("get_account_status")
            report.check(
                "A monthly plan unblocks a user whose free minutes are used, "
                "and earlier calls do not count against the plan",
                on_plan["can_call"] is True
                and on_plan["plan"] == "Starter"
                and on_plan["minutes_total"] == 100
                and on_plan["minutes_used"] == 0
                and on_plan["plan_period_end"] is not None,
                f"status {({k: on_plan[k] for k in ('plan', 'minutes_total', 'minutes_used', 'can_call')})}",
            )

            # The period covers this run's calls and holds one minute.
            (await set_plan(
                60, now - timedelta(hours=2), now + timedelta(days=30)
            )).raise_for_status()
            plan_used = await maria_ai.call("get_account_status")
            plan_refusal = await maria_ai.refusal(
                "place_call", phone_number=clinic["phone_number"], task=task
            )
            # Renewal: the same plan, a new period that starts now.
            (await set_plan(60, datetime.now(UTC), now + timedelta(days=60))).raise_for_status()
            renewed = await maria_ai.call("get_account_status")
            report.check(
                "A plan with its minutes used blocks calls until the renewal "
                "starts the count again",
                plan_used["can_call"] is False
                and plan_used["minutes_remaining"] == 0
                and bool(plan_refusal)
                and "starter" in plan_refusal.lower()
                and "renew" in plan_refusal.lower()
                and renewed["can_call"] is True
                and renewed["minutes_used"] == 0,
                f"refusal: {plan_refusal!r}; after renewal used {renewed['minutes_used']}",
            )

            # The period is over and nobody renewed. The free minutes are
            # already used, so the account must be blocked, not free again.
            (await set_plan(
                6000, now - timedelta(days=30), now - timedelta(minutes=1)
            )).raise_for_status()
            lapsed = await maria_ai.call("get_account_status")
            lapsed_refusal = await maria_ai.refusal(
                "place_call", phone_number=clinic["phone_number"], task=task
            )
            report.check(
                "When a plan period is over without a renewal the user cannot "
                "call and does not get the free minutes again",
                lapsed["can_call"] is False
                and lapsed["plan"] is None
                and bool(lapsed_refusal)
                and "monthly plan" in lapsed_refusal.lower(),
                f"refusal: {lapsed_refusal!r}",
            )
            report.evidence["plans"] = {
                "on_plan": on_plan, "plan_used": plan_used, "plan_refusal": plan_refusal,
                "renewed": renewed, "lapsed": lapsed, "lapsed_refusal": lapsed_refusal,
            }  # fmt: skip

            # Maria keeps an active plan and no free minutes for the real call
            # below: the call-start path must accept the plan too.
            (await set_plan(
                6000, datetime.now(UTC), datetime.now(UTC) + timedelta(days=30)
            )).raise_for_status()
            report.check(
                "The operator restores the allowance and the user can call again",
                restored.status_code == 200 and restored_status["can_call"] is True,
            )

            # An account at its limit must not cost the operator inbound
            # minutes either: the clinic is now at its limit and Maria calls it.
            clinic_before = await clinic_ai.call("get_account_status")
            answered_before = {
                c["call_id"]
                for c in await clinic_ai.call("list_calls", limit=50)
                if c["duration_seconds"] > 0
            }
            (
                await http.put(
                    allowance_url(clinic), headers=operator, json={"free_seconds": 60}
                )
            ).raise_for_status()
            to_blocked = await maria_ai.call(
                "place_call",
                phone_number=clinic["phone_number"],
                task="Ask if the clinic is open on Friday.",
                on_behalf_of="Maria Lopez",
            )
            callback = await wait_for_call(maria_ai, to_blocked["call_id"], 120)
            ended_plan = await http.delete(plan_url(maria), headers=operator)
            report.check(
                "A user on a plan, with the free minutes used, places a real "
                "call; the operator can end the plan",
                bool(to_blocked.get("call_id"))
                and ended_plan.status_code == 200
                and (await maria_ai.call("get_account_status"))["plan"] is None,
                f"call {to_blocked.get('call_id')}, end plan {ended_plan.status_code}",
            )
            (await http.put(
                allowance_url(maria), headers=operator, json={"free_seconds": None}
            )).raise_for_status()
            clinic_after = await clinic_ai.call("get_account_status")
            clinic_calls_after = await clinic_ai.call("list_calls", limit=50)
            answered = {
                c["call_id"] for c in clinic_calls_after if c["duration_seconds"] > 0
            }
            report.evidence["quota"] = {
                "before": before, "blocked_status": blocked_status, "refusal": blocked,
                "call_to_blocked_account": callback, "clinic_after": clinic_after,
            }  # fmt: skip
            report.check(
                "A call to a user at the free allowance is not answered and uses no call time",
                clinic_before["minutes_used"] >= 1.0
                and answered == answered_before
                and clinic_after["minutes_used"]
                == clinic_before["minutes_used"]
                and callback.get("duration_seconds", 0) == 0,
                f"caller saw: {callback.get('status')}, {callback.get('duration_seconds')} s",
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
            # Take back the clinic's number and close both test subaccounts so
            # the run can be repeated and leaves nothing behind in Twilio.
            await phone.hang_up()
            for account in accounts:
                closed_account = await http.post(
                    f"/api/v1/platform/operator/accounts/{account['organization_id']}/close",
                    headers=operator,
                )
                print(
                    f"closed account {account['organization_id']}: HTTP {closed_account.status_code}"
                )
            released = await http.post(
                "/api/v1/platform/operator/phone-identities/release",
                headers=operator, json={"phone_number": phone.number},
            )  # fmt: skip
            print(f"released the test phone: HTTP {released.status_code}")
            await phone.twilio.aclose()


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
        ("Call answered by a voicemail box", "voicemail_call"),
        ("Call answered by a call screener, then a person", "screened_call"),
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
    parser.add_argument(
        "--test-phone",
        default=os.getenv("VERIFY_TEST_PHONE", ""),
        help="An approved test number in the operator's main Twilio account. "
        "It plays the phone a user owns.",
    )
    parser.add_argument(
        "--twilio-account-sid", default=os.getenv("PLATFORM_TWILIO_ACCOUNT_SID", "")
    )
    parser.add_argument(
        "--twilio-auth-token", default=os.getenv("PLATFORM_TWILIO_AUTH_TOKEN", "")
    )
    parser.add_argument("--out", default="platform_verification/results/latest")
    parser.add_argument("--call-timeout", type=float, default=420)
    args = parser.parse_args()
    if not args.operator_token:
        print(
            "Set PLATFORM_OPERATOR_TOKEN: the run needs it for the allowance step and cleanup."
        )
        return 2
    if not (args.test_phone and args.twilio_account_sid and args.twilio_auth_token):
        print(
            "Set VERIFY_TEST_PHONE, PLATFORM_TWILIO_ACCOUNT_SID, and "
            "PLATFORM_TWILIO_AUTH_TOKEN: the run answers Twilio's check call "
            "on the test phone and reads the subaccounts."
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
