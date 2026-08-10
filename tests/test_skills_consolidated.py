"""Tests for the consolidated skill system, memory manager, and MCP marketplace."""

import tempfile
from unittest.mock import MagicMock, patch

import pytest

from app.skills import SkillCategory, skill_registry
from app.skills.mcp_marketplace import BUILTIN_MCP_SERVERS, mcp_marketplace
from app.skills.memory_manager import (
    MemoryType,
    PersistentMemoryManager,
)

# ── Consolidated Skill Registry Tests ──


class TestConsolidatedSkills:
    def test_all_categories_present(self):
        """All 5 categories should have skills."""
        cats = skill_registry.get_by_category()
        assert SkillCategory.CORE.value in cats
        assert SkillCategory.ENGINEERING.value in cats
        assert SkillCategory.QUALITY.value in cats
        assert SkillCategory.KNOWLEDGE.value in cats

    def test_core_skills(self):
        """Core category should have research, planning, evolution, memory."""
        core = skill_registry.list_skills(category="core")
        ids = [s.id for s in core]
        assert "recursive_research" in ids
        assert "task_decomposition" in ids
        assert "self_evolving" in ids
        assert "memory_manager" in ids

    def test_engineering_skills(self):
        """Engineering should have frontend, backend, database, devops, git."""
        eng = skill_registry.list_skills(category="engineering")
        ids = [s.id for s in eng]
        assert "frontend_engineer" in ids
        assert "backend_engineer" in ids
        assert "database_architect" in ids
        assert "devops_engineer" in ids
        assert "git_master" in ids

    def test_quality_skills(self):
        """Quality should have review, security, tdd, debugging."""
        qual = skill_registry.list_skills(category="quality")
        ids = [s.id for s in qual]
        assert "code_reviewer" in ids
        assert "security_auditor" in ids
        assert "tdd_engineer" in ids
        assert "systematic_debugger" in ids

    def test_knowledge_skills(self):
        """Knowledge should have data, research, docs, rag, incident, deps."""
        know = skill_registry.list_skills(category="knowledge")
        ids = [s.id for s in know]
        assert "data_analyst" in ids
        assert "tech_researcher" in ids
        assert "doc_generator" in ids
        assert "rag_organizer" in ids

    def test_no_duplicate_ids(self):
        """Every skill ID must be unique."""
        all_skills = skill_registry.list_skills()
        ids = [s.id for s in all_skills]
        assert len(ids) == len(set(ids)), f"Duplicate IDs found: { {i for i in ids if ids.count(i) > 1} }"

    def test_every_skill_has_system_prompt(self):
        """Every skill must have a substantive system prompt."""
        for skill in skill_registry.list_skills():
            assert len(skill.system_prompt) > 50, f"Skill '{skill.id}' has too short prompt"

    def test_every_skill_has_icon(self):
        """Every skill should have an icon."""
        for skill in skill_registry.list_skills():
            assert skill.icon, f"Skill '{skill.id}' missing icon"

    def test_total_skill_count(self):
        """Should have at least 18 unique skills."""
        assert len(skill_registry.list_skills()) >= 18

    @pytest.mark.asyncio
    async def test_execute_recursive_research(self):
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.text = "<html>Python programming language</html>"
            mock_resp.status_code = 200
            mock_resp.raise_for_status = MagicMock()
            mock_get.return_value = mock_resp

            result = await skill_registry.execute("recursive_research", topic="Python", depth=1)
            assert "Research Report" in result or "Python" in result

    @pytest.mark.asyncio
    async def test_execute_task_decomposition(self):
        result = await skill_registry.execute("task_decomposition", objective="Build a web app")
        assert "Decomposition" in result or "Task" in result

    @pytest.mark.asyncio
    async def test_execute_self_evolving(self):
        result = await skill_registry.execute("self_evolving", context="Previous attempt failed")
        assert "Evolution" in result or "Analysis" in result

    @pytest.mark.asyncio
    async def test_execute_frontend_engineer(self):
        result = await skill_registry.execute(
            "frontend_engineer",
            requirement="Build a dashboard",
            framework="react",
        )
        assert "Frontend" in result or "component" in result.lower()

    @pytest.mark.asyncio
    async def test_execute_code_reviewer(self):
        result = await skill_registry.execute(
            "code_reviewer",
            code="def foo(): pass",
            language="python",
        )
        assert "Review" in result or "dimension" in result.lower()

    @pytest.mark.asyncio
    async def test_execute_security_auditor(self):
        result = await skill_registry.execute(
            "security_auditor",
            code="query = f'SELECT * FROM users WHERE id = {user_id}'",
        )
        assert "Security" in result or "OWASP" in result or "injection" in result.lower()

    @pytest.mark.asyncio
    async def test_execute_tdd(self):
        result = await skill_registry.execute("tdd_engineer", task="Add user authentication")
        assert "TDD" in result or "test" in result.lower()

    @pytest.mark.asyncio
    async def test_execute_debugger(self):
        result = await skill_registry.execute(
            "systematic_debugger",
            error_description="IndexError: list index out of range",
        )
        assert "Debugging" in result or "Root Cause" in result

    @pytest.mark.asyncio
    async def test_execute_data_analyst(self):
        result = await skill_registry.execute(
            "data_analyst",
            data="name,age\nAlice,30\nBob,25",
            question="Average age?",
        )
        assert "Analysis" in result or "Data" in result

    @pytest.mark.asyncio
    async def test_execute_doc_generator(self):
        result = await skill_registry.execute(
            "doc_generator",
            content="The API uses JWT for auth",
            doc_type="api",
        )
        assert "Document" in result or "API" in result


