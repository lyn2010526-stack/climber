"""MCP Plugin: Trajectory Storage — complete execution trace recording.

Stores every reasoning step, tool call, and result for replay,
debugging, and simulation.
"""

from __future__ import annotations

import json
import os
import time
import uuid
from dataclasses import dataclass, field
from typing import Any


@dataclass
class TrajectoryStep:
    iteration: int
    timestamp: float
    action: str
    tool_name: str
    arguments: dict[str, Any]
    result_preview: str
    tokens_used: int = 0


@dataclass
class Trajectory:
    task_id: str
    goal: str
    steps: list[TrajectoryStep] = field(default_factory=list)
    final_outcome: str = ""
    success: bool = False
    total_tokens: int = 0
    created_at: float = 0.0
    completed_at: float = 0.0


class TrajectoryStorage:
    """Store and query execution trajectories."""

    def __init__(self, storage_path: str = "data/trajectories.json"):
        self._storage_path = storage_path
        self._trajectories: dict[str, Trajectory] = {}
        self._load()

    def start_trajectory(self, goal: str) -> Trajectory:
        task_id = str(uuid.uuid4())[:8]
        traj = Trajectory(
            task_id=task_id,
            goal=goal,
            created_at=time.time(),
        )
        self._trajectories[task_id] = traj
        return traj

    def record_step(
        self,
        task_id: str,
        iteration: int,
        action: str,
        tool_name: str,
        arguments: dict[str, Any],
        result: str,
        tokens_used: int = 0,
    ) -> bool:
        traj = self._trajectories.get(task_id)
        if not traj:
            return False
        traj.steps.append(TrajectoryStep(
            iteration=iteration,
            timestamp=time.time(),
            action=action,
            tool_name=tool_name,
            arguments=arguments,
            result_preview=result[:300],
            tokens_used=tokens_used,
        ))
        traj.total_tokens += tokens_used
        return True

    def complete_trajectory(
        self,
        task_id: str,
        outcome: str,
        success: bool,
    ) -> bool:
        traj = self._trajectories.get(task_id)
        if not traj:
            return False
        traj.final_outcome = outcome
        traj.success = success
        traj.completed_at = time.time()
        self._save()
        return True

    def get_trajectory(self, task_id: str) -> Trajectory | None:
        return self._trajectories.get(task_id)

    def list_trajectories(
        self,
        success_only: bool = False,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        trajs = list(self._trajectories.values())
        if success_only:
            trajs = [t for t in trajs if t.success]
        trajs.sort(key=lambda t: t.created_at, reverse=True)
        return [
            {
                "task_id": t.task_id,
                "goal": t.goal[:80],
                "steps": len(t.steps),
                "tokens": t.total_tokens,
                "success": t.success,
                "outcome": t.final_outcome[:60],
            }
            for t in trajs[:limit]
        ]

    def replay(self, task_id: str) -> list[dict[str, Any]]:
        """Get full step-by-step replay of a trajectory."""
        traj = self._trajectories.get(task_id)
        if not traj:
            return []
        return [
            {
                "iteration": s.iteration,
                "action": s.action,
                "tool": s.tool_name,
                "result": s.result_preview,
            }
            for s in traj.steps
        ]

    def find_similar_trajectories(
        self,
        goal: str,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """Find past trajectories with similar goals (simple word overlap)."""
        goal_words = set(goal.lower().split())
        scored = []
        for traj in self._trajectories.values():
            traj_words = set(traj.goal.lower().split())
            if not traj_words:
                continue
            overlap = len(goal_words & traj_words) / len(goal_words | traj_words)
            scored.append((overlap, traj))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [
            {
                "task_id": t.task_id,
                "goal": t.goal[:80],
                "similarity": score,
                "success": t.success,
                "steps": len(t.steps),
            }
            for score, t in scored[:limit]
            if score > 0.1
        ]

    def get_tool_definitions(self) -> list[dict[str, Any]]:
        return [
            {
                "name": "trajectory_start",
                "description": "Start recording a new execution trajectory",
                "parameters": {
                    "type": "object",
                    "properties": {"goal": {"type": "string"}},
                    "required": ["goal"],
                },
            },
            {
                "name": "trajectory_record",
                "description": "Record a step in the current trajectory",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "task_id": {"type": "string"},
                        "iteration": {"type": "integer"},
                        "action": {"type": "string"},
                        "tool_name": {"type": "string"},
                        "arguments": {"type": "object"},
                        "result": {"type": "string"},
                    },
                    "required": ["task_id", "iteration", "action", "tool_name"],
                },
            },
            {
                "name": "trajectory_replay",
                "description": "Replay a past trajectory step by step",
                "parameters": {
                    "type": "object",
                    "properties": {"task_id": {"type": "string"}},
                    "required": ["task_id"],
                },
            },
        ]

    def _save(self) -> None:
        os.makedirs(os.path.dirname(self._storage_path), exist_ok=True)
        data = {
            tid: {
                "task_id": t.task_id,
                "goal": t.goal,
                "steps": [
                    {
                        "iteration": s.iteration,
                        "timestamp": s.timestamp,
                        "action": s.action,
                        "tool_name": s.tool_name,
                        "arguments": s.arguments,
                        "result_preview": s.result_preview,
                        "tokens_used": s.tokens_used,
                    }
                    for s in t.steps
                ],
                "final_outcome": t.final_outcome,
                "success": t.success,
                "total_tokens": t.total_tokens,
                "created_at": t.created_at,
                "completed_at": t.completed_at,
            }
            for tid, t in self._trajectories.items()
        }
        with open(self._storage_path, "w") as f:
            json.dump(data, f, indent=2)

    def _load(self) -> None:
        if not os.path.exists(self._storage_path):
            return
        try:
            with open(self._storage_path) as f:
                data = json.load(f)
            for tid, t in data.items():
                steps = [
                    TrajectoryStep(
                        iteration=s["iteration"],
                        timestamp=s.get("timestamp", 0),
                        action=s["action"],
                        tool_name=s["tool_name"],
                        arguments=s.get("arguments", {}),
                        result_preview=s.get("result_preview", ""),
                        tokens_used=s.get("tokens_used", 0),
                    )
                    for s in t.get("steps", [])
                ]
                self._trajectories[tid] = Trajectory(
                    task_id=t["task_id"],
                    goal=t["goal"],
                    steps=steps,
                    final_outcome=t.get("final_outcome", ""),
                    success=t.get("success", False),
                    total_tokens=t.get("total_tokens", 0),
                    created_at=t.get("created_at", 0),
                    completed_at=t.get("completed_at", 0),
                )
        except (json.JSONDecodeError, KeyError):
            pass
