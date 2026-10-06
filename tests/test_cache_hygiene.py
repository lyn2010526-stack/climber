"""Cache hygiene: bounded memory stores, key unregistration, soft-limit warning."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from app.core.tool_prioritizer import ToolPrioritizer
from app.models import registry as registry_module
from app.skills.memory_manager import _CACHE_MAX_ENTRIES, PersistentMemory

if TYPE_CHECKING:
    import pytest

_SOFT_LIMIT = registry_module._MODELS_SOFT_LIMIT


class _CapturingLogger:
    """Minimal logger stand-in recording warning calls for assertions."""

    def __init__(self) -> None:
        self.warnings: list[dict[str, Any]] = []

    def warning(self, event: str, **kwargs: Any) -> None:
        self.warnings.append({"event": event, **kwargs})

    def info(self, event: str, **kwargs: Any) -> None:
        pass


def test_persistent_memory_deque_evicts_oldest() -> None:
    store = PersistentMemory()
    overflow = _CACHE_MAX_ENTRIES + 1
    for i in range(overflow):
        store.store(f"entry-{i}")

    assert len(store._cache) == _CACHE_MAX_ENTRIES
    assert store.recall(query="entry-0") == []
    assert [e.content for e in store.recall(query=f"entry-{overflow - 1}")] == [
        f"entry-{overflow - 1}"
    ]
    assert store.get_stats()["total"] == _CACHE_MAX_ENTRIES
    assert len(store.recall(limit=3)) == 3


def test_unregister_key_removes_only_target_entries() -> None:
    reg = registry_module.ModelRegistry()
    reg.register_keys("openai", "model-a", ["k1", "k2"])
    reg.register_keys("openai", "model-b", ["k3"])

    removed = reg.unregister_key("openai", "model-a", idx=0)
    assert removed == 1
    assert "openai:model-a:key:0" not in reg._models
    assert "openai:model-a:key:1" in reg._models
    assert "openai:model-b:key:0" in reg._models

    removed = reg.unregister_key("openai", "model-a")
    assert removed == 1
    assert reg.unregister_key("openai", "model-a") == 0
    assert "openai:model-b:key:0" in reg._models


def test_register_keys_warns_once_per_soft_limit_crossing(monkeypatch: pytest.MonkeyPatch) -> None:
    captured = _CapturingLogger()
    monkeypatch.setattr(registry_module, "logger", captured)
    reg = registry_module.ModelRegistry()

    reg.register_keys("openai", "bulk", [f"k{i}" for i in range(_SOFT_LIMIT + 1)])
    assert reg._size_warning_emitted is True
    warning_events = [
        w for w in captured.warnings if w["event"] == "model_registry_soft_limit_exceeded"
    ]
    assert len(warning_events) == 1

    reg.register_keys("openai", "more", ["extra"])
    warning_events = [
        w for w in captured.warnings if w["event"] == "model_registry_soft_limit_exceeded"
    ]
    assert len(warning_events) == 1

    reg.unregister_key("openai", "bulk")
    assert reg._size_warning_emitted is False


def _tool(name: str) -> dict[str, Any]:
    return {"function": {"name": name, "description": f"desc for {name}"}}


def test_tool_prioritizer_caches_bounded_and_clearable() -> None:
    prioritizer = ToolPrioritizer()
    names = [f"tool-{i:04d}" for i in range(501)]
    ranked = prioritizer.rank_tools("rank tools", [_tool(n) for n in names])

    assert ranked == names
    assert len(prioritizer._description_cache) == 500
    assert "tool-0000" not in prioritizer._description_cache
    assert "tool-0500" in prioritizer._description_cache
    assert len(prioritizer._stats) == 500
    assert "tool-0000" not in prioritizer._stats

    prioritizer.clear_caches()
    assert len(prioritizer._description_cache) == 0
    assert len(prioritizer._stats) == 0
    assert prioritizer.get_stats("tool-0000") == {
        "attempts": 0,
        "success_rate": None,
        "avg_duration_ms": None,
    }