# ── Memory Manager Tests ──


class TestPersistentMemoryManager:
    @pytest.fixture
    def mem(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = PersistentMemoryManager(base_path=tmpdir)
            yield mgr

    def test_store_and_recall(self, mem):
        mem.store("Python is a programming language", MemoryType.FACT, tags=["python"])
        results = mem.recall("Python")
        assert len(results) >= 1
        assert "Python" in results[0].content

    def test_store_with_importance(self, mem):
        mem.store("Important fact", MemoryType.FACT, importance=1.0)
        mem.store("Trivial fact", MemoryType.FACT, importance=0.1)
        results = mem.recall("")
        # Higher importance should rank first when no query
        assert results[0].importance >= results[-1].importance

    def test_recall_by_type(self, mem):
        mem.store("User prefers dark mode", MemoryType.PREFERENCE)
        mem.store("Python released in 1991", MemoryType.FACT)
        prefs = mem.recall(memory_type=MemoryType.PREFERENCE)
        assert len(prefs) >= 1
        assert all(e.type == MemoryType.PREFERENCE for e in prefs)

    def test_recall_by_tags(self, mem):
        mem.store("Fact about Django", tags=["django", "python"])
        mem.store("Fact about Flask", tags=["flask", "python"])
        results = mem.recall(tags=["django"])
        assert len(results) >= 1

    def test_update_entry(self, mem):
        entry = mem.store("Original content", MemoryType.FACT)
        updated = mem.update(entry.id, content="Updated content")
        assert updated is not None
        assert updated.content == "Updated content"

    def test_forget_entry(self, mem):
        entry = mem.store("To be forgotten", MemoryType.FACT)
        assert mem.forget(entry.id) is True
        assert mem.forget(entry.id) is False

    def test_persistence(self, mem):
        """Data should survive manager restart."""
        mem.store("Persistent fact", MemoryType.FACT, tags=["test"])
        # Create new manager pointing to same path
        mem2 = PersistentMemoryManager(base_path=mem.base_path)
        results = mem2.recall("Persistent")
        assert len(results) >= 1

    def test_consolidate(self, mem):
        mem.store("Low importance", MemoryType.FACT, importance=0.1)
        mem.store("High importance", MemoryType.FACT, importance=1.0)
        removed = mem.consolidate()
        # Low importance with 0 access might be removed
        assert isinstance(removed, dict)

    def test_get_stats(self, mem):
        mem.store("Fact 1", MemoryType.FACT)
        mem.store("Fact 2", MemoryType.FACT)
        mem.store("Pref 1", MemoryType.PREFERENCE)
        stats = mem.get_stats()
        assert stats["total_memories"] == 3
        assert "fact" in stats["by_type"]
        assert "preference" in stats["by_type"]

    def test_access_count_increments(self, mem):
        entry = mem.store("Frequently accessed", MemoryType.FACT)
        mem.recall("Frequently accessed")
        mem.recall("Frequently accessed")
        updated = mem._cache[entry.id]
        assert updated.access_count >= 2

    def test_export_all(self, mem):
        mem.store("Exportable fact", MemoryType.FACT)
        exported = mem.export_all()
        assert len(exported) >= 1
        assert all("content" in e for e in exported)


# ── MCP Marketplace Tests ──


class TestMCPMarketplace:
    def test_builtins_count(self):
        assert len(BUILTIN_MCP_SERVERS) >= 12

    def test_categories(self):
        categories = mcp_marketplace.get_categories()
        assert "development" in categories
        assert "database" in categories
        assert "research" in categories

    def test_list_all(self):
        servers = mcp_marketplace.list_servers()
        assert len(servers) >= 12

    def test_list_by_category(self):
        dev = mcp_marketplace.list_servers(category="development")
        assert len(dev) >= 3
        for s in dev:
            assert s.category == "development"

    def test_list_by_installed(self):
        installed = mcp_marketplace.list_servers(installed_only=True)
        builtin_installed = [s for s in BUILTIN_MCP_SERVERS if s.is_installed]
        assert len(installed) >= len(builtin_installed)

    def test_search(self):
        results = mcp_marketplace.list_servers(search="database")
        assert len(results) >= 1

    def test_get_server(self):
        srv = mcp_marketplace.get_server("filesystem")
        assert srv is not None
        assert srv.name == "Filesystem"

    def test_install_and_uninstall(self):
        assert mcp_marketplace.install_server("github", {"GITHUB_PERSONAL_ACCESS_TOKEN": "test"}) is True
        assert mcp_marketplace.get_server("github").is_installed is True
        assert mcp_marketplace.uninstall_server("github") is True
        assert mcp_marketplace.get_server("github").is_installed is False

    def test_cannot_uninstall_builtin(self):
        assert mcp_marketplace.uninstall_server("filesystem") is False

    def test_configure_server(self):
        assert mcp_marketplace.configure_server("postgres", {"CONNECTION_STRING": "postgresql://..."}) is True

    def test_popularity_sorting(self):
        servers = mcp_marketplace.list_servers()
        # Should be sorted by popularity descending
        for i in range(len(servers) - 1):
            assert servers[i].popularity >= servers[i + 1].popularity
