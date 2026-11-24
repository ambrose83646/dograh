"""Database access for the shared-platform calling service.

Covers the three things platform mode adds on top of the tenant model: handing
out phone numbers from the operator's pool, measuring an organization's call
usage against its free allowance, and listing an organization's calls.
"""

from collections.abc import Sequence
from datetime import datetime, timedelta

from sqlalchemy import Float, and_, cast, delete, func, or_, text, update
from sqlalchemy.future import select

from api.db.base_client import BaseDBClient
from api.db.models import (
    OrganizationModel,
    PlatformOAuthClientModel,
    PlatformOAuthTokenModel,
    TelephonyPhoneNumberModel,
    UserModel,
    WorkflowModel,
    WorkflowRunModel,
)
from api.utils.telephony_address import normalize_telephony_address

# Where a call record has the words that were said, apart from the transcript
# file: the lines of a direct talk, what was heard before the agent spoke, and
# what the tools of the agent got and gave (a direct talk gives its lines).
_WORD_FIELDS = {
    "direct_talk": ("lines",),
    "answer_supervisor": ("transcript",),
    "tool_results": ("arguments", "result"),
}
# The other logs of a call (conversation, events, extraction) have the words.
_LOGS_WITHOUT_WORDS = ("telephony_status_callbacks",)

# One global lock serializes pool assignment. Assignments are rare (one per
# signup) and the critical section is two statements.
_POOL_LOCK_KEY = 815_204_771

# The two kinds of phone number row a platform account can hold.
INBOUND_NUMBER_LABEL = "Assigned number"
CALLER_ID_LABEL = "Verified caller ID"


