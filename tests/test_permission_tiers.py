"""Tests for the three-tier permission system."""

from __future__ import annotations

from app.core.permission_tiers import (
    PermissionTier,
    PermissionTierManager,
    TierEscalationRequest,
)


class TestPermissionTier:
    def test_tier_ordering(self) -> None:
        assert PermissionTier.READ_ONLY < PermissionTier.STANDARD
        assert PermissionTier.STANDARD < PermissionTier.HIGH_RISK

    def test_tier_values(self) -> None:
        assert PermissionTier.READ_ONLY.value == 1
        assert PermissionTier.STANDARD.value == 2
        assert PermissionTier.HIGH_RISK.value == 3


class TestPermissionTierManager:
    def test_default_tier(self) -> None:
        manager = PermissionTierManager()
        assert manager.get_session_tier("session-1") == PermissionTier.STANDARD

    def test_set_session_tier(self) -> None:
        manager = PermissionTierManager()
        manager.set_session_tier("session-1", PermissionTier.READ_ONLY)
        assert manager.get_session_tier("session-1") == PermissionTier.READ_ONLY

    def test_read_only_can_read(self) -> None:
        manager = PermissionTierManager()
        manager.set_session_tier("s1", PermissionTier.READ_ONLY)
        result = manager.evaluate("s1", "read_file")
        assert result.allowed

    def test_read_only_cannot_write(self) -> None:
        manager = PermissionTierManager()
        manager.set_session_tier("s1", PermissionTier.READ_ONLY)
        result = manager.evaluate("s1", "write_file")
        assert not result.allowed
        assert result.needs_escalation

    def test_standard_can_write(self) -> None:
        manager = PermissionTierManager()
        manager.set_session_tier("s1", PermissionTier.STANDARD)
        result = manager.evaluate("s1", "write_file")
        assert result.allowed

    def test_standard_cannot_delete(self) -> None:
        manager = PermissionTierManager()
        manager.set_session_tier("s1", PermissionTier.STANDARD)
        result = manager.evaluate("s1", "delete_file")
        assert not result.allowed

    def test_high_risk_can_do_everything(self) -> None:
        manager = PermissionTierManager()
        manager.set_session_tier("s1", PermissionTier.HIGH_RISK)
        assert manager.evaluate("s1", "read_file").allowed
        assert manager.evaluate("s1", "write_file").allowed
        assert manager.evaluate("s1", "delete_file").allowed
        assert manager.evaluate("s1", "sudo").allowed

    def test_override_tool_tier(self) -> None:
        manager = PermissionTierManager()
        manager.override_tool_tier("custom_tool", PermissionTier.HIGH_RISK)
        assert manager.get_tool_tier("custom_tool") == PermissionTier.HIGH_RISK

    def test_request_escalation_standard(self) -> None:
        manager = PermissionTierManager()
        request = TierEscalationRequest(
            requested_tier=PermissionTier.STANDARD,
            reason="Need to write files",
        )
        assert manager.request_escalation(request)
        assert request.approved

    def test_request_escalation_high_risk(self) -> None:
        manager = PermissionTierManager()
        request = TierEscalationRequest(
            requested_tier=PermissionTier.HIGH_RISK,
            reason="Need to delete",
        )
        assert not manager.request_escalation(request)
        assert not request.approved

    def test_tier_prompt_fragment(self) -> None:
        manager = PermissionTierManager()
        fragment = manager.get_tier_prompt_fragment(PermissionTier.READ_ONLY)
        assert "READ-ONLY" in fragment

    def test_reset_session(self) -> None:
        manager = PermissionTierManager()
        manager.set_session_tier("s1", PermissionTier.HIGH_RISK)
        manager.reset_session("s1")
        assert manager.get_session_tier("s1") == PermissionTier.STANDARD

    def test_get_all_tiers_info(self) -> None:
        manager = PermissionTierManager()
        info = manager.get_all_tiers_info()
        assert "tiers" in info
        assert "default_tier" in info
        assert len(info["tiers"]) == 3

    def test_unknown_tool_defaults_to_standard(self) -> None:
        manager = PermissionTierManager()
        tier = manager.get_tool_tier("completely_unknown_tool")
        assert tier == PermissionTier.STANDARD
