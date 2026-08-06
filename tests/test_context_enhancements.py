import pytest

from app.core.context_manager import ContextManager


@pytest.fixture
def mgr(tmp_path):
    return ContextManager(workspace_root=str(tmp_path))


def test_hot_cold_strategy_recent_only(mgr):
    messages = [
        {"role": "user", "content": f"msg {i}"} for i in range(10)
    ]
    result = mgr.apply_hot_cold_strategy(messages, hot_window=20)
    assert len(result) == 10  # All fit in hot window


def test_hot_cold_strategy_with_cold(mgr):
    messages = [
        {"role": "user", "content": f"msg {i}"} for i in range(100)
    ]
    result = mgr.apply_hot_cold_strategy(messages, hot_window=20, cold_summary_threshold=50)
    # Should have cold summary + hot messages
    assert len(result) < 100
    assert any("cold_memory" in str(m.get("content", "")) for m in result)


def test_system_msgs_always_preserved(mgr):
    messages = [
        {"role": "system", "content": "sys1"},
        {"role": "user", "content": "msg 1"},
    ] + [{"role": "user", "content": f"msg {i}"} for i in range(60)]
    result = mgr.apply_hot_cold_strategy(messages, hot_window=10)
    assert result[0]["content"] == "sys1"


def test_tool_output_truncation_in_messages(mgr):
    messages = [
        {"role": "tool", "content": "x" * 20000},
        {"role": "user", "content": "hello"},
    ]
    result = mgr.compress_tool_outputs_in_messages(messages, max_output_chars=1000)
    assert len(str(result[0]["content"])) < 20000
    assert "truncated" in result[0]["content"].lower()


def test_stage_summary(mgr):
    messages = [
        {"role": "user", "content": "build a feature"},
        {"role": "assistant", "content": "Done. Here is the code..."},
    ]
    summary = mgr.create_stage_summary(messages, "implementation")
    assert summary["role"] == "system"
    assert "implementation" in summary["content"]


def test_summarize_empty_messages(mgr):
    result = mgr._summarize_messages([])
    assert result == "No prior conversation."
