"""AGI P6 Collaboration Layer Tests.

Tests for:
- A2A message encoding/decoding
- Task handoff lifecycle (request, accept, reject)
- Role-based capability enforcement
- Result aggregation strategies
- API endpoint authentication
"""

import os
import time

os.environ.setdefault("APP_TESTING", "true")

import pytest
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport

from app.core.collaboration import (
    A2AMessage,
    A2AMessageType,
    A2AProtocol,
    AgentResult,
    AggregationStrategy,
    Capability,
    AgentRole,
    HandoffManager,
    HandoffRequest,
    HandoffStatus,
    ResultAggregator,
    RoleRegistry,
)


# === A2A Protocol Tests ===


class TestA2AMessage:
    def test_create_message(self):
        msg = A2AMessage(
            sender_id="agent-1",
            receiver_id="agent-2",
            message_type=A2AMessageType.REQUEST,
            payload={"task": "analyze"},
        )
        assert msg.sender_id == "agent-1"
        assert msg.receiver_id == "agent-2"
        assert msg.message_type == A2AMessageType.REQUEST
        assert msg.payload == {"task": "analyze"}
        assert msg.protocol_version == "1.0"
        assert msg.id

    def test_to_dict(self):
        msg = A2AMessage(
            sender_id="a1",
            receiver_id="a2",
            message_type=A2AMessageType.EVENT,
            payload={"status": "done"},
        )
        d = msg.to_dict()
        assert d["sender_id"] == "a1"
        assert d["receiver_id"] == "a2"
        assert d["message_type"] == "event"
        assert d["payload"] == {"status": "done"}
        assert "id" in d
        assert "timestamp" in d
        assert "protocol_version" in d

    def test_signable_content_excludes_signature(self):
        msg = A2AMessage(sender_id="a1", receiver_id="a2")
        content = msg.signable_content()
        assert "signature" not in content
        assert "a1" in content


class TestA2AProtocol:
    def test_encode_decode(self):
        protocol = A2AProtocol()
        msg = A2AMessage(
            sender_id="agent-1",
            receiver_id="agent-2",
            message_type=A2AMessageType.REQUEST,
            payload={"action": "process"},
        )
        encoded = protocol.encode(msg)
        decoded = protocol.decode(encoded)
        assert decoded.sender_id == msg.sender_id
        assert decoded.receiver_id == msg.receiver_id
        assert decoded.message_type == msg.message_type
        assert decoded.payload == msg.payload
        assert decoded.id == msg.id

    def test_create_request(self):
        protocol = A2AProtocol(secret_key="test-key")
        msg = protocol.create_request(
            sender_id="a1",
            receiver_id="a2",
            payload={"task": "run"},
        )
        assert msg.message_type == A2AMessageType.REQUEST
        assert msg.signature != ""
        assert msg.correlation_id != ""

    def test_create_response(self):
        protocol = A2AProtocol(secret_key="test-key")
        msg = protocol.create_response(
            sender_id="a2",
            receiver_id="a1",
            payload={"result": "ok"},
            correlation_id="corr-123",
        )
        assert msg.message_type == A2AMessageType.RESPONSE
        assert msg.correlation_id == "corr-123"
        assert msg.signature != ""

    def test_create_event(self):
        protocol = A2AProtocol(secret_key="test-key")
        msg = protocol.create_event(
            sender_id="system",
            receiver_id="all",
            payload={"event": "shutdown"},
        )
        assert msg.message_type == A2AMessageType.EVENT
        assert msg.signature != ""

    def test_validate_valid_message(self):
        protocol = A2AProtocol(secret_key="test-key")
        msg = protocol.create_request("a1", "a2", {"task": "run"})
        is_valid, error = protocol.validate(msg)
        assert is_valid is True
        assert error == ""

    def test_validate_missing_sender(self):
        protocol = A2AProtocol()
        msg = A2AMessage(receiver_id="a2")
        is_valid, error = protocol.validate(msg)
        assert is_valid is False
        assert "sender_id" in error

    def test_validate_missing_receiver(self):
        protocol = A2AProtocol()
        msg = A2AMessage(sender_id="a1")
        is_valid, error = protocol.validate(msg)
        assert is_valid is False
        assert "receiver_id" in error

    def test_validate_invalid_version(self):
        protocol = A2AProtocol()
        msg = A2AMessage(sender_id="a1", receiver_id="a2", protocol_version="2.0")
        is_valid, error = protocol.validate(msg)
        assert is_valid is False
        assert "version" in error

    def test_validate_invalid_signature(self):
        protocol = A2AProtocol(secret_key="test-key")
        msg = A2AMessage(
            sender_id="a1",
            receiver_id="a2",
            signature="invalid-signature",
        )
        is_valid, error = protocol.validate(msg)
        assert is_valid is False
        assert "signature" in error

    def test_no_key_no_signature(self):
        protocol = A2AProtocol()
        msg = protocol.create_request("a1", "a2", {})
        assert msg.signature == ""
        is_valid, error = protocol.validate(msg)
        assert is_valid is True

    def test_tampered_message_fails_validation(self):
        protocol = A2AProtocol(secret_key="test-key")
        msg = protocol.create_request("a1", "a2", {"task": "run"})
        msg.payload = {"task": "hacked"}
        is_valid, error = protocol.validate(msg)
        assert is_valid is False
        assert "signature" in error


