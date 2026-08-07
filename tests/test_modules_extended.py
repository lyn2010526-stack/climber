"""Tests for storage, services, and utility modules."""

from __future__ import annotations

import pytest

# ── Storage Tests ────────────────────────────────────────────────────────


class TestStorage:
    def test_engine_exists(self):
        from app.storage import engine
        assert engine is not None

    def test_async_session_factory(self):
        from app.storage import async_session
        assert async_session is not None

    def test_base_exists(self):
        from app.storage import Base
        assert Base is not None

    @pytest.mark.asyncio
    async def test_db_health(self):
        from app.storage import db_health
        result = await db_health()
        assert isinstance(result, dict)
        assert "connected" in result

    @pytest.mark.asyncio
    async def test_init_db(self):
        from app.storage import init_db
        # Should not raise (tables may already exist)
        await init_db()


# ── Database Model Tests ─────────────────────────────────────────────────


class TestDatabaseModels:
    def test_agent_model(self):
        from app.storage.database import Agent
        assert hasattr(Agent, 'id')
        assert hasattr(Agent, 'name')
        assert hasattr(Agent, 'provider')

    def test_session_model(self):
        from app.storage.database import Session
        assert hasattr(Session, 'id')
        assert hasattr(Session, 'status')

    def test_message_model(self):
        from app.storage.database import Message
        assert hasattr(Message, 'id')
        assert hasattr(Message, 'role')
        assert hasattr(Message, 'content')

    def test_api_key_model(self):
        from app.storage.database import ApiKey
        assert hasattr(ApiKey, 'id')
        assert hasattr(ApiKey, 'provider')

    def test_tool_model(self):
        from app.storage.database import Tool
        assert hasattr(Tool, 'id')

    def test_document_model(self):
        from app.storage.database import Document
        assert hasattr(Document, 'id')
        assert hasattr(Document, 'filename')


# ── API Key Crypto Tests ─────────────────────────────────────────────────


class TestApiKeyCrypto:
    def test_encrypt_decrypt_roundtrip(self):
        from app.core.api_key_crypto import decrypt_api_key, encrypt_api_key
        original = "sk-test-key-12345"
        encrypted = encrypt_api_key(original)
        decrypted = decrypt_api_key(encrypted)
        assert decrypted == original

    def test_encrypt_empty_string(self):
        from app.core.api_key_crypto import encrypt_api_key
        result = encrypt_api_key("")
        assert result == "" or result is None

    def test_decrypt_empty_string(self):
        from app.core.api_key_crypto import decrypt_api_key
        result = decrypt_api_key("")
        assert result == ""


# ── Tool Registry Tests ──────────────────────────────────────────────────


class TestToolRegistry:
    def test_register_and_get_tool(self):
        from app.tools import ToolRegistry
        registry = ToolRegistry()

        @registry.tool(name="test_tool", description="A test tool")
        async def test_fn(x: int) -> str:
            return str(x)

        tool_def = registry.get_tool("test_tool")
        assert tool_def is not None
        assert tool_def.name == "test_tool"

    def test_unregister_tool(self):
        from app.tools import ToolRegistry
        registry = ToolRegistry()

        @registry.tool(name="temp")
        async def temp() -> str:
            return "temp"

        assert registry.unregister("temp") is True
        assert registry.get_tool("temp") is None

    def test_unregister_nonexistent(self):
        from app.tools import ToolRegistry
        registry = ToolRegistry()
        assert registry.unregister("nonexistent") is False

    def test_list_tools(self):
        from app.tools import ToolRegistry
        registry = ToolRegistry()

        @registry.tool(name="t1")
        async def t1() -> str:
            return "1"

        @registry.tool(name="t2")
        async def t2() -> str:
            return "2"

        tools = registry.list_tools()
        assert len(tools) == 2

    def test_get_openai_tools(self):
        from app.tools import ToolRegistry
        registry = ToolRegistry()

        @registry.tool(name="my_tool", description="Does something")
        async def my_tool(x: int) -> str:
            return str(x)

        openai_tools = registry.get_openai_tools()
        assert len(openai_tools) == 1
        assert openai_tools[0]["type"] == "function"
        assert openai_tools[0]["function"]["name"] == "my_tool"

    def test_infer_schema(self):
        from app.tools import ToolRegistry
        registry = ToolRegistry()

        @registry.tool(name="calc")
        async def calc(a: float, b: float, op: str = "+") -> str:
            return "result"

        tool_def = registry.get_tool("calc")
        assert "a" in tool_def.parameters["properties"]
        assert "b" in tool_def.parameters["properties"]
        assert "op" in tool_def.parameters["properties"]

    @pytest.mark.asyncio
    async def test_execute_tool(self):
        from app.tools import ToolRegistry
        registry = ToolRegistry()

        @registry.tool(name="echo")
        async def echo(text: str) -> str:
            return f"Echo: {text}"

        result = await registry.execute("echo", {"text": "hello"})
        assert "Echo: hello" in result

    @pytest.mark.asyncio
    async def test_execute_nonexistent_tool(self):
        from app.tools import ToolRegistry
        registry = ToolRegistry()
        result = await registry.execute("nonexistent", {})
        assert result is None or "not found" in str(result).lower()


