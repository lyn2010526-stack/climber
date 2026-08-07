"""Comprehensive tests for permissions and RBAC module."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.permissions import (
    Action,
    Permission,
    PermissionCreate,
    PermissionEffect,
    PermissionScope,
    PolicyRule,
    ResourceType,
    RoleDefinition,
    UserRoleAssignment,
)
from app.services.permission_service import PermissionService


@pytest.fixture
def mock_session() -> AsyncSession:
    session = AsyncMock(spec=AsyncSession)
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.delete = AsyncMock()
    session.execute.return_value = MagicMock()
    return session


@pytest.fixture
def permission_service(mock_session: AsyncSession) -> PermissionService:
    return PermissionService(mock_session)


@pytest.fixture
def admin_role() -> RoleDefinition:
    return RoleDefinition(id=1, name="admin", is_system=True, priority=100)


@pytest.fixture
def editor_role() -> RoleDefinition:
    return RoleDefinition(id=2, name="editor", is_system=False, priority=50)


class TestRoleManagement:
    """Tests for role CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_role(self, permission_service, mock_session):
        from app.models.permissions import RoleDefinitionCreate
        data = RoleDefinitionCreate(name="test_role", description="Test", priority=10)
        result = await permission_service.create_role(data)
        assert result.name == "test_role"
        assert result.priority == 10
        mock_session.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_role_by_id(self, permission_service, mock_session, admin_role):
        mock_session.execute.return_value.scalar_one_or_none.return_value = admin_role
        result = await permission_service.get_role(1)
        assert result is not None
        assert result.name == "admin"

    @pytest.mark.asyncio
    async def test_list_roles(self, permission_service, mock_session, admin_role, editor_role):
        mock_session.execute.return_value.scalars.return_value.all.return_value = [admin_role, editor_role]
        result = await permission_service.list_roles()
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_delete_non_system_role(self, permission_service, mock_session, editor_role):
        mock_session.execute.return_value.scalar_one_or_none.return_value = editor_role
        result = await permission_service.delete_role(2)
        assert result is True

    @pytest.mark.asyncio
    async def test_delete_system_role_blocked(self, permission_service, mock_session, admin_role):
        mock_session.execute.return_value.scalar_one_or_none.return_value = admin_role
        result = await permission_service.delete_role(1)
        assert result is False


class TestPermissionManagement:
    """Tests for permission CRUD operations."""

    @pytest.mark.asyncio
    async def test_add_permission_to_role(self, permission_service, mock_session):
        data = PermissionCreate(
            resource_type=ResourceType.AGENT,
            action=Action.READ,
            scope=PermissionScope.GLOBAL,
        )
        result = await permission_service.add_permission(1, data)
        assert result.role_id == 1
        assert result.resource_type == "agent"
        assert result.action == "read"

    @pytest.mark.asyncio
    async def test_remove_permission(self, permission_service, mock_session):
        perm = Permission(id=1, role_id=1, resource_type="agent", action="read")
        mock_session.execute.return_value.scalar_one_or_none.return_value = perm
        result = await permission_service.remove_permission(1)
        assert result is True

    @pytest.mark.asyncio
    async def test_remove_nonexistent_permission(self, permission_service, mock_session):
        mock_session.execute.return_value.scalar_one_or_none.return_value = None
        result = await permission_service.remove_permission(999)
        assert result is False


