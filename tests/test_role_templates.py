"""Tests for agent role templates."""

from __future__ import annotations

from app.multi_agent.role_templates import (
    ROLE_TEMPLATES,
    auditor_role,
    executor_role,
    get_role,
    list_roles,
    planner_role,
    researcher_role,
    security_auditor_role,
)


class TestRoleTemplates:
    def test_all_roles_present(self) -> None:
        assert "planner" in ROLE_TEMPLATES
        assert "executor" in ROLE_TEMPLATES
        assert "auditor" in ROLE_TEMPLATES
        assert "researcher" in ROLE_TEMPLATES
        assert "security_auditor" in ROLE_TEMPLATES

    def test_planner_role(self) -> None:
        role = planner_role()
        assert role.name == "planner"
        assert role.can_delegate is True
        assert len(role.tools) == 0

    def test_executor_role(self) -> None:
        role = executor_role()
        assert role.name == "executor"
        assert "read_file" in role.tools
        assert "write_file" in role.tools

    def test_auditor_role(self) -> None:
        role = auditor_role()
        assert role.name == "auditor"
        assert role.can_delegate is False

    def test_researcher_role(self) -> None:
        role = researcher_role()
        assert role.name == "researcher"
        assert "web_search" in role.tools

    def test_security_auditor_role(self) -> None:
        role = security_auditor_role()
        assert role.name == "security_auditor"
        assert "OWASP" in role.backstory

    def test_get_role_by_name(self) -> None:
        role = get_role("planner")
        assert role is not None
        assert role.name == "planner"

    def test_get_role_not_found(self) -> None:
        assert get_role("nonexistent") is None

    def test_get_role_with_extra_tools(self) -> None:
        role = get_role("planner", extra_tools=["read_file", "run_command"])
        assert role is not None
        assert "read_file" in role.tools
        assert "run_command" in role.tools

    def test_list_roles(self) -> None:
        roles = list_roles()
        assert len(roles) >= 5
        names = {r["name"] for r in roles}
        assert "planner" in names
        assert "executor" in names

    def test_role_backstory_not_empty(self) -> None:
        for name, role in ROLE_TEMPLATES.items():
            assert len(role.backstory) > 50, f"Role {name} has short backstory"
            assert len(role.goal) > 20, f"Role {name} has short goal"
