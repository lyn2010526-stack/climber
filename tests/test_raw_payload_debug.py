"""Contract tests for the Raw Payload `debug` policy.

`debug` persists the encrypted full canonical payload plus an expiry window,
so the standard projection stays comparable while storage is reclaimable.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from app.core.raw_payload import (
    RawPayloadConfig,
    RawPayloadSnapshot,
    build_raw_payload,
    decrypt_payload_ciphertext,
    payload_digest,
)
from app.core.run_protocol import RunRecord
from app.storage import async_session
from app.storage.database import Session as SessionModel
from app.storage.run_store import SQLAlchemyRunStore


def make_raw_response(**overrides):
    raw = {
        "model": "provider-model-x",
        "choices": [
            {
                "finish_reason": "stop",
                "message": {
                    "role": "assistant",
                    "content": "hello",
                    "tool_calls": [
                        {
                            "id": "call-1",
                            "type": "function",
                            "function": {
                                "name": "read_file",
                                "arguments": '{"path": "/tmp/x"}',
                            },
                        }
                    ],
                },
            }
        ],
        "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
    }
    raw.update(overrides)
    return raw


class TestBuildDebugPayload:
    def test_debug_policy_sets_ciphertext_and_expiry(self):
        config = RawPayloadConfig(policy="debug", retention_days=7, max_bytes=256 * 1024)
        snapshot = build_raw_payload(
            run_id="run-d1",
            message_id="msg-1",
            provider="openai",
            model="gpt-4o",
            raw=make_raw_response(),
            config=config,
        )

        assert isinstance(snapshot, RawPayloadSnapshot)
        assert snapshot.payload_ciphertext is not None
        assert snapshot.payload_ciphertext.startswith("pl:v1:")
        assert snapshot.expires_at is not None
        span = snapshot.expires_at - datetime.now(UTC)
        assert timedelta(days=6) < span <= timedelta(days=7)

    def test_debug_ciphertext_round_trips_to_canonical_payload(self):
        config = RawPayloadConfig(policy="debug", retention_days=1, max_bytes=256 * 1024)
        raw = make_raw_response()
        snapshot = build_raw_payload(
            run_id="run-d2",
            message_id=None,
            provider="openai",
            model="gpt-4o",
            raw=raw,
            config=config,
        )

        plaintext = decrypt_payload_ciphertext(snapshot.payload_ciphertext)
        from app.core.raw_payload import canonical_json, redact_payload

        assert plaintext == canonical_json(redact_payload(raw))

    def test_debug_digest_matches_redacted_canonical(self):
        config = RawPayloadConfig(policy="debug", retention_days=1, max_bytes=256 * 1024)
        raw = make_raw_response()
        snapshot = build_raw_payload(
            run_id="run-d3",
            message_id=None,
            provider="openai",
            model="gpt-4o",
            raw=raw,
            config=config,
        )

        assert snapshot.payload_digest == payload_digest(raw)

    def test_standard_policy_leaves_ciphertext_and_expiry_empty(self):
        config = RawPayloadConfig(policy="standard", retention_days=7, max_bytes=256 * 1024)
        snapshot = build_raw_payload(
            run_id="run-d4",
            message_id=None,
            provider="openai",
            model="gpt-4o",
            raw=make_raw_response(),
            config=config,
        )

        assert snapshot.payload_ciphertext is None
        assert snapshot.expires_at is None

    def test_decrypt_rejects_non_ciphertext(self):
        with pytest.raises(ValueError, match="pl:v1"):
            decrypt_payload_ciphertext("plain-json")


@pytest.mark.asyncio
async def test_debug_payload_persists_ciphertext_and_expiry():
    store = SQLAlchemyRunStore(session_factory=async_session)
    async with async_session() as db:
        db.add(SessionModel(id="session-d", user_id="user-1", title="debug"))
        await db.commit()
    await store.create(RunRecord(run_id="run-d5", session_id="session-d", user_id="user-1"))

    config = RawPayloadConfig(policy="debug", retention_days=7, max_bytes=256 * 1024)
    snapshot = build_raw_payload(
        run_id="run-d5",
        message_id=None,
        provider="openai",
        model="gpt-4o",
        raw=make_raw_response(),
        config=config,
    )
    stored = await store.save_raw_payload(snapshot)

    assert stored.payload_ciphertext == snapshot.payload_ciphertext
    assert stored.expires_at is not None