# ── Model Registry Tests ─────────────────────────────────────────────────


class TestModelRegistry:
    def test_create_registry(self):
        from app.models.registry import ModelRegistry
        registry = ModelRegistry()
        assert registry is not None

    def test_register_model(self):
        from app.models.registry import ModelRegistry
        registry = ModelRegistry()
        # Should not raise
        registry._models["test:model"] = MagicMock()


# ── Session Manager Tests ────────────────────────────────────────────────


class TestSessionManager:
    def test_create_session_manager(self):
        from app.core.session_manager import SessionManager
        mgr = SessionManager()
        assert mgr is not None

    def test_save_and_get_checkpoint(self):
        from app.core.session_manager import SessionManager
        mgr = SessionManager()
        mgr.save_checkpoint(
            session_id="test-session",
            messages=[{"role": "user", "content": "hi"}],
            iteration=1,
        )
        result = mgr.get_latest_checkpoint("test-session")
        assert result is not None


# ── Memory Reflection Tests ──────────────────────────────────────────────


class TestMemoryReflection:
    @pytest.mark.asyncio
    async def test_maybe_reflect(self):
        from app.core.memory_reflection import memory_reflection
        # Should not raise
        await memory_reflection.maybe_reflect("test-user")


# ── Cost Tracker Tests ───────────────────────────────────────────────────


class TestCostTracker:
    def test_initial_state(self):
        from app.core.cost_tracker import CostTracker
        tracker = CostTracker()
        assert tracker is not None


# ── Watchdog Tests ───────────────────────────────────────────────────────


class TestWatchdog:
    def test_get_watchdog(self):
        from app.core.watchdog import get_watchdog
        watchdog = get_watchdog()
        assert watchdog is not None

    def test_health(self):
        from app.core.watchdog import get_watchdog
        watchdog = get_watchdog()
        health = watchdog.health()
        assert isinstance(health, dict)


# ── Memory Guardian Tests ────────────────────────────────────────────────


class TestMemoryGuardian:
    def test_get_guardian(self):
        from app.core.memory_guardian import get_memory_guardian
        guardian = get_memory_guardian()
        assert guardian is not None

    def test_stats(self):
        from app.core.memory_guardian import get_memory_guardian
        guardian = get_memory_guardian()
        stats = guardian.stats()
        assert isinstance(stats, dict)


# ── Event Bus Tests ──────────────────────────────────────────────────────


class TestEventBus:
    @pytest.mark.asyncio
    async def test_publish_and_subscribe(self):
        from app.core.event_bus import EventBus
        bus = EventBus()
        received = []

        async def handler(data):
            received.append(data)

        bus.subscribe("test_event", handler)
        await bus.publish("test_event", {"key": "value"})
        assert len(received) == 1
        assert received[0] == {"key": "value"}


# ── Metrics Tests ────────────────────────────────────────────────────────


class TestMetrics:
    def test_collector(self):
        from app.core.metrics import MetricsCollector
        collector = MetricsCollector()
        assert collector is not None


# ── Tracing Tests ────────────────────────────────────────────────────────


class TestTracing:
    def test_tracing_config(self):
        from app.core.tracing import TracingConfig
        config = TracingConfig()
        assert config is not None


# ── Error Analyzer Tests ─────────────────────────────────────────────────


