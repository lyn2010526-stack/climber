"""Plan-stage batch tool precheck tests (sandbox review 5.2 item 3)."""

from __future__ import annotations

import json

from app.core.task_worker import _precheck_plan_steps


def _plan_step(step: int, tools: list[str], action: str = "Do the work") -> dict:
    return {
        "step": step,
        "status": "pending",
        "action": action,
        "objective": action,
        "tools": tools,
    }


def test_read_only_mode_blocks_side_effect_tools() -> None:
    """Read-only permission + side-effect tool -> blocked with non-empty reasons."""
    steps = [_plan_step(1, ["write_file"]), _plan_step(2, ["read_file"])]
    prechecks = _precheck_plan_steps(steps, "plan")

    blocked = prechecks[0]
    assert blocked["blocked"] is True
    assert blocked["reasons"]
    assert any("write_file" in reason for reason in blocked["reasons"])
    assert prechecks[1]["blocked"] is False


def test_unknown_tool_is_blocked() -> None:
    """A tool outside the factory whitelist is flagged even in permissive modes."""
    steps = [_plan_step(1, ["make_coffee"]), _plan_step(2, ["read_file"])]
    prechecks = _precheck_plan_steps(steps, "auto")

    assert prechecks[0]["blocked"] is True
    assert any("make_coffee" in reason for reason in prechecks[0]["reasons"])
    assert prechecks[1]["blocked"] is False


def test_known_tools_pass_in_permissive_mode() -> None:
    """Whitelisted tools, including side-effect tools, run in a permissive mode."""
    steps = [
        _plan_step(1, ["read_file", "list_files"]),
        _plan_step(2, ["web_search"]),
    ]
    prechecks = _precheck_plan_steps(steps, "auto")

    assert all(precheck["blocked"] is False for precheck in prechecks)
    assert len(prechecks) == len(steps)


def test_all_allowed_returns_one_entry_per_step() -> None:
    """Every step gets exactly one precheck entry when nothing is blocked."""
    steps = [_plan_step(i, ["read_file"]) for i in range(1, 4)]
    prechecks = _precheck_plan_steps(steps, "auto")

    assert len(prechecks) == len(steps)
    assert [precheck["index"] for precheck in prechecks] == [1, 2, 3]
    assert all(
        precheck["blocked"] is False and precheck["reasons"] == [] for precheck in prechecks
    )


async def test_factory_run_blocks_side_effect_step_at_plan_stage(client, monkeypatch) -> None:
    """Integration: the fallback-plan write step is blocked before it executes."""
    seen_objectives: list[str] = []

    async def _handler(payload, on_progress):
        objective = str(payload["objective"])
        seen_objectives.append(objective)
        # Call order: planner call, then one call per executed step, then the
        # synthesis call. The planner fails so the run falls back to the
        # built-in plan for file_manager: step 1 is read-only, step 2 asks for
        # write_file and must be blocked by the plan-stage precheck.
        if objective.startswith("Create a concise execution plan"):
            raise RuntimeError("planner offline")
        if objective.startswith("Produce the final answer"):
            return {"output": "synth done"}
        return {"output": f"ran: {objective}"}

    from app.api.v1 import skills_router
    from app.core.task_worker import task_manager

    async def _factory_payload(user_id, data):
        return {
            "objective": data["goal"],
            "user_id": user_id,
            "agent_id": None,
            "provider": "openai",
            "model": "test-model",
            "api_key": "test-key",
            "base_url": None,
            "system_prompt": "test",
            "tools": [],
            "factory_skills": data.get("skills", []),
            "max_steps": 10,
            "permission_mode": "plan",
        }

    monkeypatch.setattr(skills_router, "_factory_agent_payload", _factory_payload)
    monkeypatch.setitem(task_manager._handlers, "agent_run", _handler)

    resp = await client.post(
        "/api/v1/skills/autonomous/run",
        json={"goal": "write the report", "skills": ["file_manager"]},
    )
    assert resp.status_code == 200

    events = [
        json.loads(line[6:])
        for frame in resp.text.split("\n\n")
        for line in frame.splitlines()
        if line.startswith("data: ") and line != "data: [DONE]"
    ]

    types = [event["type"] for event in events]
    assert "plan_fallback" in types
    assert "synthesize" in types

    failed = next(event for event in events if event["type"] == "task_failed")
    assert failed["data"]["step"] == 2
    assert "blocked" in failed["data"]["error"]

    # The blocked step never reaches the agent handler and never starts.
    assert "write the report" not in seen_objectives
    started = [event for event in events if event["type"] == "task_start"]
    assert started
    assert all(event["data"]["step"] != 2 for event in started)