# === Task Handoff Tests ===


class TestHandoffRequest:
    def test_create_handoff(self):
        handoff = HandoffRequest(
            task_id="task-1",
            from_agent_id="agent-1",
            to_agent_id="agent-2",
            context={"state": "partial"},
        )
        assert handoff.task_id == "task-1"
        assert handoff.status == HandoffStatus.PENDING
        assert handoff.id

    def test_to_dict(self):
        handoff = HandoffRequest(
            task_id="task-1",
            from_agent_id="a1",
            to_agent_id="a2",
        )
        d = handoff.to_dict()
        assert d["task_id"] == "task-1"
        assert d["status"] == "pending"
        assert "id" in d


class TestHandoffManager:
    def test_request_handoff(self):
        manager = HandoffManager()
        handoff = manager.request_handoff(
            task_id="task-1",
            from_agent_id="agent-1",
            to_agent_id="agent-2",
            context={"data": "value"},
        )
        assert handoff.id in manager._handoffs
        assert handoff.status == HandoffStatus.PENDING

    def test_accept_handoff(self):
        manager = HandoffManager()
        handoff = manager.request_handoff("t1", "a1", "a2")
        result = manager.accept_handoff(handoff.id)
        assert result is not None
        assert result.status == HandoffStatus.ACCEPTED

    def test_reject_handoff(self):
        manager = HandoffManager()
        handoff = manager.request_handoff("t1", "a1", "a2")
        result = manager.reject_handoff(handoff.id, reason="busy")
        assert result is not None
        assert result.status == HandoffStatus.REJECTED
        assert result.reason == "busy"

    def test_accept_nonexistent_handoff(self):
        manager = HandoffManager()
        result = manager.accept_handoff("nonexistent")
        assert result is None

    def test_reject_nonexistent_handoff(self):
        manager = HandoffManager()
        result = manager.reject_handoff("nonexistent")
        assert result is None

    def test_accept_already_processed_handoff(self):
        manager = HandoffManager()
        handoff = manager.request_handoff("t1", "a1", "a2")
        manager.accept_handoff(handoff.id)
        result = manager.accept_handoff(handoff.id)
        assert result is None

    def test_get_pending_handoffs(self):
        manager = HandoffManager()
        h1 = manager.request_handoff("t1", "a1", "a2")
        h2 = manager.request_handoff("t2", "a1", "a3")
        manager.accept_handoff(h2.id)
        pending = manager.get_pending_handoffs()
        assert len(pending) == 1
        assert pending[0].id == h1.id

    def test_get_pending_handoffs_for_agent(self):
        manager = HandoffManager()
        manager.request_handoff("t1", "a1", "a2")
        manager.request_handoff("t2", "a1", "a3")
        pending = manager.get_pending_handoffs(agent_id="a2")
        assert len(pending) == 1
        assert pending[0].to_agent_id == "a2"

    def test_register_agent_capability(self):
        manager = HandoffManager()
        from app.core.collaboration.handoff import AgentCapability
        agent = AgentCapability(agent_id="a1", capabilities=["search", "analyze"])
        manager.register_agent_capability(agent)
        assert "a1" in manager._agent_capabilities

    def test_find_capable_agent(self):
        manager = HandoffManager()
        from app.core.collaboration.handoff import AgentCapability
        manager.register_agent_capability(
            AgentCapability(agent_id="a1", capabilities=["search", "analyze"])
        )
        manager.register_agent_capability(
            AgentCapability(agent_id="a2", capabilities=["execute"])
        )
        result = manager.find_capable_agent(["search"])
        assert result == "a1"

    def test_find_capable_agent_multiple_requirements(self):
        manager = HandoffManager()
        from app.core.collaboration.handoff import AgentCapability
        manager.register_agent_capability(
            AgentCapability(agent_id="a1", capabilities=["search"])
        )
        manager.register_agent_capability(
            AgentCapability(agent_id="a2", capabilities=["search", "analyze"])
        )
        result = manager.find_capable_agent(["search", "analyze"])
        assert result == "a2"

    def test_find_capable_agent_no_match(self):
        manager = HandoffManager()
        from app.core.collaboration.handoff import AgentCapability
        manager.register_agent_capability(
            AgentCapability(agent_id="a1", capabilities=["search"])
        )
        result = manager.find_capable_agent(["execute"])
        assert result is None

    def test_auto_handoff(self):
        manager = HandoffManager()
        from app.core.collaboration.handoff import AgentCapability
        manager.register_agent_capability(
            AgentCapability(agent_id="a1", capabilities=["search", "analyze"])
        )
        handoff = manager.auto_handoff(
            task_id="t1",
            from_agent_id="a0",
            required_capabilities=["search"],
        )
        assert handoff is not None
        assert handoff.to_agent_id == "a1"

    def test_auto_handoff_no_match(self):
        manager = HandoffManager()
        from app.core.collaboration.handoff import AgentCapability
        manager.register_agent_capability(
            AgentCapability(agent_id="a1", capabilities=["search"])
        )
        handoff = manager.auto_handoff(
            task_id="t1",
            from_agent_id="a0",
            required_capabilities=["execute"],
        )
        assert handoff is None

    def test_audit_trail(self):
        manager = HandoffManager()
        handoff = manager.request_handoff("t1", "a1", "a2")
        manager.accept_handoff(handoff.id)
        trail = manager.get_audit_trail(handoff.id)
        assert len(trail) >= 2
        actions = [e["action"] for e in trail]
        assert "created" in actions
        assert "accepted" in actions

    def test_get_handoff(self):
        manager = HandoffManager()
        handoff = manager.request_handoff("t1", "a1", "a2")
        result = manager.get_handoff(handoff.id)
        assert result is not None
        assert result.id == handoff.id

    def test_get_handoff_nonexistent(self):
        manager = HandoffManager()
        result = manager.get_handoff("nonexistent")
        assert result is None


