"""End-to-end tests for the chat attachment pipeline.

Covers: multipart upload -> ChatRequest.attachments -> engine content building.
"""

from __future__ import annotations

import base64
import io

import pytest

from app.core.agent_engine import AgentEngine
from app.core.session import AgentSession


async def test_upload_returns_stable_reference(client) -> None:
    files = {"file": ("note.txt", io.BytesIO(b"hello attachment"), "text/plain")}
    response = await client.post("/api/v1/uploads", files=files)

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "note.txt"
    assert body["content_type"] == "text/plain"
    assert body["size"] == len(b"hello attachment")
    assert body["kind"] == "text"
    assert body["id"]
    assert body["url"] == f"/api/v1/uploads/{body['id']}"


async def test_upload_rejects_empty_file(client) -> None:
    files = {"file": ("empty.txt", io.BytesIO(b""), "text/plain")}
    response = await client.post("/api/v1/uploads", files=files)

    assert response.status_code == 400


async def test_uploaded_file_can_be_served_back(client) -> None:
    payload = b"\x89PNG\r\n\x1a\nfake"
    files = {"file": ("pic.png", io.BytesIO(payload), "image/png")}
    uploaded = await client.post("/api/v1/uploads", files=files)
    upload_id = uploaded.json()["id"]

    fetched = await client.get(f"/api/v1/uploads/{upload_id}")

    assert fetched.status_code == 200
    assert fetched.content == payload


async def test_get_unknown_upload_is_404(client) -> None:
    response = await client.get("/api/v1/uploads/does-not-exist")

    assert response.status_code == 404


def _engine() -> AgentEngine:
    return AgentEngine(model_registry=None, tool_registry=None)  # type: ignore[arg-type]


def _session() -> AgentSession:
    return AgentSession(
        session_id="att-test",
        agent_id="",
        user_id="",
        provider="openai",
        model_id="gpt-4o-mini",
        api_key="k",
        base_url=None,
        system_prompt="",
        tools=[],
    )


def test_plain_message_without_attachments_stays_string() -> None:
    content, meta = _engine()._build_user_content("just text", None)

    assert content == "just text"
    assert meta == []


async def test_text_attachment_inlined_with_metadata(client) -> None:
    files = {"file": ("spec.md", io.BytesIO(b"# Design\nbody"), "text/markdown")}
    uploaded = (await client.post("/api/v1/uploads", files=files)).json()

    content, meta = _engine()._build_user_content(
        "review this",
        [{"id": uploaded["id"], "name": uploaded["name"], "kind": uploaded["kind"],
          "content_type": uploaded["content_type"]}],
    )

    assert isinstance(content, str)
    assert "review this" in content
    assert "# Design" in content
    assert meta[0]["id"] == uploaded["id"]
    assert meta[0]["kind"] == "text"


async def test_image_attachment_builds_multimodal_parts(client) -> None:
    payload = b"\x89PNG\r\n\x1a\nfake-image-bytes"
    files = {"file": ("shot.png", io.BytesIO(payload), "image/png")}
    uploaded = (await client.post("/api/v1/uploads", files=files)).json()

    content, meta = _engine()._build_user_content(
        "what is wrong here?",
        [{"id": uploaded["id"], "name": uploaded["name"], "kind": uploaded["kind"],
          "content_type": uploaded["content_type"]}],
    )

    assert isinstance(content, list)
    text_parts = [p for p in content if p["type"] == "text"]
    image_parts = [p for p in content if p["type"] == "image_url"]
    assert text_parts[0]["text"] == "what is wrong here?"
    assert len(image_parts) == 1
    data_url = image_parts[0]["image_url"]["url"]
    assert data_url.startswith("data:image/png;base64,")
    assert base64.b64decode(data_url.split(",", 1)[1]) == payload
    assert meta[0]["kind"] == "image"


def test_missing_attachment_is_reported_not_crashed() -> None:
    content, meta = _engine()._build_user_content(
        "look",
        [{"id": "ghost-file", "name": "ghost.png", "kind": "image",
          "content_type": "image/png"}],
    )

    assert isinstance(content, str)
    assert "ghost.png" in content
    assert meta[0]["id"] == "ghost-file"


@pytest.mark.parametrize("kind", ["file", "binary"])
def test_unresolvable_kind_falls_back_to_text(kind: str) -> None:
    content, meta = _engine()._build_user_content(
        "see attached",
        [{"id": "ghost", "name": "archive.zip", "kind": kind,
          "content_type": "application/zip"}],
    )

    assert isinstance(content, str)
    assert "archive.zip" in content
    assert meta[0]["kind"] == kind