"""Tests for long-context management (budget, sliding window, compression, external tools, RAG)."""

from __future__ import annotations

import pytest

from app.core.long_context import (
    CompressionPipeline,
    ContextBudget,
    ContextBudgetManager,
    ExternalStateTools,
    PrefixCache,
    SlidingWindowSummarizer,
    get_rag_memory_index,
)
from app.core.long_context.prefix_cache import CacheEntry


def test_budget_total_32k():
    budget = ContextBudget()
    assert budget.total == 32768


def test_budget_manager_trims_lowest_priority():
    mgr = ContextBudgetManager()
    result = mgr.allocate(
        system_prompt="S" * 100,
        long_term_memory="M" * 100,
        skill_index="K" * 100,
        history_summary="H" * 100,
        recent_turns=["user: hi" * 4000],  # 8000 chars
        rag_results=["rag" * 4000],  # 12000 chars
        tool_results=["tool" * 60000],  # 240000 chars, lowest priority, biggest
    )
    # tool_results must be trimmed (its length drops well below input)
    tool_len = len(result["components"]["tool_results"])
    assert tool_len < 60000 * 4
    # total stays within budget
    assert result["total_tokens"] <= result["budget_total"]


def test_budget_fits():
    mgr = ContextBudgetManager()
    assert mgr.fits(1000)
    assert not mgr.fits(100000)


@pytest.mark.asyncio
async def test_sliding_window_summarizer():
    s = SlidingWindowSummarizer(window_size=3, summary_step=2)
    for i in range(8):
        s.add_turn("user", f"request {i}")
        if s.should_summarize():
            await s.run_summary_update()
    blocks = s.build_prompt_blocks()
    assert blocks["recent"]
    assert len(s.recent_turns()) <= 3
    assert blocks["summary"]


def test_compression_pipeline_types():
    pipe = CompressionPipeline()
    assert pipe._compress_tool_result({"a": 1, "b": 2}) == '{"a":1,"b":2}'
    assert "truncated" in pipe._compress_code("x" * 5000)
    ui = pipe._compress_ui_tree([{"visible": False, "clickable": True}, {"visible": True, "clickable": True}])
    assert ui.count("clickable") == 1  # invisible node filtered out


@pytest.mark.asyncio
async def test_external_state_tools():
    tools = ExternalStateTools(memory_index=None, skill_store=None)
    results = await tools.search_memory("nonexistent query that won't match", limit=3)
    assert isinstance(results, list)
    state = await tools.get_app_state("com.example.app")
    assert state["package"] == "com.example.app"


def test_prefix_cache_stable_order():
    cache = PrefixCache()
    cache.set_fixed(system_prompt="SYS", long_term_memory="MEM", skill_index="SKI", tool_descriptions="TOOLS")
    prefix = cache.render_fixed_prefix()
    assert prefix.index("<system>") < prefix.index("<memory>") < prefix.index("<skills>") < prefix.index("<tools>")
    msgs = cache.assemble({"recent_turns": "recent", "summary": "sum"})
    assert msgs[0]["role"] == "system"
    assert "<system>" in msgs[0]["content"]


def test_prefix_cache_is_append_only_and_records_first_stale_block():
    cache = PrefixCache()
    original = CacheEntry(
        key="first",
        blocks=(
            ("prefix_revision", "rev-1"),
            ("tool_schema", "tools-1"),
            ("model", "openai:test"),
        ),
        value="original",
        input_tokens=12,
    )

    assert cache.append(original) is True
    assert cache.append(CacheEntry(**{**original.__dict__, "value": "replacement"})) is False
    assert cache.lookup("first").value == "original"

    cache.record_stale(
        (
            ("prefix_revision", "rev-2"),
            ("tool_schema", "tools-2"),
            ("model", "openai:test"),
        )
    )

    snip = cache.stale_snips[-1]
    assert snip.block == "prefix_revision"
    assert snip.reason == "prefix revision changed"
    assert snip.expected == "rev-1"
    assert snip.actual == "rev-2"


def test_prefix_cache_evicts_oldest_entries_at_count_and_byte_limits():
    count_limited = PrefixCache(max_entries=2, max_entry_bytes=10_000)
    for key in ("first", "second", "third"):
        assert count_limited.append(
            CacheEntry(key=key, blocks=(("messages", key),), value=key)
        )

    assert [entry.key for entry in count_limited.entries] == ["second", "third"]
    assert count_limited.lookup("first") is None

    sample = CacheEntry(key="sample", blocks=(("messages", "sample"),), value="x" * 100)
    byte_limited = PrefixCache(max_entries=10, max_entry_bytes=1)

    assert byte_limited.append(sample) is False
    assert byte_limited.entries == ()

    first = CacheEntry(key="first", blocks=(("messages", "first"),), value="x" * 100)
    second = CacheEntry(key="second", blocks=(("messages", "second"),), value="y" * 100)
    cumulative_limit = max(len(repr(first).encode("utf-8")), len(repr(second).encode("utf-8"))) + 10
    cumulative_limited = PrefixCache(max_entries=10, max_entry_bytes=cumulative_limit)

    assert cumulative_limited.append(first) is True
    assert cumulative_limited.append(second) is True
    assert [entry.key for entry in cumulative_limited.entries] == ["second"]


def test_prefix_cache_retains_only_recent_stale_diagnostics():
    cache = PrefixCache(max_stale_snips=2)
    cache.append(
        CacheEntry(
            key="base",
            blocks=(("prefix_revision", "original"),),
            value="result",
        )
    )

    for revision in ("revision-1", "revision-2", "revision-3"):
        cache.record_stale((("prefix_revision", revision),))

    assert [snip.actual for snip in cache.stale_snips] == ["revision-2", "revision-3"]


def test_rag_memory_index(tmp_path):
    idx = get_rag_memory_index(db_path=str(tmp_path / "rag.db"))
    idx.clear()
    idx.add("how to send wechat message", source="user", session_id="s1")
    idx.add("how to book a taxi", source="user", session_id="s1")
    results = idx.search("wechat", limit=5)
    assert len(results) >= 1
    assert "wechat" in results[0]["content"].lower()


def test_compression_json_single_line():
    from app.core.long_context.compression import compress_json_single_line

    assert compress_json_single_line({"a": 1}) == '{"a":1}'
