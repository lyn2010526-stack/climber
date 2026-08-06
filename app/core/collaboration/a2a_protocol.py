"""A2A Protocol Compatibility.

Provides standardized agent-to-agent communication protocol
with JSON wire format, message signing (HMAC-SHA256), and
protocol version for future compatibility.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import time
import uuid
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class A2AMessageType(StrEnum):
    REQUEST = "request"
    RESPONSE = "response"
    EVENT = "event"


@dataclass
class A2AMessage:
    """A2A protocol message for inter-agent communication."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    sender_id: str = ""
    receiver_id: str = ""
    message_type: A2AMessageType = A2AMessageType.REQUEST
    payload: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    correlation_id: str = ""
    protocol_version: str = "1.0"
    signature: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "sender_id": self.sender_id,
            "receiver_id": self.receiver_id,
            "message_type": self.message_type.value,
            "payload": self.payload,
            "timestamp": self.timestamp,
            "correlation_id": self.correlation_id,
            "protocol_version": self.protocol_version,
            "signature": self.signature,
        }

    def signable_content(self) -> str:
        """Return the content string used for signing (excludes signature field)."""
        content = {
            "id": self.id,
            "sender_id": self.sender_id,
            "receiver_id": self.receiver_id,
            "message_type": self.message_type.value,
            "payload": self.payload,
            "timestamp": self.timestamp,
            "correlation_id": self.correlation_id,
            "protocol_version": self.protocol_version,
        }
        return json.dumps(content, sort_keys=True, separators=(",", ":"))


class A2AProtocol:
    """A2A protocol encoder/decoder with message signing support."""

    def __init__(self, secret_key: str = "") -> None:
        self._secret_key = secret_key

    def encode(self, message: A2AMessage) -> str:
        """Encode message to JSON wire format."""
        return json.dumps(message.to_dict(), sort_keys=True)

    def decode(self, data: str) -> A2AMessage:
        """Decode JSON wire format to A2AMessage."""
        raw = json.loads(data)
        return A2AMessage(
            id=raw.get("id", str(uuid.uuid4())),
            sender_id=raw.get("sender_id", ""),
            receiver_id=raw.get("receiver_id", ""),
            message_type=A2AMessageType(raw.get("message_type", "request")),
            payload=raw.get("payload", {}),
            timestamp=raw.get("timestamp", time.time()),
            correlation_id=raw.get("correlation_id", ""),
            protocol_version=raw.get("protocol_version", "1.0"),
            signature=raw.get("signature", ""),
        )

    def validate(self, message: A2AMessage) -> tuple[bool, str]:
        """Validate message structure and signature.

        Returns (is_valid, error_message).
        """
        if not message.sender_id:
            return False, "missing sender_id"
        if not message.receiver_id:
            return False, "missing receiver_id"
        if message.message_type not in (
            A2AMessageType.REQUEST,
            A2AMessageType.RESPONSE,
            A2AMessageType.EVENT,
        ):
            return False, f"invalid message_type: {message.message_type}"
        if message.protocol_version != "1.0":
            return False, f"unsupported protocol version: {message.protocol_version}"
        if message.signature and not self._verify_signature(message):
            return False, "invalid signature"
        return True, ""

    def create_request(
        self,
        sender_id: str,
        receiver_id: str,
        payload: dict[str, Any],
        correlation_id: str = "",
    ) -> A2AMessage:
        """Create a signed request message."""
        msg = A2AMessage(
            sender_id=sender_id,
            receiver_id=receiver_id,
            message_type=A2AMessageType.REQUEST,
            payload=payload,
            correlation_id=correlation_id or str(uuid.uuid4()),
        )
        msg.signature = self._sign(msg.signable_content())
        return msg

    def create_response(
        self,
        sender_id: str,
        receiver_id: str,
        payload: dict[str, Any],
        correlation_id: str = "",
    ) -> A2AMessage:
        """Create a signed response message."""
        msg = A2AMessage(
            sender_id=sender_id,
            receiver_id=receiver_id,
            message_type=A2AMessageType.RESPONSE,
            payload=payload,
            correlation_id=correlation_id or str(uuid.uuid4()),
        )
        msg.signature = self._sign(msg.signable_content())
        return msg

    def create_event(
        self,
        sender_id: str,
        receiver_id: str,
        payload: dict[str, Any],
        correlation_id: str = "",
    ) -> A2AMessage:
        """Create a signed event message."""
        msg = A2AMessage(
            sender_id=sender_id,
            receiver_id=receiver_id,
            message_type=A2AMessageType.EVENT,
            payload=payload,
            correlation_id=correlation_id or str(uuid.uuid4()),
        )
        msg.signature = self._sign(msg.signable_content())
        return msg

    def _sign(self, content: str) -> str:
        """Sign content with HMAC-SHA256."""
        if not self._secret_key:
            return ""
        return hmac.new(
            self._secret_key.encode(),
            content.encode(),
            hashlib.sha256,
        ).hexdigest()

    def _verify_signature(self, message: A2AMessage) -> bool:
        """Verify HMAC-SHA256 signature of a message."""
        if not self._secret_key or not message.signature:
            return False
        expected = self._sign(message.signable_content())
        return hmac.compare_digest(expected, message.signature)
