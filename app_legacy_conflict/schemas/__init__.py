"""Pydantic schemas for API requests/responses."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


# ── Agent schemas ──

class AgentCreate(BaseModel):
    name: str
    description: str = ""
    system_prompt: str = ""
    provider: str = "openai"
    model_id: str = "gpt-4o"
    api_key: str
    base_url: str | None = None
    tools: list[str] = []
    skills: list[str] = []
    memory_config: dict[str, Any] = {}


class AgentResponse(BaseModel):
    id: str
    name: str
    description: str
    provider: str
    model_id: str
    status: str
    created_at: datetime


# ── Session schemas ──

class SessionCreate(BaseModel):
    agent_id: str


class ChatRequest(BaseModel):
    message: str
    api_key: str | None = None  # optional override
    base_url: str | None = None


class ChatResponse(BaseModel):
    session_id: str
    status: str
    message: str
    iterations: int


# ── Tool schemas ──

class ToolRegister(BaseModel):
    name: str
    description: str
    parameters: dict[str, Any]


class ToolResponse(BaseModel):
    name: str
    description: str
    type: str


# ── Model schemas ──

class ModelRegister(BaseModel):
    provider: str
    model_id: str
    api_key: str
    base_url: str | None = None


class ModelInfo(BaseModel):
    provider: str
    model_id: str
    capabilities: dict[str, Any]
