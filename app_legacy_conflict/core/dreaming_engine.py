"""Dreaming Engine — Background memory consolidation subsystem (Letta style).

Provides asynchronous memory consolidation that reviews recent conversation
history, identifies durable preferences/experiences worth remembering, and
updates MemFS memory files with extracted insights.

Reference: Letta's background memory consolidation (archival memory insertion,
core memory self-management). This implementation uses async tasks instead of
git worktrees for isolation.

Trigger modes:
- Message count: every N messages in a session
- Context compression: when conversation is compressed/summarized
- Manual: explicit consolidation request
"""

from __future__ import annotations

import asyncio
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable

import structlog

from app.core.memfs import MemFS
from app.core.memfs.memory_block import MemoryBlock

logger = structlog.get_logger()

DEFAULT_CONSOLIDATION_PROMPT = """You are a memory consolidation system. Review the conversation below and extract durable, memorable facts.

Categories to extract:
- preferences: User-stated likes, dislikes, habits, defaults
- facts: User identity, projects, tools, deadlines, decisions made
- patterns: Recurring behaviors or workflows observed
- corrections: User corrections to the assistant's behavior

Rules:
- Only extract facts that will remain true beyond this conversation.
- Do NOT extract transient states, greetings, or one-off requests.
- Each fact must be self-contained and independently understandable.
- Prefer concrete over vague: "User uses Python 3.12" over "User likes programming".

Output a JSON object with a single key "facts" containing an array of objects:
{{
  "facts": [
    {{"category": "preference", "content": "...", "importance": 0.7}},
    {{"category": "fact", "content": "...", "importance": 0.9}}
  ]
}}

Conversation:
{conversation}

Output only valid JSON, no commentary."""


@dataclass
class ConsolidationConfig:
    """Configuration for when and how consolidation triggers."""

    message_threshold: int = 10
    """Trigger consolidation after this many messages since last run."""

    min_messages: int = 4
    """Minimum messages required before consolidation can run."""

    enable_periodic: bool = False
    """Whether to enable periodic background consolidation."""

    periodic_interval_seconds: int = 3600
    """Interval for periodic consolidation if enabled."""

    max_facts_per_run: int = 20
    """Maximum number of facts to extract per consolidation run."""

    importance_threshold: float = 0.3
    """Minimum importance score for a fact to be stored."""

    llm_provider: str = "openai"
    llm_model: str = "gpt-4o-mini"
    api_key: str = ""
    base_url: str | None = None


@dataclass
class ConsolidatedFact:
    """A single extracted fact from consolidation."""

    category: str
    content: str
    importance: float
    tags: list[str] = field(default_factory=list)
    source_session_id: str = ""
    extracted_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_memory_block(self, path: str) -> MemoryBlock:
        """Convert to a MemoryBlock for MemFS storage."""
        tags = [self.category, "consolidated"] + self.tags
        return MemoryBlock.new(
            path=path,
            content=self.content,
            description=f"{self.category}: {self.content[:60]}",
            category="reference",
            importance=self.importance,
            tags=tags,
        )


@dataclass
class ConsolidationResult:
    """Result of a consolidation pass."""

    consolidation_id: str
    session_id: str
    timestamp: str
    facts_extracted: int
    facts_stored: int
    facts_deduplicated: int
    facts_low_importance: int
    memory_paths: list[str]
    duration_ms: float
    trigger: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "consolidation_id": self.consolidation_id,
            "session_id": self.session_id,
            "timestamp": self.timestamp,
            "facts_extracted": self.facts_extracted,
            "facts_stored": self.facts_stored,
            "facts_deduplicated": self.facts_deduplicated,
            "facts_low_importance": self.facts_low_importance,
            "memory_paths": self.memory_paths,
            "duration_ms": self.duration_ms,
            "trigger": self.trigger,
        }


