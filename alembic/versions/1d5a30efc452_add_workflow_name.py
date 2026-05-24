"""add workflow name

Revision ID: 1d5a30efc452
Revises: b8f02e58c5a9
Create Date: 2026-05-24 02:22:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "1d5a30efc452"
down_revision: Union[str, Sequence[str], None] = "b8f02e58c5a9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _columns(table_name: str) -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if table_name not in inspector.get_table_names():
        return set()
    return {column["name"] for column in inspector.get_columns(table_name)}


def upgrade() -> None:
    """Upgrade schema."""
    if "name" in _columns("workflow_definitions"):
        return

    with op.batch_alter_table("workflow_definitions") as batch_op:
        batch_op.add_column(
            sa.Column(
                "name",
                sa.String(length=255),
                nullable=False,
                server_default="",
            )
        )

    op.execute("UPDATE workflow_definitions SET name = 'Workflow ' || id WHERE name = ''")


def downgrade() -> None:
    """Downgrade schema."""
    if "name" not in _columns("workflow_definitions"):
        return

    with op.batch_alter_table("workflow_definitions") as batch_op:
        batch_op.drop_column("name")
