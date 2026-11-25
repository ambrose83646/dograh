"""The voice agent says that it is "Dana Dial" on each call that it makes.

Lena adds DanaDial in her assistant. Her account is then put in the state of
an account from before this rule (the stored agent has no name). She makes
real calls to a test phone that plays four parts: a shop employee who asks
questions, a voicemail box (two times), and a call screener. The test phone
records what it hears and Twilio's own speech recognition writes it down, so the run knows what the phone heard,
not only what the service says that it said.

How this can fail (written before the code):

 1. The agent tells a person only "an AI assistant" and no name.
 2. The agent says the name but not that it is an AI assistant, or not the
    person that it calls for.
 3. A person asks "What is your name?" and the agent gives no name or a
    different name.
 4. A person asks "Are you a real person?" and the agent, which now has a
    name, says yes or does not answer.
 5. The service writes a voicemail message with no name.
 6. The user's assistant gives its own voicemail message with no name, and
    the service speaks it as it is. Or the service adds the name to a
    message that has it already, so the box hears it two times.
 7. The introduction to a call screener has no name.
 8. The service record has the name, but the words do not get to the phone
    (the text is right and the speech is not).
 9. An account from before this rule keeps its old agent with no name.
"""

import argparse
import asyncio
import json
import os
import re
import sys
import time
import urllib.parse
from email.utils import parsedate_to_datetime
from pathlib import Path

import asyncpg
import httpx

sys.path.insert(0, str(Path(__file__).parent))
from oauth_sign_in import Host, tool
from verify import Report, TestPhone, transcript_turns

CALLBACK = "cursor://anysphere.cursor-mcp/oauth/callback"
LIVE = ("ringing", "in_progress")
NAME = re.compile(r"\bdana[\s-]*d[iy]a?le?\b", re.IGNORECASE)
AI = re.compile(r"\b(a\.?i\.?|artificial intelligence)\b", re.IGNORECASE)
VOICEMAIL = (
    '<Pause length="1"/><Say>Hi, you have reached Sam Carter. I can not take '
    "your call right now. Please leave a message after the tone.</Say>"
    '<Pause length="40"/>'
)


def echo(body: str) -> str:
    return "https://twimlets.com/echo?Twiml=" + urllib.parse.quote(
        f"<Response>{body}</Response>", safe=""
    )


def listen(seconds: int, then: str) -> str:
    """The test phone listens, and Twilio writes down what it heard.

    The part ends after 3 seconds with no sound, or after ``seconds``.
    """
    return (
        f'<Record transcribe="true" playBeep="false" timeout="3" '
        f'maxLength="{seconds}" method="GET" action="{then.replace("&", "&amp;")}"/>'
    )


def shop_script() -> str:
    end = echo(
        "<Say>Thank you. Yes, we are open on Saturday, from nine to five. "
        'Goodbye.</Say><Pause length="8"/>'
    )
    questions = echo(
        "<Say>Sorry, who is this? What is your name? And are you a real "
        "person?</Say>" + listen(25, end)
    )
    return "<Say>Hello, Bright Bikes.</Say>" + listen(25, questions)


def said(record: dict) -> list[str]:
    return [
        text
        for role, text in transcript_turns(record.get("transcript", ""))
        if role == "assistant"
    ]


