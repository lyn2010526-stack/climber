"""Coverage tests for app.core.metacognition.capability_discovery."""

from __future__ import annotations

import json
from pathlib import Path

from app.core.metacognition.capability_discovery import CapabilityDiscovery, ComposedCapability


def _discovery(tmp_path: Path) -> CapabilityDiscovery:
    return CapabilityDiscovery(storage_path=str(tmp_path / "discovered.json"))


def test_composed_capability_success_rate_zero_uses() -> None:
    cap = ComposedCapability(
        name="c",
        description="d",
        tool_chain=[],
        inputs={},
        output_description="o",
    )
    assert cap.success_rate == 0.0
    cap.use_count = 4
    cap.success_count = 3
    assert cap.success_rate == 0.75


def test_discover_analyze_pattern(tmp_path: Path) -> None:
    d = _discovery(tmp_path)
    cap = d.discover("transform data", ["read_file", "write_file", "run_command"], "analyze csv")
    assert cap is not None
    assert [s["tool"] for s in cap.tool_chain] == ["read_file", "run_command", "write_file"]
    assert d.get_capability(cap.name) is cap
    assert (tmp_path / "discovered.json").exists()


def test_discover_search_pattern_web_and_read(tmp_path: Path) -> None:
    d = _discovery(tmp_path)
    cap = d.discover("gather", ["web_search", "read_file", "write_file"], "search for info")
    assert cap is not None
    assert [s["tool"] for s in cap.tool_chain] == ["web_search", "read_file", "write_file"]


def test_discover_search_pattern_read_only(tmp_path: Path) -> None:
    d = _discovery(tmp_path)
    cap = d.discover("gather", ["read_file"], "find references")
    assert cap is not None
    assert [s["tool"] for s in cap.tool_chain] == ["read_file"]


def test_discover_search_pattern_web_only(tmp_path: Path) -> None:
    d = _discovery(tmp_path)
    cap = d.discover("gather", ["web_search"], "search the web")
    assert cap is not None
    assert [s["tool"] for s in cap.tool_chain] == ["web_search"]


def test_discover_monitor_pattern(tmp_path: Path) -> None:
    d = _discovery(tmp_path)
    cap = d.discover("watch", ["read_file", "run_command"], "monitor the log file")
    assert cap is not None
    assert cap.tool_chain[0]["purpose"] == "Read current state"


def test_discover_validate_pattern(tmp_path: Path) -> None:
    d = _discovery(tmp_path)
    cap = d.discover("check", ["read_file", "run_command"], "validate schema")
    assert cap is not None
    assert cap.output_description.startswith("Validation result")


def test_discover_database_pattern(tmp_path: Path) -> None:
    d = _discovery(tmp_path)
    cap = d.discover("query", ["run_command"], "query database")
    assert cap is not None
    assert "(via CLI)" in cap.description


def test_discover_no_match_returns_none_and_saves_nothing(tmp_path: Path) -> None:
    d = _discovery(tmp_path)
    assert d.discover("goal", ["run_command"], "unrelated capability") is None
    assert d.list_capabilities() == []
    assert not (tmp_path / "discovered.json").exists()


def test_record_usage_success_and_failure(tmp_path: Path) -> None:
    d = _discovery(tmp_path)
    cap = d.discover("transform", ["read_file", "write_file"], "extract fields")
    assert cap is not None
    d.record_usage(cap.name, success=True)
    d.record_usage(cap.name, success=False)
    assert cap.use_count == 2
    assert cap.success_count == 1
    # Persisted and reloadable.
    reloaded = _discovery(tmp_path)
    loaded = reloaded.get_capability(cap.name)
    assert loaded is not None
    assert loaded.use_count == 2
    assert loaded.success_count == 1


def test_record_usage_unknown_name_is_noop(tmp_path: Path) -> None:
    d = _discovery(tmp_path)
    d.record_usage("missing", success=True)
    assert d.list_capabilities() == []


def test_list_capabilities_shape(tmp_path: Path) -> None:
    d = _discovery(tmp_path)
    d.discover("transform", ["read_file", "write_file"], "analyze report")
    listing = d.list_capabilities()
    assert len(listing) == 1
    assert listing[0]["tools"] == ["read_file", "run_command", "write_file"]
    assert listing[0]["success_rate"] == 0.0


def test_make_name_deduplicates(tmp_path: Path) -> None:
    d = _discovery(tmp_path)
    first = d.discover("g", ["read_file", "write_file"], "analyze data")
    assert first is not None
    # Same normalized name already registered -> suffix appended.
    second = d.discover("g", ["read_file", "write_file"], "analyze data")
    assert second is not None
    assert second.name != first.name
    assert second.name.startswith(first.name + "_")


def test_make_name_falls_back_to_capability(tmp_path: Path) -> None:
    d = _discovery(tmp_path)
    # All words are stop-words -> no key words -> generic fallback name.
    assert d._make_name("the a an") == "capability"


def test_load_existing_file(tmp_path: Path) -> None:
    path = tmp_path / "discovered.json"
    path.write_text(
        json.dumps(
            {
                "cached": {
                    "name": "cached",
                    "description": "from disk",
                    "tool_chain": [{"tool": "read_file", "purpose": "x"}],
                    "inputs": {},
                    "output_description": "o",
                    "use_count": 5,
                    "success_count": 4,
                }
            }
        )
    )
    d = CapabilityDiscovery(storage_path=str(path))
    loaded = d.get_capability("cached")
    assert loaded is not None
    assert loaded.use_count == 5
    assert loaded.success_rate == 0.8


def test_load_missing_count_keys_defaults_zero(tmp_path: Path) -> None:
    path = tmp_path / "discovered.json"
    path.write_text(
        json.dumps(
            {
                "x": {
                    "name": "x",
                    "description": "d",
                    "tool_chain": [],
                    "inputs": {},
                    "output_description": "o",
                }
            }
        )
    )
    d = CapabilityDiscovery(storage_path=str(path))
    assert d.get_capability("x").use_count == 0


def test_load_corrupt_json_is_ignored(tmp_path: Path) -> None:
    path = tmp_path / "discovered.json"
    path.write_text("{not valid json")
    d = CapabilityDiscovery(storage_path=str(path))
    assert d.list_capabilities() == []


def test_load_missing_keys_is_ignored(tmp_path: Path) -> None:
    path = tmp_path / "discovered.json"
    path.write_text(json.dumps({"x": {"name": "x"}}))
    d = CapabilityDiscovery(storage_path=str(path))
    assert d.list_capabilities() == []


def test_load_no_file_is_noop(tmp_path: Path) -> None:
    d = CapabilityDiscovery(storage_path=str(tmp_path / "nope" / "x.json"))
    assert d.list_capabilities() == []
