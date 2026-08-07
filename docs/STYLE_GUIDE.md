# Climber Agent Engine - Code Style Guide

> Comprehensive code style guidelines for Python and TypeScript/JavaScript development.

## Table of Contents

- [General Principles](#general-principles)
- [Python Style Guide](#python-style-guide)
- [TypeScript/JavaScript Style Guide](#typescriptjavascript-style-guide)
- [Naming Conventions](#naming-conventions)
- [Documentation Standards](#documentation-standards)
- [Error Handling](#error-handling)
- [Testing Style](#testing-style)
- [Git Commit Style](#git-commit-style)

---

## General Principles

1. **Readability First** — Code is read more often than written
2. **Explicit Over Implicit** — Clear code beats clever code
3. **DRY (Don't Repeat Yourself)** — Extract reusable patterns
4. **KISS (Keep It Simple)** — Simplicity over complexity
5. **YAGNI (You Aren't Gonna Need It)** — Don't add functionality until needed
6. **Fail Fast** — Detect and report errors as early as possible

---

## Python Style Guide

Based on [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html) with project-specific additions.

### Formatting

- **Line length**: Maximum 100 characters
- **Indentation**: 4 spaces (no tabs)
- **Quotes**: Double quotes for strings, single quotes only within double-quoted strings
- **Trailing commas**: Use in multi-line collections

### Imports

```python
# Correct import ordering
import asyncio  # 1. Standard library
import os
from pathlib import Path
from typing import Any, Optional

import structlog  # 2. Third-party packages
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.core.agent_engine import AgentEngine  # 3. Local application
from app.storage.database import get_session
from app.utils.helpers import format_timestamp
```

Import rules:
- Use absolute imports (no relative imports in app code)
- Import specific symbols rather than wildcard imports
- Group imports: stdlib → third-party → local
- Separate groups with blank line

### Type Hints

All functions must have complete type hints:

```python
from typing import Any, AsyncIterator

from app.models.session import Session, SessionConfig


async def create_session(
    user_id: str,
    config: SessionConfig | None = None,
    *,
    metadata: dict[str, Any] | None = None,
) -> Session:
    """Create a new agent session."""
    ...


async def stream_response(
    session: Session,
    message: str,
    *,
    max_tokens: int = 4096,
) -> AsyncIterator[str]:
    """Stream response tokens from the model."""
    ...
```

### Function Design

- **Single Responsibility**: Each function does one thing
- **Max lines**: 50 lines (excluding docstring)
- **Max parameters**: 5 (use dataclass/config object if more)
- **Prefer keyword-only arguments** for clarity when 3+ params

### Class Design

```python
class AgentEngine:
    """Main orchestrator for agent execution.

    This class manages the lifecycle of agent sessions, including
    message processing, tool execution, and response streaming.

    Attributes:
        config: The engine configuration.
        model_registry: Registry of available model adapters.
        tool_registry: Registry of available tools.
    """

    def __init__(
        self,
        config: EngineConfig,
        model_registry: ModelRegistry,
        tool_registry: ToolRegistry,
    ) -> None:
        self._config = config
        self._model_registry = model_registry
        self._tool_registry = tool_registry
        self._logger = structlog.get_logger(__name__)

    @property
    def config(self) -> EngineConfig:
        """Get engine configuration."""
        return self._config
```

### Error Handling

```python
# Use specific exceptions
class AgentEngineError(Exception):
    """Base exception for AgentEngine."""
    pass


class SessionNotFoundError(AgentEngineError):
    """Raised when session is not found."""
    def __init__(self, session_id: str) -> None:
        super().__init__(f"Session not found: {session_id}")
        self.session_id = session_id


class ModelProviderError(AgentEngineError):
    """Raised when model provider fails."""
    def __init__(self, provider: str, detail: str) -> None:
        super().__init__(f"Model provider '{provider}' failed: {detail}")
        self.provider = provider


# Handle exceptions at appropriate boundaries
async def process_message(session_id: str, message: str) -> Response:
    session = await session_repo.get(session_id)
    if session is None:
        raise SessionNotFoundError(session_id)

    try:
        response = await model.chat(session.context, message)
    except ModelProviderError as e:
        logger.error("Model call failed", exc_info=True, provider=e.provider)
        raise HTTPException(status_code=502, detail=str(e)) from e

    return response
```

### Async/Await

```python
# Correct async patterns
async def fetch_all_users() -> list[User]:
    """Fetch all users concurrently."""
    async with get_session() as session:
        result = await session.execute(select(User))
        return list(result.scalars().all())


async def process_in_parallel(items: list[str]) -> list[Result]:
    """Process items in parallel with gather."""
    tasks = [process_item(item) for item in items]
    return await asyncio.gather(*tasks)


async def process_with_semaphore(items: list[str]) -> list[Result]:
    """Process items with concurrency limit."""
    semaphore = asyncio.Semaphore(10)

    async def limited_task(item: str) -> Result:
        async with semaphore:
            return await process_item(item)

    return await asyncio.gather(*[limited_task(i) for i in items])
```

---

## TypeScript/JavaScript Style Guide

Based on [Google TypeScript Style Guide](https://google.github.io/styleguide/tsguide.html) and [Airbnb JS Style Guide](https://github.com/airbnb/javascript).

### Formatting

- **Line length**: Maximum 100 characters
- **Indentation**: 2 spaces
- **Semicolons**: Required
- **Quotes**: Double quotes for strings
- **Trailing commas**: Required in multi-line

### Imports

```typescript
// Correct import ordering
// 1. React and external libraries
import { useState, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";

// 2. UI libraries
import { Button } from "@/components/ui/Button";
import { Dialog } from "@/components/ui/Dialog";

// 3. Internal modules
import { useAuth } from "@/hooks/useAuth";
import { chatService } from "@/services/chat";
import type { Message, Session } from "@/types";

// 4. Styles (if any)
import "./ChatView.css";
```

### Types & Interfaces

```typescript
// Prefer interface for object shapes
interface UserProfile {
  readonly id: string;
  name: string;
  email: string;
  avatarUrl?: string;
  readonly createdAt: Date;
}

// Use type for unions, intersections, and mapped types
type MessageRole = "user" | "assistant" | "system";

type AsyncState<T> =
  | { status: "loading" }
  | { status: "success"; data: T }
  | { status: "error"; error: Error };

// Generic constraints
interface Repository<T extends { id: string }> {
  findById(id: string): Promise<T | null>;
  save(entity: T): Promise<T>;
  delete(id: string): Promise<boolean>;
}
```

### Function Style

```typescript
// Arrow functions for component definitions
export function ChatView({ sessionId }: ChatViewProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const { user } = useAuth();

  useEffect(() => {
    void loadMessages(sessionId).then(setMessages);
  }, [sessionId]);

  const handleSend = useCallback(async (content: string) => {
    const response = await chatService.sendMessage(sessionId, content);
    setMessages((prev) => [...prev, response]);
  }, [sessionId]);

  return (
    <div className="chat-view">
      {/* ... */}
    </div>
  );
}

// Named exports preferred
export async function fetchSession(id: string): Promise<Session> {
  const response = await fetch(`/api/v1/sessions/${id}`);
  if (!response.ok) {
    throw new Error(`Failed to fetch session: ${response.statusText}`);
  }
  return response.json() as Promise<Session>;
}
```

### React Patterns

```typescript
// Custom hook with proper typing
export function useChat(sessionId: string): ChatHookReturn {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const sendMessage = useCallback(async (content: string) => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await chatService.sendMessage(sessionId, content);
      setMessages((prev) => [...prev, response]);
    } catch (err) {
      setError(err instanceof Error ? err : new Error(String(err)));
    } finally {
      setIsLoading(false);
    }
  }, [sessionId]);

  return { messages, isLoading, error, sendMessage };
}

// Component with discriminated union props
interface LoadingProps {
  variant: "spinner" | "skeleton";
  size?: "sm" | "md" | "lg";
}

export function LoadingIndicator({ variant, size = "md" }: LoadingProps) {
  if (variant === "skeleton") {
    return <Skeleton size={size} />;
  }
  return <Spinner size={size} />;
}
```

---

## Naming Conventions

### Python

| Element | Convention | Example |
|---------|-----------|---------|
| File | `snake_case.py` | `agent_engine.py` |
| Package | `snake_case` | `app/core/` |
| Class | `PascalCase` | `AgentEngine` |
| Function | `snake_case` | `create_session` |
| Variable | `snake_case` | `user_id` |
| Constant | `SCREAMING_SNAKE` | `MAX_RETRIES` |
| Private | `_leading_underscore` | `_internal_state` |
| TypeVar | `PascalCase` | `T`, `TConfig` |
| Exception | `PascalCase` + Error | `SessionNotFoundError` |
| Test file | `test_*.py` | `test_agent_engine.py` |
| Test class | `Test*` | `TestAgentEngine` |
| Test function | `test_*` | `test_create_session` |

### TypeScript/JavaScript

| Element | Convention | Example |
|---------|-----------|---------|
| File | `PascalCase.tsx` or `kebab-case.ts` | `ChatView.tsx`, `api-client.ts` |
| Component | `PascalCase` | `ChatView`, `UserProfile` |
| Function | `camelCase` | `sendMessage`, `fetchSession` |
| Variable | `camelCase` | `userId`, `isLoading` |
| Constant | `SCREAMING_SNAKE` | `MAX_FILE_SIZE` |
| Interface | `PascalCase` | `UserProfile`, `ChatProps` |
| Type | `PascalCase` | `MessageRole`, `AsyncState` |
| Hook | `use*` | `useAuth`, `useChat` |
| Enum | `PasmentCase` | `UserRole`, `MessageStatus` |

---

## Documentation Standards

### Python Docstrings

```python
async def execute_tool(
    tool_name: str,
    parameters: dict[str, Any],
    context: ToolContext,
) -> ToolResult:
    """Execute a registered tool with given parameters.

    This function looks up the tool in the registry, validates parameters
    against the tool schema, executes the tool function, and returns
    the result.

    Args:
        tool_name: The registered name of the tool to execute.
        parameters: Dictionary of parameter names to values.
        context: The execution context containing session and user info.

    Returns:
        A ToolResult containing the execution output and metadata.

    Raises:
        ToolNotFoundError: If tool_name is not in the registry.
        ToolValidationError: If parameters don't match schema.
        ToolExecutionError: If tool execution fails.

    Example:
        >>> result = await execute_tool("web_search", {"query": "AI"}, ctx)
        >>> print(result.output)
    """
```

### TypeScript JSDoc

```typescript
/**
 * Send a message to the chat session and receive a streaming response.
 *
 * This function establishes a Server-Sent Events connection to the chat
 * endpoint and yields response chunks as they arrive from the model.
 *
 * @param sessionId - The unique identifier of the chat session.
 * @param content - The message content to send.
 * @param options - Optional configuration for the request.
 * @yields Response chunks from the model.
 *
 * @throws {NetworkError} When the connection fails.
 * @throws {SessionNotFoundError} When the session doesn't exist.
 *
 * @example
 * ```ts
 * for await (const chunk of streamMessage("session-123", "Hello")) {
 *   process.stdout.write(chunk.content);
 * }
 * ```
 */
export async function* streamMessage(
  sessionId: string,
  content: string,
  options?: StreamOptions,
): AsyncGenerator<ResponseChunk> {
  // ...
}
```

---

## Error Handling

### Error Hierarchy

```
AgentEngineError (base)
├── SessionNotFoundError
├── ModelProviderError
│   ├── ModelTimeoutError
│   └── ModelRateLimitError
├── ToolError
│   ├── ToolNotFoundError
│   ├── ToolValidationError
│   └── ToolExecutionError
├── StorageError
│   ├── DatabaseConnectionError
│   └── MigrationError
└── AuthenticationError
    ├── TokenExpiredError
    └── InvalidCredentialsError
```

### Error Response Format

```json
{
  "error": {
    "code": "SESSION_NOT_FOUND",
    "message": "Session not found: abc-123",
    "details": {
      "session_id": "abc-123"
    },
    "request_id": "req-xyz-789"
  }
}
```

---

## Testing Style

### Test Naming

```python
# Pattern: test_<action>_<expected_behavior>_<condition>
def test_create_session_returns_valid_session():
    """Should return a session with valid ID when config is valid."""

def test_create_session_raises_on_empty_user_id():
    """Should raise ValueError when user_id is empty."""

def test_stream_response_emits_tokens_in_order():
    """Should emit tokens in correct order during streaming."""
```

### Test Structure (Arrange-Act-Assert)

```python
async def test_agent_handles_tool_calls(engine: AgentEngine, session: Session) -> None:
    """Should execute tool calls and include results in response."""
    # Arrange
    mock_tool.return_value = {"result": "success"}

    # Act
    events = [event async for event in engine.run(session, "Search for AI")]

    # Assert
    tool_events = [e for e in events if e.type == "tool_call"]
    assert len(tool_events) == 1
    assert tool_events[0].tool_name == "web_search"
```

---

## Git Commit Style

### Commit Message Format

```
<type>(<scope>): <description>

[optional body]

[optional footer(s)]
```

### Examples

```
feat(chat): add SSE streaming for real-time responses

Implement Server-Sent Events endpoint for streaming model responses
to the client. This provides better UX for long-running generation.

Refs: #123

---

fix(auth): resolve token refresh race condition

When multiple requests refresh the token simultaneously, only the first
refresh should succeed. Others should wait and use the new token.

Fixes #456

---

refactor(core): extract model scheduling logic

Move model selection and load balancing from AgentEngine to a dedicated
ModelScheduler class for better testability and extensibility.

BREAKING CHANGE: AgentEngine constructor no longer accepts model_config