class TestAccessControl:
    """Tests for access control checks."""

    @pytest.mark.asyncio
    async def test_check_access_no_assignments(self, permission_service, mock_session):
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = []
        mock_session.execute.side_effect = [result_mock]
        result = await permission_service.check_access(
            1, ResourceType.AGENT, Action.READ
        )
        assert result.allowed is False
        assert "No role assignments" in result.reason

    @pytest.mark.asyncio
    async def test_check_access_with_allow_permission(self, permission_service, mock_session):
        assignment = UserRoleAssignment(id=1, user_id=1, role_id=1)
        perm = Permission(
            id=1, role_id=1, resource_type="agent",
            action="read", effect="allow",
        )
        result1 = MagicMock()
        result1.scalars.return_value.all.return_value = [assignment]
        result2 = MagicMock()
        result2.scalars.return_value.all.return_value = [perm]
        mock_session.execute.side_effect = [result1, result2]
        result = await permission_service.check_access(
            1, ResourceType.AGENT, Action.READ
        )
        assert result.allowed is True

    @pytest.mark.asyncio
    async def test_check_access_deny_takes_precedence(self, permission_service, mock_session):
        assignment = UserRoleAssignment(id=1, user_id=1, role_id=1)
        allow_perm = Permission(
            id=1, role_id=1, resource_type="agent",
            action="read", effect="allow",
        )
        deny_perm = Permission(
            id=2, role_id=1, resource_type="agent",
            action="read", effect="deny",
        )
        result1 = MagicMock()
        result1.scalars.return_value.all.return_value = [assignment]
        result2 = MagicMock()
        result2.scalars.return_value.all.return_value = [allow_perm, deny_perm]
        mock_session.execute.side_effect = [result1, result2]
        result = await permission_service.check_access(
            1, ResourceType.AGENT, Action.READ
        )
        assert result.allowed is False


class TestPolicyRules:
    """Tests for policy rule management."""

    @pytest.mark.asyncio
    async def test_create_policy_rule(self, permission_service, mock_session):
        from app.models.permissions import PolicyRuleCreate
        data = PolicyRuleCreate(
            name="no_delete_prod",
            resource_type=ResourceType.AGENT,
            action=Action.DELETE,
            effect=PermissionEffect.DENY,
            priority=100,
        )
        result = await permission_service.create_policy_rule(data)
        assert result.name == "no_delete_prod"
        assert result.effect == "deny"

    @pytest.mark.asyncio
    async def test_list_active_policy_rules(self, permission_service, mock_session):
        rules = [
            PolicyRule(id=1, name="rule1", resource_type="agent", action="delete"),
            PolicyRule(id=2, name="rule2", resource_type="session", action="create"),
        ]
        mock_session.execute.return_value.scalars.return_value.all.return_value = rules
        result = await permission_service.list_policy_rules(active_only=True)
        assert len(result) == 2


class TestAuditLogging:
    """Tests for audit log operations."""

    @pytest.mark.asyncio
    async def test_log_access_check(self, permission_service, mock_session):
        result = await permission_service.log_access_check(
            user_id=1,
            action="read",
            resource_type="agent",
            resource_id="agent-123",
            effect="allow",
            reason="Allow rule matched",
        )
        assert result.user_id == 1
        assert result.effect == "allow"
        mock_session.add.assert_called()

    @pytest.mark.asyncio
    async def test_get_audit_trail(self, permission_service, mock_session):
        mock_session.execute.return_value.scalars.return_value.all.return_value = []
        mock_session.execute.return_value.scalar.return_value = 0
        logs, total = await permission_service.get_audit_trail(user_id=1)
        assert total == 0


class TestEnums:
    """Tests for enum values."""

    def test_resource_type_values(self):
        assert ResourceType.AGENT.value == "agent"
        assert ResourceType.SESSION.value == "session"
        assert ResourceType.DOCUMENT.value == "document"
        assert ResourceType.WORKFLOW.value == "workflow"
        assert ResourceType.TOOL.value == "tool"
        assert ResourceType.SKILL.value == "skill"
        assert ResourceType.GROUP.value == "group"
        assert ResourceType.USER.value == "user"
        assert ResourceType.BILLING.value == "billing"
        assert ResourceType.SETTINGS.value == "settings"

    def test_action_values(self):
        assert Action.CREATE.value == "create"
        assert Action.READ.value == "read"
        assert Action.UPDATE.value == "update"
        assert Action.DELETE.value == "delete"
        assert Action.EXECUTE.value == "execute"
        assert Action.MANAGE.value == "manage"
        assert Action.SHARE.value == "share"
        assert Action.EXPORT.value == "export"
        assert Action.ADMIN.value == "admin"

    def test_permission_scope_values(self):
        assert PermissionScope.GLOBAL.value == "global"
        assert PermissionScope.WORKSPACE.value == "workspace"
        assert PermissionScope.PROJECT.value == "project"
        assert PermissionScope.RESOURCE.value == "resource"

    def test_permission_effect_values(self):
        assert PermissionEffect.ALLOW.value == "allow"
        assert PermissionEffect.DENY.value == "deny"
