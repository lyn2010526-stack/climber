"""Local regressions for reported defects 17 and 18; no network or Docker."""

import socket
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, call, patch

import httpx

from app.core.engine.safety import setup_default_permissions, validate_tool_call
from app.core.interfaces import ExecutionResult, ExecutionStatus
from app.core.security import DockerSandbox
from app.core.security_sandbox import (
    AgentMode, PermissionLevel, PermissionOverlay, PermissionRule, SecuritySandbox,
)
from app.tools import builtins
from app.utils.ssrf import blocked_reason


class DockerResultTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.sandbox = DockerSandbox()
        self.sandbox._available = True

    def test_missing_container_uses_real_result(self):
        result = self.sandbox.execute_command("missing")
        self.assertIs(type(result), ExecutionResult)
        self.assertEqual(result.status, ExecutionStatus.FAILED)
        self.assertEqual(result.metrics, {"returncode": -1, "timed_out": False})
        self.assertIn("not found", result.error)

    def test_exit_status_and_output(self):
        for code in (0, 2):
            with self.subTest(returncode=code):
                container = Mock()
                container.wait.return_value = {"StatusCode": code}
                container.logs.return_value = b"local output"
                self.sandbox._active_containers["mock"] = container
                result = self.sandbox.execute_command("mock", timeout=3)
                self.assertIs(type(result), ExecutionResult)
                expected = ExecutionStatus.COMPLETED if code == 0 else ExecutionStatus.FAILED
                self.assertEqual(result.status, expected)
                self.assertEqual(result.output, "local output")
                self.assertEqual(result.metrics, {"returncode": code, "timed_out": False})
                container.wait.assert_called_once_with(timeout=3)

    def test_wait_timeout_returns_failure(self):
        container = Mock()
        container.wait.side_effect = TimeoutError("mock timeout")
        self.sandbox._active_containers["mock"] = container
        result = self.sandbox.execute_command("mock")
        self.assertEqual(result.status, ExecutionStatus.FAILED)
        self.assertTrue(result.metrics["timed_out"])
        self.assertIn("mock timeout", result.error)
        container.kill.assert_called_once_with()

    async def test_unavailable_stops_without_fallback_execution(self):
        self.sandbox._available = False
        with patch.object(self.sandbox, "create_container") as create:
            result = await self.sandbox.execute(["echo", "hello"], ".")
        create.assert_not_called()
        self.assertEqual(result.status, ExecutionStatus.FAILED)
        self.assertEqual(result.error, "Docker not available")

    async def test_creation_failure_uses_real_result(self):
        with patch.object(self.sandbox, "create_container", side_effect=RuntimeError("mock failure")):
            result = await self.sandbox.execute(["echo", "hello"], ".")
        self.assertIs(type(result), ExecutionResult)
        self.assertEqual(result.status, ExecutionStatus.FAILED)
        self.assertEqual(result.metrics["returncode"], -1)
        self.assertIn("mock failure", result.error)

    async def test_execution_keeps_result_and_cleanup(self):
        container = Mock()
        container.wait.return_value = {"StatusCode": 0}
        container.logs.return_value = b"hello"
        self.sandbox._active_containers["mock"] = container
        with patch.object(self.sandbox, "create_container", return_value="mock"):
            result = await self.sandbox.execute(["echo", "hello"], ".")
        self.assertEqual(result.output, "hello")
        container.remove.assert_called_once_with(force=True)
        self.assertNotIn("mock", self.sandbox._active_containers)


class ExistingSafetyChainTests(unittest.TestCase):
    def setUp(self):
        self.permissions = PermissionOverlay()
        self.sandbox = SecuritySandbox()
        definition = SimpleNamespace(parameters={
            "type": "object",
            "properties": {"command": {"type": "string"}},
            "required": ["command"],
        })
        self.registry = SimpleNamespace(get_tool=Mock(return_value=definition))

    def validate(self, arguments, mode=AgentMode.ACT):
        return validate_tool_call(
            self.sandbox, self.permissions, mode, self.registry, "run_command", arguments,
        )

    def allow_execution(self):
        self.permissions.set_defaults([
            PermissionRule("execute", "*", PermissionLevel.ALLOW),
        ])

    def test_default_approval_gate_remains_active(self):
        setup_default_permissions(self.permissions)
        allowed, reason = self.validate({"command": "echo hello"})
        self.assertFalse(allowed)
        self.assertIn("Permission required", reason)

    def test_plan_mode_remains_read_only(self):
        self.allow_execution()
        allowed, reason = self.validate({"command": "echo hello"}, AgentMode.PLAN)
        self.assertFalse(allowed)
        self.assertIn("PLAN mode", reason)

    def test_allowed_command_reaches_real_sandbox(self):
        self.allow_execution()
        with patch.object(self.sandbox, "validate_command", wraps=self.sandbox.validate_command) as validate:
            self.assertEqual(self.validate({"command": "echo hello"}), (True, "OK"))
        validate.assert_called_once_with("echo hello")

    def test_required_schema_field_remains_checked(self):
        self.allow_execution()
        allowed, reason = self.validate({})
        self.assertFalse(allowed)
        self.assertIn("Missing required field: command", reason)


class FetchUrlTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.requests = []
        self.checker = self.enterContext(patch.object(builtins, "blocked_reason", wraps=blocked_reason))
        self.enterContext(patch(
            "app.utils.ssrf.socket.getaddrinfo",
            return_value=[(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("8.8.8.8", 443))],
        ))
        self.enterContext(patch.object(
            httpx.AsyncHTTPTransport, "handle_async_request",
            side_effect=AssertionError("Real HTTP transport is forbidden in this test"),
        ))

    def client(self, handler):
        def dispatch(request):
            self.requests.append(str(request.url))
            self.assertEqual(self.checker.call_args, call(str(request.url)))
            return handler(request)

        client = httpx.AsyncClient(transport=httpx.MockTransport(dispatch))
        factory = self.enterContext(patch.object(builtins.httpx, "AsyncClient", return_value=client))
        return factory

    async def test_success_keeps_output_limit_and_timeout(self):
        factory = self.client(lambda request: httpx.Response(200, text="x" * 6000))
        result = await builtins.fetch_url("https://example.com/")
        self.assertEqual(result, "URL: https://example.com/\nStatus: 200\n\n" + "x" * 5000)
        factory.assert_called_once_with(timeout=15, follow_redirects=False)

    async def test_each_normal_redirect_is_rechecked(self):
        def response(request):
            if request.url.path == "/start":
                return httpx.Response(302, headers={"location": "/next"})
            if request.url.path == "/next":
                return httpx.Response(307, headers={"location": "https://www.example.com/final"})
            return httpx.Response(200, text="finished")

        self.client(response)
        result = await builtins.fetch_url("https://example.com/start")
        urls = ["https://example.com/start", "https://example.com/next", "https://www.example.com/final"]
        self.assertEqual(self.requests, urls)
        self.assertEqual(self.checker.call_args_list, [call(url) for url in urls])
        self.assertTrue(result.endswith("finished"))

    async def test_existing_local_policy_stops_before_client_creation(self):
        with patch.object(builtins.httpx, "AsyncClient") as factory:
            result = await builtins.fetch_url("http://127.0.0.1/")
        factory.assert_not_called()
        self.assertIn("not reachable externally", result)

    async def test_redirect_policy_denial_prevents_next_request(self):
        self.checker.side_effect = [None, "mock policy denial"]
        self.client(lambda request: httpx.Response(302, headers={"location": "/next"}))
        result = await builtins.fetch_url("https://example.com/start")
        self.assertEqual(self.requests, ["https://example.com/start"])
        self.assertIn("redirect blocked: mock policy denial", result)

    async def test_redirect_limit_is_bounded(self):
        self.client(lambda request: httpx.Response(302, headers={"location": "/next"}))
        result = await builtins.fetch_url("https://example.com/start")
        self.assertEqual(len(self.requests), 6)
        self.assertIn("too many redirects", result)

    async def test_timeout_is_reported(self):
        def response(request):
            raise httpx.ReadTimeout("mock timeout", request=request)

        self.client(response)
        result = await builtins.fetch_url("https://example.com/")
        self.assertIn("request timed out (15s timeout)", result)

    async def test_http_error_is_reported(self):
        self.client(lambda request: httpx.Response(404))
        result = await builtins.fetch_url("https://example.com/")
        self.assertTrue(result.startswith("Error fetching URL:"))
        self.assertIn("404", result)

    async def test_missing_redirect_location_is_reported(self):
        self.client(lambda request: httpx.Response(302))
        result = await builtins.fetch_url("https://example.com/")
        self.assertEqual(len(self.requests), 1)
        self.assertTrue(result.startswith("Error fetching URL:"))


if __name__ == "__main__":
    unittest.main()
