"""move tools from playbooks to workflows

Revision ID: b8f02e58c5a9
Revises: 9e7bc2c8b3d1
Create Date: 2026-05-24 02:09:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b8f02e58c5a9"
down_revision: Union[str, Sequence[str], None] = "9e7bc2c8b3d1"
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
    bind = op.get_bind()

    # Existing local workflow definitions used the old shape. The user approved
    # clearing them to keep this schema transition simple.
    bind.execute(sa.text("DELETE FROM workflow_definitions"))

    workflow_columns = _columns("workflow_definitions")
    with op.batch_alter_table("workflow_definitions") as batch_op:
        if "playbook_name" not in workflow_columns:
            batch_op.add_column(
                sa.Column(
                    "playbook_name",
                    sa.String(length=255),
                    nullable=False,
                    server_default="Single Turn",
                )
            )
        if "allowed_tools_json" not in workflow_columns:
            batch_op.add_column(
                sa.Column(
                    "allowed_tools_json",
                    sa.Text(),
                    nullable=False,
                    server_default="[]",
                )
            )
        if "system_prompt" in workflow_columns:
            batch_op.drop_column("system_prompt")

    playbook_columns = _columns("playbook_settings")
    if "allowed_tools_json" in playbook_columns:
        with op.batch_alter_table("playbook_settings") as batch_op:
            batch_op.drop_column("allowed_tools_json")


def downgrade() -> None:
    """Downgrade schema."""
    workflow_columns = _columns("workflow_definitions")
    with op.batch_alter_table("workflow_definitions") as batch_op:
        if "system_prompt" not in workflow_columns:
            batch_op.add_column(
                sa.Column(
                    "system_prompt",
                    sa.Text(),
                    nullable=False,
                    server_default="",
                )
            )
        if "allowed_tools_json" in workflow_columns:
            batch_op.drop_column("allowed_tools_json")
        if "playbook_name" in workflow_columns:
            batch_op.drop_column("playbook_name")

    playbook_columns = _columns("playbook_settings")
    if "allowed_tools_json" not in playbook_columns:
        with op.batch_alter_table("playbook_settings") as batch_op:
            batch_op.add_column(
                sa.Column(
                    "allowed_tools_json",
                    sa.Text(),
                    nullable=False,
                    server_default="[]",
                )
            )
