"""Owner-scoped discovery router; mount alongside existing /models routes."""

from typing import Annotated, Any

from fastapi import APIRouter, HTTPException, Query, Request, Response
from sqlalchemy import select

from app.api.v1.common import current_user_id
from app.core.api_key_crypto import decrypt_api_key
from app.services.model_discovery import DiscoveryError, discover_models
from app.storage import async_session
from app.storage.database import ApiKey

router = APIRouter(prefix="/models", tags=["model-discovery"])


@router.get("/discover")
async def discover_saved_models(
    request: Request, response: Response,
    credential_id: Annotated[str, Query(min_length=1, max_length=128)],
) -> dict[str, Any]:
    owner_id = current_user_id(request)
    response.headers["Cache-Control"] = "no-store"
    async with async_session() as session:
        row = (await session.execute(
            select(ApiKey).where(
                ApiKey.id == credential_id, ApiKey.user_id == owner_id, ApiKey.is_active.is_(True),
            )
        )).scalar_one_or_none()
        if row is None:
            raise HTTPException(404, detail={"code": "credential_not_found", "message": "Active credential not found."}, headers={"Cache-Control": "no-store"})
        provider, base_url = row.provider, row.base_url
        try:
            api_key = decrypt_api_key(row.api_key_encrypted or "")
        except ValueError:
            raise HTTPException(422, detail={"code": "credential_unreadable", "message": "Save the provider credential again."}, headers={"Cache-Control": "no-store"}) from None
    try:
        result = await discover_models(provider, api_key, base_url)
    except DiscoveryError as exc:
        raise HTTPException(exc.status_code, detail={"code": exc.code, "message": str(exc)}, headers={"Cache-Control": "no-store"}) from None
    return {**result, "credential_id": credential_id}
