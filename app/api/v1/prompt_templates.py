"""API endpoints for prompt template management."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException

from app.core.prompt_engine.template_repository import PromptTemplateRepository

logger = logging.getLogger(__name__)

router = APIRouter()

_repository: PromptTemplateRepository | None = None


def get_repository() -> PromptTemplateRepository:
    """Get or create the template repository singleton."""
    global _repository
    if _repository is None:
        _repository = PromptTemplateRepository()
    return _repository


def set_repository(repo: PromptTemplateRepository) -> None:
    """Set the template repository (for testing/dependency injection)."""
    global _repository
    _repository = repo


@router.get("")
async def list_templates(
    tag: str | None = None,
    model_id: str | None = None,
    builtin_only: bool = False,
    custom_only: bool = False,
) -> list[dict[str, Any]]:
    """List prompt templates with optional filtering."""
    repo = get_repository()

    if builtin_only:
        templates = repo.list_builtins()
    elif custom_only:
        templates = repo.list_custom()
    elif tag:
        templates = repo.list_by_tag(tag)
    elif model_id:
        templates = repo.list_by_model(model_id)
    else:
        templates = repo.list_all()

    return [t.to_dict() for t in templates]


@router.post("")
async def create_template(body: dict[str, Any]) -> dict[str, Any]:
    """Create a new prompt template."""
    repo = get_repository()
    name = body.get("name", "").strip()
    content = body.get("content", "").strip()

    if not name:
        raise HTTPException(status_code=400, detail="Template name is required")
    if not content:
        raise HTTPException(status_code=400, detail="Template content is required")

    template = repo.create(
        name=name,
        content=content,
        description=body.get("description", ""),
        variables=body.get("variables"),
        tags=body.get("tags"),
        model_id=body.get("model_id"),
    )
    return template.to_dict()


@router.post("/import")
async def import_template(body: dict[str, Any]) -> dict[str, Any]:
    """Import a template from JSON."""
    repo = get_repository()
    json_str = body.get("json", "")
    if not json_str:
        raise HTTPException(status_code=400, detail="JSON data is required")

    template = repo.import_template(json_str)
    if template is None:
        raise HTTPException(status_code=400, detail="Failed to import template")

    return {"status": "imported", "template": template.to_dict()}


@router.post("/import-bulk")
async def import_bulk(body: dict[str, Any]) -> dict[str, Any]:
    """Import multiple templates from JSON array."""
    repo = get_repository()
    json_str = body.get("json", "")
    if not json_str:
        raise HTTPException(status_code=400, detail="JSON data is required")

    imported = repo.import_bulk(json_str)
    return {
        "status": "imported",
        "count": len(imported),
        "templates": [t.to_dict() for t in imported],
    }


@router.get("/export-all")
async def export_all() -> dict[str, str]:
    """Export all custom templates as JSON."""
    repo = get_repository()
    return {"json": repo.export_all()}


@router.get("/{template_id}")
async def get_template(template_id: str) -> dict[str, Any]:
    """Get a specific template by ID."""
    repo = get_repository()
    template = repo.get(template_id)
    if template is None:
        raise HTTPException(status_code=404, detail="Template not found")
    return template.to_dict()


@router.put("/{template_id}")
async def update_template(template_id: str, body: dict[str, Any]) -> dict[str, Any]:
    """Update an existing template."""
    repo = get_repository()
    updates = {
        key: body[key]
        for key in ["name", "content", "description", "variables", "tags", "model_id"]
        if key in body
    }
    template = repo.update(template_id, **updates)
    if template is None:
        raise HTTPException(status_code=404, detail="Template not found or is built-in")
    return template.to_dict()


@router.delete("/{template_id}")
async def delete_template(template_id: str) -> dict[str, str]:
    """Delete a template."""
    repo = get_repository()
    if not repo.delete(template_id):
        raise HTTPException(status_code=404, detail="Template not found or is built-in")
    return {"status": "deleted", "id": template_id}


@router.post("/{template_id}/duplicate")
async def duplicate_template(
    template_id: str, body: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Duplicate an existing template."""
    repo = get_repository()
    new_name = body.get("name") if body else None
    template = repo.duplicate(template_id, new_name)
    if template is None:
        raise HTTPException(status_code=404, detail="Template not found")
    return template.to_dict()


@router.post("/{template_id}/render")
async def render_template(
    template_id: str, body: dict[str, Any] | None = None
) -> dict[str, str]:
    """Render a template with variable substitution."""
    repo = get_repository()
    template = repo.get(template_id)
    if template is None:
        raise HTTPException(status_code=404, detail="Template not found")
    variables = body.get("variables") if body else None
    return {"rendered": template.render(variables), "template_id": template_id}


@router.get("/{template_id}/export")
async def export_template(template_id: str) -> dict[str, str]:
    """Export a template as JSON."""
    repo = get_repository()
    exported = repo.export_template(template_id)
    if exported is None:
        raise HTTPException(status_code=404, detail="Template not found")
    return {"json": exported}
