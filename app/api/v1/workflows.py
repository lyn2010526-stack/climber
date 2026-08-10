"""Workflow import, export, and template endpoints."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import structlog
from fastapi import APIRouter, HTTPException, Request, Response
from sqlalchemy import select

from app.workflow.io import WorkflowIO
from app.workflow.templates import WorkflowTemplates
from app.storage import async_session
from app.storage.models_platform import Workflow as WorkflowModel
from app.api.v1.generic import _payload

logger = structlog.get_logger()
router = APIRouter()


def _workflow_dict(w: WorkflowModel) -> dict[str, Any]:
    return {
        "id": w.id,
        "name": w.name,
        "description": w.description,
        "nodes": w.nodes or [],
        "edges": w.edges or [],
        "is_template": w.is_template,
        "run_count": w.run_count,
        "last_status": w.last_status,
        "created_at": w.created_at.isoformat() if w.created_at else None,
    }


@router.get("/templates")
@router.get("/templates/")
async def list_workflow_templates() -> list[dict[str, Any]]:
    """List available built-in workflow templates."""
    template_meta = WorkflowTemplates.list_templates()
    builtin: list[dict[str, Any]] = []
    for tpl in template_meta:
        template_fn = getattr(WorkflowTemplates, tpl["id"], None)
        if template_fn and callable(template_fn):
            try:
                if tpl["id"] == "simple_qa":
                    workflow = template_fn(provider="openai", model_id="gpt-4o", api_key="")
                elif tpl["id"] == "tool_use":
                    workflow = template_fn(tool_name="list_files", provider="openai", model_id="gpt-4o", api_key="")
                elif tpl["id"] == "chain_of_thought":
                    workflow = template_fn(provider="openai", model_id="gpt-4o", api_key="")
                elif tpl["id"] == "map_reduce":
                    workflow = template_fn(provider="openai", model_id="gpt-4o", api_key="")
                elif tpl["id"] == "conditional_branch":
                    workflow = template_fn(
                        provider="openai",
                        model_id="gpt-4o",
                        api_key="",
                        condition_var="input",
                        condition_value="true",
                        true_prompt="Handle true case",
                        false_prompt="Handle false case",
                    )
                else:
                    continue
                builtin.append({
                    "template_id": tpl["id"],
                    "name": tpl["name"],
                    "description": tpl["description"],
                    "nodes": [
                        {"id": n.id, "type": n.type.value, "data": {"label": n.name, **n.config}}
                        for n in workflow.nodes
                    ],
                    "edges": [
                        {"id": f"e{i}", "source": e.source, "target": e.target, "condition": e.condition}
                        for i, e in enumerate(workflow.edges)
                    ],
                })
            except Exception as exc:
                logger.warning("workflows.list_templates_failed", template_id=tpl["id"], error=str(exc))
                builtin.append({
                    "template_id": tpl["id"],
                    "name": tpl["name"],
                    "description": tpl["description"],
                })
        else:
            builtin.append({
                "template_id": tpl["id"],
                "name": tpl["name"],
                "description": tpl["description"],
            })
    return builtin


@router.post("/templates/{template_id}")
@router.post("/templates/{template_id}/create")
async def create_from_template(template_id: str, request: Request) -> dict[str, Any]:
    templates = await list_workflow_templates()
    tpl = next((t for t in templates if t["template_id"] == template_id), None)
    if tpl is None:
        raise HTTPException(status_code=404, detail=f"Template '{template_id}' not found")

    data = await _payload(request)
    async with async_session() as db:
        wf = WorkflowModel(
            user_id="default-user",
            name=data.get("name") or tpl["name"],
            description=tpl["description"],
            nodes=tpl.get("nodes", []),
            edges=tpl.get("edges", []),
            template_id=template_id,
        )
        db.add(wf)
        await db.commit()
        await db.refresh(wf)
        return _workflow_dict(wf)


@router.post("/import")
async def import_workflow(request: Request) -> dict[str, Any]:
    """Import a workflow from JSON or YAML data."""
    body = await request.json()
    if not isinstance(body, dict):
        raise HTTPException(status_code=422, detail="Request body must be a JSON object")
    workflow_data = body.get("data", body)

    result = WorkflowIO.import_workflow(workflow_data)
    if not result.success:
        raise HTTPException(
            status_code=422,
            detail={
                "message": "Workflow validation failed",
                "errors": [e.model_dump() for e in result.errors],
                "warnings": result.warnings,
            },
        )

    if result.workflow is None:
        raise HTTPException(status_code=422, detail="Failed to construct workflow from import data")

    async with async_session() as db:
        wf = WorkflowModel(
            user_id="default-user",
            name=result.workflow.name,
            description=result.workflow.description,
            nodes=[n.model_dump() for n in result.workflow.nodes],
            edges=[e.model_dump() for e in result.workflow.edges],
        )
        db.add(wf)
        await db.commit()
        await db.refresh(wf)

        response = _workflow_dict(wf)
        response["migrated"] = result.migrated
        response["original_version"] = result.original_version
        response["warnings"] = result.warnings
        return response


@router.post("/{workflow_id}/export")
async def export_workflow(workflow_id: str, request: Request) -> Response:
    """Export a workflow as a downloadable file."""
    body = await request.json()
    fmt = (body.get("format") or "json").lower() if isinstance(body, dict) else "json"

    async with async_session() as db:
        wf = (await db.execute(
            select(WorkflowModel).where(WorkflowModel.id == workflow_id)
        )).scalar_one_or_none()
        if wf is None:
            raise HTTPException(status_code=404, detail="Workflow not found")

    from app.workflow import Workflow, WorkflowNode, WorkflowEdge
    workflow = Workflow(
        id=wf.id,
        name=wf.name,
        description=wf.description,
        nodes=[WorkflowNode(**n) for n in (wf.nodes or [])],
        edges=[WorkflowEdge(**e) for e in (wf.edges or [])],
    )

    return _build_export_response(workflow, workflow_id, fmt)


@router.get("/{workflow_id}/export")
async def export_workflow_get(workflow_id: str, format: str = "json") -> Response:
    """Export a workflow as a downloadable file (GET)."""
    fmt = format.lower()

    async with async_session() as db:
        wf = (await db.execute(
            select(WorkflowModel).where(WorkflowModel.id == workflow_id)
        )).scalar_one_or_none()
        if wf is None:
            raise HTTPException(status_code=404, detail="Workflow not found")

    from app.workflow import Workflow, WorkflowNode, WorkflowEdge
    workflow = Workflow(
        id=wf.id,
        name=wf.name,
        description=wf.description,
        nodes=[WorkflowNode(**n) for n in (wf.nodes or [])],
        edges=[WorkflowEdge(**e) for e in (wf.edges or [])],
    )

    return _build_export_response(workflow, workflow_id, fmt)


def _build_export_response(workflow: WorkflowModel, workflow_id: str, fmt: str) -> Response:
    if fmt == "yaml":
        try:
            import yaml  # type: ignore[import-untyped]
            content = yaml.dump(WorkflowIO.export_workflow(workflow), allow_unicode=True, sort_keys=False)
            media_type = "application/x-yaml"
            filename = f"workflow-{workflow_id}.yaml"
        except ImportError:
            raise HTTPException(status_code=400, detail="PyYAML is required for YAML export. Install it with: pip install pyyaml")
    else:
        content = json.dumps(WorkflowIO.export_workflow(workflow), indent=2, ensure_ascii=False)
        media_type = "application/json"
        filename = f"workflow-{workflow_id}.json"

    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
