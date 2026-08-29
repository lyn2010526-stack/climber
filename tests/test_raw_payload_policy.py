"""Contract tests for the Raw Payload `standard` policy.

Covers configuration loading, redaction, canonical digest, standard field
projection, truncation, and durable persistence of RawPayloadRecord.
"""

from __future__ import annotations

import hashlib

import pytest

from app.core.raw_payload import (
    REDACTED,
    REDACTION_VERSION,
    RawPayloadConfig,
    build_raw_payload,
    canonical_json,
    extract_standard_fields,
    load_raw_payload_config,
    payload_digest,
    redact_payload,
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


class TestConfig:
    def test_defaults(self, monkeypatch):
        for key in ("RUN_RAW_PAYLOAD_POLICY", "RUN_RAW_PAYLOAD_RETENTION_DAYS", "RUN_RAW_PAYLOAD_MAX_BYTES"):
            monkeypatch.delenv(key, raising=False)
        config = load_raw_payload_config()
        assert config.policy == "standard"
        assert config.retention_days == 7
        assert config.max_bytes > 0

    def test_env_overrides(self, monkeypatch):
        monkeypatch.setenv("RUN_RAW_PAYLOAD_POLICY", "debug")
        monkeypatch.setenv("RUN_RAW_PAYLOAD_RETENTION_DAYS", "3")
        monkeypatch.setenv("RUN_RAW_PAYLOAD_MAX_BYTES", "1024")
        config = load_raw_payload_config()
        assert config.policy == "debug"
        assert config.retention_days == 3
        assert config.max_bytes == 1024

    def test_invalid_policy_falls_back_to_standard(self, monkeypatch):
        monkeypatch.setenv("RUN_RAW_PAYLOAD_POLICY", "bogus")
        config = load_raw_payload_config()
        assert config.policy == "standard"

    def test_invalid_numeric_env_keeps_defaults(self, monkeypatch):
        monkeypatch.setenv("RUN_RAW_PAYLOAD_RETENTION_DAYS", "not-an-int")
        monkeypatch.setenv("RUN_RAW_PAYLOAD_MAX_BYTES", "")
        config = load_raw_payload_config()
        assert isinstance(config, RawPayloadConfig)
        assert config.retention_days > 0
        assert config.max_bytes > 0


class TestRedaction:
    def test_masks_sensitive_keys_recursively(self):
        payload = {
            "api_key": "sk-secret-value",
            "Authorization": "Bearer token-abc",
            "nested": {"access_token": "t1", "model": "m"},
            "items": [{"password": "p", "keep": 1}, "plain"],
        }
        result = redact_payload(payload)
        assert result["api_key"] == REDACTED
        assert result["Authorization"] == REDACTED
        assert result["nested"]["access_token"] == REDACTED
        assert result["nested"]["model"] == "m"
        assert result["items"][0]["password"] == REDACTED
        assert result["items"][0]["keep"] == 1
        assert result["items"][1] == "plain"

    def test_does_not_mutate_input(self):
        payload = {"api_key": "v", "data": {"token": "t"}}
        redact_payload(payload)
        assert payload == {"api_key": "v", "data": {"token": "t"}}

    def test_passthrough_for_non_collection_values(self):
        assert redact_payload("text") == "text"
        assert redact_payload(42) == 42
        assert redact_payload(None) is None


class TestDigest:
    def test_canonical_json_is_sorted_and_stable(self):
        assert canonical_json({"b": 1, "a": {"d": 1, "c": 2}}) == b'{"a":{"c":2,"d":1},"b":1}'

    def test_digest_matches_sha256_of_redacted_canonical(self):
        payload = {"api_key": "sk-1", "model": "m"}
        expected = hashlib.sha256(canonical_json(redact_payload(payload))).hexdigest()
        assert payload_digest(payload) == expected

    def test_digest_is_insensitive_to_secret_values(self):
        a = {"api_key": "sk-a", "model": "m"}
        b = {"api_key": "sk-b", "model": "m"}
        assert payload_digest(a) == payload_digest(b)


class TestStandardFields:
    def test_extracts_openai_shape(self):
        fields = extract_standard_fields(make_raw_response(), provider="openai", model="gpt-x")
        assert fields["provider"] == "openai"
        assert fields["model"] == "gpt-x"
        assert fields["finish_reason"] == "stop"
        assert fields["usage"] == {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}
        tool_call = fields["tool_calls"][0]
        assert tool_call["id"] == "call-1"
        assert tool_call["name"] == "read_file"
        assert tool_call["arguments"] == {"path": "/tmp/x"}

    def test_tolerates_missing_sections(self):
        fields = extract_standard_fields({}, provider="p", model="m")
        assert fields["finish_reason"] is None
        assert fields["usage"] == {}
        assert fields["tool_calls"] == []

    def test_tolerates_non_dict_payload(self):
        fields = extract_standard_fields("not-a-dict", provider="p", model="m")
        assert fields["finish_reason"] is None
        assert fields["tool_calls"] == []


class TestBuildRawPayload:
    def test_standard_mode_stores_projection_and_digest_only(self):
        config = RawPayloadConfig(policy="standard")
        result = build_raw_payload(
            run_id="run-1",
            message_id="msg-1",
            provider="openai",
            model="gpt-x",
            raw=make_raw_response(),
            config=config,
        )
        assert result.run_id == "run-1"
        assert result.message_id == "msg-1"
        assert result.provider == "openai"
        assert result.payload_ciphertext is None
        assert result.expires_at is None
        assert result.redaction_version == REDACTION_VERSION
        assert len(result.payload_digest) == 64
        assert result.standard_fields["provider"] == "openai"
        assert "payload_truncated" not in result.standard_fields

    def test_truncation_flag_when_canonical_exceeds_limit(self):
        config = RawPayloadConfig(policy="standard", max_bytes=50)
        raw = make_raw_response()
        raw["choices"][0]["message"]["content"] = "x" * 10_000
        result = build_raw_payload(
            run_id="run-1",
            message_id=None,
            provider="openai",
            model="gpt-x",
            raw=raw,
            config=config,
        )
        assert result.standard_fields["payload_truncated"] is True
        assert result.payload_ciphertext is None


@pytest.mark.asyncio
async def test_sqlalchemy_store_persists_raw_payload_roundtrip():
    async with async_session() as db:
        db.add(SessionModel(id="session-rp", user_id="user-1", title="Raw payload"))
        await db.commit()

    store = SQLAlchemyRunStore(session_factory=async_session)
    await store.create(
        RunRecord(run_id="run-rp-1", session_id="session-rp", user_id="user-1")
    )

    config = RawPayloadConfig(policy="standard")
    result = build_raw_payload(
        run_id="run-rp-1",
        message_id="msg-rp-1",
        provider="openai",
        model="gpt-x",
        raw=make_raw_response(),
        config=config,
    )
    saved = await store.save_raw_payload(result)

    loaded_store = SQLAlchemyRunStore(session_factory=async_session)
    records = await loaded_store.list_raw_payloads("run-rp-1")
    assert [r.id for r in records] == [saved.id]
    record = records[0]
    assert record.run_id == "run-rp-1"
    assert record.message_id == "msg-rp-1"
    assert record.provider == "openai"
    assert record.payload_digest == result.payload_digest
    assert record.redaction_version == REDACTION_VERSION
    assert record.payload_ciphertext is None
    assert record.expires_at is None
    assert record.standard_fields["finish_reason"] == "stop"

    assert await loaded_store.list_raw_payloads("run-missing") == []