class DreamingEngine:
    """Background memory consolidation engine.

    Reviews recent conversation history to extract durable memories
    and persists them to MemFS. Designed as an async-friendly service
    that runs alongside agent sessions without blocking.

    Args:
        memfs: The MemFS instance for memory storage.
        llm_caller: Async callable that takes messages and returns text.
        config: Consolidation configuration.
        consolidation_prompt: Custom prompt for fact extraction.
    """

    def __init__(
        self,
        memfs: MemFS,
        llm_callable: Callable[[list[dict[str, str]]], Awaitable[str]] | None = None,
        config: ConsolidationConfig | None = None,
        consolidation_prompt: str | None = None,
    ) -> None:
        self._memfs = memfs
        self._llm_callable = llm_callable
        self._config = config or ConsolidationConfig()
        self._consolidation_prompt = consolidation_prompt or DEFAULT_CONSOLIDATION_PROMPT

        self._last_consolidation: dict[str, float] = {}
        self._message_counts: dict[str, int] = {}
        self._consolidation_history: list[ConsolidationResult] = []
        self._running = False
        self._periodic_task: asyncio.Task | None = None
        self._lock = asyncio.Lock()

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def consolidation_count(self) -> int:
        return len(self._consolidation_history)

    async def should_trigger(self, session_id: str) -> bool:
        """Check if enough messages have accumulated to trigger consolidation.

        Args:
            session_id: The session to check.

        Returns:
            True if consolidation should run, False otherwise.
        """
        count = self._message_counts.get(session_id, 0)
        if count < self._config.min_messages:
            return False

        elapsed = self._last_consolidation.get(session_id, 0)
        if elapsed > 0:
            elapsed_seconds = datetime.now(timezone.utc).timestamp() - elapsed
            if elapsed_seconds < self._config.periodic_interval_seconds:
                return count >= self._config.message_threshold

        return count >= self._config.message_threshold

    def record_messages(self, session_id: str, count: int = 1) -> None:
        """Record new messages for a session.

        Args:
            session_id: The session identifier.
            count: Number of messages to add.
        """
        self._message_counts[session_id] = (
            self._message_counts.get(session_id, 0) + count
        )

    async def consolidate(
        self,
        session_id: str,
        messages: list[dict[str, str]] | None = None,
        trigger: str = "manual",
    ) -> ConsolidationResult:
        """Run memory consolidation for a session.

        1. Fetch recent conversation
        2. Ask LLM to extract memorable facts
        3. Deduplicate against existing memories
        4. Store new facts to MemFS
        5. Commit changes

        Args:
            session_id: The session to consolidate.
            messages: Optional pre-fetched conversation messages.
            trigger: What triggered this consolidation (manual, threshold, periodic).

        Returns:
            ConsolidationResult with stats about the operation.
        """
        start_time = datetime.now(timezone.utc)
        consolidation_id = str(uuid.uuid4())[:12]

        async with self._lock:
            result = await self._run_consolidation(
                session_id, messages, trigger, consolidation_id, start_time
            )

        self._consolidation_history.append(result)
        self._last_consolidation[session_id] = datetime.now(timezone.utc).timestamp()
        self._message_counts[session_id] = 0

        if len(self._consolidation_history) > 100:
            self._consolidation_history = self._consolidation_history[-50:]

        logger.info(
            "dreaming_consolidation_complete",
            consolidation_id=consolidation_id,
            session_id=session_id,
            facts_stored=result.facts_stored,
            trigger=trigger,
            duration_ms=result.duration_ms,
        )

        return result

    async def _run_consolidation(
        self,
        session_id: str,
        messages: list[dict[str, str]] | None,
        trigger: str,
        consolidation_id: str,
        start_time: datetime,
    ) -> ConsolidationResult:
        """Internal consolidation logic."""
        facts: list[ConsolidatedFact] = []
        memory_paths: list[str] = []
        facts_deduplicated = 0
        facts_low_importance = 0

        if messages is None:
            messages = await self._fetch_conversation(session_id)

        if not messages:
            return self._empty_result(
                consolidation_id, session_id, start_time, trigger
            )

        raw_facts = await self._extract_facts(messages)

        for raw in raw_facts:
            importance = raw.get("importance", 0.5)
            if importance < self._config.importance_threshold:
                facts_low_importance += 1
                continue

            fact = ConsolidatedFact(
                category=raw.get("category", "fact"),
                content=raw.get("content", ""),
                importance=min(1.0, max(0.0, importance)),
                tags=raw.get("tags", []),
                source_session_id=session_id,
            )

            if await self._is_duplicate(fact):
                facts_deduplicated += 1
                continue

            facts.append(fact)

        for fact in facts[: self._config.max_facts_per_run]:
            try:
                path = await self._store_fact(fact, session_id)
                memory_paths.append(path)
            except Exception as e:
                logger.warning(
                    "dreaming_store_fact_failed",
                    fact=fact.content[:50],
                    error=str(e),
                )

        elapsed = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000

        return ConsolidationResult(
            consolidation_id=consolidation_id,
            session_id=session_id,
            timestamp=start_time.isoformat(),
            facts_extracted=len(raw_facts),
            facts_stored=len(memory_paths),
            facts_deduplicated=facts_deduplicated,
            facts_low_importance=facts_low_importance,
            memory_paths=memory_paths,
            duration_ms=elapsed,
            trigger=trigger,
        )

    def _empty_result(
        self,
        consolidation_id: str,
        session_id: str,
        start_time: datetime,
        trigger: str,
    ) -> ConsolidationResult:
        """Create an empty consolidation result."""
        elapsed = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
        return ConsolidationResult(
            consolidation_id=consolidation_id,
            session_id=session_id,
            timestamp=start_time.isoformat(),
            facts_extracted=0,
            facts_stored=0,
            facts_deduplicated=0,
            facts_low_importance=0,
            memory_paths=[],
            duration_ms=elapsed,
            trigger=trigger,
        )

    async def _fetch_conversation(
        self, session_id: str
    ) -> list[dict[str, str]]:
        """Fetch recent conversation history for a session.

        Attempts to read from the MemFS conversations directory.
        Returns empty list if no history is found.

        Args:
            session_id: The session identifier.

        Returns:
            List of message dicts with 'role' and 'content'.
        """
        try:
            history_path = f"conversations/{session_id}.json"
            raw = await self._memfs.read(history_path)
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                return parsed
            if isinstance(parsed, dict) and "messages" in parsed:
                return parsed["messages"]
        except FileNotFoundError:
            logger.debug(
                "dreaming_no_history_found",
                session_id=session_id,
            )
        except (json.JSONDecodeError, Exception) as e:
            logger.warning(
                "dreaming_fetch_conversation_failed",
                session_id=session_id,
                error=str(e),
            )

        return []

    async def _extract_facts(
        self,
        messages: list[dict[str, str]],
    ) -> list[dict[str, Any]]:
        """Use LLM to extract memorable facts from conversation.

        Falls back to heuristic extraction if no LLM caller is configured.

        Args:
            messages: Conversation messages.

        Returns:
            List of raw fact dicts.
        """
        conversation_text = self._format_messages(messages)

        if self._llm_callable is None:
            return self._heuristic_extract(messages)

        try:
            prompt = self._consolidation_prompt.format(
                conversation=conversation_text
            )
            response = await self._llm_callable([
                {"role": "user", "content": prompt},
            ])
            return self._parse_facts_response(response)
        except Exception as e:
            logger.warning(
                "dreaming_llm_extract_failed",
                error=str(e),
                fallback="heuristic",
            )
            return self._heuristic_extract(messages)

    def _format_messages(self, messages: list[dict[str, str]]) -> str:
        """Format messages into a single string for LLM input."""
        lines: list[str] = []
        for msg in messages:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            if content:
                lines.append(f"[{role.upper()}] {content}")
        return "\n\n".join(lines)

    def _parse_facts_response(self, response: str) -> list[dict[str, Any]]:
        """Parse LLM response into raw fact dicts.

        Handles both clean JSON and JSON wrapped in markdown code blocks.
        """
        text = response.strip()

        if text.startswith("```"):
            lines = text.splitlines()
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            text = "\n".join(lines).strip()

        try:
            data = json.loads(text)
            facts = data.get("facts", [])
            if isinstance(facts, list):
                return facts
        except json.JSONDecodeError:
            logger.warning("dreaming_facts_parse_failed", response=text[:200])

        return []

    def _heuristic_extract(
        self,
        messages: list[dict[str, str]],
    ) -> list[dict[str, Any]]:
        """Fallback heuristic fact extraction without LLM.

        Uses keyword signals to identify preferences, facts, and decisions.
        """
        results: list[dict[str, Any]] = []

        preference_signals = [
            "i prefer", "i like", "i want", "i need",
            "i always", "i never", "my favorite", "remember that",
        ]
        fact_signals = [
            "my name is", "i work at", "i live in", "i use",
            "the project is", "the deadline is", "we decided",
        ]
        decision_signals = [
            "let's go with", "we'll use", "decided to", "the plan is",
            "agreed that", "final choice", "conclusion:",
        ]

        for msg in messages:
            content = msg.get("content", "")
            if not content or len(content) < 10:
                continue
            if msg.get("role") != "user":
                continue

            lower = content.lower()

            for signal in preference_signals:
                if signal in lower:
                    results.append({
                        "category": "preference",
                        "content": content[:500],
                        "importance": 0.7,
                        "tags": ["heuristic", "preference"],
                    })
                    break

            for signal in fact_signals:
                if signal in lower:
                    results.append({
                        "category": "fact",
                        "content": content[:500],
                        "importance": 0.8,
                        "tags": ["heuristic", "fact"],
                    })
                    break

            for signal in decision_signals:
                if signal in lower:
                    results.append({
                        "category": "decision",
                        "content": content[:500],
                        "importance": 0.75,
                        "tags": ["heuristic", "decision"],
                    })
                    break

        return results

    async def _is_duplicate(self, fact: ConsolidatedFact) -> bool:
        """Check if a fact already exists in memory.

        Uses MemFS search to find semantically similar existing facts.
        """
        try:
            existing = await self._memfs.search(fact.content[:50])
            for result in existing:
                if result.get("total_matches", 0) > 0:
                    return True
        except Exception as e:
            logger.debug("dreaming_dedup_error", error=str(e))

        return False

    async def _store_fact(
        self,
        fact: ConsolidatedFact,
        session_id: str,
    ) -> str:
        """Store a consolidated fact to MemFS.

        Args:
            fact: The fact to store.
            session_id: Source session for path naming.

        Returns:
            The memory file path where the fact was stored.
        """
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        short_id = uuid.uuid4().hex[:8]
        category = fact.category.replace(" ", "_")
        path = f"reference/consolidated/{category}/{timestamp}_{short_id}.md"

        block = fact.to_memory_block(path)
        await self._memfs.write_block(block)

        logger.debug(
            "dreaming_fact_stored",
            path=path,
            category=fact.category,
            importance=fact.importance,
        )

        return path

    async def start_periodic(self, session_id: str | None = None) -> None:
        """Start periodic background consolidation.

        Args:
            session_id: Optional session to consolidate. If None, all sessions
                are checked during each periodic pass.
        """
        if self._running:
            logger.warning("dreaming_periodic_already_running")
            return

        if not self._config.enable_periodic:
            logger.warning(
                "dreaming_periodic_disabled",
                hint="Set config.enable_periodic=True to enable",
            )
            return

        self._running = True
        self._periodic_task = asyncio.create_task(
            self._periodic_loop(session_id)
        )
        logger.info(
            "dreaming_periodic_started",
            interval_seconds=self._config.periodic_interval_seconds,
        )

    async def stop_periodic(self) -> None:
        """Stop the periodic consolidation loop."""
        self._running = False
        if self._periodic_task is not None:
            self._periodic_task.cancel()
            try:
                await self._periodic_task
            except asyncio.CancelledError:
                pass
            self._periodic_task = None
        logger.info("dreaming_periodic_stopped")

    async def _periodic_loop(self, session_id: str | None) -> None:
        """Internal periodic consolidation loop."""
        interval = self._config.periodic_interval_seconds

        while self._running:
            try:
                await asyncio.sleep(interval)

                if not self._running:
                    break

                if session_id:
                    if await self.should_trigger(session_id):
                        await self.consolidate(session_id, trigger="periodic")
                else:
                    for sid in list(self._message_counts.keys()):
                        if await self.should_trigger(sid):
                            await self.consolidate(sid, trigger="periodic")

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("dreaming_periodic_error", error=str(e))

    def get_stats(self) -> dict[str, Any]:
        """Get dreaming engine statistics.

        Returns:
            Dict with runtime stats.
        """
        return {
            "is_running": self._running,
            "consolidation_count": len(self._consolidation_history),
            "tracked_sessions": len(self._message_counts),
            "total_messages_tracked": sum(self._message_counts.values()),
            "last_consolidations": {
                k: datetime.fromtimestamp(v, tz=timezone.utc).isoformat()
                for k, v in self._last_consolidation.items()
            },
        }

    def get_history(
        self, limit: int = 10
    ) -> list[ConsolidationResult]:
        """Get recent consolidation history.

        Args:
            limit: Maximum number of results to return.

        Returns:
            List of recent ConsolidationResult instances.
        """
        return self._consolidation_history[-limit:]
