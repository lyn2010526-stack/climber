"""Execution orchestration for chat slash commands.

``SlashCommandService`` turns a :class:`ParseOutcome` into an outcome the HTTP
layer can serve:

- ``help`` / ``status`` / ``model`` (read) / ``level`` (read) → a local reply
  rendered as a synthetic assistant message;
- ``model`` (write) / ``clear`` → a persisted session effect plus a receipt;
- ``stop`` → the session-level interrupt (thin wrapper over the engine's
  cooperative ``_stop_requested`` flag — task_worker is never touched);
- ``retry`` / passthrough → the caller streams from the engine, exactly like
  the regular chat endpoint.

Storage and engine access are injected, keeping this module unit-testable
without a running server.
"""

from __future__ import annotations

import contextlib
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

from app.core.slash.registry import default_registry
from app.core.slash.specs import (
    REASONING_LEVELS,
    CommandRegistry,
    ParseOutcome,
    SlashCommandError,
    parse_input,
)

DbSessionFactory = Callable[[], Any]


@dataclass
class SlashReply:
    """A self-contained reply produced without contacting the model."""

    command: str
    content: str
    effect: str | None = (
        None  # "cleared" | "model_updated" | "level_updated" | "stop_requested" | None
    )
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass
class SlashExecution:
    """What the HTTP layer should do after command resolution."""

    kind: str  # "reply" | "passthrough" | "error"
    raw: str
    reply: SlashReply | None = None
    # For "passthrough": the text the agent should receive (= original input).
    agent_message: str | None = None


