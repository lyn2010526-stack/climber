"""Tests for structured summarization helpers and compress fallback."""

from __future__ import annotations

import pytest

from app.core import ContextConfig
from app.core.compressor import (
    ContextCompressor,
    _drop_orphan_tool_prefix,
    _file_operation_manifest,
    _group_into_turns,
    _message_text,
)


def _tool_call(name: str, path: str) -> dict:
    return {
        "role": "assistant",
        "content": "",
        "tool_calls": [
            {
                "function": {
                    "name": name,
                    "arguments": f'{{"path": "{path}"}}',
                }
            }
        ],
    }


class TestGroupIntoTurns:
    def test_groups_at_user_messages(self):
        msgs = [
            {"role": "user", "content": "a"},
            {"role": "assistant", "content": "b"},
            {"role": "user", "content": "c"},
            {"role": "assistant", "content": "d"},
        ]
        turns = _group_into_turns(msgs)
        assert [t[0] for t in turns] == [1, 2]
        assert len(turns[0][1]) == 2
        assert len(turns[1][1]) == 2

    def test_leading_non_user_forms_turn_one(self):
        msgs = [
            {"role": "system", "content": "s"},
            {"role": "assistant", "content": "a"},
            {"role": "user", "content": "u"},
        ]
        turns = _group_into_turns(msgs)
        assert turns[0][0] == 1
        assert len(turns[0][1]) == 2
        assert turns[1][0] == 2

    def test_empty(self):
        assert _group_into_turns([]) == []


class TestMessageText:
    def test_includes_tool_call_names(self):
        msg = {
            "role": "assistant",
            "content": "thinking",
            "tool_calls": [{"function": {"name": "read_file"}}],
        }
        assert "thinking" in _message_text(msg)
        assert "read_file" in _message_text(msg)

    def test_multimodal_text_only(self):
        msg = {
            "role": "user",
            "content": [
                {"type": "text", "text": "hello"},
                {"type": "image_url", "image_url": {"url": "data:..."}},
            ],
        }
        assert _message_text(msg) == "hello"

    def test_plain_string(self):
        assert _message_text({"role": "user", "content": "plain"}) == "plain"


class TestFileOperationManifest:
    def test_dedupes_same_operation(self):
        msgs = [_tool_call("read_file", "a.py"), _tool_call("read_file", "a.py")]
        manifest = _file_operation_manifest(msgs)
        assert manifest == ["- read_file: a.py"]

    def test_distinct_operations_kept(self):
        msgs = [_tool_call("read_file", "a.py"), _tool_call("write_file", "a.py")]
        manifest = _file_operation_manifest(msgs)
        assert len(manifest) == 2

    def test_accepts_file_path_alias(self):
        msg = {
            "role": "assistant",
            "tool_calls": [
                {"function": {"name": "edit", "arguments": '{"file_path": "b.py"}'}}
            ],
        }
        assert _file_operation_manifest([msg]) == ["- edit: b.py"]

    def test_bad_json_skipped(self):
        msg = {
            "role": "assistant",
            "tool_calls": [{"function": {"name": "x", "arguments": "not-json"}}],
        }
        assert _file_operation_manifest([msg]) == []

    def test_no_tool_calls(self):
        assert _file_operation_manifest([{"role": "user", "content": "hi"}]) == []


class _FakeResult:
    def __init__(self, content: str):
        self.content = content


class _FakeModel:
    def __init__(self, content: str = "summary body", fail: bool = False):
        self._content = content
        self._fail = fail
        self.prompts: list[str] = []
        self.calls: list[list[dict]] = []

    async def chat(self, messages, tools=None):
        if self._fail:
            raise RuntimeError("model down")
        self.calls.append([dict(m) for m in messages])
        self.prompts.append(messages[-1]["content"])
        return _FakeResult(self._content)


@pytest.mark.asyncio
class TestSummarize:
    async def test_summary_labels_turns(self):
        comp = ContextCompressor(ContextConfig(keep_recent_messages=1))
        msgs = [
            {"role": "system", "content": "sys"},
            {"role": "user", "content": "first request"},
            {"role": "assistant", "content": "first answer"},
            {"role": "user", "content": "latest"},
        ]
        model = _FakeModel()
        out = await comp._summarize(msgs, model)
        recap = next(m for m in out if m.get("role") == "system" and "Summary of earlier" in m["content"])
        assert "[turn N]" in model.prompts[0]
        assert "turns 1-1" in recap["content"]
        assert out[-1]["content"] == "latest"

    async def test_manifest_appended(self):
        comp = ContextCompressor(ContextConfig(keep_recent_messages=1))
        msgs = [
            {"role": "system", "content": "sys"},
            {"role": "user", "content": "edit please"},
            _tool_call("write_file", "c.py"),
            {"role": "user", "content": "latest"},
        ]
        out = await comp._summarize(msgs, _FakeModel())
        recap = next(m for m in out if m.get("role") == "system" and "Summary of earlier" in m["content"])
        assert "Files touched" in recap["content"]
        assert "write_file: c.py" in recap["content"]

    async def test_model_failure_falls_back_to_truncate(self):
        comp = ContextCompressor(ContextConfig(keep_recent_messages=2))
        msgs = [
            {"role": "system", "content": "sys"},
            {"role": "user", "content": "a"},
            {"role": "assistant", "content": "b"},
            {"role": "user", "content": "c"},
            {"role": "assistant", "content": "d"},
        ]
        out = await comp._summarize(msgs, _FakeModel(fail=True))
        assert out[0]["content"] == "sys"
        assert any("truncated" in m.get("content", "") for m in out)

    async def test_short_conversation_unchanged(self):
        comp = ContextCompressor(ContextConfig(keep_recent_messages=10))
        msgs = [{"role": "user", "content": "only"}]
        assert await comp._summarize(msgs, _FakeModel()) == msgs


