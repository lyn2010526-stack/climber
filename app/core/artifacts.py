"""Structured, versioned artifacts for collaboration workflows."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, TypeAlias
from uuid import uuid4

JSONScalar: TypeAlias = str | int | float | bool | None
JSONValue: TypeAlias = JSONScalar | list["JSONValue"] | dict[str, "JSONValue"]

_CHECKPOINT_KEY = "__climber_artifact__"
_CHECKPOINT_VERSION = 1


class ArtifactType(StrEnum):
    DOCUMENT = "document"
    CODE = "code"
    DATA = "data"
    RESULT = "result"


class ArtifactStage(StrEnum):
    DRAFT = "draft"
    REVIEW = "review"
    FINAL = "final"


class ArtifactStatus(StrEnum):
    DRAFT = "draft"
    IN_REVIEW = "in_review"
    BLOCKED = "blocked"
    APPROVED = "approved"


class GateKind(StrEnum):
    SCHEMA = "schema"
    REVIEWER = "reviewer"
    HUMAN = "human"


class StageGateError(ValueError):
    """Raised when an artifact crosses a stage without required approval."""


def _copy_json(value: JSONValue) -> JSONValue:
    try:
        return json.loads(json.dumps(value, allow_nan=False))
    except (TypeError, ValueError) as exc:
        raise ValueError("Artifact content must be valid JSON") from exc


@dataclass(frozen=True)
class ArtifactReference:
    artifact_id: str
    version: int

    def to_dict(self) -> dict[str, Any]:
        return {"artifact_id": self.artifact_id, "version": self.version}

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> ArtifactReference:
        return cls(artifact_id=str(value["artifact_id"]), version=int(value["version"]))


@dataclass(frozen=True)
class StageGate:
    kind: GateKind
    approved: bool
    actor: str
    reason: str = ""
    decided_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind.value,
            "approved": self.approved,
            "actor": self.actor,
            "reason": self.reason,
            "decided_at": self.decided_at,
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> StageGate:
        return cls(
            kind=GateKind(value["kind"]),
            approved=bool(value["approved"]),
            actor=str(value["actor"]),
            reason=str(value.get("reason", "")),
            decided_at=str(value["decided_at"]),
        )


@dataclass(frozen=True)
class Artifact:
    artifact_id: str
    artifact_type: ArtifactType
    stage: ArtifactStage
    version: int
    lineage: tuple[ArtifactReference, ...]
    status: ArtifactStatus
    content: JSONValue
    required_gates: tuple[GateKind, ...] = ()
    gates: tuple[StageGate, ...] = ()

    def __post_init__(self) -> None:
        if not self.artifact_id:
            raise ValueError("artifact_id is required")
        if self.version < 1:
            raise ValueError("Artifact version must be positive")
        object.__setattr__(self, "content", _copy_json(self.content))

    @classmethod
    def create(
        cls,
        *,
        artifact_type: ArtifactType,
        stage: ArtifactStage,
        content: JSONValue,
        required_gates: tuple[GateKind, ...] = (),
        artifact_id: str | None = None,
    ) -> Artifact:
        return cls(
            artifact_id=artifact_id or str(uuid4()),
            artifact_type=artifact_type,
            stage=stage,
            version=1,
            lineage=(),
            status=ArtifactStatus.DRAFT,
            content=content,
            required_gates=tuple(dict.fromkeys(required_gates)),
        )

    def revise(self, *, content: JSONValue, stage: ArtifactStage = ArtifactStage.DRAFT) -> Artifact:
        return replace(
            self,
            stage=stage,
            version=self.version + 1,
            lineage=(*self.lineage, ArtifactReference(self.artifact_id, self.version)),
            status=ArtifactStatus.DRAFT,
            content=content,
            gates=(),
        )

    def record_gate(self, kind: GateKind, *, approved: bool, actor: str, reason: str = "") -> Artifact:
        if kind not in self.required_gates:
            raise StageGateError(f"{kind.value} gate is not required for this artifact")
        gates = (*tuple(gate for gate in self.gates if gate.kind != kind), StageGate(kind, approved, actor, reason))
        results = {gate.kind: gate.approved for gate in gates}
        if any(results.get(required) is False for required in self.required_gates):
            status = ArtifactStatus.BLOCKED
        elif all(results.get(required) is True for required in self.required_gates):
            status = ArtifactStatus.APPROVED
        else:
            status = ArtifactStatus.IN_REVIEW
        return replace(self, status=status, gates=gates)

    def advance(self, stage: ArtifactStage) -> Artifact:
        failures = self._gate_failures()
        if failures:
            raise StageGateError(f"Required stage gates have not passed: {', '.join(failures)}")
        status = ArtifactStatus.APPROVED if stage is ArtifactStage.FINAL else self.status
        return replace(self, stage=stage, status=status)

    def _gate_failures(self) -> list[str]:
        results = {gate.kind: gate.approved for gate in self.gates}
        return [kind.value for kind in self.required_gates if results.get(kind) is not True]

    def to_dict(self) -> dict[str, Any]:
        return {
            "artifact_id": self.artifact_id,
            "type": self.artifact_type.value,
            "stage": self.stage.value,
            "version": self.version,
            "lineage": [reference.to_dict() for reference in self.lineage],
            "status": self.status.value,
            "content": _copy_json(self.content),
            "required_gates": [kind.value for kind in self.required_gates],
            "gates": [gate.to_dict() for gate in self.gates],
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> Artifact:
        return cls(
            artifact_id=str(value["artifact_id"]),
            artifact_type=ArtifactType(value["type"]),
            stage=ArtifactStage(value["stage"]),
            version=int(value["version"]),
            lineage=tuple(ArtifactReference.from_dict(item) for item in value.get("lineage", [])),
            status=ArtifactStatus(value["status"]),
            content=value["content"],
            required_gates=tuple(GateKind(kind) for kind in value.get("required_gates", [])),
            gates=tuple(StageGate.from_dict(gate) for gate in value.get("gates", [])),
        )

    def to_checkpoint(self) -> str:
        payload = {_CHECKPOINT_KEY: _CHECKPOINT_VERSION, "artifact": self.to_dict()}
        return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))

    @classmethod
    def from_checkpoint(cls, payload: str) -> Artifact | None:
        try:
            value = json.loads(payload)
        except (TypeError, json.JSONDecodeError):
            return None
        if not isinstance(value, dict) or value.get(_CHECKPOINT_KEY) != _CHECKPOINT_VERSION:
            return None
        artifact = value.get("artifact")
        if not isinstance(artifact, dict):
            raise ValueError("Invalid artifact checkpoint payload")
        return cls.from_dict(artifact)

    def content_json(self) -> str:
        return json.dumps(self.content, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


@dataclass(frozen=True)
class HandoffAudit:
    artifact_id: str
    artifact_version: int
    from_agent: str
    to_agent: str
    content_digest: str
    content: JSONValue
    stage: ArtifactStage
    status: ArtifactStatus
    reason: str = ""
    handed_off_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    @staticmethod
    def content_hash(content: JSONValue) -> str:
        canonical = json.dumps(content, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
        return hashlib.sha256(canonical.encode()).hexdigest()

    @classmethod
    def capture(
        cls,
        artifact: Artifact,
        *,
        from_agent: str,
        to_agent: str,
        reason: str = "",
    ) -> HandoffAudit:
        failures = artifact._gate_failures()
        if failures or artifact.status is not ArtifactStatus.APPROVED:
            labels = failures or [artifact.status.value]
            raise StageGateError(f"Artifact cannot be handed off before approval: {', '.join(labels)}")
        return cls(
            artifact_id=artifact.artifact_id,
            artifact_version=artifact.version,
            from_agent=from_agent,
            to_agent=to_agent,
            content_digest=cls.content_hash(artifact.content),
            content=_copy_json(artifact.content),
            stage=artifact.stage,
            status=artifact.status,
            reason=reason,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "artifact_id": self.artifact_id,
            "artifact_version": self.artifact_version,
            "from_agent": self.from_agent,
            "to_agent": self.to_agent,
            "content_digest": self.content_digest,
            "content": _copy_json(self.content),
            "stage": self.stage.value,
            "status": self.status.value,
            "reason": self.reason,
            "handed_off_at": self.handed_off_at,
        }