class SlashCommandService:
    """Resolve and execute chat slash commands for one session."""

    def __init__(
        self,
        registry: CommandRegistry | None = None,
        *,
        db_factory: DbSessionFactory | None = None,
        load_session: Callable[..., Awaitable[Any]] | None = None,
        engine_sessions: dict[str, Any] | None = None,
        now: Callable[[], float] = time.time,
    ) -> None:
        self.registry = registry or default_registry
        self._db_factory = db_factory
        self._load_session = load_session
        self._engine_sessions = engine_sessions if engine_sessions is not None else {}
        self._now = now

    # ------------------------------------------------------------------ parse

    def parse(self, raw: str) -> ParseOutcome:
        return parse_input(raw, self.registry)

    # ---------------------------------------------------------------- helpers

    async def _require_owned_session(self, session_id: str, user_id: str) -> Any:
        if self._load_session is None:
            raise LookupError("Session storage is not configured")
        row = await self._load_session(session_id, user_id)
        if row is None:
            raise LookupError(f"Session {session_id} not found")
        return row

    def engine_session(self, session_id: str) -> Any | None:
        """The warm in-memory session, if the engine has one."""
        return self._engine_sessions.get(session_id)

    def _clear_engine_session(self, session_id: str) -> bool:
        """Drop the warm session so the next turn rebuilds clean context."""
        return self._engine_sessions.pop(session_id, None) is not None

    @staticmethod
    def _session_state(engine_session: Any) -> dict[str, Any]:
        return {
            "state": getattr(getattr(engine_session, "state_machine", None), "state", None)
            and engine_session.state_machine.state.value,
            "iterations": getattr(engine_session, "_last_iteration", 0) or 0,
            "max_iterations": getattr(engine_session, "max_iterations", 0) or 0,
            "messages": len(getattr(engine_session, "messages", []) or []),
            "tokens_used": getattr(getattr(engine_session, "metrics", None), "total_tokens_used", 0)
            or 0,
            "stop_requested": bool(getattr(engine_session, "_stop_requested", False)),
            "restart_count": getattr(engine_session, "restart_count", 0) or 0,
        }

    # --------------------------------------------------------------- commands

    async def execute(
        self,
        outcome: ParseOutcome,
        *,
        session_id: str,
        user_id: str,
        running: bool = False,
    ) -> SlashExecution:
        """Execute a parsed outcome. Streaming kinds return ``passthrough``."""
        if outcome.kind == "passthrough":
            return SlashExecution(kind="passthrough", raw=outcome.raw, agent_message=outcome.raw)
        if outcome.kind == "error":
            return SlashExecution(
                kind="error",
                raw=outcome.raw,
                reply=SlashReply(
                    command=outcome.command or "",
                    content=outcome.error or "Invalid command arguments",
                ),
            )
        if outcome.spec is None:  # pragma: no cover - registry guarantees spec
            return SlashExecution(
                kind="error",
                raw=outcome.raw,
                reply=SlashReply(
                    command="",
                    content="Unknown command",
                ),
            )
        if running and not outcome.spec.allowed_while_streaming:
            return SlashExecution(
                kind="error",
                raw=outcome.raw,
                reply=SlashReply(
                    command=outcome.command or "",
                    content=f"/{outcome.command} cannot run while a turn is streaming. Use /stop first.",
                ),
            )

        handlers = {
            "help": self._cmd_help,
            "status": self._cmd_status,
            "model": self._cmd_model,
            "level": self._cmd_level,
            "clear": self._cmd_clear,
            "stop": self._cmd_stop,
        }
        handler = handlers.get(outcome.command or "")
        if handler is None:
            # retry (streaming) is handled by the HTTP layer; anything else here
            # is a registry/service desync.
            if outcome.command == "retry":
                return SlashExecution(kind="passthrough", raw=outcome.raw, agent_message=None)
            return SlashExecution(
                kind="error",
                raw=outcome.raw,
                reply=SlashReply(
                    command=outcome.command or "",
                    content=f"/{outcome.command} is not executable in this context",
                ),
            )
        try:
            reply = await handler(outcome, session_id=session_id, user_id=user_id)
        except SlashCommandError as exc:
            return SlashExecution(
                kind="error",
                raw=outcome.raw,
                reply=SlashReply(
                    command=outcome.command or "",
                    content=str(exc),
                ),
            )
        except LookupError as exc:
            return SlashExecution(
                kind="error",
                raw=outcome.raw,
                reply=SlashReply(
                    command=outcome.command or "",
                    content=str(exc),
                ),
            )
        return SlashExecution(kind="reply", raw=outcome.raw, reply=reply)

    async def _cmd_help(
        self, outcome: ParseOutcome, *, session_id: str, user_id: str
    ) -> SlashReply:
        topic = outcome.args[0] if outcome.args else None
        if topic:
            spec = self.registry.get(topic)
            if spec is None:
                raise LookupError(f"Unknown command '/{topic}'. Type /help to list all commands.")
            lines = [f"/{spec.name} — {spec.usage}", "", spec.summary]
            if spec.aliases:
                lines.append(f"Aliases: {', '.join('/' + a for a in spec.aliases)}")
            content = "\n".join(lines)
        else:
            lines = ["Available commands:", ""]
            for spec in self.registry.all_commands():
                aliases = f" (/{', /'.join(spec.aliases)})" if spec.aliases else ""
                lines.append(f"/{spec.name}{aliases} — {spec.usage}  ·  {spec.summary}")
            lines += ["", "Any other input is sent to the agent as a normal message."]
            content = "\n".join(lines)
        return SlashReply(command="help", content=content)

    async def _cmd_status(
        self, outcome: ParseOutcome, *, session_id: str, user_id: str
    ) -> SlashReply:
        row = await self._require_owned_session(session_id, user_id)
        settings = dict(getattr(row, "model_settings", None) or {})
        warm = self.engine_session(session_id)
        lines = [
            f"Session: {session_id}",
            f"Title: {getattr(row, 'title', '') or '(untitled)'}",
            f"Status: {getattr(row, 'status', 'unknown')}",
            f"Model: {settings.get('provider') or '-'}:{settings.get('model_id') or '-'}",
            f"Reasoning level: {(settings.get('context_data') or {}).get('reasoning_level', 'auto') if isinstance(settings.get('context_data'), dict) else 'auto'}",
        ]
        if warm is not None:
            state = self._session_state(warm)
            lines += [
                f"Engine: warm session, {state['messages']} in-memory messages",
                f"Iterations: {state['iterations']}/{state['max_iterations']}",
                f"Tokens used: {state['tokens_used']}",
                f"State: {state['state'] or 'unknown'}",
            ]
        else:
            lines.append("Engine: cold (no in-memory session)")
        return SlashReply(
            command="status",
            content="\n".join(lines),
            payload={
                "session_id": session_id,
                "title": getattr(row, "title", None),
                "status": getattr(row, "status", None),
                "model_settings": settings,
                "engine": self._session_state(warm) if warm is not None else None,
            },
        )

    async def _cmd_model(
        self, outcome: ParseOutcome, *, session_id: str, user_id: str
    ) -> SlashReply:
        row = await self._require_owned_session(session_id, user_id)
        settings = dict(getattr(row, "model_settings", None) or {})
        if not outcome.args:
            current = f"{settings.get('provider') or '-'}:{settings.get('model_id') or '-'}"
            return SlashReply(
                command="model",
                content=f"Current model: {current}",
                payload={
                    "provider": settings.get("provider"),
                    "model_id": settings.get("model_id"),
                },
            )
        spec_value = outcome.args[0]
        if ":" not in spec_value:
            raise SlashCommandError("Expected provider:model_id, e.g. /model openai:gpt-4o-mini")
        provider, model_id = (part.strip() for part in spec_value.split(":", 1))
        if not provider or not model_id:
            raise SlashCommandError("Both provider and model_id are required")
        credential_id = settings.get("credential_id")
        if credential_id:
            # The stored credential pins one provider; switching providers
            # without a new credential would silently break decryption.
            await self._assert_credential_matches(user_id, credential_id, provider)
        settings["provider"] = provider
        settings["model_id"] = model_id
        settings.pop("base_url", None)
        await self._persist_model_settings(row, settings)
        warm = self.engine_session(session_id)
        if warm is not None:
            # chat.py rebinds these on every turn; mirror that here so a warm
            # session picks up the switch without waiting for a rebuild.
            for attr in ("provider", "model_id"):
                setattr(warm, attr, settings[attr])
            if getattr(warm, "session_config", None) is not None:
                setattr(warm.session_config, attr, settings[attr])
        return SlashReply(
            command="model",
            content=f"Model switched to {provider}:{model_id}",
            effect="model_updated",
            payload={"provider": provider, "model_id": model_id},
        )

    async def _assert_credential_matches(
        self, user_id: str, credential_id: str, provider: str
    ) -> None:
        if self._db_factory is None:
            raise LookupError("Credential storage is not configured")
        from sqlalchemy import select

        from app.storage.database import ApiKey

        async with self._db_factory() as db:
            row = (
                await db.execute(
                    select(ApiKey).where(
                        ApiKey.id == credential_id,
                        ApiKey.user_id == user_id,
                        ApiKey.is_active.is_(True),
                    )
                )
            ).scalar_one_or_none()
        if row is None:
            raise LookupError("Selected model credential is unavailable or revoked")
        if row.provider != provider:
            raise SlashCommandError(
                f"Stored credential is bound to provider '{row.provider}', cannot switch to '{provider}'"
            )

    async def _persist_model_settings(self, row: Any, settings: dict[str, Any]) -> None:
        if self._db_factory is None:
            raise LookupError("Session storage is not configured")
        async with self._db_factory() as db:
            attached = await db.get(type(row), row.id)
            if attached is None:
                raise LookupError(f"Session {row.id} not found")
            attached.model_settings = settings
            await db.commit()

    async def _cmd_level(
        self, outcome: ParseOutcome, *, session_id: str, user_id: str
    ) -> SlashReply:
        row = await self._require_owned_session(session_id, user_id)
        if not outcome.args:
            return SlashReply(
                command="level",
                content=("Reasoning levels: " + ", ".join(REASONING_LEVELS)),
                payload={"levels": list(REASONING_LEVELS)},
            )
        level = outcome.args[0]
        context_data = dict(getattr(row, "context_data", None) or {})
        context_data["reasoning_level"] = level
        if self._db_factory is None:
            raise LookupError("Session storage is not configured")
        async with self._db_factory() as db:
            attached = await db.get(type(row), row.id)
            if attached is None:
                raise LookupError(f"Session {row.id} not found")
            attached.context_data = context_data
            await db.commit()
        return SlashReply(
            command="level",
            content=f"Reasoning level set to '{level}'.",
            effect="level_updated",
            payload={"level": level},
        )

    async def _cmd_clear(
        self, outcome: ParseOutcome, *, session_id: str, user_id: str
    ) -> SlashReply:
        row = await self._require_owned_session(session_id, user_id)
        if self._db_factory is None:
            raise LookupError("Session storage is not configured")
        from sqlalchemy import delete

        from app.storage.database import Message

        async with self._db_factory() as db:
            attached = await db.get(type(row), row.id)
            if attached is None:
                raise LookupError(f"Session {row.id} not found")
            await db.execute(delete(Message).where(Message.session_id == session_id))
            await db.commit()
        dropped_warm = self._clear_engine_session(session_id)
        note = " In-memory context will rebuild on the next message." if dropped_warm else ""
        return SlashReply(
            command="clear", content="Session history cleared." + note, effect="cleared"
        )

    async def _cmd_stop(
        self, outcome: ParseOutcome, *, session_id: str, user_id: str
    ) -> SlashReply:
        warm = self.engine_session(session_id)
        if warm is None:
            return SlashReply(command="stop", content="No running turn to interrupt.", effect=None)
        # Cooperative cancel: the engine's iteration/stream loops poll
        # `_stop_requested` (agent_engine._iteration_loop) and unwind without
        # losing the session. No task_worker involvement for session chats.
        warm._stop_requested = True
        stop = getattr(warm, "stop", None)
        if stop is not None:
            with contextlib.suppress(Exception):  # pragma: no cover - state machine edge cases
                stop()
        return SlashReply(
            command="stop",
            content="Stop requested; the running turn will halt.",
            effect="stop_requested",
        )


def last_user_message(messages: list[dict[str, Any]]) -> str | None:
    """The most recent user-authored text, for /retry."""
    for message in reversed(messages):
        if str(message.get("role", "")).lower() == "user":
            content = message.get("content")
            if isinstance(content, str) and content.strip():
                return content
    return None
