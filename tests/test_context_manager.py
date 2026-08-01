# tests/test_context_manager.py
import pytest
from app.core.context_manager import ContextManager, ContextLayer

@pytest.fixture
def mgr(tmp_path):
    return ContextManager(workspace_root=str(tmp_path))

def test_assemble_empty_context(mgr):
    messages = mgr.assemble_context(session_id="s1", user_id="u1", agent_id="a1", query="hello")
    assert isinstance(messages, list)
    assert len(messages) > 0

def test_claude_md_loading(mgr, tmp_path):
    claude_md = tmp_path / "CLAUDE.md"
    claude_md.write_text("# Project Rules\n- Always write tests\n- Use type hints")
    messages = mgr.assemble_context(session_id="s1", user_id="u1", agent_id="a1", query="hello")
    content = "\n".join(m.get("", "") for m in messages if isinstance(m, dict))
    # Check that CLAUDE.md content is present
    found = any("Always write tests" in str(m.get("content", "")) for m in messages if isinstance(m, dict))
    assert found

def test_tool_output_truncation(mgr):
    long_output = "x" * 20000
    truncated = mgr.truncate_tool_output(long_output, max_chars=5000)
    assert len(truncated) <= 6000  # allowance for truncation marker
    assert len(truncated) < len(long_output)

def test_plan_md_progress_save(mgr, tmp_path):
    plan_content = "# Plan\n1. Step one\n2. Step two"
    mgr.save_progress(session_id="s1", content=plan_content)
    plan_file = tmp_path / "sessions" / "s1" / "PLAN.md"
    assert plan_file.exists()
    assert "Step one" in plan_file.read_text()
