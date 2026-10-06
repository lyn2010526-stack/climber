"""Isolated permission routes with an in-memory policy and no database cleanup."""

import json
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import httpx
from fastapi import FastAPI

# Application imports normally load dotenv; keep this isolated suite file-free.
with patch("dotenv.load_dotenv", return_value=False):
    from app.api.v1 import permissions
    from app.api.v1.routes import reasoning
    from app.core.agent_engine import AgentEngine
    from app.core.engine import bootstrap
    from app.core.permission_rules import (
        PermissionConfig,
        PermissionMode,
        PermissionRule,
        PermissionTier,
        RuleDecision,
    )


class PermissionTierApiTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.config = PermissionConfig(
            mode=PermissionMode.DEFAULT,
            tier=PermissionTier.READ_ONLY,
            rules=[PermissionRule(RuleDecision.DENY, "file_delete")],
            allowed_tools=["read_file"],
            denied_tools=["fetch"],
        )
        self.engine = self
        app = FastAPI()
        app.include_router(permissions.router, prefix="/api/v1/permissions")
        app.include_router(reasoning.router, prefix="/api/v1")
        for route in app.routes:
            if getattr(route, "path", "") in {
                "/api/v1/permissions/config", "/api/v1/reasoning/permission-tiers",
            }:
                for dependency in route.dependant.dependencies:
                    if dependency.call is not reasoning.get_engine:
                        app.dependency_overrides[dependency.call] = lambda: {"id": "test-admin"}
        app.dependency_overrides[reasoning.get_engine] = lambda: self.engine
        patcher = patch.object(permissions, "get_engine", return_value=self.engine)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.client = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test",
        )
        self.addAsyncCleanup(self.client.aclose)

    def get_permission_config(self):
        return self.config

    def update_permission_config(self, config):
        # Exercise the production serialization boundary without touching disk/DB.
        self.config = PermissionConfig.from_dict(json.loads(json.dumps(config.to_dict())))

    async def test_three_tiers_round_trip_and_enforce_capabilities(self):
        for tier, mode, write, command in (
            ("read_only", "plan", "deny", "deny"),
            ("partial_write", "default", "ask", "deny"),
            ("full_write", "auto", "allow", "allow"),
        ):
            with self.subTest(tier=tier):
                response = await self.client.put(
                    "/api/v1/permissions/config", json={"tier": tier, "mode": mode},
                )
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json(), {"status": "updated", "tier": tier, "mode": mode})
                config = (await self.client.get("/api/v1/permissions/config")).json()
                view = (await self.client.get("/api/v1/reasoning/permission-tiers")).json()
                self.assertEqual(config["tier"], tier)
                self.assertEqual(view["current"], {"tier": tier, "mode": mode})
                self.assertEqual([row["id"] for row in view["tiers"]],
                                 ["read_only", "partial_write", "full_write"])
                states = {row["tool"]: row["decision"] for row in view["tool_states"]}
                for tool, decision in states.items():
                    self.assertEqual(decision, self.config.evaluate(tool).value)
                for tool in ("read_file", "list_directory", "search", "glob"):
                    expected = "ask" if tier == "partial_write" and tool != "read_file" else "allow"
                    self.assertEqual(self.config.evaluate(tool, {"path": "src/example.py"}).value, expected)
                for tool in ("write_file", "edit", "append_file", "apply_patch"):
                    self.assertEqual(self.config.evaluate(tool, {"path": "src/example.py"}).value, write)
                self.assertEqual(self.config.evaluate("bash", {"command": "git status"}).value, command)
                self.assertEqual(states["read_file"], "allow")
                self.assertEqual(states["write_file"], write)
                self.assertEqual(states["run_command"], command)
                self.assertEqual(states["file_delete"], "deny")
                self.assertEqual(config["allowed_tools"], ["read_file"])
                self.assertEqual(config["denied_tools"], ["fetch"])
                self.assertEqual(config["rules"][0]["decision"], "deny")

    async def test_view_reports_actual_tier_independently_of_mode(self):
        self.config.mode = PermissionMode.AUTO
        view = (await self.client.get("/api/v1/reasoning/permission-tiers")).json()
        self.assertEqual(view["current"], {"mode": "auto", "tier": "read_only"})
        self.assertEqual(self.config.evaluate("write_file"), RuleDecision.DENY)

    async def test_tier_only_update_preserves_mode(self):
        response = await self.client.put(
            "/api/v1/permissions/config", json={"tier": "partial_write"},
        )
        self.assertEqual(response.json()["mode"], "default")
        self.assertEqual(self.config.tier, PermissionTier.PARTIAL_WRITE)

    async def test_mode_only_update_preserves_tier(self):
        response = await self.client.put("/api/v1/permissions/config", json={"mode": "auto"})
        self.assertEqual(response.json()["tier"], "read_only")
        self.assertEqual(self.config.evaluate("write_file"), RuleDecision.DENY)

    async def test_invalid_values_leave_policy_unchanged(self):
        original = self.config
        for body in ({"tier": "partial"}, {"tier": "full"}, {"tier": ""}, {"mode": ""}):
            with self.subTest(body=body):
                response = await self.client.put("/api/v1/permissions/config", json=body)
                self.assertEqual(response.status_code, 400)
                self.assertIs(self.config, original)

    async def test_missing_config_has_no_current_tier(self):
        self.config = None
        view = (await self.client.get("/api/v1/reasoning/permission-tiers")).json()
        self.assertEqual(view["current"], {"mode": None, "tier": None})
        self.assertEqual(view["tool_states"], [])

    async def test_policy_restrictions_survive_every_mode(self):
        for mode in PermissionMode:
            with self.subTest(mode=mode):
                response = await self.client.put("/api/v1/permissions/config", json={
                    "tier": "full_write", "mode": mode.value,
                    "rules": [
                        {"decision": "deny", "tool": "edit", "pattern": "locked/*"},
                        {"decision": "ask", "tool": "write_file", "pattern": "src/*"},
                    ],
                    "allowed_tools": ["*"], "denied_tools": ["file_delete"],
                })
                self.assertEqual(response.status_code, 200)
                self.assertEqual(self.config.evaluate("edit_file", {"path": "locked/a.py"}), RuleDecision.DENY)
                expected = RuleDecision.DENY if mode == PermissionMode.PLAN else RuleDecision.ASK
                self.assertEqual(self.config.evaluate("write_file", {"path": "src/a.py"}), expected)
                self.assertEqual(self.config.evaluate("delete", {"path": "src/a.py"}), RuleDecision.DENY)

    async def test_partial_tier_ceiling_survives_explicit_allow_and_modes(self):
        for mode in ("auto", "bypass", "acceptEdits", "default", "strict"):
            with self.subTest(mode=mode):
                response = await self.client.put("/api/v1/permissions/config", json={
                    "tier": "partial_write", "mode": mode,
                    "rules": [{"decision": "allow", "tool": "*"}],
                    "allowed_tools": ["*"], "denied_tools": [],
                })
                self.assertEqual(response.status_code, 200)
                for tool in ("run_command", "web_search", "fetch", "file_delete", "unknown_tool"):
                    self.assertEqual(self.config.evaluate(tool), RuleDecision.DENY)
                self.assertEqual(self.config.evaluate("write_file"), RuleDecision.ASK)
                self.assertEqual(self.config.evaluate("write_file", {"path": "/etc"}), RuleDecision.DENY)
                self.assertEqual(self.config.evaluate("write_file", {"path": "/var/../etc/config"}), RuleDecision.DENY)

    async def test_clean_tier_matrix_with_real_arguments(self):
        for tier, mode, write, command in (
            ("read_only", "plan", "deny", "deny"),
            ("partial_write", "default", "ask", "deny"),
            ("full_write", "auto", "allow", "allow"),
        ):
            with self.subTest(tier=tier):
                response = await self.client.put("/api/v1/permissions/config", json={
                    "tier": tier, "mode": mode, "rules": [],
                    "allowed_tools": [], "denied_tools": [],
                })
                self.assertEqual(response.status_code, 200)
                for tool in ("read_file", "glob", "file_exists", "file_info", "file_diff"):
                    self.assertEqual(self.config.evaluate(tool, {"path": "src/a.py"}).value, "allow")
                self.assertEqual(self.config.evaluate("write_file", {"path": "src/a.py"}).value, write)
                self.assertEqual(self.config.evaluate("run_command", {"command": "git status"}).value, command)

    async def test_full_write_keeps_default_delete_confirmation(self):
        await self.client.put("/api/v1/permissions/config", json={
            "tier": "full_write", "mode": "default", "rules": [],
            "allowed_tools": [], "denied_tools": [],
        })
        self.assertEqual(self.config.evaluate("file_delete", {"path": "src/a.py"}), RuleDecision.ASK)

    async def test_parameter_rules_require_matching_arguments(self):
        await self.client.put("/api/v1/permissions/config", json={
            "tier": "full_write", "mode": "auto", "rules": [
                {"decision": "deny", "tool": "edit_file", "pattern": "locked/*"},
            ], "allowed_tools": [], "denied_tools": [],
        })
        self.assertEqual(self.config.evaluate("edit_file", {"path": "src/a.py"}), RuleDecision.ALLOW)
        self.assertEqual(self.config.evaluate("edit_file"), RuleDecision.ALLOW)

    async def test_real_engine_save_reload_and_existing_session_policy(self):
        directory = tempfile.mkdtemp(prefix="permission-tier-", dir="/tmp/opencode")
        engine = AgentEngine.__new__(AgentEngine)
        engine._default_permission_config = self.config
        session = SimpleNamespace(permission_config=self.config)
        engine._sessions = {"existing": session}
        with patch.object(bootstrap, "permission_config_path", return_value=f"{directory}/permission_config.json"):
            for tier, mode in (("read_only", "plan"), ("partial_write", "default"), ("full_write", "auto")):
                with self.subTest(tier=tier):
                    config = PermissionConfig(mode=PermissionMode(mode), tier=PermissionTier(tier))
                    engine.update_permission_config(config)
                    self.assertIs(session.permission_config, config)
                    loaded = engine._load_permission_config()
                    self.assertIsNotNone(loaded)
                    self.assertEqual(loaded.to_dict(), config.to_dict())
                    for tool, args in (("write_file", {"path": "src/a.py"}), ("bash", {"command": "git status"})):
                        self.assertEqual(loaded.evaluate(tool, args), session.permission_config.evaluate(tool, args))
        print(f"Persistence evidence (retained): {directory}/permission_config.json")


if __name__ == "__main__":
    unittest.main()
