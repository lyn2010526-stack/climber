"""Persistent append-only event store.

Every state change in the runtime is recorded as an immutable event with a
unified envelope:

- ``sequence``: globally monotonic integer (SQLite AUTOINCREMENT)
- ``event_id``: uuid4
- ``stream_id``: owning stream (e.g. a session id, ``"main"``)
- ``event_type``: dotted type such as ``message``, ``tool_call``
- ``ts``: unix timestamp
- ``data``: JSON payload

The store only exposes INSERT + SELECT paths — there is no update or delete,
so the on-disk log stays append-only. Events survive process restarts, which
makes them the durable source of truth behind projections
(:class:`EventSourcingManager`) and replay tooling.
"""

from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from typing import Any

import aiosqlite

_SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id TEXT NOT NULL,
    stream_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    ts REAL NOT NULL,
    data TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_events_stream ON events(stream_id, sequence);
CREATE INDEX IF NOT EXISTS idx_events_type ON events(event_type);
"""


class EventStore:
    """SQLite-backed append-only event log.

    Args:
        path: database file path; parent directories are created.
    """

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._db: aiosqlite.Connection | None = None

    async def _conn(self) -> aiosqlite.Connection:
        if self._db is None:
            self._db = await aiosqlite.connect(str(self._path))
            await self._db.executescript(_SCHEMA)
            await self._db.commit()
        return self._db

    async def append(
        self,
        event_type: str,
        data: dict[str, Any],
        stream_id: str = "main",
    ) -> dict[str, Any]:
        """Append one event and return its stored envelope."""
        db = await self._conn()
        envelope = {
            "event_id": str(uuid.uuid4()),
            "stream_id": stream_id,
            "event_type": event_type,
            "ts": time.time(),
            "data": data,
        }
        payload = json.dumps(data, ensure_ascii=False, default=str)
        # Return the data exactly as persisted so callers never observe a
        # richer in-memory form than what would survive a restart.
        envelope["data"] = json.loads(payload)
        async with db.execute(
            "INSERT INTO events (event_id, stream_id, event_type, ts, data)"
            " VALUES (?, ?, ?, ?, ?)",
            (
                envelope["event_id"],
                stream_id,
                event_type,
                envelope["ts"],
                payload,
            ),
        ) as cursor:
            envelope["sequence"] = cursor.lastrowid
        await db.commit()
        return envelope

    async def read(
        self,
        stream_id: str | None = None,
        event_type: str | None = None,
        after_sequence: int = 0,
        limit: int = 1000,
    ) -> list[dict[str, Any]]:
        """Read events in sequence order with optional filters."""
        db = await self._conn()
        query = (
            "SELECT sequence, event_id, stream_id, event_type, ts, data"
            " FROM events WHERE sequence > ?"
        )
        params: list[Any] = [after_sequence]
        if stream_id is not None:
            query += " AND stream_id = ?"
            params.append(stream_id)
        if event_type is not None:
            query += " AND event_type = ?"
            params.append(event_type)
        query += " ORDER BY sequence LIMIT ?"
        params.append(limit)

        events: list[dict[str, Any]] = []
        async with db.execute(query, params) as cursor:
            async for sequence, event_id, sid, etype, ts, payload in cursor:
                events.append(
                    {
                        "sequence": sequence,
                        "event_id": event_id,
                        "stream_id": sid,
                        "event_type": etype,
                        "ts": ts,
                        "data": json.loads(payload),
                    }
                )
        return events

    async def count(self, stream_id: str | None = None) -> int:
        """Return the number of stored events, optionally per stream."""
        db = await self._conn()
        if stream_id is None:
            cursor = await db.execute("SELECT COUNT(*) FROM events")
        else:
            cursor = await db.execute(
                "SELECT COUNT(*) FROM events WHERE stream_id = ?", (stream_id,)
            )
        async with cursor:
            row = await cursor.fetchone()
        return int(row[0]) if row else 0

    async def close(self) -> None:
        if self._db is not None:
            await self._db.close()
            self._db = None
