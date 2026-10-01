"""API tests for skill tools validation, version management, and static test runs.

Covers the versioning endpoints added on the skill CRUD router:
- tools field validation against the global tool registry (400 on unknowns)
- version create / list / activate flow with deprecated marking
- test case CRUD and static-mode runs persisting SkillTestResult
"""

from __future__ import annotations

from sqlalchemy import func, select

from app.tools import tool_registry

_TEST_TOOL = "_skill_versioning_api_test_tool"


def _ensure_test_tool_registered() -> None:
    """Register a stable test tool in the global registry once."""
    if tool_registry.get_tool(_TEST_TOOL) is None:
        tool_registry.register(
            _TEST_TOOL,
            "test tool for skill API validation",
            {"type": "object", "properties": {}},
            lambda: "ok",
        )


async def _create_skill(client, **overrides) -> dict:
    payload = {"name": "versioned-skill", "prompt_template": "Hello {name}", "tools": []}
    payload.update(overrides)
    resp = await client.post("/api/v1/skills", json=payload)
    assert resp.status_code == 200, resp.text
    return resp.json()


# --- tools field validation --------------------------------------------------


async def test_create_skill_rejects_unknown_tools_listing_all_names(client) -> None:
    resp = await client.post(
        "/api/v1/skills",
        json={"name": "bad-tools", "tools": ["no_such_tool_a", "no_such_tool_b"]},
    )
    assert resp.status_code == 400
    detail = resp.json()["detail"]
    assert "no_such_tool_a" in detail
    assert "no_such_tool_b" in detail
    assert "Unknown tools" in detail


async def test_create_skill_allows_empty_and_registered_tools(client) -> None:
    _ensure_test_tool_registered()

    resp = await client.post("/api/v1/skills", json={"name": "empty-tools", "tools": []})
    assert resp.status_code == 200
    assert resp.json()["tools"] == []

    resp = await client.post("/api/v1/skills", json={"name": "no-tools-field"})
    assert resp.status_code == 200
    assert resp.json()["tools"] == []

    resp = await client.post("/api/v1/skills", json={"name": "known-tools", "tools": [_TEST_TOOL]})
    assert resp.status_code == 200
    assert resp.json()["tools"] == [_TEST_TOOL]


# --- version management ------------------------------------------------------


async def test_version_lifecycle_marks_old_versions_deprecated(client) -> None:
    skill = await _create_skill(client, prompt_template="Hello {name}")
    skill_id = skill["id"]

    first = await client.post(f"/api/v1/skills/{skill_id}/versions", json={})
    assert first.status_code == 200, first.text
    first_body = first.json()
    assert first_body["ok"] is True
    assert first_body["version"] == "v1"
    v1_id = first_body["version_id"]

    second = await client.post(
        f"/api/v1/skills/{skill_id}/versions",
        json={"prompt": "Second {name} prompt", "changelog": "rewrite"},
    )
    assert second.status_code == 200
    second_body = second.json()
    assert second_body["version"] == "v2"
    v2_id = second_body["version_id"]
    assert v2_id != v1_id
    assert v1_id in second_body["deprecated_version_ids"]

    listing = await client.get(f"/api/v1/skills/{skill_id}/versions")
    assert listing.status_code == 200
    listing_body = listing.json()
    assert listing_body["active_version_id"] == v2_id
    by_label = {v["version"]: v for v in listing_body["versions"]}
    assert set(by_label) == {"v1", "v2"}
    assert by_label["v1"]["prompt"] == "Hello {name}"
    assert by_label["v1"]["tools"] == []
    assert by_label["v1"]["is_active"] is False
    assert by_label["v2"]["is_active"] is True
    assert by_label["v2"]["prompt"] == "Second {name} prompt"

    activate = await client.post(f"/api/v1/skills/{skill_id}/versions/{v1_id}/activate")
    assert activate.status_code == 200, activate.text
    activate_body = activate.json()
    assert activate_body["active_version_id"] == v1_id
    assert v2_id in activate_body["deprecated_version_ids"]

    relisted = (await client.get(f"/api/v1/skills/{skill_id}/versions")).json()
    assert relisted["active_version_id"] == v1_id
    relisted_by_label = {v["version"]: v for v in relisted["versions"]}
    assert relisted_by_label["v1"]["is_active"] is True
    assert relisted_by_label["v2"]["is_active"] is False


