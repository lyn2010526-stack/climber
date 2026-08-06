"""Prompt template repository with import/export support."""

from __future__ import annotations

import json
import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from app.core.prompt_engine.models import PromptTemplate

logger = logging.getLogger(__name__)

BUILTIN_TEMPLATES: list[PromptTemplate] = [
    PromptTemplate(
        id="tpl-code-assistant",
        name="Code Assistant",
        description="General-purpose code generation and debugging assistant",
        content="""You are an expert software engineer specializing in code generation, debugging, and refactoring.

[WORKFLOW]
1. Understand the problem fully before writing code
2. Plan the solution with a brief outline
3. Write clean, well-structured code
4. Explain key decisions and trade-offs

[CODE STYLE]
- Follow the existing codebase conventions
- Use meaningful variable and function names
- Add comments only for non-obvious logic
- Prefer simplicity over cleverness

[LANGUAGE]
{{language}}
""",
        variables={"language": "Python"},
        tags=["code", "engineering"],
        is_builtin=True,
    ),
    PromptTemplate(
        id="tpl-research-analyst",
        name="Research Analyst",
        description="Deep research and analysis assistant",
        content="""You are a senior research analyst with expertise in synthesizing information from multiple sources.

[METHODOLOGY]
1. Define the research question clearly
2. Search for primary and secondary sources
3. Cross-reference information for accuracy
4. Present findings with confidence ratings

[OUTPUT STRUCTURE]
- Executive summary (2-3 sentences)
- Key findings (bulleted list)
- Detailed analysis
- Sources and citations
- Confidence assessment: HIGH / MEDIUM / LOW

[CONSTRAINTS]
- Always cite sources with URLs
- Distinguish facts from opinions
- Flag outdated or unverifiable claims
""",
        variables={},
        tags=["research", "analysis"],
        is_builtin=True,
    ),
    PromptTemplate(
        id="tpl-devops-engineer",
        name="DevOps Engineer",
        description="Infrastructure, deployment, and CI/CD specialist",
        content="""You are a DevOps engineer specializing in cloud infrastructure, CI/CD pipelines, and deployment automation.

[EXPERTISE]
- Container orchestration (Docker, Kubernetes)
- CI/CD pipeline design (GitHub Actions, GitLab CI)
- Infrastructure as Code (Terraform, Pulumi)
- Cloud platforms (AWS, GCP, Azure)
- Monitoring and observability

[WORKFLOW]
1. Assess current infrastructure state
2. Identify improvement opportunities
3. Propose solutions with trade-off analysis
4. Provide implementation steps

[SAFETY]
- Always confirm before destructive operations
- Prefer reversible changes
- Document rollback procedures
""",
        variables={},
        tags=["devops", "infrastructure"],
        is_builtin=True,
    ),
    PromptTemplate(
        id="tpl-code-reviewer",
        name="Code Reviewer",
        description="Thorough code review with constructive feedback",
        content="""You are a senior code reviewer ensuring code quality, security, and maintainability.

[REVIEW CRITERIA]
1. Correctness: Does the code work as intended?
2. Security: Are there any vulnerabilities?
3. Performance: Are there obvious bottlenecks?
4. Readability: Is the code easy to understand?
5. Maintainability: Is the code easy to modify?

[FEEDBACK FORMAT]
- Issue: [description]
- Severity: CRITICAL / HIGH / MEDIUM / LOW
- Suggestion: [specific fix]
- Location: [file:line]

[TONE]
- Be constructive and specific
- Explain the "why" behind suggestions
- Acknowledge good patterns when found
""",
        variables={},
        tags=["review", "quality"],
        is_builtin=True,
    ),
]


