"""File and image upload endpoints for chat attachments."""

from __future__ import annotations

import base64
import hashlib
from pathlib import Path
from typing import Any
from uuid import uuid4

import structlog
from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from pydantic import BaseModel

from app.api.v1.common import current_user_id

logger = structlog.get_logger()

router = APIRouter()

UPLOAD_ROOT = Path("./data/uploads")
MAX_UPLOAD_BYTES = 20 * 1024 * 1024

IMAGE_TYPES = {"image/png", "image/jpeg", "image/webp", "image/gif"}
TEXT_SUFFIXES = {
    ".txt", ".md", ".py", ".js", ".ts", ".tsx", ".jsx", ".json", ".yaml",
    ".yml", ".toml", ".csv", ".html", ".css", ".sh", ".go", ".rs", ".java",
    ".c", ".cpp", ".h", ".sql",
}


class UploadResponse(BaseModel):
    id: str
    name: str
    content_type: str
    size: int
    kind: str
    url: str


def _classify(content_type: str, filename: str) -> str:
    if content_type in IMAGE_TYPES or content_type.startswith("image/"):
        return "image"
    if Path(filename).suffix.lower() in TEXT_SUFFIXES:
        return "text"
    return "file"


def _safe_suffix(filename: str) -> str:
    suffix = Path(filename).suffix.lower()
    if len(suffix) > 10 or not suffix.replace(".", "").isalnum():
        return ""
    return suffix


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def _read_upload(upload_id: str) -> Path:
    if "/" in upload_id or "\\" in upload_id or upload_id.startswith("."):
        raise HTTPException(status_code=400, detail="Invalid upload id")
    target = UPLOAD_ROOT / upload_id
    if not target.exists() or not target.is_file() or not _is_within(target, UPLOAD_ROOT):
        raise HTTPException(status_code=404, detail="Upload not found")
    return target


@router.post("", response_model=UploadResponse)
async def upload_file(request: Request, file: UploadFile = File(...)) -> UploadResponse:
    """Store an uploaded file and return a stable reference for chat messages."""
    user_id = current_user_id(request)
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty upload")
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Upload exceeds 20MB limit")

    filename = file.filename or "upload"
    content_type = file.content_type or "application/octet-stream"
    digest = hashlib.sha256(content).hexdigest()[:12]
    upload_id = f"{uuid4().hex}-{digest}{_safe_suffix(filename)}"

    UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)
    (UPLOAD_ROOT / upload_id).write_bytes(content)

    logger.info(
        "uploads.stored",
        upload_id=upload_id,
        user_id=user_id,
        content_type=content_type,
        size=len(content),
    )
    return UploadResponse(
        id=upload_id,
        name=filename,
        content_type=content_type,
        size=len(content),
        kind=_classify(content_type, filename),
        url=f"/api/v1/uploads/{upload_id}",
    )


@router.get("/{upload_id}")
async def get_upload(upload_id: str, request: Request) -> Any:
    """Serve a previously uploaded file."""
    from fastapi.responses import FileResponse

    current_user_id(request)
    path = _read_upload(upload_id)
    return FileResponse(path)


def resolve_attachment_content(
    upload_id: str,
    kind: str,
    content_type: str,
    max_text_bytes: int = 100_000,
) -> dict[str, Any] | None:
    """Load an uploaded attachment into a model-ready content part.

    Returns an OpenAI-style content part for images, or a text block for
    text/code files. Returns None when the attachment cannot be inlined.
    """
    try:
        path = _read_upload(upload_id)
    except HTTPException:
        return None

    data = path.read_bytes()
    if kind == "image":
        encoded = base64.b64encode(data).decode("ascii")
        return {
            "type": "image_url",
            "image_url": {"url": f"data:{content_type};base64,{encoded}"},
        }
    if kind == "text":
        try:
            text = data[:max_text_bytes].decode("utf-8")
        except UnicodeDecodeError:
            return None
        return {"type": "text", "text": f"\n\n[Attached file: {path.name}]\n{text}"}
    return None