"""Append-only full-chain trace event log.

Records everything the agent does as immutable, append-only events:

- system prompt changes
- reasoning traces (with the model used)
- tool calls (name + params)
- tool results (success/failure + content)
- screenshots (file path)
- decisions (action + target + confidence)
- model switches (from -> to + reason)
- subagent scheduling (task + agent id)
- context injections (source + content + token count)
- skill loads (skill id + level)

Logs are written to private directories, one file per session, and files are
rotated once they exceed a size cap (default 50 MB). On top of the log we
build Resume / Fork / Search / Replay / Trajectory capabilities.
"""

from __future__ import annotations

import asyncio
import json
import os
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import structlog

logger = structlog.get_logger()

# ── event type constants ──
EVENT_SYSTEM_PROMPT = "system_prompt"
EVENT_REASONING = "reasoning"
EVENT_TOOL_CALL = "tool_call"
EVENT_TOOL_RESULT = "tool_result"
EVENT_SCREENSHOT = "screenshot"
EVENT_DECISION = "decision"
EVENT_MODEL_SWITCH = "model_switch"
EVENT_SUBAGENT = "subagent"
EVENT_CONTEXT_INJECTION = "context_injection"
EVENT_SKILL_LOAD = "skill_load"

ALL_EVENT_TYPES = (
    EVENT_SYSTEM_PROMPT,
    EVENT_REASONING,
    EVENT_TOOL_CALL,
    EVENT_TOOL_RESULT,
    EVENT_SCREENSHOT,
    EVENT_DECISION,
    EVENT_MODEL_SWITCH,
    EVENT_SUBAGENT,
    EVENT_CONTEXT_INJECTION,
    EVENT_SKILL_LOAD,
)

DEFAULT_MAX_BYTES = 50 * 1024 * 1024  # 50 MB


@dataclass
class TraceEvent:
    """A single immutable trace event."""

    event_type: str
    data: dict[str, Any] = field(default_factory=dict)
    event_id: str = ""
    ts: float = 0.0
    session_id: str = ""
    sequence: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "ts": self.ts,
            "session_id": self.session_id,
            "sequence": self.sequence,
            "data": self.data,
        }

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> TraceEvent:
        return cls(
            event_type=raw.get("event_type", ""),
            data=raw.get("data", {}),
            event_id=raw.get("event_id", ""),
            ts=raw.get("ts", 0.0),
            session_id=raw.get("session_id", ""),
            sequence=raw.get("sequence", 0),
        )


