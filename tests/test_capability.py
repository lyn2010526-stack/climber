"""Tests for the unified capability abstraction (registry routing, adapters, market)."""

from __future__ import annotations

import pytest

from app.core.capability import (
    Capability,
    CapabilityMeta,
    CapabilityRegistry,
    McpCapability,
    NoExecutableCapability,
    WrappedCapability,
)


def _meta(cid: str, mtype: str = "tool", **kw) -> CapabilityMeta:
    return CapabilityMeta(
        id=cid,
        name=cid,
        description=f"cap {cid}",
        capability_type=mtype,
        **kw,
    )


class SimpleCap(Capability):
    def __init__(self, cid: str, executable: bool = True, fail: bool = False):
        self._meta = _meta(cid)
        self._executable = executable
        self._fail = fail
        self.calls = 0

    @property
    def meta(self) -> CapabilityMeta:
        return self._meta

    async def execute(self, **kwargs):
        self.calls += 1
        if self._fail:
            raise RuntimeError("boom")
        return f"result-{self._meta.id}"

    def is_executable(self) -> bool:
        return self._executable


@pytest.mark.asyncio
async def test_register_and_execute_best_implementation():
    reg = CapabilityRegistry()
    cap = SimpleCap("greet")
    reg.register(cap)
    result = await reg.execute("greet", name="bob")
    assert result == "result-greet"
    assert cap.calls == 1


@pytest.mark.asyncio
async def test_routing_picks_successful_impl_over_failing_one():
    reg = CapabilityRegistry()
    fail = SimpleCap("dual", fail=True)
    ok = SimpleCap("dual")
    reg.register(fail)
    reg.register(ok)
    # Both have zero stats; ranked by cost. Verify fallback works when the
    # first implementation fails.
    result = await reg.execute("dual")
    assert result == "result-dual"
    assert fail.calls >= 1
    assert ok.calls >= 1


@pytest.mark.asyncio
async def test_no_executable_raises():
    reg = CapabilityRegistry()
    reg.register(SimpleCap("notexec", executable=False))
    with pytest.raises(NoExecutableCapability):
        await reg.execute("notexec")


@pytest.mark.asyncio
async def test_unknown_capability_raises():
    reg = CapabilityRegistry()
    with pytest.raises(NoExecutableCapability):
        await reg.execute("missing")


def test_mcp_adapter():
    async def fake_execute(**kwargs):
        return "mcp-result"

    cap = McpCapability(_meta("mcp_tool", mtype="mcp"), "my_tool", fake_execute)
    assert cap.meta.capability_type == "mcp"
    assert cap.is_executable()
    assert asyncio.run(cap.execute(a=1)) == "mcp-result"


def test_wrapped_capability():
    cap = WrappedCapability(_meta("wrapped"), lambda x: x * 2, executable_check=lambda: False)
    assert not cap.is_executable()
    assert asyncio.run(cap.execute(x=21)) == 42


def test_stats_success_rate():
    reg = CapabilityRegistry()
    cap = SimpleCap("statcap")
    reg.register(cap)
    reg._record("statcap", cap, success=True, ms=10)
    reg._record("statcap", cap, success=True, ms=20)
    reg._record("statcap", cap, success=False, ms=30)
    stats = reg.stats()
    entry = stats["statcap"][cap.meta.id]
    assert entry["use_count"] == 3
    assert abs(entry["success_rate"] - 2 / 3) < 1e-6
    assert abs(entry["avg_ms"] - 20) < 1e-6


def test_capability_market_export_install(tmp_path):
    from app.core.capability.market import CapabilityMarket

    reg = CapabilityRegistry()
    market = CapabilityMarket(registry=reg, market_dir=str(tmp_path / "cap_market"))
    cap = SimpleCap("market_cap")
    pkg_bytes = market.export_package(cap)
    assert pkg_bytes

    pkg = market.scan_package(pkg_bytes)
    assert pkg.cap_id == "market_cap"

    installed = market.install_package(pkg)
    assert installed is not None
    assert reg.get_implementations("market_cap")


def test_capability_market_lru_and_core():
    from app.core.capability.market import CapabilityMarket

    reg = CapabilityRegistry()
    market = CapabilityMarket(registry=reg, market_dir="data/test_cap_lru", lru_capacity=2)
    assert market.is_core_capability("model_call")
    assert not market.is_core_capability("random_cap")
    assert market.needs_lazy_load("random_cap")

    # LRU eviction
    for cid in ("a", "b", "c"):
        cap = SimpleCap(cid)
        reg.register(cap)
        market.touch(cid, cap)
    assert "a" not in market._lru


import asyncio
