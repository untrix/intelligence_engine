"""Prompt validation helpers for workflow definitions."""

from __future__ import annotations

import re

# This intentionally supports simple variable names only. More complex Mustache
# features can be added later if workflow prompts need sections or partials.
_MUSTACHE_VARIABLE_RE = re.compile(r"{{\s*([A-Za-z_][A-Za-z0-9_]*)\s*}}")


def extract_user_prompt_variables(prompt_template: str) -> list[str]:
    """Return unique Mustache variable names in first-seen order."""
    variables: list[str] = []
    seen: set[str] = set()
    for match in _MUSTACHE_VARIABLE_RE.finditer(prompt_template or ""):
        name = match.group(1)
        if name not in seen:
            seen.add(name)
            variables.append(name)
    return variables


def system_prompt_has_variables(system_prompt: str) -> bool:
    """Return true when the system prompt contains simple Mustache variables."""
    return bool(_MUSTACHE_VARIABLE_RE.search(system_prompt or ""))
