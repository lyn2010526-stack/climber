"""Dual-loop coordinator: user profile (loop 1) x genetic evolution (loop 2).

A deliberately thin, fail-open bridge between the agent engine main loop and
the two adaptive algorithm layers. Every public method degrades silently on
any failure (debug log only), so the ReAct loop is never blocked or crashed by
profile or evolution code - including while the parallel evolution/profile
extensions are still being developed.
"""

from __future__ import annotations

import inspect
import os
from typing import TYPE_CHECKING, Any

import structlog

if TYPE_CHECKING:
    from collections.abc import Callable

logger = structlog.get_logger()


def _int_env(name: str, default: int) -> int:
    try:
        return max(1, int(os.environ.get(name, str(default))))
    except (TypeError, ValueError):
        return default


# Trigger one genetic-evolution step every N finished runs, per user.
EVOLUTION_TICK_INTERVAL = _int_env("CLIMBER_EVOLUTION_TICK_INTERVAL", 10)

# Below this weighted-sample confidence the profile context is considered too
# thin to be useful and is omitted from the prompt entirely.
PROFILE_MIN_CONFIDENCE = 0.2

_TOP_PREFERENCES = 5

# Candidate entry points the genetic-evolution extension (task B) may expose;
# tried in order, first callable wins. Missing names are a normal, tolerated
# state while that extension is in flight.
_EVOLUTION_ENTRY_NAMES: tuple[str, ...] = (
    "run_evolution_tick",
    "evolution_tick",
    "maybe_evolve",
)

_VALID_OUTCOMES = ("success", "failure")
_VALID_FEEDBACK = ("positive", "negative", "neutral")