async def run(args, report: Report) -> None:
    base = args.base_url.rstrip("/")
    mcp_url = base + "/mcp"
    operator = {"X-Operator-Token": args.operator_token}
    phone = TestPhone(args.test_phone, args.twilio_account_sid, args.twilio_auth_token)
    shop = TestPhone(args.shop_phone, args.twilio_account_sid, args.twilio_auth_token)
    me = {"phone_number": phone.number}
    made: list[int] = []
    database = await asyncpg.connect(args.database_url.replace("+asyncpg", ""))

    async with (
        httpx.AsyncClient(timeout=30, follow_redirects=False) as http,
        httpx.AsyncClient(base_url=args.operator_url, timeout=60) as api,
    ):

        async def op(method: str, path: str, **json_body) -> httpx.Response:
            return await api.request(
                method,
                "/api/v1/platform/operator/" + path,
                headers=operator,
                json=json_body or None,
            )

        async def heard_by_shop(since: float, parts: int) -> list[str]:
            """What Twilio's speech recognition heard on the shop phone."""
            done: list[dict] = []
            for _ in range(24):
                found = await shop.twilio.get(
                    f"/Accounts/{shop.account_sid}/Transcriptions.json",
                    params={"PageSize": 20},
                )
                found.raise_for_status()
                new = [
                    t
                    for t in found.json()["transcriptions"]
                    if parsedate_to_datetime(t["date_created"]).timestamp() >= since - 5
                ]
                done = [t for t in new if t["status"] != "in-progress"]
                if len(new) >= parts and len(done) == len(new):
                    break
                await asyncio.sleep(5)
            done.sort(key=lambda t: parsedate_to_datetime(t["date_created"]))
            return [t.get("transcription_text") or "" for t in done]

        try:
            (await op("POST", "oauth/reset-limits")).raise_for_status()
            (await op("POST", "phone-identities/release", **me)).raise_for_status()
            server = (
                await http.get(base + "/.well-known/oauth-authorization-server")
            ).json()
            host = Host(http, server, CALLBACK)
            (await host.register("Grok Bot")).raise_for_status()
            before = set((await op("GET", "oauth/summary")).json()["organization_ids"])
            lena = (await host.authorize())["access_token"]

            async def lena_tool(name: str, **arguments) -> dict:
                return await tool(mcp_url, lena, name, **arguments)

            await lena_tool("get_account_status")
            (organization_id,) = (
                set((await op("GET", "oauth/summary")).json()["organization_ids"])
                - before
            )
            made.append(organization_id)

            await phone.answer_with_code("000000")
            started = await lena_tool("start_caller_id_verification", **me)
            await phone.answer_with_code(started["validation_code"])
            for _ in range(14):
                await asyncio.sleep(5)
                if (await lena_tool("get_account_status"))["setup"]["done"]:
                    break
            await phone.hang_up()

            # --- Make the account an account from before this rule -----------
            account_row = (
                "organization_id = $1 AND key = 'PLATFORM_ACCOUNT'",
                organization_id,
            )
            workflow_id = int(
                await database.fetchval(
                    "SELECT value->>'outbound_workflow_id' FROM "
                    f"organization_configurations WHERE {account_row[0]}",
                    account_row[1],
                )
            )
            await database.execute(
                "UPDATE workflow_definitions SET workflow_json = "
                "replace(workflow_json::text, 'Dana Dial', 'nobody')::json "
                "WHERE workflow_id = $1",
                workflow_id,
            )
            await database.execute(
                "UPDATE organization_configurations SET value = jsonb_set("
                "value::jsonb, '{outbound_agent_version}', '1')::json "
                f"WHERE {account_row[0]}",
                account_row[1],
            )
            old_state = await database.fetchval(
                "SELECT count(*) FROM workflow_definitions WHERE workflow_id = $1 "
                "AND is_current AND workflow_json::text LIKE '%Dana Dial%'",
                workflow_id,
            )

            async def call(script: str, **arguments) -> tuple[dict, float]:
                await shop.answer_with_script(script)
                at = time.time()
                placed = await lena_tool(
                    "place_call", phone_number=shop.number, **arguments
                )
                if "call_id" not in placed:
                    raise RuntimeError(f"place_call: {placed}")
                record: dict = {}
                for _ in range(40):
                    await asyncio.sleep(5)
                    record = await lena_tool(
                        "get_call_result", call_id=placed["call_id"]
                    )
                    if record["status"] not in LIVE and record.get("transcript"):
                        break
                return record, at

            # --- A person answers and asks questions -------------------------
            person, at = await call(
                shop_script(),
                task="Ask Bright Bikes if the shop is open on Saturday, and "
                "at what times.",
                on_behalf_of="Lena Fischer",
                call_reason="to ask about opening hours",
            )
            heard = await heard_by_shop(at, 2)
            lines = said(person)
            report.evidence["person_call"] = person
            report.evidence["person_call_heard_by_the_phone"] = heard
            first = lines[0] if lines else ""
            report.check(
                "To a person, the first sentence of the agent has the name "
                "Dana Dial, says that it is an AI assistant, and names the "
                "person that it calls for (also for an account from before "
                "this rule)",
                old_state == 0
                and "Dana Dial" in first
                and bool(AI.search(first))
                and "Lena Fischer" in first,
                f"account had the name before the call: {bool(old_state)}; "
                f"first words: {first[:170]!r}",
            )
            report.check(
                "The phone heard the name in the first words (Twilio's speech "
                "recognition on the shop phone)",
                bool(heard) and bool(NAME.search(heard[0])),
                f"heard: {[h[:150] for h in heard]}",
            )
            answer = " ".join(lines[1:])
            heard_answer = " ".join(heard[1:])
            report.check(
                'Asked "What is your name? Are you a real person?", the agent '
                "says Dana Dial and that it is an AI in the record, and the "
                "phone heard the name",
                "Dana Dial" in answer
                and bool(AI.search(answer))
                # Twilio's recognition writes "AI assistant" as "an assistant"
                # or "an A assistant", so only the name is read from it.
                and bool(NAME.search(heard_answer)),
                f"said: {answer[:170]!r}; heard: {heard_answer[:170]!r}",
            )
            report.check(
                "The call still does its task",
                "nine" in json.dumps(person.get("result")).lower()
                or "9" in json.dumps(person.get("result")),
                str(person.get("result"))[:170],
            )

            # --- A voicemail box; the service writes the message --------------
            written, _ = await call(
                VOICEMAIL,
                task="Remind Sam Carter of the bike service on Thursday at 9 am.",
                on_behalf_of="Lena Fischer",
            )
            written_said = " ".join(said(written))
            report.evidence["voicemail_written_call"] = written
            report.check(
                "A voicemail message that the service writes has the name, "
                "one time, and says that it is an AI assistant",
                written.get("answered_by") == "voicemail"
                and written.get("voicemail_message_left") is True
                and written_said.count("Dana Dial") == 1
                and bool(AI.search(written_said))
                and "Lena Fischer" in written_said,
                f"answered_by {written.get('answered_by')}; said: "
                f"{written_said[:200]!r}",
            )

            # --- A voicemail box; her assistant gives a message with no name --
            given, _ = await call(
                VOICEMAIL,
                task="Remind Sam Carter of the bike service on Thursday at 9 am.",
                on_behalf_of="Lena Fischer",
                voicemail_message=(
                    "Hello Sam, this is a reminder from Lena Fischer of the bike "
                    "service on Thursday at nine. Goodbye."
                ),
            )
            given_said = " ".join(said(given))
            report.evidence["voicemail_given_call"] = given
            report.check(
                "A voicemail message from her assistant that has no name "
                "gets the name before it, and the message stays complete",
                given.get("voicemail_message_left") is True
                and given_said.count("Dana Dial") == 1
                and given_said.index("Dana Dial") < given_said.index("reminder")
                and "Thursday at nine" in given_said,
                f"said: {given_said[:200]!r}",
            )
            named, _ = await call(
                VOICEMAIL,
                task="Remind Sam Carter of the bike service on Thursday at 9 am.",
                on_behalf_of="Lena Fischer",
                voicemail_message=(
                    "Hello Sam, this is Dana Dial, the AI assistant of Lena "
                    "Fischer, with a reminder of the bike service on Thursday "
                    "at nine. Goodbye."
                ),
            )
            named_said = " ".join(said(named))
            report.evidence["voicemail_named_call"] = named
            report.check(
                "A voicemail message that has the name already is spoken as "
                "it is: the name is not said two times",
                named.get("voicemail_message_left") is True
                and named_said.count("Dana Dial") == 1
                and named_said.startswith("Hello Sam"),
                f"said: {named_said[:200]!r}",
            )

            # --- A call screener ----------------------------------------------
            after_screen = echo(
                '<Say>Thank you. Please stay on the line.</Say><Pause length="4"/>'
                "<Say>Hello, this is Sam Carter speaking. Go ahead.</Say>"
                '<Pause length="12"/><Say>Yes, Thursday at nine is fine. '
                'Goodbye.</Say><Pause length="15"/>'
            )
            screened, at = await call(
                "<Say>Hi. Before I try to connect you, please say your name and "
                "the reason for your call.</Say>" + listen(20, after_screen),
                task="Ask Sam Carter if Thursday at 9 am is fine for the bike service.",
                on_behalf_of="Lena Fischer",
                call_reason="about a bike service",
            )
            screen_heard = await heard_by_shop(at, 1)
            screen_lines = said(screened)
            report.evidence["screened_call"] = screened
            report.evidence["screened_call_heard_by_the_phone"] = screen_heard
            first = screen_lines[0] if screen_lines else ""
            report.check(
                "To a call screener, the agent gives the name Dana Dial, in "
                "the record and in what the phone heard",
                screened.get("call_screener_detected") is True
                and "Dana Dial" in first
                and bool(AI.search(first))
                and "Lena Fischer" in first
                and bool(screen_heard)
                and bool(NAME.search(screen_heard[0])),
                f"said: {first[:150]!r}; heard: {[h[:150] for h in screen_heard]}",
            )
        finally:
            await phone.hang_up()
            await shop.hang_up()
            await op("POST", "oauth/reset-limits")
            await op("POST", "phone-identities/release", **me)
            for organization_id in made:
                closed = await op("POST", f"accounts/{organization_id}/close")
                print(f"closed account {organization_id}: HTTP {closed.status_code}")
            await database.close()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--operator-url", required=True)
    parser.add_argument("--operator-token", required=True)
    parser.add_argument("--database-url", required=True)
    parser.add_argument("--test-phone", required=True)
    parser.add_argument("--shop-phone", required=True)
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
        '# The agent says that it is "Dana Dial"',
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
