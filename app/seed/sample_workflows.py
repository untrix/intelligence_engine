"""Load and install bundled sample workflow definitions."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import WorkflowDefinition
from app.services.workflow_prompts import extract_user_prompt_variables

_MANIFEST_DIR = Path(__file__).resolve().parent / "sample_workflows"


@dataclass(frozen=True)
class SampleWorkflowManifest:
    seed_slug: str
    name: str
    playbook_name: str
    user_prompt_template: str
    variables: list[str]
    allowed_tools: list[str]
    variable_defaults: dict[str, str]


def _load_manifest(path: Path) -> SampleWorkflowManifest:
    data = json.loads(path.read_text(encoding="utf-8"))
    variables = data.get("variables")
    if not variables:
        variables = extract_user_prompt_variables(data["user_prompt_template"])
    return SampleWorkflowManifest(
        seed_slug=data["seed_slug"],
        name=data["name"],
        playbook_name=data.get("playbook_name", "Single Turn"),
        user_prompt_template=data["user_prompt_template"],
        variables=list(variables),
        allowed_tools=list(data.get("allowed_tools") or []),
        variable_defaults=dict(data.get("variable_defaults") or {}),
    )


def list_sample_manifests() -> list[SampleWorkflowManifest]:
    """Return all sample workflow manifests from disk."""
    if not _MANIFEST_DIR.is_dir():
        return []
    manifests: list[SampleWorkflowManifest] = []
    for path in sorted(_MANIFEST_DIR.glob("*.json")):
        manifests.append(_load_manifest(path))
    return manifests


def get_sample_manifest(seed_slug: str) -> SampleWorkflowManifest | None:
    for manifest in list_sample_manifests():
        if manifest.seed_slug == seed_slug:
            return manifest
    return None


async def ensure_sample_workflows(db: AsyncSession) -> list[str]:
    """Create sample workflows that are missing. Returns slugs that were installed."""
    installed: list[str] = []
    for manifest in list_sample_manifests():
        result = await db.execute(
            select(WorkflowDefinition).where(
                WorkflowDefinition.seed_slug == manifest.seed_slug
            )
        )
        if result.scalar_one_or_none():
            continue

        legacy = await db.execute(
            select(WorkflowDefinition).where(
                WorkflowDefinition.seed_slug.is_(None),
                WorkflowDefinition.name == manifest.name,
            )
        )
        existing = legacy.scalar_one_or_none()
        if existing:
            existing.seed_slug = manifest.seed_slug
            installed.append(manifest.seed_slug)
            continue

        db.add(
            WorkflowDefinition(
                seed_slug=manifest.seed_slug,
                name=manifest.name,
                playbook_name=manifest.playbook_name,
                user_prompt_template=manifest.user_prompt_template,
                user_prompt_variables_json=json.dumps(manifest.variables),
                allowed_tools_json=json.dumps(manifest.allowed_tools),
            )
        )
        installed.append(manifest.seed_slug)
    if installed:
        await db.commit()
    return installed


def missing_sample_slugs(existing_slugs: set[str | None]) -> list[str]:
    """Return seed slugs from manifests that are not present in the database."""
    return [
        m.seed_slug
        for m in list_sample_manifests()
        if m.seed_slug not in existing_slugs
    ]
