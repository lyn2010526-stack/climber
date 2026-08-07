"""Regression coverage for runtime infrastructure fixes."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from starlette.requests import Request

from app.api.v1 import prompt_templates
from app.config import Settings
from app.core.api_key_crypto import decrypt_api_key, encrypt_api_key
from app.main import FRONTEND_DIR, app
from app.middleware.metrics import MetricsMiddleware
from app.middleware.security import RateLimitMiddleware, SecurityHeadersMiddleware
from app.storage import async_session
from app.storage.database import Agent, Message, Session
from app.storage.models_eval import EvalDataset
from app.storage.models_feedback import Feedback
from app.storage.models_reasoning import ReasoningFeedbackDB, ReasoningTraceDB
from app.storage.usage import usage_tracker


def _request(client_host: str, headers: list[tuple[bytes, bytes]]) -> Request:
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/api/v1/stats",
            "headers": headers,
            "client": (client_host, 1234),
            "scheme": "http",
            "server": ("test", 80),
            "query_string": b"",
        }
    )


def test_rate_limit_uses_forwarded_ip_only_for_trusted_proxy() -> None:
    middleware = RateLimitMiddleware(lambda scope, receive, send: None, trusted_proxies=["10.0.0.0/8"])
    forwarded = [(b"x-forwarded-for", b"203.0.113.9, 10.1.2.3")]

    assert middleware._get_client_ip(_request("10.1.2.3", forwarded)) == "203.0.113.9"
    assert middleware._get_client_ip(_request("198.51.100.4", forwarded)) == "198.51.100.4"


def test_rate_limit_skips_health_and_options(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    async def reject(client_id: str) -> tuple[bool, str]:
        calls.append(client_id)
        return False, "limited"

    monkeypatch.setattr(usage_tracker, "check_rate_limit", reject)
    test_app = FastAPI()
    test_app.add_middleware(RateLimitMiddleware, trusted_proxies=[])

    @test_app.get("/health")
    async def health() -> dict[str, bool]:
        return {"ok": True}

    @test_app.get("/limited")
    async def limited() -> dict[str, bool]:
        return {"ok": True}

    with TestClient(test_app) as client:
        assert client.get("/health").status_code == 200
        assert client.options("/limited").status_code != 429
        assert client.get("/limited").status_code == 429
    assert len(calls) == 1


def test_429_keeps_cors_security_headers_and_metrics(monkeypatch: pytest.MonkeyPatch) -> None:
    async def reject(client_id: str) -> tuple[bool, str]:
        return False, "limited"

    monkeypatch.setattr(usage_tracker, "check_rate_limit", reject)
    with TestClient(app) as client:
        response = client.get(
            "/api/v1/stats",
            headers={"Origin": "http://localhost:5173"},
        )
    assert response.status_code == 429
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert response.headers["x-content-type-options"] == "nosniff"

    monkeypatch.undo()
    with TestClient(app) as client:
        metrics = client.get("/metrics").text
    assert 'endpoint="/api/v1/stats",method="GET",status="429"' in metrics


def test_500_keeps_security_headers_and_metrics() -> None:
    test_app = FastAPI()
    test_app.add_middleware(SecurityHeadersMiddleware)
    test_app.add_middleware(MetricsMiddleware)
    test_app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @test_app.get("/boom")
    async def boom() -> None:
        raise RuntimeError("boom")

    with TestClient(test_app) as client:
        response = client.get("/boom", headers={"Origin": "http://localhost:5173"})
    assert response.status_code == 500
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_frontend_dist_and_docker_multistage_contract() -> None:
    root = Path(__file__).resolve().parents[1]
    dockerfile = (root / "Dockerfile").read_text(encoding="utf-8")

    assert root / "frontend-react" / "dist" == FRONTEND_DIR
    assert (FRONTEND_DIR / "index.html").is_file()
    assert (FRONTEND_DIR / "assets").is_dir()
    assert "FROM node:22-slim AS frontend-builder" in dockerfile
    assert "RUN npm ci" in dockerfile
    assert "RUN npm run build" in dockerfile
    assert "COPY --from=frontend-builder /frontend/dist /app/frontend-react/dist" in dockerfile


def test_prompt_template_routes_have_one_prefix_and_fixed_routes_first() -> None:
    paths = [route.path for route in prompt_templates.router.routes]
    app_paths = set(app.openapi()["paths"])

    assert all("prompt-templates/prompt-templates" not in path for path in app_paths)
    assert "/api/v1/prompt-templates" in app_paths
    assert paths.index("/import") < paths.index("/{template_id}")
    assert paths.index("/import-bulk") < paths.index("/{template_id}")
    assert paths.index("/export-all") < paths.index("/{template_id}")


def test_stable_secret_across_settings_and_crypto_instances() -> None:
    first = Settings(_env_file=None, app_testing=True, app_secret_key="")
    second = Settings(_env_file=None, app_testing=True, app_secret_key="")
    assert first.app_secret_key == second.app_secret_key

    encrypted = encrypt_api_key("provider-secret")
    assert decrypt_api_key(encrypted) == "provider-secret"


def test_same_key_decrypts_across_processes() -> None:
    env = os.environ.copy()
    env["APP_SECRET_KEY"] = "test-persistent-cross-process-key"
    encrypted = subprocess.run(
        [sys.executable, "-c", "from app.core.api_key_crypto import encrypt_api_key; print(encrypt_api_key('value'))"],
        check=True,
        capture_output=True,
        text=True,
        env=env,
    ).stdout.strip()
    decrypted = subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys; from app.core.api_key_crypto import decrypt_api_key; print(decrypt_api_key(sys.argv[1]))",
            encrypted,
        ],
        check=True,
        capture_output=True,
        text=True,
        env=env,
    ).stdout.strip()
    assert decrypted == "value"


def test_auth_and_production_require_explicit_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("APP_SECRET_KEY", raising=False)
    with pytest.raises(ValueError, match="APP_SECRET_KEY"):
        Settings(
            _env_file=None,
            app_env="local",
            app_testing=False,
            enable_auth=True,
            app_secret_key="",
        )
    with pytest.raises(ValueError, match="APP_SECRET_KEY"):
        Settings(
            _env_file=None,
            app_env="production",
            app_testing=False,
            enable_auth=False,
            app_secret_key="",
        )


@pytest.mark.asyncio
async def test_message_and_reasoning_feedback_use_correct_relations(client) -> None:
    async with async_session() as db:
        agent = Agent(user_id="default-user", name="A", provider="test", model_id="test")
        db.add(agent)
        await db.flush()
        session = Session(agent_id=agent.id, user_id="default-user")
        db.add(session)
        await db.flush()
        message = Message(session_id=session.id, role="assistant", content="answer")
        trace = ReasoningTraceDB(
            trace_id="trace-feedback",
            user_id="default-user",
            task="task",
            mode="standard",
        )
        db.add_all([message, trace])
        await db.commit()
        message_id = message.id

    missing = await client.post("/api/v1/feedback", json={"message_id": "missing", "rating": "up"})
    assert missing.status_code == 404
    created = await client.post(
        "/api/v1/feedback",
        json={"message_id": message_id, "rating": "up"},
    )
    assert created.status_code == 200
    reasoning = await client.post(
        "/api/v1/feedback/reason/trace-feedback/feedback",
        json={"thumbs": "down", "comment": "incorrect path"},
    )
    assert reasoning.status_code == 200

    async with async_session() as db:
        message_feedback = (await db.execute(select(Feedback))).scalars().all()
        reasoning_feedback = (await db.execute(select(ReasoningFeedbackDB))).scalars().all()
    assert [row.message_id for row in message_feedback] == [message_id]
    assert [row.trace_id for row in reasoning_feedback] == ["trace-feedback"]


@pytest.mark.asyncio
async def test_eval_validation_ownership_and_user_filtered_list(client) -> None:
    async with async_session() as db:
        own_agent = Agent(user_id="default-user", name="own", provider="test", model_id="test")
        other_agent = Agent(user_id="other", name="other", provider="test", model_id="test")
        own_dataset = EvalDataset(user_id="default-user", name="own")
        other_dataset = EvalDataset(user_id="other", name="other")
        db.add_all([own_agent, other_agent, own_dataset, other_dataset])
        await db.commit()
        ids = own_agent.id, other_agent.id, own_dataset.id, other_dataset.id

    own_agent_id, other_agent_id, own_dataset_id, other_dataset_id = ids
    assert (await client.post("/api/v1/eval/run", json={})).status_code == 422
    assert (
        await client.post(
            "/api/v1/eval/run",
            json={"dataset_id": other_dataset_id, "agent_id": own_agent_id},
        )
    ).status_code == 404
    assert (
        await client.post(
            "/api/v1/eval/run",
            json={"dataset_id": own_dataset_id, "agent_id": other_agent_id},
        )
    ).status_code == 404
    created = await client.post(
        "/api/v1/eval/run",
        json={"dataset_id": own_dataset_id, "agent_id": own_agent_id},
    )
    assert created.status_code == 200
    datasets = (await client.get("/api/v1/eval/datasets")).json()
    assert [dataset["id"] for dataset in datasets] == [own_dataset_id]


@pytest.mark.asyncio
async def test_feedback_integrity_error_rolls_back(monkeypatch: pytest.MonkeyPatch, client) -> None:
    class BrokenSession:
        rolled_back = False
        execute_calls = 0

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def execute(self, statement):
            self.execute_calls += 1

            class Result:
                def __init__(self, value):
                    self.value = value

                def scalar_one_or_none(self):
                    return self.value

            return Result(object() if self.execute_calls == 1 else None)

        def add(self, value):
            return None

        async def commit(self):
            raise IntegrityError("insert", {}, Exception("constraint"))

        async def rollback(self):
            self.rolled_back = True

    broken = BrokenSession()
    monkeypatch.setattr("app.api.v1.feedback.async_session", lambda: broken)
    response = await client.post(
        "/api/v1/feedback",
        json={"message_id": "message", "rating": "up"},
    )
    assert response.status_code == 422
    assert broken.rolled_back is True


def test_openapi_scale_and_operation_ids_are_unique() -> None:
    schema = app.openapi()
    operation_ids = [
        operation["operationId"]
        for path in schema["paths"].values()
        for operation in path.values()
        if isinstance(operation, dict) and "operationId" in operation
    ]
    assert 150 <= len(schema["paths"]) <= 165
    assert len(operation_ids) == len(set(operation_ids))
