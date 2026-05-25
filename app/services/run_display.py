"""Display helpers for workflow run UI."""

from __future__ import annotations

from typing import Literal, TypedDict

from app.models import WorkflowRun, WorkflowRunMessage

ResultKind = Literal["assistant", "error", "empty", "in_progress"]


class RunResultDisplay(TypedDict):
    kind: ResultKind
    body: str


def _last_assistant_message(messages: list[WorkflowRunMessage]) -> WorkflowRunMessage | None:
    last: WorkflowRunMessage | None = None
    for msg in messages:
        if msg.role == "assistant":
            last = msg
    return last


def run_result_content(
    run: WorkflowRun, messages: list[WorkflowRunMessage]
) -> RunResultDisplay:
    """Derive formatted result tab content from run status and messages."""
    last_assistant = _last_assistant_message(messages)
    assistant_text = (last_assistant.content or "").strip() if last_assistant else ""

    if run.status == "running":
        return {
            "kind": "in_progress",
            "body": assistant_text,
        }

    if run.status == "error" and (run.error or "").strip():
        return {
            "kind": "error",
            "body": run.error.strip(),
        }

    if assistant_text:
        return {
            "kind": "assistant",
            "body": assistant_text,
        }

    if run.status == "error":
        return {
            "kind": "empty",
            "body": "Run ended with an error. Open the Full thread tab for details.",
        }

    return {
        "kind": "empty",
        "body": "No assistant response was recorded for this run.",
    }
