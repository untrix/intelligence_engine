"""SQLAlchemy ORM models."""

from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text

from app.database import Base


def utcnow():
    return datetime.now(timezone.utc)


class AppSettings(Base):
    """Key-value store for application configuration persisted in the database."""

    __tablename__ = "app_settings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(255), unique=True, nullable=False)
    value = Column(Text, nullable=True)


class WorkflowDefinition(Base):
    """A reusable agent workflow definition."""

    __tablename__ = "workflow_definitions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    playbook_name = Column(String(255), nullable=False, default="Single Turn")
    user_prompt_template = Column(Text, nullable=False)
    user_prompt_variables_json = Column(Text, nullable=False, default="[]")
    allowed_tools_json = Column(Text, nullable=False, default="[]")
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)


class PlaybookSettings(Base):
    """Persisted settings for an agent orchestration playbook."""

    __tablename__ = "playbook_settings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    playbook_name = Column(String(255), unique=True, nullable=False)
    system_prompt = Column(Text, nullable=False, default="")
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)


class WorkflowRun(Base):
    """A single execution of a workflow."""

    __tablename__ = "workflow_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    workflow_id = Column(Integer, ForeignKey("workflow_definitions.id"), nullable=False)
    workflow_name = Column(String(255), nullable=False)
    status = Column(String(20), nullable=False, default="running")
    provider = Column(String(50), nullable=False)
    model = Column(String(100), nullable=False)
    started_at = Column(DateTime, default=utcnow, nullable=False)
    ended_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)
    error = Column(Text, nullable=True)
    variables_json = Column(Text, nullable=False, default="{}")


class WorkflowRunMessage(Base):
    """A persisted message in a workflow run chat."""

    __tablename__ = "workflow_run_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(Integer, ForeignKey("workflow_runs.id"), nullable=False)
    sequence = Column(Integer, nullable=False)
    role = Column(String(20), nullable=False)
    content = Column(Text, nullable=True)
    tool_name = Column(String(100), nullable=True)
    tool_call_id = Column(String(100), nullable=True)
    metadata_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)
