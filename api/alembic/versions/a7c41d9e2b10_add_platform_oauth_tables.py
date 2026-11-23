"""add platform oauth tables

Revision ID: a7c41d9e2b10
Revises: f3a9c21b7e40
Create Date: 2026-11-21 21:10:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a7c41d9e2b10"
down_revision: Union[str, None] = "f3a9c21b7e40"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "platform_oauth_clients",
        sa.Column("client_id", sa.String(length=64), nullable=False),
        sa.Column("client_info", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("client_id"),
    )
    op.create_table(
        "platform_oauth_tokens",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("kind", sa.String(length=8), nullable=False),
        sa.Column("client_id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("grant_id", sa.String(length=32), nullable=False),
        sa.Column("scopes", sa.JSON(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_platform_oauth_tokens_token_hash",
        "platform_oauth_tokens",
        ["token_hash"],
        unique=True,
    )
    op.create_index(
        "ix_platform_oauth_tokens_user_id", "platform_oauth_tokens", ["user_id"]
    )
    op.create_index(
        "ix_platform_oauth_tokens_grant_id", "platform_oauth_tokens", ["grant_id"]
    )


def downgrade() -> None:
    op.drop_table("platform_oauth_tokens")
    op.drop_table("platform_oauth_clients")
