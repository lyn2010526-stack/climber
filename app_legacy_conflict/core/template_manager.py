"""Standardized output templates.

"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class OutputTemplate:
    id: str
    name: str
    category: str  # code / doc / report / test
    schema: dict[str, Any]
    prompt_template: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class TemplateManager:
    """Manage standardized output templates.

    """

    def __init__(self, storage_path: str = "./data/templates"):
        self._templates: dict[str, OutputTemplate] = {}
        self._storage_path = Path(storage_path)
        self._storage_path.mkdir(parents=True, exist_ok=True)
        self._load_defaults()

    def _load_defaults(self) -> None:
        defaults = [
            OutputTemplate(
                id="code_review",
                name="Code Review",
                category="report",
                schema={
                    "type": "object",
                    "properties": {
                        "summary": {"type": "string"},
                        "issues": {"type": "array", "items": {"type": "string"}},
                        "suggestions": {"type": "array", "items": {"type": "string"}},
                    },
                },
                prompt_template="Review the following code and output: summary, issues, suggestions.",
            ),
            OutputTemplate(
                id="requirement_doc",
                name="Requirement Document",
                category="doc",
                schema={
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "description": {"type": "string"},
                        "acceptance_criteria": {"type": "array", "items": {"type": "string"}},
                    },
                },
                prompt_template="Generate a requirement document with title, description, acceptance criteria.",
            ),
            OutputTemplate(
                id="unit_test",
                name="Unit Test",
                category="test",
                schema={
                    "type": "object",
                    "properties": {
                        "test_cases": {"type": "array", "items": {"type": "object"}},
                        "coverage_target": {"type": "number"},
                    },
                },
                prompt_template="Generate unit tests for the given code.",
            ),
        ]
        for t in defaults:
            self._templates[t.id] = t

    def register(self, template: OutputTemplate) -> None:
        self._templates[template.id] = template
        logger.info("template_registered", template_id=template.id, name=template.name)

    def get(self, template_id: str) -> OutputTemplate | None:
        return self._templates.get(template_id)

    def list_by_category(self, category: str) -> list[OutputTemplate]:
        return [t for t in self._templates.values() if t.category == category]

    def list_all(self) -> list[OutputTemplate]:
        return list(self._templates.values())

    def remove(self, template_id: str) -> bool:
        if template_id in self._templates:
            del self._templates[template_id]
            return True
        return False

    def render_prompt(self, template_id: str, context: dict[str, Any]) -> str:
        template = self._templates.get(template_id)
        if not template:
            raise ValueError(f"Template not found: {template_id}")
        return template.prompt_template.format(**context)

    def to_dict(self) -> dict[str, Any]:
        return {
            "templates": [
                {
                    "id": t.id,
                    "name": t.name,
                    "category": t.category,
                    "schema": t.schema,
                    "prompt_template": t.prompt_template,
                }
                for t in self._templates.values()
            ]
        }

    def save(self) -> None:
        data = self.to_dict()
        with open(self._storage_path / "templates.json", "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def load_from_file(self, file_path: str) -> None:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(file_path)
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        for item in data.get("templates", []):
            template = OutputTemplate(
                id=item["id"],
                name=item["name"],
                category=item["category"],
                schema=item["schema"],
                prompt_template=item["prompt_template"],
            )
            self._templates[template.id] = template


template_manager = TemplateManager()