class PromptTemplateRepository:
    """Repository for managing prompt templates with persistence."""

    def __init__(self) -> None:
        self._templates: dict[str, PromptTemplate] = {}
        self._load_builtins()

    def _load_builtins(self) -> None:
        """Load built-in templates."""
        for template in BUILTIN_TEMPLATES:
            self._templates[template.id] = template

    def create(
        self,
        name: str,
        content: str,
        description: str = "",
        variables: dict[str, str] | None = None,
        tags: list[str] | None = None,
        model_id: str | None = None,
    ) -> PromptTemplate:
        """Create a new prompt template."""
        now = datetime.now(UTC).isoformat()
        template = PromptTemplate(
            id=str(uuid.uuid4()),
            name=name,
            description=description,
            content=content,
            variables=variables or {},
            tags=tags or [],
            model_id=model_id,
            created_at=now,
            updated_at=now,
        )
        self._templates[template.id] = template
        return template

    def get(self, template_id: str) -> PromptTemplate | None:
        """Get a template by ID."""
        return self._templates.get(template_id)

    def list_all(self) -> list[PromptTemplate]:
        """List all templates."""
        return list(self._templates.values())

    def list_by_tag(self, tag: str) -> list[PromptTemplate]:
        """List templates filtered by tag."""
        return [t for t in self._templates.values() if tag in t.tags]

    def list_by_model(self, model_id: str) -> list[PromptTemplate]:
        """List templates for a specific model."""
        return [t for t in self._templates.values() if t.model_id == model_id]

    def list_builtins(self) -> list[PromptTemplate]:
        """List only built-in templates."""
        return [t for t in self._templates.values() if t.is_builtin]

    def list_custom(self) -> list[PromptTemplate]:
        """List only user-created templates."""
        return [t for t in self._templates.values() if not t.is_builtin]

    def update(self, template_id: str, **kwargs: Any) -> PromptTemplate | None:
        """Update an existing template."""
        template = self._templates.get(template_id)
        if not template:
            return None
        if template.is_builtin:
            logger.warning("Cannot update built-in template: %s", template_id)
            return None

        for key, value in kwargs.items():
            if hasattr(template, key) and key != "id":
                setattr(template, key, value)

        template.updated_at = datetime.now(UTC).isoformat()
        return template

    def delete(self, template_id: str) -> bool:
        """Delete a template. Built-in templates cannot be deleted."""
        template = self._templates.get(template_id)
        if not template:
            return False
        if template.is_builtin:
            logger.warning("Cannot delete built-in template: %s", template_id)
            return False
        del self._templates[template_id]
        return True

    def duplicate(self, template_id: str, new_name: str | None = None) -> PromptTemplate | None:
        """Duplicate an existing template."""
        template = self._templates.get(template_id)
        if not template:
            return None

        now = datetime.now(UTC).isoformat()
        new_template = PromptTemplate(
            id=str(uuid.uuid4()),
            name=new_name or f"{template.name} (Copy)",
            description=template.description,
            content=template.content,
            variables=dict(template.variables),
            tags=list(template.tags),
            model_id=template.model_id,
            created_at=now,
            updated_at=now,
        )
        self._templates[new_template.id] = new_template
        return new_template

    def export_template(self, template_id: str) -> str | None:
        """Export a single template as JSON string."""
        template = self._templates.get(template_id)
        if not template:
            return None
        return json.dumps(template.to_dict(), indent=2, ensure_ascii=False)

    def export_all(self) -> str:
        """Export all custom templates as JSON string."""
        custom = [t.to_dict() for t in self._templates.values() if not t.is_builtin]
        return json.dumps(custom, indent=2, ensure_ascii=False)

    def import_template(self, json_str: str) -> PromptTemplate | None:
        """Import a template from JSON string."""
        try:
            data = json.loads(json_str)
            if isinstance(data, list):
                if not data:
                    return None
                data = data[0]

            template = PromptTemplate.from_dict(data)
            template.id = str(uuid.uuid4())
            template.is_builtin = False
            template.created_at = datetime.now(UTC).isoformat()
            template.updated_at = template.created_at
            self._templates[template.id] = template
            return template
        except (json.JSONDecodeError, KeyError) as e:
            logger.error("Failed to import template: %s", e)
            return None

    def import_bulk(self, json_str: str) -> list[PromptTemplate]:
        """Import multiple templates from JSON string."""
        imported: list[PromptTemplate] = []
        try:
            data = json.loads(json_str)
            if not isinstance(data, list):
                data = [data]

            for item in data:
                try:
                    template = PromptTemplate.from_dict(item)
                    template.id = str(uuid.uuid4())
                    template.is_builtin = False
                    template.created_at = datetime.now(UTC).isoformat()
                    template.updated_at = template.created_at
                    self._templates[template.id] = template
                    imported.append(template)
                except Exception as e:
                    logger.warning("Skipping invalid template: %s", e)
        except json.JSONDecodeError as e:
            logger.error("Failed to parse import JSON: %s", e)

        return imported