class TraceLog:
    """Append-only, session-partitioned, size-rotated trace event log.

    Args:
        base_dir: private directory where log files live.
        max_file_bytes: per-file rotation cap.
    """

    def __init__(self, base_dir: str | Path = "data/traces", max_file_bytes: int = DEFAULT_MAX_BYTES):
        self._base_dir = Path(base_dir)
        self._base_dir.mkdir(parents=True, exist_ok=True)
        self._max_file_bytes = max_file_bytes
        self._current_session: str = ""
        self._current_file: Path | None = None
        self._current_bytes = 0
        self._sequence = 0
        self._lock = asyncio.Lock()

    def _session_file(self, session_id: str) -> Path:
        safe = session_id.replace("/", "_").replace("..", "_") or "default"
        return self._base_dir / f"{safe}.jsonl"

    async def _open_session(self, session_id: str) -> None:
        if self._current_session == session_id and self._current_file is not None:
            return
        self._current_session = session_id
        self._current_file = self._session_file(session_id)
        if self._current_file.exists():
            self._current_bytes = self._current_file.stat().st_size
        else:
            self._current_bytes = 0
        # resume sequence from existing events
        self._sequence = await self._count_events()

    async def _count_events(self) -> int:
        if self._current_file is None or not self._current_file.exists():
            return 0
        count = 0
        with self._current_file.open(encoding="utf-8") as fh:
            for _line in fh:
                count += 1
        return count

    def _rotate_if_needed(self, line_len: int) -> None:
        if self._current_file is None:
            return
        if self._current_bytes + line_len > self._max_file_bytes:
            rotated = self._base_dir / f"{self._current_session}-{int(time.time())}.jsonl"
            try:
                os.replace(self._current_file, rotated)
            except OSError:
                pass
            self._current_file = self._base_dir / f"{self._current_session}.jsonl"
            self._current_bytes = 0
            self._sequence = 0

    async def append(
        self,
        event_type: str,
        data: dict[str, Any],
        session_id: str,
    ) -> TraceEvent:
        """Append a single event to the current session's log file."""
        async with self._lock:
            await self._open_session(session_id)
            self._sequence += 1
            event = TraceEvent(
                event_type=event_type,
                data=data,
                event_id=str(uuid.uuid4()),
                ts=time.time(),
                session_id=session_id,
                sequence=self._sequence,
            )
            line = json.dumps(event.to_dict(), ensure_ascii=False, default=str) + "\n"
            self._rotate_if_needed(len(line.encode("utf-8")))
            if self._current_file is None:
                self._current_file = self._session_file(session_id)
            with self._current_file.open("a", encoding="utf-8") as fh:
                fh.write(line)
            self._current_bytes += len(line.encode("utf-8"))
            return event

    async def append_batch(
        self, events: list[dict[str, Any]], session_id: str
    ) -> list[TraceEvent]:
        """Append a batch of ``{"event_type", "data"}`` dicts."""
        results: list[TraceEvent] = []
        for ev in events:
            results.append(
                await self.append(ev["event_type"], ev.get("data", {}), session_id)
            )
        return results

    async def read(
        self,
        session_id: str,
        event_type: str | None = None,
        start_sequence: int = 0,
        limit: int = 1000,
        time_range: tuple[float, float] | None = None,
    ) -> list[TraceEvent]:
        """Read events from a session's log, optionally filtered."""
        path = self._session_file(session_id)
        if not path.exists():
            return []
        events: list[TraceEvent] = []
        with path.open(encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    raw = json.loads(line)
                except json.JSONDecodeError:
                    continue
                ev = TraceEvent.from_dict(raw)
                if event_type and ev.event_type != event_type:
                    continue
                if ev.sequence < start_sequence:
                    continue
                if time_range and not (time_range[0] <= ev.ts <= time_range[1]):
                    continue
                events.append(ev)
                if len(events) >= limit:
                    break
        return events

    def list_sessions(self) -> list[str]:
        return sorted(
            {p.stem.split("-")[0] for p in self._base_dir.glob("*.jsonl") if p.stem}
        )

    async def search(
        self,
        query: str,
        session_id: str | None = None,
        event_type: str | None = None,
        limit: int = 50,
    ) -> list[TraceEvent]:
        """Substring search over event data in one or all sessions."""
        needle = query.lower()
        sessions = [session_id] if session_id else self.list_sessions()
        matches: list[TraceEvent] = []
        for sid in sessions:
            path = self._session_file(sid)
            if not path.exists():
                continue
            with path.open(encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        raw = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    ev = TraceEvent.from_dict(raw)
                    if event_type and ev.event_type != event_type:
                        continue
                    blob = json.dumps(ev.to_dict(), ensure_ascii=False, default=str).lower()
                    if needle in blob:
                        matches.append(ev)
                    if len(matches) >= limit:
                        break
            if len(matches) >= limit:
                break
        return matches

    async def fork(self, session_id: str, after_sequence: int, new_session_id: str) -> int:
        """Fork a new session containing all events after a given sequence."""
        events = await self.read(session_id, start_sequence=after_sequence + 1, limit=10**9)
        await self.append_batch(
            [{"event_type": e.event_type, "data": e.data} for e in events],
            new_session_id,
        )
        return len(events)

    async def replay(self, session_id: str) -> list[TraceEvent]:
        """Return the full ordered event sequence for a session (Replay)."""
        return await self.read(session_id, limit=10**9)

    async def trajectory(
        self, session_id: str, event_type: str | None = None
    ) -> list[dict[str, Any]]:
        """Timeline view; each entry is {event_type, ts, sequence, summary}."""
        events = await self.read(session_id, event_type=event_type, limit=10**9)
        return [
            {
                "event_type": e.event_type,
                "ts": e.ts,
                "sequence": e.sequence,
                "summary": self._summarize(e),
            }
            for e in events
        ]

    @staticmethod
    def _summarize(event: TraceEvent) -> str:
        data = event.data
        try:
            if event.event_type == EVENT_TOOL_CALL:
                return f"tool_call: {data.get('name', '?')}"
            if event.event_type == EVENT_TOOL_RESULT:
                status = "ok" if data.get("success", True) else "fail"
                return f"tool_result({status}): {str(data.get('result', ''))[:80]}"
            if event.event_type == EVENT_DECISION:
                return f"decision: {data.get('action', '?')} -> {data.get('target', '?')} ({data.get('confidence', 0):.2f})"
            if event.event_type == EVENT_MODEL_SWITCH:
                return f"model_switch: {data.get('from')} -> {data.get('to')} ({data.get('reason', '')})"
            if event.event_type == EVENT_SUBAGENT:
                return f"subagent: {data.get('task', '?')[:60]} ({data.get('agent_id', '?')})"
            if event.event_type == EVENT_SKILL_LOAD:
                return f"skill_load: {data.get('skill_id')} @ {data.get('level', '?')}"
            if event.event_type == EVENT_CONTEXT_INJECTION:
                return f"context_inject: {data.get('source', '?')} ({data.get('token_count', '?')} tokens)"
            if event.event_type == EVENT_SCREENSHOT:
                return f"screenshot: {data.get('path', '?')}"
            if event.event_type == EVENT_REASONING:
                return f"reasoning ({data.get('model', '?')}): {str(data.get('content', ''))[:80]}"
            if event.event_type == EVENT_SYSTEM_PROMPT:
                return f"system_prompt: {str(data.get('content', ''))[:80]}"
            return event.event_type
        except Exception:
            return event.event_type


# Global singleton
_trace_log: TraceLog | None = None


def get_trace_log(base_dir: str | Path = "data/traces") -> TraceLog:
    global _trace_log
    if _trace_log is None:
        _trace_log = TraceLog(base_dir=base_dir)
    return _trace_log
