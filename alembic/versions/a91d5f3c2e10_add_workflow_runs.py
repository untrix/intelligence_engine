"""add workflow runs

Revision ID: a91d5f3c2e10
Revises: 1d5a30efc452
Create Date: 2026-05-24 02:56:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a91d5f3c2e10"
down_revision: Union[str, Sequence[str], None] = "1d5a30efc452"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_table(table_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return table_name in inspector.get_table_names()


def upgrade() -> None:
    """Upgrade schema."""
    if not _has_table("workflow_runs"):
        op.create_table(
            "workflow_runs",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("workflow_id", sa.Integer(), nullable=False),
            sa.Column("workflow_name", sa.String(length=255), nullable=False),
            sa.Column("status", sa.String(length=20), nullable=False),
            sa.Column("provider", sa.String(length=50), nullable=False),
            sa.Column("model", sa.String(length=100), nullable=False),
            sa.Column("started_at", sa.DateTime(), nullable=False),
            sa.Column("ended_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.Column("error", sa.Text(), nullable=True),
            sa.Column("variables_json", sa.Text(), nullable=False),
            sa.ForeignKeyConstraint(["workflow_id"], ["workflow_definitions.id"]),
            sa.PrimaryKeyConstraint("id"),
        )

    if not _has_table("workflow_run_messages"):
        op.create_table(
            "workflow_run_messages",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("run_id", sa.Integer(), nullable=False),
            sa.Column("sequence", sa.Integer(), nullable=False),
            sa.Column("role", sa.String(length=20), nullable=False),
            sa.Column("content", sa.Text(), nullable=True),
            sa.Column("tool_name", sa.String(length=100), nullable=True),
            sa.Column("tool_call_id", sa.String(length=100), nullable=True),
            sa.Column("metadata_json", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["run_id"], ["workflow_runs.id"]),
            sa.PrimaryKeyConstraint("id"),
        )


def downgrade() -> None:
    """Downgrade schema."""
    if _has_table("workflow_run_messages"):
        op.drop_table("workflow_run_messages")
    if _has_table("workflow_runs"):
        op.drop_table("workflow_runs")
