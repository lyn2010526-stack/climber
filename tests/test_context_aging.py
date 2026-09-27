"""Tests for tool-result truncation, history aging, disclosure, and recall."""

from __future__ import annotations

from app.core.context_aging import (
    PRUNED_MARKER,
    ToolResultConfig,
    disclose_old_tool_results,
    make_stub,
    prune_old_tool_results,
    truncate_tool_result,
)
from app.core.recall_tools import recall_tool_definitions


def _tool_msg(text: str, call_id: str) -> dict:
    return {"role": "tool", "content": text, "tool_call_id": call_id}


class TestTruncateToolResult:
    def test_short_text_untouched(self):
        assert truncate_tool_result("hello") == "hello"

    def test_long_text_middle_truncated(self):
        cfg = ToolResultConfig(max_result_chars=100, head_ratio=0.4, tail_ratio=0.4)
        text = "H" * 200 + "M" * 200 + "T" * 200
        out = truncate_tool_result(text, cfg)
        assert len(out) < len(text)
        assert out.startswith("H")
        assert out.endswith("T")
        assert "Output truncated" in out
        assert "520 characters elided" in out

    def test_zero_limit_disables(self):
        cfg = ToolResultConfig(max_result_chars=0)
        text = "x" * 100_000
        assert truncate_tool_result(text, cfg) == text

    def test_ratio_defaults_kept(self):
        cfg = ToolResultConfig(max_result_chars=1000)
        text = "a" * 5000
        out = truncate_tool_result(text, cfg)
        assert "Output truncated" in out
        assert out.endswith("a")


class TestPruneOldToolResults:
    def test_under_budget_untouched(self):
        cfg = ToolResultConfig(prune_budget_chars=100_000, prune_protect_recent=1)
        msgs = [_tool_msg("a" * 10, f"t{i}") for i in range(3)]
        assert prune_old_tool_results(msgs, cfg) == 0
        assert all(m["content"] == "a" * 10 for m in msgs)

    def test_over_budget_oldest_pruned(self):
        cfg = ToolResultConfig(
            prune_budget_chars=1000, prune_protect_recent=1, max_result_chars=0
        )
        msgs = [_tool_msg("x" * 2000, f"t{i}") for i in range(4)]
        rewritten = prune_old_tool_results(msgs, cfg)
        assert rewritten >= 1
        assert msgs[0]["content"] == PRUNED_MARKER
        assert msgs[-1]["content"] == "x" * 2000

    def test_recent_results_protected(self):
        cfg = ToolResultConfig(
            prune_budget_chars=100, prune_protect_recent=3, max_result_chars=0
        )
        msgs = [_tool_msg("x" * 5000, f"t{i}") for i in range(5)]
        prune_old_tool_results(msgs, cfg)
        assert all(m["content"] == "x" * 5000 for m in msgs[-3:])

    def test_zero_budget_disables(self):
        cfg = ToolResultConfig(prune_budget_chars=0)
        msgs = [_tool_msg("x" * 999_999, "t0")]
        assert prune_old_tool_results(msgs, cfg) == 0

    def test_non_tool_messages_ignored(self):
        cfg = ToolResultConfig(prune_budget_chars=10, prune_protect_recent=0, max_result_chars=0)
        msgs = [
            {"role": "user", "content": "x" * 10_000},
            {"role": "assistant", "content": "y" * 10_000},
            _tool_msg("z" * 10_000, "t0"),
        ]
        prune_old_tool_results(msgs, cfg)
        assert msgs[0]["content"] == "x" * 10_000
        assert msgs[1]["content"] == "y" * 10_000


class TestDiscloseOldToolResults:
    def test_archives_original_and_stubs(self):
        cfg = ToolResultConfig(disclose_budget_chars=1000, prune_protect_recent=1)
        msgs = [_tool_msg("x" * 2000, f"t{i}") for i in range(4)]
        store: dict[str, str] = {}
        stubbed = disclose_old_tool_results(msgs, store, cfg)
        assert stubbed >= 1
        assert "t0" in store
        assert store["t0"] == "x" * 2000
        assert "recall_tool_call" in msgs[0]["content"]

    def test_recent_untouched(self):
        cfg = ToolResultConfig(disclose_budget_chars=1000, prune_protect_recent=2)
        msgs = [_tool_msg("x" * 5000, f"t{i}") for i in range(4)]
        store: dict[str, str] = {}
        disclose_old_tool_results(msgs, store, cfg)
        assert msgs[-2]["content"] == "x" * 5000
        assert msgs[-1]["content"] == "x" * 5000

    def test_zero_budget_disables(self):
        cfg = ToolResultConfig(disclose_budget_chars=0)
        msgs = [_tool_msg("x" * 999_999, "t0")]
        store: dict[str, str] = {}
        assert disclose_old_tool_results(msgs, store, cfg) == 0
        assert store == {}

    def test_multimodal_content_preserved(self):
        cfg = ToolResultConfig(disclose_budget_chars=10, prune_protect_recent=0)
        msgs = [
            {
                "role": "tool",
                "content": [
                    {"type": "text", "text": "x" * 5000},
                    {"type": "image_url", "image_url": {"url": "data:image/png;base64,AAAA"}},
                ],
                "tool_call_id": "t0",
            }
        ]
        store: dict[str, str] = {}
        disclose_old_tool_results(msgs, store, cfg)
        blocks = msgs[0]["content"]
        assert any(b.get("type") == "image_url" for b in blocks)
        assert store["t0"] == "x" * 5000

    def test_stub_names_id(self):
        stub = make_stub("abc", 1234)
        assert "abc" in stub
        assert "1234" in stub


class TestRecallTools:
    def test_definitions_shape(self):
        defs = recall_tool_definitions({"a": "text"})
        names = [d[0] for d in defs]
        assert names == ["recall_tool_call", "recall_range"]
        for _name, desc, schema, func in defs:
            assert desc
            assert schema["type"] == "object"
            assert "tool_call_id" in schema["properties"]
            assert callable(func)

    def test_recall_returns_original(self):
        store = {"t0": "the original output"}
        defs = recall_tool_definitions(store)
        recall = dict((d[0], d[3]) for d in defs)["recall_tool_call"]
        assert recall(tool_call_id="t0") == "the original output"

    def test_recall_missing_id_lists_available(self):
        store = {"t0": "x", "t1": "y"}
        defs = recall_tool_definitions(store)
        recall = dict((d[0], d[3]) for d in defs)["recall_tool_call"]
        out = recall(tool_call_id="missing")
        assert "No archived output" in out
        assert "t0" in out and "t1" in out

    def test_recall_range_slices(self):
        store = {"t0": "0123456789"}
        defs = recall_tool_definitions(store)
        recall_range = dict((d[0], d[3]) for d in defs)["recall_range"]
        assert recall_range(tool_call_id="t0", start=2, end=5) == "234"

    def test_recall_clips_huge_output(self):
        store = {"t0": "z" * 100_000}
        defs = recall_tool_definitions(store)
        recall = dict((d[0], d[3]) for d in defs)["recall_tool_call"]
        out = recall(tool_call_id="t0")
        assert "recall clipped" in out
        assert len(out) < 100_000
