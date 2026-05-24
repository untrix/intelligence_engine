"""add playbook settings

Revision ID: 9e7bc2c8b3d1
Revises: 6d3a8a99852f
Create Date: 2026-05-24 01:34:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "9e7bc2c8b3d1"
down_revision: Union[str, Sequence[str], None] = "6d3a8a99852f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "playbook_settings" in inspector.get_table_names():
        return

    op.create_table(
        "playbook_settings",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("playbook_name", sa.String(length=255), nullable=False),
        sa.Column("system_prompt", sa.Text(), nullable=False),
        sa.Column("allowed_tools_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("playbook_name"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("playbook_settings")