class TestDropOrphanToolPrefix:
    def test_drops_leading_tool_messages(self):
        msgs = [
            {"role": "tool", "tool_call_id": "1", "content": "r1"},
            {"role": "tool", "tool_call_id": "2", "content": "r2"},
            {"role": "assistant", "content": "a"},
        ]
        out = _drop_orphan_tool_prefix(msgs)
        assert [m["role"] for m in out] == ["assistant"]

    def test_keeps_messages_without_leading_tools(self):
        msgs = [
            {"role": "assistant", "content": "a", "tool_calls": []},
            {"role": "tool", "tool_call_id": "1", "content": "r"},
        ]
        assert _drop_orphan_tool_prefix(msgs) == msgs

    def test_all_tools_dropped(self):
        msgs = [{"role": "tool", "content": "r1"}, {"role": "tool", "content": "r2"}]
        assert _drop_orphan_tool_prefix(msgs) == []

    def test_empty_list(self):
        assert _drop_orphan_tool_prefix([]) == []

    def test_input_not_mutated(self):
        msgs = [{"role": "tool", "content": "r"}, {"role": "user", "content": "u"}]
        _drop_orphan_tool_prefix(msgs)
        assert msgs[0]["role"] == "tool"


def _messages_with_tool_pair():
    """Conversation whose recent-window cut can land inside a tool pair."""
    return [
        {"role": "system", "content": "sys"},
        {"role": "user", "content": "find it"},
        _tool_call("read_file", "a.py"),
        {"role": "tool", "tool_call_id": "t1", "content": "file body"},
        {"role": "assistant", "content": "done"},
        {"role": "user", "content": "latest"},
    ]


class TestOrphanToolResults:
    def test_truncate_drops_orphan_tool_tail(self):
        comp = ContextCompressor(ContextConfig(keep_recent_messages=3))
        out = comp._truncate(_messages_with_tool_pair())
        assert "tool" not in [m["role"] for m in out]
        assert out[-1]["content"] == "latest"

    def test_sliding_drops_orphan_tool_tail(self):
        comp = ContextCompressor(ContextConfig(keep_recent_messages=3))
        out = comp._sliding(_messages_with_tool_pair())
        assert "tool" not in [m["role"] for m in out]
        assert out[-1]["content"] == "latest"

    def test_budget_compress_drops_orphan_tool_prefix(self):
        comp = ContextCompressor(ContextConfig())
        msgs = [
            {"role": "system", "content": "sys"},
            {"role": "user", "content": "x" * 40},
            _tool_call("read_file", "a.py"),
            {"role": "tool", "tool_call_id": "t1", "content": "y" * 80},
            {"role": "assistant", "content": "done"},
            {"role": "user", "content": "latest"},
        ]
        out = comp.compress_with_budget(msgs, max_tokens=30)
        roles = [m["role"] for m in out]
        assert "tool" not in roles
        assert out[-1]["content"] == "latest"


@pytest.mark.asyncio
class TestSummarizeOrphansAndPrefix:
    async def test_output_has_no_orphan_tool_results(self):
        # The tail starts with a tool result whose paired tool_calls message
        # falls into the summarized middle (gap 2); it must be dropped.
        comp = ContextCompressor(ContextConfig(keep_recent_messages=3))
        out = await comp._summarize(_messages_with_tool_pair(), _FakeModel())
        assert "tool" not in [m["role"] for m in out]
        assert out[0]["content"] == "sys"
        assert out[-1]["content"] == "latest"

    async def test_pathological_summary_falls_back_to_truncate(self):
        comp = ContextCompressor(ContextConfig(keep_recent_messages=1))
        msgs = [
            {"role": "system", "content": "sys"},
            {"role": "user", "content": "short question"},
            {"role": "assistant", "content": "short answer"},
            {"role": "user", "content": "latest"},
        ]
        model = _FakeModel(content="b" * 500)
        out = await comp._summarize(msgs, model)
        assert any("truncated" in m.get("content", "") for m in out)
        assert all("Summary of earlier" not in m.get("content", "") for m in out)

    async def test_hold_messages_reuse_session_prefix(self):
        comp = ContextCompressor(ContextConfig(keep_recent_messages=1))
        msgs = [
            {"role": "system", "content": "sys"},
            {"role": "user", "content": "first"},
            {"role": "assistant", "content": "reply", "extra": "internal"},
            {"role": "user", "content": "latest"},
        ]
        model = _FakeModel()
        await comp._summarize(msgs, model)
        sent = model.calls[0]
        assert sent[0] == {"role": "system", "content": "sys"}
        assert sent[1] == {"role": "user", "content": "first"}
        assert sent[2] == {"role": "assistant", "content": "reply"}
        instruction = sent[-1]
        assert instruction["role"] == "user"
        assert "Summarize" in instruction["content"]
        assert "[turn N]" in instruction["content"]
        assert "bullet list" in instruction["content"]

    async def test_hold_messages_send_real_conversation(self):
        comp = ContextCompressor(ContextConfig(keep_recent_messages=1))
        msgs = [
            {"role": "system", "content": "sys"},
            {"role": "user", "content": "first request"},
            {"role": "assistant", "content": "first answer"},
            {"role": "user", "content": "latest"},
        ]
        model = _FakeModel()
        await comp._summarize(msgs, model)
        sent = model.calls[0]
        assert {"role": "user", "content": "first request"} in sent
        assert {"role": "assistant", "content": "first answer"} in sent
        assert sent[-1]["role"] == "user"