class DualLoopCoordinator:
    """Coordinate the profile loop and the genetic evolution loop.

    Loop 1 (profile): format user-profile context for prompt injection and
    feed finished runs back into the profile store. Loop 2 (evolution): count
    finished runs and advance the genetic evolution engine on an interval.
    """

    def __init__(self) -> None:
        self._profile_store: Any | None = None
        self._profile_store_loaded = False
        self._run_counters: dict[str, int] = {}

    def _get_profile_store(self) -> Any | None:
        """Lazily build the ProfileStore once; None when unavailable."""
        if not self._profile_store_loaded:
            self._profile_store_loaded = True
            try:
                from app.core.profile.persistence import ProfileStore

                self._profile_store = ProfileStore()
            except Exception as exc:
                logger.debug("dual_loop.profile_store_unavailable", error=str(exc))
                self._profile_store = None
        return self._profile_store

    async def profile_context(self, user_id: str, instruction: str) -> str:
        """Format the user profile as injectable prompt context.

        Returns an empty string when the store is unavailable, the profile is
        disabled, or confidence is below :data:`PROFILE_MIN_CONFIDENCE` - all
        of which are normal, non-error states for a cold profile.
        """
        try:
            store = self._get_profile_store()
            if store is None:
                return ""
            summary = await store.summary(user_id)
            if not getattr(summary, "enabled", False):
                return ""
            confidence = float(getattr(summary, "confidence", 0.0))
            if confidence < PROFILE_MIN_CONFIDENCE:
                return ""
            hints = await store.suggestions(user_id, instruction)
            if not isinstance(hints, dict) or hints.get("enabled") is not True:
                return ""
            return self._format_profile_context(summary, hints)
        except Exception as exc:
            logger.debug("dual_loop.profile_context_failed", error=str(exc))
            return ""

    async def record_run_outcome(
        self,
        user_id: str,
        instruction: str,
        *,
        outcome: str,
        interrupted: bool = False,
        retried: bool = False,
        reasoning_level: str = "standard",
        tool: str | None = None,
        feedback: str = "neutral",
    ) -> None:
        """Map one finished run onto a ProfileEvent and persist it."""
        try:
            text = (instruction or "").strip()
            if not text:
                return
            store = self._get_profile_store()
            if store is None:
                return
            await store.record_event(
                user_id,
                instruction=text,
                task_type=self._infer_task_type(text),
                outcome=outcome if outcome in _VALID_OUTCOMES else "failure",
                interrupted=bool(interrupted),
                retried=bool(retried),
                reasoning_level=reasoning_level or "standard",
                tool=tool,
                feedback=feedback if feedback in _VALID_FEEDBACK else "neutral",
                source="agent_internal",
            )
        except Exception as exc:
            logger.debug("dual_loop.record_run_outcome_failed", error=str(exc))

    async def evolution_tick(self, user_id: str) -> None:
        """Advance the genetic evolution loop every N finished runs (best effort)."""
        try:
            count = self._run_counters.get(user_id, 0) + 1
            if count < EVOLUTION_TICK_INTERVAL:
                self._run_counters[user_id] = count
                return
            self._run_counters[user_id] = 0
            entry = self._resolve_evolution_entry()
            if entry is None:
                logger.debug("dual_loop.evolution_entry_unavailable")
                return
            result = self._call_evolution_entry(entry, user_id)
            if inspect.isawaitable(result):
                await result
        except Exception as exc:
            logger.debug("dual_loop.evolution_tick_failed", error=str(exc))

    def _resolve_evolution_entry(self) -> Callable[..., Any] | None:
        """Find the genetic-evolution entry point exposed by task B, if any."""
        try:
            from app.core.prompts import evolution as evolution_module
        except Exception as exc:
            logger.debug("dual_loop.evolution_module_unavailable", error=str(exc))
            return None
        for name in _EVOLUTION_ENTRY_NAMES:
            candidate = getattr(evolution_module, name, None)
            if callable(candidate):
                return candidate
        return None

    @staticmethod
    def _call_evolution_entry(entry: Callable[..., Any], user_id: str) -> Any:
        """Call a module entry using the argument shape its signature accepts."""
        try:
            signature = inspect.signature(entry)
        except (TypeError, ValueError):
            return entry(user_id)

        candidates = (((user_id,), {}), ((), {"user_id": user_id}), ((), {}))
        for args, kwargs in candidates:
            try:
                signature.bind(*args, **kwargs)
            except TypeError:
                continue
            return entry(*args, **kwargs)
        try:
            signature.bind()
        except TypeError:
            return entry(user_id)
        return entry()

    def _format_profile_context(self, summary: Any, hints: Any) -> str:
        """Render a ProfileSummary + suggestions payload as prompt text."""

        def ranked(values: dict[str, float]) -> str:
            items = sorted(values.items(), key=lambda kv: kv[1], reverse=True)
            return ", ".join(
                f"{key}:{value:.2f}" for key, value in items[:_TOP_PREFERENCES] if value > 0
            )

        lines = [
            "User behavior profile (advisory only; it must never override the current instruction):",
            f"- confidence: {float(getattr(summary, 'confidence', 0.0)):.2f}",
        ]
        cluster = getattr(summary, "persona_cluster", None)
        if cluster is not None:
            cluster_confidence = float(getattr(summary, "persona_cluster_confidence", 0.0))
            lines.append(f"- persona_cluster: {cluster} (confidence {cluster_confidence:.2f})")
        for label, values in (
            ("task_preferences", getattr(summary, "task_preferences", {}) or {}),
            ("tool_preferences", getattr(summary, "tool_preferences", {}) or {}),
            ("reasoning_preferences", getattr(summary, "reasoning_preferences", {}) or {}),
        ):
            rendered = ranked(values)
            if rendered:
                lines.append(f"- {label}: {rendered}")
        suggestion_map = hints.get("suggestions", {}) if isinstance(hints, dict) else {}
        if isinstance(suggestion_map, dict):
            top = {key: value for key, value in suggestion_map.items() if value}
            if top:
                lines.append(f"- suggestions: {top}")
        return "\n".join(lines)

    @staticmethod
    def _infer_task_type(instruction: str) -> str:
        """Deterministic, local keyword heuristic for the task_type field."""
        text = instruction.lower()
        for keyword, task_type in (
            ("test", "testing"),
            ("debug", "debugging"),
            ("fix", "debugging"),
            ("refactor", "refactoring"),
            ("document", "documentation"),
            ("docs", "documentation"),
            ("deploy", "deployment"),
            ("implement", "implementation"),
            ("add", "implementation"),
            ("create", "implementation"),
        ):
            if keyword in text:
                return task_type
        return "general"
