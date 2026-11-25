"""The service deletes the words of a call when the storage time is over.

The privacy policy says: "We store a transcript for 30 days. After that, we
delete it." Lena adds DanaDial in her assistant and makes two real calls to a
shop phone that plays a hold message. The run then starts the timed deletion
with a shorter age, so that the first call is "old" and the second is not.
It reads the result three ways: through her assistant (MCP), in the file
storage, and in the database row.

How this can fail (written before the code):

 1. The deletion removes the file, but the assistant still gets the words
    (they are also in the logs of the call record).
 2. The assistant gets no words, but the file or the database row still has
    them.
 3. The deletion removes the words of a call that is not old.
 4. The deletion runs during a call. It marks the call as deleted, or the
    words of that call are lost or are never deleted later.
 5. The deletion also removes data that the policy keeps: the status, the
    length, the result of the call, the list of calls, the minutes used.
 6. After the deletion the assistant gets "the transcript appears within a
    minute", so it waits for words that will not come.
 7. A second run of the deletion fails, or reports the same call again.
 8. The deletion stops after the first group of calls, so an old call stays.
"""

import argparse
import asyncio
import json
import os
import re
import sys
import time
from pathlib import Path

import asyncpg
import httpx

sys.path.insert(0, str(Path(__file__).parent))
from oauth_sign_in import Host, tool
from verify import HOLD_SCRIPT, HOLD_TASK, Report, TestPhone

