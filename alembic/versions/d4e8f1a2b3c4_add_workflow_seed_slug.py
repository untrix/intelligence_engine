"""add workflow seed_slug

Revision ID: d4e8f1a2b3c4
Revises: a91d5f3c2e10
Create Date: 2026-05-24 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d4e8f1a2b3c4"
down_revision: Union[str, Sequence[str], None] = "a91d5f3c2e10"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "workflow_definitions" not in inspector.get_table_names():
        return
    columns = {c["name"] for c in inspector.get_columns("workflow_definitions")}
    if "seed_slug" not in columns:
        with op.batch_alter_table("workflow_definitions") as batch_op:
            batch_op.add_column(sa.Column("seed_slug", sa.String(length=64), nullable=True))
        op.create_index(
            "ix_workflow_definitions_seed_slug",
            "workflow_definitions",
            ["seed_slug"],
            unique=True,
        )
    op.execute(
        sa.text(
            "UPDATE workflow_definitions SET seed_slug = 'job_candidate_review' "
            "WHERE name = 'Job Candidate Review' AND seed_slug IS NULL"
        )
    )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "workflow_definitions" not in inspector.get_table_names():
        return
    columns = {c["name"] for c in inspector.get_columns("workflow_definitions")}
    if "seed_slug" in columns:
        op.drop_index("ix_workflow_definitions_seed_slug", table_name="workflow_definitions")
        with op.batch_alter_table("workflow_definitions") as batch_op:
            batch_op.drop_column("seed_slug")
