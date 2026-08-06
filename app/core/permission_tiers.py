"""Three-tier permission control system.

Tier 1: READ_ONLY — View-only operations (no modifications)
Tier 2: STANDARD — Normal modifications (create, edit, run)
Tier 3: HIGH_RISK — Destructive operations (delete, system commands, network)

Each tool is assigned a required tier. The user's current tier determines
which tools they can invoke. Tier escalation requires explicit approval.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import IntEnum, StrEnum
from typing import Any

logger = logging.getLogger(__name__)


class PermissionTier(IntEnum):
    """Three permission tiers ordered by privilege level."""

    READ_ONLY = 1
    STANDARD = 2
    HIGH_RISK = 3


class PermissionAction(StrEnum):
    """Common permission actions."""

    READ = "read"
    WRITE = "write"
    EXECUTE = "execute"
    DELETE = "delete"
    NETWORK = "network"
    SYSTEM = "system"
    ADMIN = "admin"


TIER_PROMPT_FRAGMENTS: dict[PermissionTier, str] = {
    PermissionTier.READ_ONLY: """[PERMISSION LEVEL: READ-ONLY]
You are operating in read-only mode. You may:
- Read files and directories
- Search code and documentation
- View system status and logs
You may NOT: create, modify, or delete files; execute commands; make network requests.
""",
    PermissionTier.STANDARD: """[PERMISSION LEVEL: STANDARD]
You have standard modification privileges. You may:
- Read, create, and edit files
- Execute non-destructive commands
- Make network requests to approved endpoints
- Run tests and builds
You may NOT: delete protected files; execute system-level commands; modify permissions.
""",
    PermissionTier.HIGH_RISK: """[PERMISSION LEVEL: HIGH-RISK]
