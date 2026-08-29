"""Provider raw payload policy.

`standard` persists provider, model, finish reason, usage, tool call standard
fields and a hash digest of the redacted canonical payload. Payloads whose
canonical encoding exceeds the configured byte limit keep the digest and
record `payload_truncated` instead of the full projection.

`debug` persists the same standard projection plus the full canonical payload
encrypted with the app secret, and stamps an expiry so a cleanup task can
reclaim storage after `retention_days`.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

import structlog

from app.core.api_key_crypto import _fernet

logger = structlog.get_logger(__name__)

REDACTED = "[REDACTED]"
REDACTION_VERSION = "1"

DEFAULT_RETENTION_DAYS = 7
DEFAULT_MAX_BYTES = 256 * 1024

_PAYLOAD_CIPHER_PREFIX = "pl:v1:"

_SENSITIVE_KEY_MARKERS = (
    "api_key",
    "apikey",
    "token",
    "secret",
    "password",
    "passwd",
    "authorization",
    "cookie",
    "private_key",
    "credential",
)
_USAGE_KEYS = ("prompt_tokens", "completion_tokens", "total_tokens")


@dataclass
class RawPayloadConfig:
    policy: str = "standard"
    retention_days: int = DEFAULT_RETENTION_DAYS
    max_bytes: int = DEFAULT_MAX_BYTES


@dataclass
class RawPayloadSnapshot:
    run_id: str
    message_id: str | None
    provider: str
    standard_fields: dict[str, Any] = field(default_factory=dict)
    payload_digest: str = ""
    redaction_version: str = REDACTION_VERSION
    payload_ciphertext: str | None = None
    expires_at: Any = None


def load_raw_payload_config() -> RawPayloadConfig:
    policy = (os.environ.get("RUN_RAW_PAYLOAD_POLICY") or "standard").strip().lower()
    if policy not in ("standard", "debug"):
        logger.warning("raw_payload.invalid_policy", policy=policy)
        policy = "standard"
    return RawPayloadConfig(
        policy=policy,
        retention_days=_read_positive_int("RUN_RAW_PAYLOAD_RETENTION_DAYS", DEFAULT_RETENTION_DAYS),
        max_bytes=_read_positive_int("RUN_RAW_PAYLOAD_MAX_BYTES", DEFAULT_MAX_BYTES),
    )


def _read_positive_int(name: str, default: int) -> int:
    raw = (os.environ.get(name) or "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        logger.warning("raw_payload.invalid_int_env", name=name, raw=raw)
        return default
    return value if value > 0 else default


def redact_payload(payload: Any) -> Any:
    if isinstance(payload, dict):
        return {
            key: REDACTED if _is_sensitive_key(key) else redact_payload(value)
            for key, value in payload.items()
        }
    if isinstance(payload, list):
        return [redact_payload(item) for item in payload]
    return payload


def _is_sensitive_key(key: Any) -> bool:
    if not isinstance(key, str):
        return False
    lowered = key.lower()
    return any(marker in lowered for marker in _SENSITIVE_KEY_MARKERS)


def canonical_json(payload: Any) -> bytes:
    return json.dumps(
        payload,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")


def payload_digest(payload: Any) -> str:
    return hashlib.sha256(canonical_json(redact_payload(payload))).hexdigest()


def extract_standard_fields(raw: Any, *, provider: str, model: str) -> dict[str, Any]:
    choice: dict[str, Any] = {}
    usage: dict[str, Any] = {}
    if isinstance(raw, dict):
        choices = raw.get("choices")
        if isinstance(choices, list) and choices and isinstance(choices[0], dict):
            choice = choices[0]
        raw_usage = raw.get("usage")
        if isinstance(raw_usage, dict):
            usage = raw_usage

    message = choice.get("message") if isinstance(choice.get("message"), dict) else {}
    return {
        "provider": provider,
        "model": model,
        "finish_reason": choice.get("finish_reason"),
        "usage": {key: usage[key] for key in _USAGE_KEYS if key in usage},
        "tool_calls": _standardize_tool_calls(message.get("tool_calls")),
    }


def _standardize_tool_calls(tool_calls: Any) -> list[dict[str, Any]]:
    if not isinstance(tool_calls, list):
        return []
    standardized: list[dict[str, Any]] = []
    for tool_call in tool_calls:
        if not isinstance(tool_call, dict):
            continue
        function = tool_call.get("function")
        if not isinstance(function, dict):
            function = {}
        arguments = function.get("arguments")
        if isinstance(arguments, str):
            try:
                arguments = json.loads(arguments)
            except ValueError:
                arguments = {"_raw": arguments}
        standardized.append(
            {
                "id": tool_call.get("id"),
                "type": tool_call.get("type") or "function",
                "name": function.get("name"),
                "arguments": arguments if isinstance(arguments, dict) else {},
            }
        )
    return standardized


def build_raw_payload(
    *,
    run_id: str,
    message_id: str | None,
    provider: str,
    model: str,
    raw: Any,
    config: RawPayloadConfig,
) -> RawPayloadSnapshot:
    """Build the durable snapshot for one provider call.

    Under the `standard` policy only the projection plus digest are kept.
    Under the `debug` policy the full redacted canonical payload is encrypted
    into `payload_ciphertext` and `expires_at` is stamped from `retention_days`.
    """
    redacted = redact_payload(raw)
    canonical = canonical_json(redacted)
    standard_fields = extract_standard_fields(redacted, provider=provider, model=model)
    if config.max_bytes > 0 and len(canonical) > config.max_bytes:
        standard_fields["payload_truncated"] = True
    snapshot = RawPayloadSnapshot(
        run_id=run_id,
        message_id=message_id,
        provider=provider,
        standard_fields=standard_fields,
        payload_digest=hashlib.sha256(canonical).hexdigest(),
    )
    if config.policy == "debug":
        snapshot.payload_ciphertext = _encrypt_payload_bytes(canonical)
        snapshot.expires_at = datetime.now(UTC) + timedelta(days=config.retention_days)
    return snapshot


def _encrypt_payload_bytes(canonical: bytes) -> str:
    token = _fernet().encrypt(canonical)
    return _PAYLOAD_CIPHER_PREFIX + base64.urlsafe_b64encode(token).decode("ascii")


def decrypt_payload_ciphertext(value: str) -> bytes:
    """Return the plaintext canonical payload bytes for a `pl:v1:` ciphertext."""
    if not value or not value.startswith(_PAYLOAD_CIPHER_PREFIX):
        raise ValueError("raw payload is not a pl:v1 ciphertext")
    try:
        token = base64.urlsafe_b64decode(value[len(_PAYLOAD_CIPHER_PREFIX) :].encode("ascii"))
        return _fernet().decrypt(token)
    except Exception as exc:
        raise ValueError("raw payload ciphertext cannot be decrypted") from exc
