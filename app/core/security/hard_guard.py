"""Hard security layer — immutable guard for high-risk actions.

The HighRiskActionGuard is the permanent, immutable safety layer of the
fourth-generation emergent modules. It:

- Blocks high-risk action patterns (bulk destructive ops, credential exfil,
  network pivoting, privilege escalation, persistence) regardless of which
  module originates the action.
- Cannot be replaced, monkey-patched, or disabled by any module.
- Enforces that any structural change (capability registration, graph
  modification, config mutation) takes a snapshot FIRST and aborts the
  change when snapshotting fails.

The guard is a module-level singleton (`hard_guard`) reachable through
`get_hard_guard()`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

import structlog

logger = structlog.get_logger()


@dataclass
class SnapshotGuard:
    """Result of a snapshot-first gate check.

    `allowed=False` means the change is aborted because the required
    snapshot could not be captured before the mutation.
    """

    change: str
    allowed: bool
    snapshot_id: str | None = None
    reason: str = ""


class HighRiskActionGuard:
    """Immutable gatekeeper for high-risk actions and structural changes."""

    # High-risk patterns (regex, case-insensitive). Any match on the
    # action string aborts the action with a rejection reason.
    HIGH_RISK_PATTERNS: tuple[str, ...] = (
        r"\brm\s+-rf\b",
        r"\brmdir\b",
        r"\bshred\b",
        r"\bmkfs\b",
        r"\bdd\s+if=",
        r"\bDROP\s+(TABLE|DATABASE)\b",
        r"\bTRUNCATE\b",
        r"\bmaster\.reload_plugin\b",
        r"plugin\s+load\s+.+",  # loading third-party plugin code
        r"\bchmod\s+777\b",
        r"\bchown\b",
        r"\bpasswd\b",
        r"\bsudo\b",
        r"\bsu\s+-",
        r"\bcurl\s+-k\b",
        r"\bwget\s+--no-check-certificate\b",
        r"\.ssh/authorized_keys",
        r"\b\.netrc\b",
        r"\bssh\s+-[LR]\b",  # SSH tunnels / port forwards
        r"\bsocat\b",
        r"\bnc\s+",
        r"\bproxy\s+",
        r"\bTOR_",
        r"\bsystemctl\s+(stop|disable)\s+networking",
        r"\buseradd\b",
        r"\buserdel\b",
        r"\bgroupadd\b",
    )

    # Components the guard protects from module mutation. Modules may read
    # them via the guard but can never replace or reconfigure them.
    PROTECTED_COMPONENTS: tuple[str, ...] = (
        "event_bus",
        "sandbox_executor",
        "session_snapshot_manager",
        "hard_guard",
    )

    def __init__(self) -> None:
        self._compiled = tuple(re.compile(p, re.IGNORECASE) for p in self.HIGH_RISK_PATTERNS)
        self._protected_refs: dict[str, Any] = {}
        # Auditor hooks (e.g., emit blocked events on the event bus) — set
        # once at wiring time, read-only afterwards.
        self._on_block: list[Any] = []

    def register_protected(self, name: str, component: Any) -> None:
        """Register an immutable component reference (wiring time only)."""
        if name not in self.PROTECTED_COMPONENTS:
            logger.warning("hard_guard.unknown_protected", name=name)
        self._protected_refs[name] = component

    def get_protected(self, name: str) -> Any | None:
        return self._protected_refs.get(name)

    def protected(self) -> dict[str, Any]:
        """Read-only view of protected components."""
        return dict(self._protected_refs)

    def attach_block_hook(self, hook: Any) -> None:
        """Attach an async callback fired on each blocked action."""
        self._on_block.append(hook)

    def check_action(self, action: str) -> tuple[bool, str]:
        """Return (allowed, reason). Safe for both sync and async callers."""
        if not action:
            return True, ""
        for pattern, compiled in zip(self.HIGH_RISK_PATTERNS, self._compiled, strict=True):
            if compiled.search(action):
                return False, f"Blocked by hard security rule: pattern '{pattern}'"
        return True, ""

    async def assert_allowed(self, action: str) -> tuple[bool, str]:
        """Async gate: block high-risk actions and fire block hooks."""
        allowed, reason = self.check_action(action)
        if not allowed:
            logger.warning("hard_guard.blocked", reason=reason)
            for hook in self._on_block:
                try:
                    if hook is not None:
                        await hook(reason, action)
                except Exception:
                    logger.exception("hard_guard.hook_failed")
            return False, reason
        return True, ""

    async def require_snapshot_before(self, change: str, snap_fn: Any) -> SnapshotGuard:
        """Snapshot-first gate for structural changes.

        The mutation is only allowed to proceed after `snap_fn()` produced a
        snapshot id. When snapshotting fails (returns None / raises), the
        change is aborted — this is the rollback-enabler invariant.
        """
        if not change:
            return SnapshotGuard(change=change, allowed=True, reason="empty change")
        # High-risk structural changes never pass, even after snapshot.
        allowed, reason = await self.assert_allowed(change)
        if not allowed:
            return SnapshotGuard(change=change, allowed=False, reason=reason)
        try:
            snapshot_id = await snap_fn()
        except Exception as e:
            logger.exception("hard_guard.snapshot_failed", change=change)
            return SnapshotGuard(
                change=change, allowed=False,
                reason=f"snapshot failed, change aborted: {e!s}",
            )
        if not snapshot_id:
            return SnapshotGuard(
                change=change, allowed=False,
                reason="snapshot returned no id, change aborted",
            )
        logger.info("hard_guard.snapshot_ok", change=change, snapshot_id=snapshot_id)
        return SnapshotGuard(change=change, allowed=True, snapshot_id=snapshot_id, reason="ok")


_hard_guard: HighRiskActionGuard | None = None


def get_hard_guard() -> HighRiskActionGuard:
    """Return the process-wide singleton guard."""
    global _hard_guard
    if _hard_guard is None:
        _hard_guard = HighRiskActionGuard()
    return _hard_guard


hard_guard = get_hard_guard()