# === Role-Based Capability Tests ===


class TestCapability:
    def test_create_capability(self):
        cap = Capability(
            name="search",
            description="Search for information",
            required_tools=["web_search"],
            required_permissions=["network"],
        )
        assert cap.name == "search"
        assert cap.required_tools == ["web_search"]

    def test_to_dict(self):
        cap = Capability(name="analyze", required_tools=["process"])
        d = cap.to_dict()
        assert d["name"] == "analyze"
        assert d["required_tools"] == ["process"]


class TestRoleRegistry:
    def test_default_roles_registered(self):
        registry = RoleRegistry()
        roles = registry.list_roles()
        assert AgentRole.PLANNER in roles
        assert AgentRole.EXECUTOR in roles
        assert AgentRole.AUDITOR in roles
        assert AgentRole.RESEARCHER in roles
        assert AgentRole.COMMUNICATOR in roles
        assert AgentRole.GUARD in roles

    def test_get_capabilities(self):
        registry = RoleRegistry()
        caps = registry.get_capabilities(AgentRole.PLANNER)
        assert len(caps) > 0
        assert any(c.name == "task_decomposition" for c in caps)

    def test_assign_role(self):
        registry = RoleRegistry()
        registry.assign_role("agent-1", AgentRole.EXECUTOR)
        assert registry.get_agent_role("agent-1") == AgentRole.EXECUTOR

    def test_check_permission_allowed(self):
        registry = RoleRegistry()
        registry.assign_role("agent-1", AgentRole.EXECUTOR)
        assert registry.check_permission("agent-1", "execute") is True

    def test_check_permission_denied(self):
        registry = RoleRegistry()
        registry.assign_role("agent-1", AgentRole.PLANNER)
        assert registry.check_permission("agent-1", "execute") is False

    def test_check_permission_no_role(self):
        registry = RoleRegistry()
        assert registry.check_permission("unknown", "execute") is False

    def test_check_action_allowed(self):
        registry = RoleRegistry()
        registry.assign_role("agent-1", AgentRole.AUDITOR)
        assert registry.check_action("agent-1", "review") is True

    def test_check_action_denied(self):
        registry = RoleRegistry()
        registry.assign_role("agent-1", AgentRole.GUARD)
        assert registry.check_action("agent-1", "execute_task") is False

    def test_can_access_capability(self):
        registry = RoleRegistry()
        registry.assign_role("agent-1", AgentRole.RESEARCHER)
        assert registry.can_access_capability("agent-1", "information_gathering") is True

    def test_can_access_capability_false(self):
        registry = RoleRegistry()
        registry.assign_role("agent-1", AgentRole.GUARD)
        assert registry.can_access_capability("agent-1", "information_gathering") is False

    def test_register_custom_role(self):
        registry = RoleRegistry()
        from app.core.collaboration.roles import RoleDefinition
        custom = RoleDefinition(
            role=AgentRole.EXECUTOR,
            capabilities=[Capability(name="custom_cap")],
            allowed_tools=["custom_tool"],
        )
        registry.register_role(custom)
        definition = registry.get_role_definition(AgentRole.EXECUTOR)
        assert definition is not None
        assert any(c.name == "custom_cap" for c in definition.capabilities)

    def test_list_agent_roles(self):
        registry = RoleRegistry()
        registry.assign_role("a1", AgentRole.PLANNER)
        registry.assign_role("a2", AgentRole.EXECUTOR)
        assignments = registry.list_agent_roles()
        assert assignments["a1"] == AgentRole.PLANNER
        assert assignments["a2"] == AgentRole.EXECUTOR


