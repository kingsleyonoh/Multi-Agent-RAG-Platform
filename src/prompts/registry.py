"""In-memory prompt registry with Jinja2 rendering.

Provides CRUD operations for prompt templates with automatic versioning,
``is_active`` flag for A/B testing, and ``model_hint`` for per-prompt
model suggestions.

Templates use Jinja2 syntax so callers can inject variables
(``{{ context }}``, ``{{ question }}``, etc.) at render time.
"""

from __future__ import annotations

import uuid
from typing import Any

from jinja2 import Template


class PromptRegistry:
    """In-memory store for Jinja2 prompt templates.

    Each prompt has: id, name, template, version, is_active, model_hint.
    """

    def __init__(self) -> None:
        self._prompts: dict[str, dict[str, Any]] = {}

    # ── CRUD ─────────────────────────────────────────────────────────

    def create(
        self,
        name: str,
        template: str,
        *,
        model_hint: str | None = None,
    ) -> dict[str, Any]:
        """Create a new prompt template."""
        pid = str(uuid.uuid4())
        entry = {
            "id": pid,
            "name": name,
            "template": template,
            "version": 1,
            "is_active": True,
            "model_hint": model_hint,
        }
        self._prompts[pid] = entry
        return dict(entry)

    def get(self, prompt_id: str) -> dict[str, Any] | None:
        """Return prompt by ID, or *None*."""
        entry = self._prompts.get(prompt_id)
        return dict(entry) if entry else None

    def list_all(self) -> list[dict[str, Any]]:
        """Return all prompts."""
        return [dict(e) for e in self._prompts.values()]

    def update(
        self,
        prompt_id: str,
        *,
        template: str | None = None,
        is_active: bool | None = None,
        model_hint: str | None = None,
    ) -> dict[str, Any] | None:
        """Update a prompt — auto-increments version when template changes."""
        entry = self._prompts.get(prompt_id)
        if entry is None:
            return None

        if template is not None:
            entry["template"] = template
            entry["version"] += 1
        if is_active is not None:
            entry["is_active"] = is_active
        if model_hint is not None:
            entry["model_hint"] = model_hint
        return dict(entry)

    # ── rendering ────────────────────────────────────────────────────

    def render(
        self,
        prompt_id: str,
        variables: dict[str, Any],
    ) -> str | None:
        """Render a stored Jinja2 template with *variables*."""
        entry = self._prompts.get(prompt_id)
        if entry is None:
            return None
        tpl = Template(entry["template"])
        return tpl.render(**variables)