CALLBACK = "cursor://anysphere.cursor-mcp/oauth/callback"
LIVE = ("ringing", "in_progress")
# The shop says this. The task and the result of the call do not have it.
SPOKEN = "call is important"
KEPT = ("status", "duration_seconds", "to", "from", "started_at", "task", "result")


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
        httpx.AsyncClient(base_url=args.operator_url, timeout=120) as api,
    ):

        async def op(method: str, path: str, **json_body) -> httpx.Response:
            return await api.request(
                method,
                "/api/v1/platform/operator/" + path,
                headers=operator,
                json=json_body or None,
            )

        async def delete_older_than(seconds: float) -> list[int]:
            answer = await op(
                "POST", "transcripts/delete-old", older_than_seconds=seconds
            )
            answer.raise_for_status()
            return answer.json()["call_ids"]

        async def stored(call_id: int, transcript: str = "") -> dict:
            """Where the words of a call are, read without the service.

            With ``transcript`` (the words before the deletion), the answer
            also has each sentence of it that is still in the database row.
            """
            file = await http.get(
                f"{args.storage_url.rstrip('/')}/transcripts/{call_id}.txt"
            )
            row = await database.fetchval(
                "SELECT row_to_json(r)::text FROM workflow_runs r WHERE id = $1",
                call_id,
            )
            found = {
                "file_status": file.status_code,
                "words_in_file": SPOKEN in file.text,
                "words_in_row": SPOKEN in row,
            }
            if transcript:
                sentences = {
                    part.strip()
                    for line in transcript.splitlines()
                    for part in re.split(r"[.?!]", line.split(": ", 1)[-1])
                    if len(part.strip()) >= 20
                }
                row_text = json.dumps(json.loads(row), ensure_ascii=False)
                found["sentences_checked"] = len(sentences)
                found["sentences_in_row"] = sorted(
                    s for s in sentences if s in row_text
                )
            return found

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
            made += (
                set((await op("GET", "oauth/summary")).json()["organization_ids"])
                - before
            )

            await phone.answer_with_code("000000")
            started = await lena_tool("start_caller_id_verification", **me)
            await phone.answer_with_code(started["validation_code"])
            for _ in range(14):
                await asyncio.sleep(5)
                if (await lena_tool("get_account_status"))["setup"]["done"]:
                    break
            await phone.hang_up()

            async def call_until_words() -> int:
                await shop.answer_with_script(HOLD_SCRIPT)
                call = await lena_tool(
                    "place_call",
                    phone_number=shop.number,
                    task=HOLD_TASK,
                    on_behalf_of="Lena Fischer",
                    call_reason="to ask about opening hours",
                )
                for _ in range(25):
                    await asyncio.sleep(4)
                    progress = await lena_tool(
                        "get_call_result", call_id=call["call_id"]
                    )
                    if SPOKEN in (progress.get("transcript") or ""):
                        break
                return call["call_id"]

            async def record_when_over(call_id: int) -> dict:
                record: dict = {}
                for _ in range(14):
                    await asyncio.sleep(5)
                    record = await lena_tool("get_call_result", call_id=call_id)
                    if record["status"] not in LIVE and record.get("transcript"):
                        break
                return record

            # --- The first call, complete ------------------------------------
            first_id = await call_until_words()
            await lena_tool("end_call", call_id=first_id)
            first = await record_when_over(first_id)
            first_stored = await stored(first_id)
            minutes = (await lena_tool("get_account_status"))["minutes_used"]
            report.evidence["first_call_before"] = first
            report.check(
                "Before the deletion, the words of the first call are in the "
                "answer to the assistant, in the file and in the database row",
                SPOKEN in first.get("transcript", "")
                and first_stored
                == {"file_status": 200, "words_in_file": True, "words_in_row": True},
                f"call {first_id}: {len(first.get('transcript', ''))} characters; "
                f"{first_stored}",
            )
            await asyncio.sleep(5)
            between = time.time()
            await asyncio.sleep(5)

            # --- The second call is in progress ------------------------------
            second_id = await call_until_words()
            deleted = await delete_older_than(time.time() - between)
            first_after = await lena_tool("get_call_result", call_id=first_id)
            first_stored_after = await stored(first_id, first["transcript"])
            report.evidence["first_call_after"] = first_after
            report.check(
                "The deletion removes the words of the old call from the "
                "answer to the assistant, the file and the database row",
                first_id in deleted
                and first_after.get("transcript") == ""
                and first_stored_after["file_status"] == 404
                and not first_stored_after["words_in_row"]
                and first_stored_after["sentences_checked"] >= 3
                and first_stored_after["sentences_in_row"] == [],
                f"deleted {len(deleted)} calls, call {first_id} included: "
                f"{first_id in deleted}; {first_stored_after}",
            )
            report.check(
                "The assistant is told that the words were deleted, and is "
                "not told to wait for them",
                first_after.get("transcript_deleted") is True
                and "deleted" in first_after.get("next_step", "")
                and "appears" not in first_after.get("next_step", ""),
                first_after.get("next_step", "")[:160],
            )
            listed = await lena_tool("list_calls")
            minutes_after = (await lena_tool("get_account_status"))["minutes_used"]
            changed = [k for k in KEPT if first_after.get(k) != first.get(k)]
            report.check(
                "The other data of the old call stays: status, length, "
                "numbers, task, result, the list of calls, the minutes used",
                not changed
                and bool(first_after.get("result"))
                and first_id in [c["call_id"] for c in listed]
                and minutes_after >= minutes > 0,
                f"changed fields: {changed or 'none'}; result: "
                f"{str(first_after.get('result'))[:90]}; minutes used "
                f"{minutes} before",
            )
            report.check(
                "A call that is not old keeps its words",
                second_id not in deleted,
                f"call {second_id} started after the age limit; deleted: "
                f"{second_id in deleted}",
            )

            # --- The deletion with age 0 while the second call continues -----
            during = await delete_older_than(0)
            await asyncio.sleep(8)
            live = await lena_tool("get_call_result", call_id=second_id)
            await lena_tool("end_call", call_id=second_id)
            second = await record_when_over(second_id)
            second_stored = await stored(second_id)
            report.evidence["second_call"] = second
            report.check(
                "A deletion during a call does not touch that call: the call "
                "continues and its words are stored at the end",
                second_id not in during
                and live["status"] == "in_progress"
                and SPOKEN in second.get("transcript", "")
                and "transcript_deleted" not in second
                and second_stored["file_status"] == 200
                and second_stored["words_in_row"],
                f"call {second_id} during the deletion: {live['status']}; "
                f"after the end: {len(second.get('transcript', ''))} characters; "
                f"{second_stored}",
            )

            # --- Later, the second call is old too ---------------------------
            late = await delete_older_than(0)
            again = await delete_older_than(0)
            second_after = await lena_tool("get_call_result", call_id=second_id)
            second_stored_after = await stored(second_id)
            report.check(
                "When the second call is old, a new deletion removes its words too",
                second_id in late
                and second_after.get("transcript") == ""
                and second_after.get("transcript_deleted") is True
                and second_stored_after
                == {"file_status": 404, "words_in_file": False, "words_in_row": False},
                f"{second_stored_after}",
            )
            report.check(
                "A deletion that finds nothing more to do reports no call",
                again == [] and first_id not in during + late,
                f"calls reported by the last deletion: {again}",
            )
            left = await database.fetchval(
                "SELECT count(*) FROM workflow_runs WHERE is_completed "
                "AND (transcript_url IS NOT NULL "
                "OR logs::text LIKE '%realtime_feedback_events%')"
            )
            report.check(
                "No completed call of any account in the database keeps "
                "words (the deletion did all groups of calls)",
                left == 0,
                f"{left} completed calls with a transcript file or word events",
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
    parser.add_argument("--storage-url", required=True, help="bucket address")
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
        "# Transcript storage time check",
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