async def test_version_endpoints_return_404_for_unknown_skill_or_version(client) -> None:
    resp = await client.post("/api/v1/skills/does-not-exist/versions", json={})
    assert resp.status_code == 404

    resp = await client.get("/api/v1/skills/does-not-exist/versions")
    assert resp.status_code == 404

    skill = await _create_skill(client)
    resp = await client.post(f"/api/v1/skills/{skill['id']}/versions/nope/activate")
    assert resp.status_code == 404


# --- test cases and static runs ----------------------------------------------


async def test_test_case_crud_and_static_run(client) -> None:
    skill = await _create_skill(client, prompt_template="Hello {name}, welcome to {place}")
    skill_id = skill["id"]

    created = await client.post(
        f"/api/v1/skills/{skill_id}/test-cases",
        json={
            "name": "greeting-passes",
            "input_params": {"name": "World", "place": "Climber"},
            "expected_output_contains": "Hello World, welcome to Climber",
        },
    )
    assert created.status_code == 200, created.text
    pass_case_id = created.json()["test_case_id"]

    failed = await client.post(
        f"/api/v1/skills/{skill_id}/test-cases",
        json={
            "name": "greeting-fails",
            "input_params": {"name": "World", "place": "Climber"},
            "expected_output_contains": "goodbye",
        },
    )
    assert failed.status_code == 200
    fail_case_id = failed.json()["test_case_id"]

    missing = await client.post(
        f"/api/v1/skills/{skill_id}/test-cases",
        json={"name": "missing-variables", "input_params": {}},
    )
    assert missing.status_code == 200
    missing_case_id = missing.json()["test_case_id"]

    listing = await client.get(f"/api/v1/skills/{skill_id}/test-cases")
    assert listing.status_code == 200
    listing_body = listing.json()
    assert listing_body["skill_id"] == skill_id
    assert len(listing_body["test_cases"]) == 3
    listed_pass = next(c for c in listing_body["test_cases"] if c["id"] == pass_case_id)
    assert listed_pass["name"] == "greeting-passes"
    assert listed_pass["input_params"] == {"name": "World", "place": "Climber"}
    assert listed_pass["expected_output_contains"] == "Hello World, welcome to Climber"

    run_pass = await client.post(f"/api/v1/skills/{skill_id}/test-cases/{pass_case_id}/run")
    assert run_pass.status_code == 200, run_pass.text
    run_pass_body = run_pass.json()
    assert run_pass_body["source"] == "static"
    assert run_pass_body["passed"] is True
    assert run_pass_body["skill_id"] == skill_id
    assert run_pass_body["output"] == "Hello World, welcome to Climber"
    assert run_pass_body["duration_ms"] >= 0

    run_fail = await client.post(f"/api/v1/skills/{skill_id}/test-cases/{fail_case_id}/run")
    assert run_fail.status_code == 200
    run_fail_body = run_fail.json()
    assert run_fail_body["source"] == "static"
    assert run_fail_body["passed"] is False

    run_missing = await client.post(f"/api/v1/skills/{skill_id}/test-cases/{missing_case_id}/run")
    assert run_missing.status_code == 200
    run_missing_body = run_missing.json()
    assert run_missing_body["source"] == "static"
    assert run_missing_body["passed"] is False
    assert "missing required variables" in run_missing_body["error"]
    assert "name" in run_missing_body["error"]

    from app.storage import async_session
    from app.storage.models_skills import SkillTestResult

    async with async_session() as db:
        persisted = (
            (await db.execute(select(SkillTestResult).where(SkillTestResult.skill_id == skill_id)))
            .scalars()
            .all()
        )
        total = (
            await db.execute(
                select(func.count())
                .select_from(SkillTestResult)
                .where(SkillTestResult.skill_id == skill_id)
            )
        ).scalar_one()
    assert total == 3
    assert len(persisted) == 3
    pass_rows = [r for r in persisted if r.test_id == pass_case_id]
    assert len(pass_rows) == 1
    assert pass_rows[0].passed is True
    assert "Hello World, welcome to Climber" in pass_rows[0].actual_output


async def test_test_case_endpoints_return_404_for_unknown_skill_or_case(client) -> None:
    resp = await client.post("/api/v1/skills/does-not-exist/test-cases", json={"name": "case"})
    assert resp.status_code == 404

    resp = await client.get("/api/v1/skills/does-not-exist/test-cases")
    assert resp.status_code == 404

    skill = await _create_skill(client)
    resp = await client.post(f"/api/v1/skills/{skill['id']}/test-cases/nope/run")
    assert resp.status_code == 404