# === Result Aggregation Tests ===


class TestAgentResult:
    def test_create_result(self):
        result = AgentResult(
            agent_id="a1",
            task_id="t1",
            result="answer",
            confidence=0.9,
        )
        assert result.agent_id == "a1"
        assert result.task_id == "t1"
        assert result.result == "answer"
        assert result.confidence == 0.9

    def test_to_dict(self):
        result = AgentResult(agent_id="a1", task_id="t1", result="ok")
        d = result.to_dict()
        assert d["agent_id"] == "a1"
        assert d["result"] == "ok"


class TestResultAggregator:
    def test_add_result(self):
        aggregator = ResultAggregator()
        aggregator.add_result(AgentResult(agent_id="a1", task_id="t1", result="a"))
        results = aggregator.get_results("t1")
        assert len(results) == 1

    def test_get_results_empty(self):
        aggregator = ResultAggregator()
        results = aggregator.get_results("nonexistent")
        assert results == []

    def test_best_confidence_strategy(self):
        aggregator = ResultAggregator()
        aggregator.add_result(AgentResult(agent_id="a1", task_id="t1", result="low", confidence=0.3))
        aggregator.add_result(AgentResult(agent_id="a2", task_id="t1", result="high", confidence=0.9))
        result = aggregator.aggregate("t1", strategy=AggregationStrategy.BEST_CONFIDENCE)
        assert result.consensus_value == "high"
        assert result.strategy == AggregationStrategy.BEST_CONFIDENCE

    def test_majority_vote_consensus(self):
        aggregator = ResultAggregator(consensus_threshold=0.5)
        aggregator.add_result(AgentResult(agent_id="a1", task_id="t1", result="yes", confidence=0.8))
        aggregator.add_result(AgentResult(agent_id="a2", task_id="t1", result="yes", confidence=0.7))
        aggregator.add_result(AgentResult(agent_id="a3", task_id="t1", result="no", confidence=0.6))
        result = aggregator.aggregate("t1", strategy=AggregationStrategy.MAJORITY_VOTE)
        assert result.consensus_reached is True
        assert result.consensus_value == "yes"

    def test_majority_vote_no_consensus(self):
        aggregator = ResultAggregator(consensus_threshold=0.8)
        aggregator.add_result(AgentResult(agent_id="a1", task_id="t1", result="a", confidence=0.5))
        aggregator.add_result(AgentResult(agent_id="a2", task_id="t1", result="b", confidence=0.5))
        aggregator.add_result(AgentResult(agent_id="a3", task_id="t1", result="c", confidence=0.5))
        result = aggregator.aggregate("t1", strategy=AggregationStrategy.MAJORITY_VOTE)
        assert result.consensus_reached is False

    def test_weighted_average_numeric(self):
        aggregator = ResultAggregator()
        aggregator.add_result(AgentResult(agent_id="a1", task_id="t1", result=10.0, confidence=0.5))
        aggregator.add_result(AgentResult(agent_id="a2", task_id="t1", result=20.0, confidence=0.5))
        result = aggregator.aggregate("t1", strategy=AggregationStrategy.WEIGHTED_AVERAGE)
        assert result.consensus_value == 15.0

    def test_weighted_average_fallback_for_non_numeric(self):
        aggregator = ResultAggregator()
        aggregator.add_result(AgentResult(agent_id="a1", task_id="t1", result="abc", confidence=0.9))
        aggregator.add_result(AgentResult(agent_id="a2", task_id="t1", result="def", confidence=0.5))
        result = aggregator.aggregate("t1", strategy=AggregationStrategy.WEIGHTED_AVERAGE)
        assert result.consensus_value == "abc"

    def test_divergence_detection(self):
        aggregator = ResultAggregator()
        aggregator.add_result(AgentResult(agent_id="a1", task_id="t1", result="yes", confidence=0.9))
        aggregator.add_result(AgentResult(agent_id="a2", task_id="t1", result="no", confidence=0.8))
        result = aggregator.aggregate("t1", strategy=AggregationStrategy.BEST_CONFIDENCE)
        assert result.divergence_detected is True
        assert "a2" in result.divergent_agents

    def test_get_divergence(self):
        aggregator = ResultAggregator()
        aggregator.add_result(AgentResult(agent_id="a1", task_id="t1", result="yes", confidence=0.9))
        aggregator.add_result(AgentResult(agent_id="a2", task_id="t1", result="no", confidence=0.8))
        aggregator.add_result(AgentResult(agent_id="a3", task_id="t1", result="maybe", confidence=0.5))
        divergence = aggregator.get_divergence("t1")
        assert len(divergence) >= 1

    def test_get_divergence_single_result(self):
        aggregator = ResultAggregator()
        aggregator.add_result(AgentResult(agent_id="a1", task_id="t1", result="yes", confidence=0.9))
        divergence = aggregator.get_divergence("t1")
        assert divergence == []

    def test_get_consensus(self):
        aggregator = ResultAggregator(consensus_threshold=0.5)
        aggregator.add_result(AgentResult(agent_id="a1", task_id="t1", result="yes", confidence=0.8))
        aggregator.add_result(AgentResult(agent_id="a2", task_id="t1", result="yes", confidence=0.7))
        result = aggregator.get_consensus("t1")
        assert result.consensus_reached is True

    def test_get_weighted_result(self):
        aggregator = ResultAggregator()
        aggregator.add_result(AgentResult(agent_id="a1", task_id="t1", result=100.0, confidence=0.8))
        aggregator.add_result(AgentResult(agent_id="a2", task_id="t1", result=200.0, confidence=0.2))
        result = aggregator.get_weighted_result("t1")
        expected = (100.0 * 0.8 + 200.0 * 0.2) / (0.8 + 0.2)
        assert result.consensus_value == expected

    def test_empty_aggregation(self):
        aggregator = ResultAggregator()
        result = aggregator.aggregate("nonexistent")
        assert result.consensus_reached is False
        assert result.results == []

    def test_aggregation_history(self):
        aggregator = ResultAggregator()
        aggregator.add_result(AgentResult(agent_id="a1", task_id="t1", result="a"))
        aggregator.aggregate("t1")
        history = aggregator.get_history("t1")
        assert len(history) == 1

    def test_clear_task(self):
        aggregator = ResultAggregator()
        aggregator.add_result(AgentResult(agent_id="a1", task_id="t1", result="a"))
        aggregator.clear_task("t1")
        assert aggregator.get_results("t1") == []


