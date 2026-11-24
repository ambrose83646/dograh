"""Delete the words of calls when the storage time is over.

The privacy policy gives the time (30 days). The words of a call are in the
transcript file and in the call record. The status, the length, the task and
the result of the call stay.
"""

from datetime import UTC, datetime, timedelta
from typing import Any

from loguru import logger

from api.db import db_client
from api.services.storage import get_storage_for_backend

_GROUP = 100


async def delete_old(older_than: timedelta) -> dict[str, Any]:
    now = datetime.now(UTC)
    deleted: list[int] = []
    failed: set[int] = set()
    while True:
        runs = [
            run
            for run in await db_client.list_runs_with_old_words(
                now - older_than, _GROUP + len(failed)
            )
            if run[0] not in failed
        ]
        if not runs:
            break
        for run_id, transcript_url, storage_backend in runs:
            if transcript_url and not await get_storage_for_backend(
                storage_backend
            ).adelete_file(transcript_url):
                # The record keeps the address, so the next run tries again.
                logger.error("Transcript file of call {} was not deleted", run_id)
                failed.add(run_id)
                continue
            await db_client.remove_words_of_run(run_id, now)
            deleted.append(run_id)
    if deleted:
        logger.info("Deleted the words of {} old calls", len(deleted))
    return {"deleted": len(deleted), "call_ids": deleted, "failed": sorted(failed)}
