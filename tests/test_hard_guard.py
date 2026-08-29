"""Tests for the hard security guard layer."""
from __future__ import annotations

import pytest

from app.core.security import get_hard_guard, hard_guard


def test_hard_guard_singleton():
    assert get_hard_guard() is hard_guard


def test_high_risk_patterns_blocked():
    g = hard_guard
    assert g.check_action("rm -rf /")[0] is False
    assert g.check_action("DROP TABLE users")[0] is False
    assert g.check_action("sudo ls")[0] is False
    assert g.check_action("chmod 777 /etc/passwd")[0] is False
    assert "Blocked" in g.check_action("rm -rf /")[1]


def test_safe_actions_allowed():
    g = hard_guard
    assert g.check_action("ls -la")[0] is True
    assert g.check_action("echo hello")[0] is True
    assert g.check_action("")[0] is True
    assert g.check_action("python3 script.py")[0] is True


def test_protected_components_immutable():
    g = hard_guard
    g.register_protected("event_bus", "bus_ref")
    assert g.get_protected("event_bus") == "bus_ref"
    refs = g.protected()
    assert refs["event_bus"] == "bus_ref"


@pytest.mark.asyncio
async def test_assert_allowed_async():
    g = hard_guard
    allowed, reason = await g.assert_allowed("shred file.txt")
    assert allowed is False
    assert "Blocked" in reason
    allowed, reason = await g.assert_allowed("ls -la")
    assert allowed is True


@pytest.mark.asyncio
async def test_snapshot_guard_aborts_on_failure():
    g = hard_guard

    async def bad_snap():
        return None

    sg = await g.require_snapshot_before("change config", bad_snap)
    assert sg.allowed is False
    assert "aborted" in sg.reason


@pytest.mark.asyncio
async def test_snapshot_guard_passes_on_success():
    g = hard_guard

    async def good_snap():
        return "snap_123"

    sg = await g.require_snapshot_before("change config", good_snap)
    assert sg.allowed is True
    assert sg.snapshot_id == "snap_123"


@pytest.mark.asyncio
async def test_snapshot_guard_blocks_high_risk():
    g = hard_guard

    async def good_snap():
        return "snap_456"

    sg = await g.require_snapshot_before("rm -rf /data", good_snap)
    assert sg.allowed is False
    assert "Blocked" in sg.reason