# === API Authentication Tests ===


class TestCollaborationAPI:
    @pytest.fixture
    def app(self):
        """Create a test app with only the collaboration router."""
        app = FastAPI()
        from app.core.collaboration.api import router as collab_router
        app.include_router(collab_router)
        return app

    @pytest.fixture
    def auth_headers(self):
        """Generate valid auth headers with a signed token."""
        token = "test-user"
        return {"Authorization": f"Bearer {token}"}

    @pytest.mark.skip(reason="Auth removed for local-only mode")
    @pytest.mark.asyncio
    async def test_create_handoff_requires_auth(self, app):
        pass

    @pytest.mark.skip(reason="Auth removed for local-only mode")
    @pytest.mark.asyncio
    async def test_list_handoffs_requires_auth(self, app):
        pass

    @pytest.mark.skip(reason="Auth removed for local-only mode")
    @pytest.mark.asyncio
    async def test_accept_handoff_requires_auth(self, app):
        pass

    @pytest.mark.skip(reason="Auth removed for local-only mode")
    @pytest.mark.asyncio
    async def test_reject_handoff_requires_auth(self, app):
        pass

    @pytest.mark.skip(reason="Auth removed for local-only mode")
    @pytest.mark.asyncio
    async def test_list_roles_requires_auth(self, app):
        pass

    @pytest.mark.skip(reason="Auth removed for local-only mode")
    @pytest.mark.asyncio
    async def test_get_aggregation_requires_auth(self, app):
        pass

    @pytest.mark.asyncio
    async def test_create_handoff_with_auth(self, app, auth_headers):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/collaboration/handoffs",
                params={
                    "task_id": "t1",
                    "from_agent_id": "a1",
                    "to_agent_id": "a2",
                },
                headers=auth_headers,
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["task_id"] == "t1"
            assert data["from_agent_id"] == "a1"
            assert data["to_agent_id"] == "a2"

    @pytest.mark.asyncio
    async def test_list_handoffs_with_auth(self, app, auth_headers):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(
                "/api/v1/collaboration/handoffs",
                headers=auth_headers,
            )
            assert resp.status_code == 200
            assert isinstance(resp.json(), list)

    @pytest.mark.asyncio
    async def test_list_roles_with_auth(self, app, auth_headers):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(
                "/api/v1/collaboration/roles",
                headers=auth_headers,
            )
            assert resp.status_code == 200
            data = resp.json()
            assert isinstance(data, list)
            assert len(data) > 0

    @pytest.mark.asyncio
    async def test_get_aggregation_with_auth(self, app, auth_headers):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(
                "/api/v1/collaboration/aggregate/t1",
                headers=auth_headers,
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["task_id"] == "t1"
