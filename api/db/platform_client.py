"""Database access for the shared-platform calling service.

Covers the three things platform mode adds on top of the tenant model: handing
out phone numbers from the operator's pool, measuring an organization's call
usage against its free allowance, and listing an organization's calls.
"""

from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import Float, cast, func, text
from sqlalchemy.future import select

from api.db.base_client import BaseDBClient
from api.db.models import (
    TelephonyPhoneNumberModel,
    UserModel,
    WorkflowModel,
    WorkflowRunModel,
)
from api.utils.telephony_address import normalize_telephony_address

# One global lock serializes pool assignment. Assignments are rare (one per
# signup) and the critical section is two statements.
_POOL_LOCK_KEY = 815_204_771


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
                            TelephonyPhoneNumberModel.address_normalized.in_(canonical)
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
                label="Assigned number",
                is_active=True,
                is_default_caller_id=True,
                extra_metadata={},
            )
            session.add(row)
            await session.commit()
            await session.refresh(row)
            return row

    async def get_platform_call_seconds(self, organization_id: int) -> float:
        """Total recorded call seconds across every run the organization owns."""
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
                .where(WorkflowModel.organization_id == organization_id)
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