You have elevated privileges. You may execute any operation including:
- Destructive file operations (delete, overwrite)
- System commands and service management
- Network configuration changes
- Permission modifications
Exercise extreme caution. Prefer reversible operations. Confirm scope before executing.
""",
}

TOOL_TIER_MAP: dict[str, PermissionTier] = {
    "read_file": PermissionTier.READ_ONLY,
    "list_files": PermissionTier.READ_ONLY,
    "search_code": PermissionTier.READ_ONLY,
    "grep": PermissionTier.READ_ONLY,
    "cat": PermissionTier.READ_ONLY,
    "head": PermissionTier.READ_ONLY,
    "tail": PermissionTier.READ_ONLY,
    "find_files": PermissionTier.READ_ONLY,
    "get_file_info": PermissionTier.READ_ONLY,
    "web_search": PermissionTier.READ_ONLY,
    "fetch_url": PermissionTier.READ_ONLY,
    "wikipedia_summary": PermissionTier.READ_ONLY,
    "write_file": PermissionTier.STANDARD,
    "edit_file": PermissionTier.STANDARD,
    "create_file": PermissionTier.STANDARD,
    "run_command": PermissionTier.STANDARD,
    "execute_code": PermissionTier.STANDARD,
    "run_tests": PermissionTier.STANDARD,
    "git_status": PermissionTier.READ_ONLY,
    "git_diff": PermissionTier.READ_ONLY,
    "git_log": PermissionTier.READ_ONLY,
    "git_commit": PermissionTier.STANDARD,
    "git_push": PermissionTier.STANDARD,
    "browser_navigate": PermissionTier.READ_ONLY,
    "browser_click": PermissionTier.STANDARD,
    "browser_type": PermissionTier.STANDARD,
    "delete_file": PermissionTier.HIGH_RISK,
    "rm": PermissionTier.HIGH_RISK,
    "sudo": PermissionTier.HIGH_RISK,
    "chmod": PermissionTier.HIGH_RISK,
    "chown": PermissionTier.HIGH_RISK,
    "systemctl": PermissionTier.HIGH_RISK,
    "docker_run": PermissionTier.STANDARD,
    "docker_exec": PermissionTier.STANDARD,
    "docker_rm": PermissionTier.HIGH_RISK,
    "pip_install": PermissionTier.STANDARD,
    "npm_install": PermissionTier.STANDARD,
    "install_package": PermissionTier.HIGH_RISK,
    "network_request": PermissionTier.STANDARD,
    "curl": PermissionTier.STANDARD,
    "wget": PermissionTier.STANDARD,
    "ssh": PermissionTier.HIGH_RISK,
    "scp": PermissionTier.HIGH_RISK,
}


@dataclass
class TierEscalationRequest:
    """Request to escalate permission tier."""

    requested_tier: PermissionTier
    reason: str
    tool_name: str = ""
    arguments: dict[str, Any] = field(default_factory=dict)
    approved: bool = False
    expires_at: str | None = None


@dataclass
class TierEvaluationResult:
    """Result of a permission tier evaluation."""

    allowed: bool
    required_tier: PermissionTier
    current_tier: PermissionTier
    reason: str = ""
    needs_escalation: bool = False


class PermissionTierManager:
    """Manages three-tier permission control."""

    def __init__(self, default_tier: PermissionTier = PermissionTier.STANDARD) -> None:
        self._default_tier = default_tier
        self._session_tiers: dict[str, PermissionTier] = {}
        self._escalation_history: list[TierEscalationRequest] = []
        self._tool_tier_overrides: dict[str, PermissionTier] = {}

    def get_session_tier(self, session_id: str) -> PermissionTier:
        """Get the current permission tier for a session."""
        return self._session_tiers.get(session_id, self._default_tier)

    def set_session_tier(self, session_id: str, tier: PermissionTier) -> None:
        """Set the permission tier for a session."""
        self._session_tiers[session_id] = tier
        logger.info("Session %s permission tier set to %s", session_id[:8], tier.name)

    def override_tool_tier(self, tool_name: str, tier: PermissionTier) -> None:
        """Override the required tier for a specific tool."""
        self._tool_tier_overrides[tool_name] = tier

    def get_tool_tier(self, tool_name: str) -> PermissionTier:
        """Get the required tier for a tool."""
        if tool_name in self._tool_tier_overrides:
            return self._tool_tier_overrides[tool_name]
        return TOOL_TIER_MAP.get(tool_name, PermissionTier.STANDARD)

    def evaluate(
        self,
        session_id: str,
        tool_name: str,
        arguments: dict[str, Any] | None = None,
    ) -> TierEvaluationResult:
        """Evaluate whether a tool call is permitted at the current tier."""
        current_tier = self.get_session_tier(session_id)
        required_tier = self.get_tool_tier(tool_name)

        if current_tier >= required_tier:
            return TierEvaluationResult(
                allowed=True,
                required_tier=required_tier,
                current_tier=current_tier,
                reason=f"Access granted: {current_tier.name} >= {required_tier.name}",
            )

        return TierEvaluationResult(
            allowed=False,
            required_tier=required_tier,
            current_tier=current_tier,
            reason=f"Access denied: requires {required_tier.name}, current is {current_tier.name}",
            needs_escalation=True,
        )

    def request_escalation(self, request: TierEscalationRequest) -> bool:
        """Request tier escalation. Returns True if auto-approved."""
        self._escalation_history.append(request)

        if request.requested_tier <= self._default_tier:
            request.approved = True
            return True

        if request.requested_tier == PermissionTier.HIGH_RISK:
            request.approved = False
            return False

        request.approved = True
        return True

    def get_tier_prompt_fragment(self, tier: PermissionTier) -> str:
        """Get the prompt fragment for a permission tier."""
        return TIER_PROMPT_FRAGMENTS.get(tier, "")

    def get_escalation_history(
        self, session_id: str | None = None
    ) -> list[TierEscalationRequest]:
        """Get escalation history, optionally filtered by session."""
        if session_id:
            return [
                r
                for r in self._escalation_history
                if r.tool_name.startswith(session_id[:8])
            ]
        return list(self._escalation_history)

    def reset_session(self, session_id: str) -> None:
        """Reset a session to the default tier."""
        self._session_tiers.pop(session_id, None)

    def get_all_tiers_info(self) -> dict[str, Any]:
        """Get information about all permission tiers."""
        return {
            "default_tier": self._default_tier.name,
            "tiers": {
                tier.name: {
                    "level": tier.value,
                    "description": self._get_tier_description(tier),
                    "tools_count": sum(
                        1 for t in TOOL_TIER_MAP.values() if t == tier
                    ),
                }
                for tier in PermissionTier
            },
            "tool_mappings": {
                name: tier.name for name, tier in TOOL_TIER_MAP.items()
            },
        }

    def _get_tier_description(self, tier: PermissionTier) -> str:
        descriptions = {
            PermissionTier.READ_ONLY: "View-only operations, no modifications",
            PermissionTier.STANDARD: "Normal modifications, safe execution",
            PermissionTier.HIGH_RISK: "Destructive operations, system-level access",
        }
        return descriptions.get(tier, "Unknown tier")
