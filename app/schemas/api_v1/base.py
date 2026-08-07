"""Shared API v1 schema behavior."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, model_validator


class StrictRequest(BaseModel):
    """Forbid unknown fields and accept the legacy data envelope."""

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="before")
    @classmethod
    def unwrap_data_envelope(cls, value: Any) -> Any:
        if isinstance(value, dict) and set(value) == {"data"} and isinstance(value["data"], dict):
            return value["data"]
        return value


class EmptyRequest(StrictRequest):
    """Named request body for write actions without parameters."""


class PublicResponse(BaseModel):
    """Response base that ignores storage-only and secret fields."""

    model_config = ConfigDict(extra="ignore", from_attributes=True)
