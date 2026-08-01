"""Task model with goal -> sub-tasks -> step iteration.

Provides structured task representation with hierarchical support,
persistence via SQLite, and lifecycle management integrated with TaskState.
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Any

from app.core.task_state_machine import TaskState


@dataclass
class SubTask:
    """A single unit of work within a task."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    description: str = ""
    status: str = TaskState.PENDING.value
    dependencies: list[str] = field(default_factory=list)
    assigned_agent: str = ""
    result: str = ""
    error: str = ""
    started_at: str = ""
    completed_at: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SubTask:
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class Task:
    """Top-level task with goal, sub-tasks, and iteration tracking."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    goal: str = ""
    status: str = TaskState.PENDING.value
    sub_tasks: list[SubTask] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    max_iterations: int = 100
    current_iteration: int = 0
    timeout_seconds: int = 3600
    parent_id: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["sub_tasks"] = [st.to_dict() for st in self.sub_tasks]
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Task:
        sub_tasks_data = data.pop("sub_tasks", [])
        task = cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
        task.sub_tasks = [SubTask.from_dict(st) for st in sub_tasks_data]
        return task


class TaskStore:
    """SQLite-backed persistence for tasks and sub-tasks."""

    def __init__(self, db_path: str = ":memory:"):
        self._db_path = db_path
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._create_tables()

    def _create_tables(self) -> None:
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                goal TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                sub_tasks_json TEXT NOT NULL DEFAULT '[]',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                max_iterations INTEGER NOT NULL DEFAULT 100,
                current_iteration INTEGER NOT NULL DEFAULT 0,
                timeout_seconds INTEGER NOT NULL DEFAULT 3600,
                parent_id TEXT DEFAULT '',
                metadata_json TEXT NOT NULL DEFAULT '{}'
            );
        """)
        self._conn.commit()

    def save(self, task: Task) -> None:
        task.updated_at = datetime.now(timezone.utc).isoformat()
        self._conn.execute(
            """
            INSERT OR REPLACE INTO tasks
            (id, goal, status, sub_tasks_json, created_at, updated_at,
             max_iterations, current_iteration, timeout_seconds, parent_id, metadata_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                task.id,
                task.goal,
                task.status,
                json.dumps([st.to_dict() for st in task.sub_tasks]),
                task.created_at,
                task.updated_at,
                task.max_iterations,
                task.current_iteration,
                task.timeout_seconds,
                task.parent_id,
                json.dumps(task.metadata),
            ),
        )
        self._conn.commit()

    def load(self, task_id: str) -> Task | None:
        row = self._conn.execute(
            "SELECT * FROM tasks WHERE id = ?", (task_id,)
        ).fetchone()
        if not row:
            return None
        return self._row_to_task(row)

    def update(self, task: Task) -> None:
        self.save(task)

    def delete(self, task_id: str) -> bool:
        cursor = self._conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        self._conn.commit()
        return cursor.rowcount > 0

    def list_all(self, parent_id: str | None = None) -> list[Task]:
        if parent_id is not None:
            rows = self._conn.execute(
                "SELECT * FROM tasks WHERE parent_id = ?", (parent_id,)
            ).fetchall()
        else:
            rows = self._conn.execute("SELECT * FROM tasks").fetchall()
        return [self._row_to_task(row) for row in rows]

    def get_children(self, task_id: str) -> list[Task]:
        return self.list_all(parent_id=task_id)

    def _row_to_task(self, row: sqlite3.Row) -> Task:
        sub_tasks_data = json.loads(row["sub_tasks_json"])
        metadata = json.loads(row["metadata_json"])
        return Task(
            id=row["id"],
            goal=row["goal"],
            status=row["status"],
            sub_tasks=[SubTask.from_dict(st) for st in sub_tasks_data],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            max_iterations=row["max_iterations"],
            current_iteration=row["current_iteration"],
            timeout_seconds=row["timeout_seconds"],
            parent_id=row["parent_id"],
            metadata=metadata,
        )

    def close(self) -> None:
        self._conn.close()