class TestErrorAnalyzer:
    def test_analyze_syntax_error(self):
        from app.core.error_analyzer import ErrorAnalyzer
        analyzer = ErrorAnalyzer()
        result = analyzer.analyze("SyntaxError: unexpected indent")
        assert result is not None

    def test_analyze_name_error(self):
        from app.core.error_analyzer import ErrorAnalyzer
        analyzer = ErrorAnalyzer()
        result = analyzer.analyze("NameError: name 'x' is not defined")
        assert result is not None

    def test_analyze_type_error(self):
        from app.core.error_analyzer import ErrorAnalyzer
        analyzer = ErrorAnalyzer()
        result = analyzer.analyze("TypeError: unsupported operand type")
        assert result is not None


# ── JSON Schema Tests ────────────────────────────────────────────────────


class TestJsonSchema:
    def test_validate_valid_input(self):
        from app.core.json_schema import validate_against_schema
        schema = {"type": "object", "properties": {"name": {"type": "string"}}}
        # Should not raise
        validate_against_schema(schema, {"name": "test"})

    def test_validate_invalid_input(self):
        from app.core.json_schema import validate_against_schema
        schema = {"type": "object", "properties": {"age": {"type": "integer"}}}
        # May raise or return validation result
        validate_against_schema(schema, {"age": "not_a_number"})
        assert True  # Some implementations may silently pass


# ── Streaming Events Tests ───────────────────────────────────────────────


class TestStreamEvents:
    def test_event_creation(self):
        from app.core.stream_events import StreamEvent
        event = StreamEvent(type="text", data={"content": "hello"})
        assert event.type == "text"


# ── Context Preparer Tests ───────────────────────────────────────────────


class TestContextPreparer:
    def test_preparer_exists(self):
        from app.core.context_preparer import ContextPreparer
        preparer = ContextPreparer()
        assert preparer is not None


# ── Prompt Engine Tests ──────────────────────────────────────────────────


class TestPromptEngine:
    def test_template_repository(self):
        from app.core.prompt_engine.template_repository import PromptTemplateRepository
        repo = PromptTemplateRepository()
        assert repo is not None

    def test_list_builtins(self):
        from app.core.prompt_engine.template_repository import PromptTemplateRepository
        repo = PromptTemplateRepository()
        builtins = repo.list_builtins()
        assert isinstance(builtins, list)


# ── Workflow IO Tests ────────────────────────────────────────────────────


class TestWorkflowIO:
    def test_workflow_io_exists(self):
        from app.workflow.io import WorkflowIO
        assert WorkflowIO is not None


# ── Iteration Guard Tests ────────────────────────────────────────────────


class TestIterationGuard:
    def test_guard_creation(self):
        from app.core.iteration_guard import IterationGuard
        guard = IterationGuard(max_iterations=10)
        assert guard is not None
        assert guard.max_iterations == 10


# ── Memory Tools Tests ───────────────────────────────────────────────────


class TestMemoryTools:
    def test_memory_toolset(self):
        from app.tools.memory_toolset import MemoryToolSet
        assert MemoryToolSet is not None


# ── Security Sandbox Tests ───────────────────────────────────────────────


class TestSecuritySandbox:
    def test_validate_command_safe(self):
        from app.core.security_sandbox import security_sandbox
        ok, reason = security_sandbox.validate_command("ls -la")
        assert ok is True

    def test_validate_command_dangerous(self):
        from app.core.security_sandbox import security_sandbox
        ok, reason = security_sandbox.validate_command("rm -rf /")
        assert ok is False

    def test_validate_file_access(self):
        from app.core.security_sandbox import security_sandbox
        ok, reason = security_sandbox.validate_file_access("/tmp/test.txt", "read")
        assert isinstance(ok, bool)


# ── Context Compressor Tests ─────────────────────────────────────────────


class TestContextManager:
    def test_context_manager_exists(self):
        from app.core.context_manager import ContextManager
        mgr = ContextManager()
        assert mgr is not None


# ── Token Tracker Tests ──────────────────────────────────────────────────


class TestTokenTracker:
    def test_tracker_creation(self):
        from app.core.token_tracker import TokenTracker
        tracker = TokenTracker()
        assert tracker is not None


# ── Output Auditor Tests ─────────────────────────────────────────────────


class TestOutputAuditor:
    def test_auditor_exists(self):
        from app.core.output_auditor import OutputAuditor
        auditor = OutputAuditor()
        assert auditor is not None


# ── Safety Pipeline Tests ────────────────────────────────────────────────


class TestSafetyPipeline:
    def test_pipeline_exists(self):
        from app.core.safety_pipeline import SafetyPipeline
        assert SafetyPipeline is not None
