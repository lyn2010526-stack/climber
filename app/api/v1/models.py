"""Model API endpoints."""

from __future__ import annotations

from typing import Any

import structlog
from fastapi import APIRouter

logger = structlog.get_logger()

router = APIRouter()


@router.get("/models")
@router.get("/models/")
async def list_models() -> list[dict[str, Any]]:
    models: list[dict[str, Any]] = [
        {"provider": "openai", "model_id": "gpt-4o", "label": "GPT-4o"},
        {"provider": "openai", "model_id": "gpt-4o-mini", "label": "GPT-4o mini"},
        {"provider": "anthropic", "model_id": "claude-3-5-sonnet-20241022", "label": "Claude 3.5 Sonnet"},
        {"provider": "google", "model_id": "gemini-1.5-pro", "label": "Gemini 1.5 Pro"},
        {"provider": "stepfun", "model_id": "step-1v-8k", "label": "Step-1V 8K"},
    ]
    try:
        import httpx
        from app.config import settings
        base = getattr(settings, "ollama_base_url", "http://localhost:11434")
        async with httpx.AsyncClient(timeout=1.5) as client:
            resp = await client.get(f"{base}/api/tags")
            if resp.status_code == 200:
                for m in resp.json().get("models", []):
                    models.append(
                        {"provider": "ollama", "model_id": m.get("name", ""), "label": f"{m.get('name','')} (local)"}
                    )
    except Exception as e:
        logger.warning("models.list_models_ollama_discovery", error=str(e))
    return models