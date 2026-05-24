"""Mustache-style prompt rendering for workflow templates."""

import chevron


def render_prompt(template: str, variables: dict[str, str]) -> str:
    """Render a prompt template with ``{{placeholder}}`` variables."""
    return chevron.render(template, variables)