class PlatformClient(BaseDBClient):
    async def assign_platform_pool_number(
        self,
        organization_id: int,
        telephony_configuration_id: int,
        pool: Sequence[str],
    ) -> TelephonyPhoneNumberModel | None:
        """Give the organization the first pool number nobody holds yet.

        Returns the organization's existing number when it already has one in
        this configuration, and None when the pool is exhausted. A number held
        by any organization, active or not, is never handed out again.
        """
        canonical = [normalize_telephony_address(n).canonical for n in pool]
        async with self.async_session() as session:
            await session.execute(
                text("SELECT pg_advisory_xact_lock(:key)"), {"key": _POOL_LOCK_KEY}
            )
            existing = await session.scalar(
                select(TelephonyPhoneNumberModel)
                .where(
                    TelephonyPhoneNumberModel.organization_id == organization_id,
                    TelephonyPhoneNumberModel.telephony_configuration_id
                    == telephony_configuration_id,
                    TelephonyPhoneNumberModel.label == INBOUND_NUMBER_LABEL,
                )
                .order_by(TelephonyPhoneNumberModel.id)
                .limit(1)
            )
            if existing is not None:
                return existing
            if not canonical:
                return None

            taken = set(
                (
                    await session.scalars(
                        select(TelephonyPhoneNumberModel.address_normalized).where(
                            TelephonyPhoneNumberModel.address_normalized.in_(canonical),
                            TelephonyPhoneNumberModel.label == INBOUND_NUMBER_LABEL,
                        )
                    )
                ).all()
            )
            free = next((n for n in canonical if n not in taken), None)
            if free is None:
                return None

            normalized = normalize_telephony_address(free)
            row = TelephonyPhoneNumberModel(
                organization_id=organization_id,
                telephony_configuration_id=telephony_configuration_id,
                address=free,
                address_normalized=normalized.canonical,
                address_type=normalized.address_type,
                country_code=normalized.country_code,
                label=INBOUND_NUMBER_LABEL,
                is_active=True,
                is_default_caller_id=False,
                extra_metadata={},
            )
            session.add(row)
            await session.commit()
            await session.refresh(row)
            return row

    async def set_platform_caller_id(
        self,
        organization_id: int,
        telephony_configuration_id: int,
        phone_number: str,
    ) -> TelephonyPhoneNumberModel:
        """Record the organization's one verified caller ID, replacing any other.

        The caller must have confirmed with Twilio that the organization's own
        subaccount holds this number as a verified caller ID.
        """
        normalized = normalize_telephony_address(phone_number)
        async with self.async_session() as session:
            await session.execute(
                delete(TelephonyPhoneNumberModel).where(
                    TelephonyPhoneNumberModel.organization_id == organization_id,
                    TelephonyPhoneNumberModel.label == CALLER_ID_LABEL,
                )
            )
            row = TelephonyPhoneNumberModel(
                organization_id=organization_id,
                telephony_configuration_id=telephony_configuration_id,
                address=normalized.canonical,
                address_normalized=normalized.canonical,
                address_type=normalized.address_type,
                country_code=normalized.country_code,
                label=CALLER_ID_LABEL,
                is_active=True,
                is_default_caller_id=True,
                extra_metadata={},
            )
            session.add(row)
            await session.commit()
            await session.refresh(row)
            return row

    async def get_platform_phone_user(self, provider_id: str) -> UserModel | None:
        async with self.async_session() as session:
            return await session.scalar(
                select(UserModel).where(UserModel.provider_id == provider_id)
            )

    async def release_platform_phone_identity(self, provider_id: str) -> bool:
        """Rename the user and its organization so the phone can sign up again."""
        suffix = f"released_{int(datetime.now().timestamp())}_"
        async with self.async_session() as session:
            user = await session.scalar(
                select(UserModel).where(UserModel.provider_id == provider_id)
            )
            if user is None:
                return False
            organization = await session.scalar(
                select(OrganizationModel).where(
                    OrganizationModel.provider_id == f"org_{provider_id}"
                )
            )
            if organization is not None:
                organization.provider_id = f"org_{suffix}{provider_id}"
            user.provider_id = f"{suffix}{provider_id}"
            await session.commit()
            return True

    async def get_platform_number_owner(
        self, phone_number: str, organization_id: int
    ) -> int | None:
        """The different organization that has this number as its sign-in
        phone or as its caller ID. The sign-in phone wins."""
        async with self.async_session() as session:
            identity = await session.scalar(
                select(UserModel.selected_organization_id).where(
                    UserModel.provider_id == f"phone_{phone_number}"
                )
            )
            if identity is not None and identity != organization_id:
                return identity
            return await session.scalar(
                select(TelephonyPhoneNumberModel.organization_id)
                .where(
                    TelephonyPhoneNumberModel.address_normalized == phone_number,
                    TelephonyPhoneNumberModel.label == CALLER_ID_LABEL,
                    TelephonyPhoneNumberModel.organization_id != organization_id,
                )
                .limit(1)
            )

    async def platform_number_owner_differs(
        self, phone_number: str, organization_id: int
    ) -> bool:
        """True when the number is the sign-in phone or the caller ID of a
        different organization."""
        owner = await self.get_platform_number_owner(phone_number, organization_id)
        return owner is not None

    async def clear_platform_caller_id(self, organization_id: int) -> None:
        async with self.async_session() as session:
            await session.execute(
                delete(TelephonyPhoneNumberModel).where(
                    TelephonyPhoneNumberModel.organization_id == organization_id,
                    TelephonyPhoneNumberModel.label == CALLER_ID_LABEL,
                )
            )
            await session.commit()

    async def get_platform_call_seconds(
        self,
        organization_id: int,
        since: datetime | None = None,
        until: datetime | None = None,
    ) -> float:
        """Recorded call seconds of the organization's runs, all or in a period."""
        conditions = [WorkflowModel.organization_id == organization_id]
        if since is not None:
            conditions.append(WorkflowRunModel.created_at >= since)
        if until is not None:
            conditions.append(WorkflowRunModel.created_at < until)
        async with self.async_session() as session:
            total = await session.scalar(
                select(
                    func.coalesce(
                        func.sum(
                            cast(
                                WorkflowRunModel.usage_info.op("->>")(
                                    "call_duration_seconds"
                                ),
                                Float,
                            )
                        ),
                        0.0,
                    )
                )
                .join(WorkflowModel, WorkflowRunModel.workflow_id == WorkflowModel.id)
                .where(*conditions)
            )
            return float(total or 0.0)

    async def count_platform_runs_since(
        self, organization_id: int, since: datetime
    ) -> int:
        async with self.async_session() as session:
            count = await session.scalar(
                select(func.count(WorkflowRunModel.id))
                .join(WorkflowModel, WorkflowRunModel.workflow_id == WorkflowModel.id)
                .where(
                    WorkflowModel.organization_id == organization_id,
                    WorkflowRunModel.created_at >= since,
                )
            )
            return int(count or 0)

    async def list_platform_calls(
        self, organization_id: int, limit: int = 20
    ) -> list[WorkflowRunModel]:
        """The organization's most recent runs, newest first."""
        async with self.async_session() as session:
            result = await session.scalars(
                select(WorkflowRunModel)
                .join(WorkflowModel, WorkflowRunModel.workflow_id == WorkflowModel.id)
                .where(WorkflowModel.organization_id == organization_id)
                .order_by(WorkflowRunModel.id.desc())
                .limit(limit)
            )
            return list(result.all())

    async def get_platform_owner_user_id(self, organization_id: int) -> int | None:
        """The user who owns a self-signed-up organization (its first member)."""
        async with self.async_session() as session:
            return await session.scalar(
                select(UserModel.id)
                .where(UserModel.selected_organization_id == organization_id)
                .order_by(UserModel.id)
                .limit(1)
            )

    async def set_platform_inbound_workflow(
        self,
        organization_id: int,
        phone_number_id: int,
        inbound_workflow_id: int,
    ) -> bool:
        """Route the organization's own number to its own workflow.

        Both ids are checked against ``organization_id`` in the same statement,
        so neither a foreign number nor a foreign workflow can be attached.
        """
        async with self.async_session() as session:
            owns_workflow = await session.scalar(
                select(WorkflowModel.id).where(
                    WorkflowModel.id == inbound_workflow_id,
                    WorkflowModel.organization_id == organization_id,
                )
            )
            if owns_workflow is None:
                return False
            row = await session.scalar(
                select(TelephonyPhoneNumberModel)
                .where(
                    TelephonyPhoneNumberModel.id == phone_number_id,
                    TelephonyPhoneNumberModel.organization_id == organization_id,
                )
                .with_for_update()
            )
            if row is None:
                return False
            row.inbound_workflow_id = inbound_workflow_id
            await session.commit()
            return True

    async def get_platform_phone_number(
        self, organization_id: int, phone_number_id: int
    ) -> TelephonyPhoneNumberModel | None:
        async with self.async_session() as session:
            return await session.scalar(
                select(TelephonyPhoneNumberModel).where(
                    TelephonyPhoneNumberModel.id == phone_number_id,
                    TelephonyPhoneNumberModel.organization_id == organization_id,
                )
            )

    async def release_platform_phone_number(
        self, organization_id: int, phone_number_id: int
    ) -> bool:
        """Take the organization's number away so the pool can hand it out again."""
        async with self.async_session() as session:
            await session.execute(
                text("SELECT pg_advisory_xact_lock(:key)"), {"key": _POOL_LOCK_KEY}
            )
            result = await session.execute(
                delete(TelephonyPhoneNumberModel).where(
                    TelephonyPhoneNumberModel.id == phone_number_id,
                    TelephonyPhoneNumberModel.organization_id == organization_id,
                )
            )
            await session.commit()
            return bool(result.rowcount)

    # --- OAuth: clients that registered, and the tokens of each consent ------

    async def save_platform_oauth_client(self, client_id: str, info: dict) -> None:
        async with self.async_session() as session:
            await session.merge(
                PlatformOAuthClientModel(client_id=client_id, client_info=info)
            )
            await session.commit()

    async def get_platform_oauth_client(self, client_id: str) -> dict | None:
        async with self.async_session() as session:
            return await session.scalar(
                select(PlatformOAuthClientModel.client_info).where(
                    PlatformOAuthClientModel.client_id == client_id
                )
            )

    async def add_platform_oauth_tokens(
        self, tokens: Sequence[PlatformOAuthTokenModel]
    ) -> None:
        async with self.async_session() as session:
            session.add_all(tokens)
            await session.commit()

    async def get_platform_oauth_token(
        self, token_hash: str, kind: str
    ) -> PlatformOAuthTokenModel | None:
        """The token, when it exists and its time has not ended."""
        async with self.async_session() as session:
            return await session.scalar(
                select(PlatformOAuthTokenModel).where(
                    PlatformOAuthTokenModel.token_hash == token_hash,
                    PlatformOAuthTokenModel.kind == kind,
                    PlatformOAuthTokenModel.expires_at > func.now(),
                )
            )

    async def end_platform_oauth_token(self, token_id: int, at: datetime) -> None:
        """Bring the end of a token forward. It never moves the end later."""
        async with self.async_session() as session:
            await session.execute(
                update(PlatformOAuthTokenModel)
                .where(
                    PlatformOAuthTokenModel.id == token_id,
                    PlatformOAuthTokenModel.expires_at > at,
                )
                .values(expires_at=at)
            )
            await session.commit()

    async def delete_platform_oauth_grant(self, grant_id: str) -> None:
        async with self.async_session() as session:
            await session.execute(
                delete(PlatformOAuthTokenModel).where(
                    PlatformOAuthTokenModel.grant_id == grant_id
                )
            )
            await session.commit()

    async def list_platform_oauth_accounts(self) -> list[int]:
        """Organizations of accounts that came from OAuth and have no phone."""
        async with self.async_session() as session:
            rows = await session.scalars(
                select(UserModel.selected_organization_id).where(
                    UserModel.provider_id.like("oauth\\_%"),
                    UserModel.selected_organization_id.is_not(None),
                )
            )
            return sorted(rows)

    async def list_platform_oauth_users(self) -> list[UserModel]:
        """Users that came from an OAuth consent and are not retired."""
        async with self.async_session() as session:
            rows = await session.scalars(
                select(UserModel)
                .where(UserModel.provider_id.like("oauth\\_%"))
                .order_by(UserModel.id)
            )
            return list(rows)

    async def move_platform_oauth_tokens(
        self, from_user_id: int, to_user_id: int
    ) -> int:
        """Make the tokens of one account work for a different account."""
        async with self.async_session() as session:
            result = await session.execute(
                update(PlatformOAuthTokenModel)
                .where(PlatformOAuthTokenModel.user_id == from_user_id)
                .values(user_id=to_user_id)
            )
            await session.commit()
            return result.rowcount

    async def delete_platform_oauth_tokens_of_user(self, user_id: int) -> int:
        async with self.async_session() as session:
            result = await session.execute(
                delete(PlatformOAuthTokenModel).where(
                    PlatformOAuthTokenModel.user_id == user_id
                )
            )
            await session.commit()
            return result.rowcount

    async def retire_platform_oauth_user(self, user_id: int) -> None:
        """Rename the user so that it is not an OAuth account from now on."""
        async with self.async_session() as session:
            user = await session.get(UserModel, user_id)
            if user is not None and user.provider_id.startswith("oauth_"):
                user.provider_id = (
                    f"retired_{int(datetime.now().timestamp())}_{user.provider_id}"
                )
                await session.commit()

    async def list_runs_with_old_words(
        self, started_before: datetime, limit: int
    ) -> list[tuple[int, str | None, str]]:
        """Calls older than the storage time whose words are not deleted yet.

        A call that did not get its end is not touched until one more day,
        so a call in progress is never in this list.
        """
        async with self.async_session() as session:
            rows = await session.execute(
                select(
                    WorkflowRunModel.id,
                    WorkflowRunModel.transcript_url,
                    WorkflowRunModel.storage_backend,
                )
                .where(
                    WorkflowRunModel.extra.op("->>")("transcript_deleted_at").is_(None),
                    or_(
                        and_(
                            WorkflowRunModel.is_completed.is_(True),
                            WorkflowRunModel.created_at < started_before,
                        ),
                        WorkflowRunModel.created_at
                        < started_before - timedelta(days=1),
                    ),
                )
                .order_by(WorkflowRunModel.id)
                .limit(limit)
            )
            return [tuple(row) for row in rows]

    async def remove_words_of_run(self, run_id: int, deleted_at: datetime) -> None:
        """Remove what was said in a call from its record. The rest stays."""
        async with self.async_session() as session:
            run = await session.scalar(
                select(WorkflowRunModel)
                .where(WorkflowRunModel.id == run_id)
                .with_for_update()
            )
            if run is None:
                return
            gathered = dict(run.gathered_context or {})
            for key, fields in _WORD_FIELDS.items():
                entries = gathered.get(key)
                if isinstance(entries, list):
                    gathered[key] = [
                        {k: v for k, v in entry.items() if k not in fields}
                        if isinstance(entry, dict)
                        else entry
                        for entry in entries
                    ]
            run.gathered_context = gathered
            run.logs = {
                k: v for k, v in (run.logs or {}).items() if k in _LOGS_WITHOUT_WORDS
            }
            run.transcript_url = None
            run.extra = {
                **(run.extra or {}),
                "transcript_deleted_at": deleted_at.isoformat(),
            }
            await session.commit()
