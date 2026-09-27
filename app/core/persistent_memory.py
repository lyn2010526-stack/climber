"""Persistent memory service — MemGPT/Letta-style memory management.

Provides:
- Episodic memory storage, retrieval, and summarization
- Knowledge graph construction and querying
- Opt-in, bounded graph memory: triples extracted from episodic content and read
  back per agent, gated by ``Agent.memory_config["graph_memory"]``
- User profile management
- Automatic memory extraction from conversations
- Relevance-based memory retrieval with scoring
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

import structlog
from sqlalchemy import String, and_, desc, func, select

from app.core.vector_memory import vector_memory
from app.storage import async_session
from app.storage.models_memory import (
    ArchivalPassage,
    EpisodicMemory,
    KnowledgeGraph,
    MemoryRetrievalLog,
    UserProfile,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

logger = structlog.get_logger()

# ─── Graph memory configuration and extraction ──────────────────────────────

#: Key inside ``Agent.memory_config`` that opts an agent into graph memory.
GRAPH_MEMORY_CONFIG_KEY = "graph_memory"

#: Per-turn triple budget requested when the config enables graph memory but
#: omits ``max_triples_per_turn``.
GRAPH_MEMORY_DEFAULT_TRIPLES = 3

#: Hard ceiling on ``max_triples_per_turn``. A config value can lower the
#: budget but never lift it past this bound, so a misconfigured agent cannot
#: turn one turn into an unbounded number of graph writes.
GRAPH_MEMORY_HARD_TRIPLE_CAP = 12

#: Hard ceiling on rows returned by any graph read helper.
GRAPH_QUERY_HARD_LIMIT = 20

#: Default number of rows a consumer asks for.
GRAPH_QUERY_DEFAULT_LIMIT = 5

#: Confidence stamped on heuristically extracted triples. Deliberately below
#: the 0.8 default of :meth:`add_triple` because the extractor is pattern based.
GRAPH_EXTRACT_CONFIDENCE = 0.6

#: Marks triples written without an agent scope (the shared pool).
GRAPH_SCOPE_SHARED = "shared"

#: Reserved tag prefix carrying the agent scope on triples. ``knowledge_graph``
#: has no ``agent_id`` column and no migration may be added, so the scope rides
#: in the existing JSON ``tags`` column.
GRAPH_SCOPE_TAG_PREFIX = "agent:"

#: Max words accepted for one extracted entity. Keeps runaway noun phrases out
#: of a 200-character column.
_GRAPH_ENTITY_MAX_WORDS = 4

# Leading/trailing words stripped from an extracted entity: determiners,
# prepositions, copulas and auxiliaries. Stripping both ends keeps a window
# from dragging "the", "for" or a stray verb into the stored entity.
_GRAPH_EDGE_STOPWORDS = frozenset({
    # determiners / demonstratives
    "a", "an", "the", "this", "that", "these", "those", "our", "my", "its",
    "their", "his", "her", "any", "some", "each", "every",
    # prepositions
    "for", "of", "in", "on", "at", "to", "from", "by", "with", "about",
    # verbs / auxiliaries
    "is", "are", "was", "were", "be", "been", "has", "have", "had", "do",
    "does", "did",
})

_GRAPH_USER_SUBJECT = "user"

# Role labels of the "User: ... Assistant: ..." transcript format episodic
# memories are stored in. They prefix a sentence and are not entities, so they
# are removed before extraction.
_GRAPH_TRANSCRIPT_LABEL = re.compile(
    r"^\s*(?:user|assistant|system|human|bot)\s*:\s*", re.IGNORECASE
)

_GRAPH_FIRST_PERSON_SUBJECTS = frozenset({"i", "we", "my", "me", "our", "us"})

# An extracted entity never spans a clause boundary; the window is cut here.
_GRAPH_CLAUSE_BREAKS = frozenset({
    "and", "or", "but", "then", "because", "while", "which", "that", "so",
    "however", "although", "though", "since", "unless", "if", "when", "where",
    "after", "before", "also", "plus", "with", "as", "at",
})

# Punctuation stripped from the edges of an extracted entity.
_GRAPH_EDGE_PUNCT = " \t\r\n,.;:!?\"'`()[]{}<>*_|/\\"

# (predicate, first-person subject alias, third-person verb). A frame needs all
# three parts to yield a triple, which keeps the grammar conservative. Each
# surface form is listed explicitly because the matcher is literal: an inflected
# variant is a new frame, not a pattern.
_GRAPH_VERB_FRAMES: tuple[tuple[str, str, str], ...] = (
    ("works_at", "i", "works at"),
    ("works_at", "i", "work at"),
    ("works_at", "", "works at"),
    ("works_at", "", "work at"),
    ("worked_at", "i", "worked at"),
    ("worked_at", "", "worked at"),
    ("lives_in", "i", "live in"),
    ("lives_in", "", "lives in"),
    ("lives_in", "", "live in"),
    ("based_in", "i", "am based in"),
    ("based_in", "", "is based in"),
    ("uses", "i", "use"),
    ("uses", "", "uses"),
    ("prefers", "i", "prefer"),
    ("prefers", "", "prefers"),
    ("knows", "i", "know"),
    ("knows", "", "knows"),
    ("wrote", "i", "wrote"),
    ("built", "i", "built"),
    ("maintains", "i", "maintain"),
    ("named", "my name is", ""),
    ("depends_on", "", "depends on"),
    ("depends_on", "", "depend on"),
    ("deployed_on", "", "is deployed on"),
    ("deployed_on", "", "are deployed on"),
    ("runs_on", "", "runs on"),
    ("runs_on", "", "run on"),
    ("integrates", "i", "integrate"),
    ("integrates", "", "integrates"),
    ("integrates", "", "integrate"),
    ("depends_on", "i", "depend on"),
    ("belongs_to", "", "belongs to"),
    ("owns", "", "owns"),
    ("created", "", "created"),
    ("created", "", "create"),
    ("reports_to", "i", "report to"),
    ("reports_to", "", "reports to"),
)


@dataclass(frozen=True)
class GraphMemorySettings:
    """Resolved graph-memory opt-in for a single agent turn.

    Attributes:
        enabled: False when the agent did not opt in. The disabled path is a
            no-op that performs no database work at all.
        max_triples_per_turn: Extraction budget, already clamped to
            ``1..GRAPH_MEMORY_HARD_TRIPLE_CAP``. Meaningless while disabled.
    """

    enabled: bool
    max_triples_per_turn: int = GRAPH_MEMORY_DEFAULT_TRIPLES


@dataclass(frozen=True)
class GraphTriple:
    """A candidate triple produced by :func:`extract_triples`.

    Attributes:
        subject: Normalized subject entity.
        predicate: Normalized snake_case relation.
        object: Normalized object entity. Named ``object`` to mirror the
            ``(subject, predicate, object_)`` triple vocabulary; the storage
            column is ``object_``.
        confidence: Confidence assigned at write time.
        context: Source sentence the triple came from.
    """

    subject: str
    predicate: str
    object: str
    confidence: float = GRAPH_EXTRACT_CONFIDENCE
    context: str = ""


def _as_int(value: Any, default: int) -> int:
    """Coerce a config value to ``int``, falling back to ``default``."""
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def resolve_graph_memory_settings(memory_config: Any) -> GraphMemorySettings:
    """Resolve the graph-memory opt-in from an agent's ``memory_config``.

    Expected shape::

        memory_config = {
            "graph_memory": {
                "enabled": True,
                "max_triples_per_turn": 3,  # optional, default 3
            }
        }

    A bare ``"graph_memory": True`` also enables the feature with the default
    budget. Anything else — missing key, ``False``, ``None``, a non-dict
    ``memory_config``, or an unparsable budget — resolves to disabled, so the
    default path stays a pure in-memory check with no database work.

    An already-resolved :class:`GraphMemorySettings` is returned unchanged, so a
    caller that read the flag once (via
    :meth:`PersistentMemoryService.get_graph_memory_settings`) can forward it
    into the write and read helpers without a second lookup.

    Args:
        memory_config: The agent's raw ``memory_config`` value, or a resolved
            :class:`GraphMemorySettings`.

    Returns:
        GraphMemorySettings: Enabled flag plus a clamped per-turn budget.
    """
    if isinstance(memory_config, GraphMemorySettings):
        return memory_config
    if not isinstance(memory_config, dict):
        return GraphMemorySettings(enabled=False)
    raw = memory_config.get(GRAPH_MEMORY_CONFIG_KEY)
    if raw is None or raw is False:
        return GraphMemorySettings(enabled=False)
    if raw is True:
        return GraphMemorySettings(enabled=True)
    if not isinstance(raw, dict):
        return GraphMemorySettings(enabled=False)
    if not raw.get("enabled", False):
        return GraphMemorySettings(enabled=False)
    budget = _as_int(raw.get("max_triples_per_turn"), GRAPH_MEMORY_DEFAULT_TRIPLES)
    budget = max(1, min(budget, GRAPH_MEMORY_HARD_TRIPLE_CAP))
    return GraphMemorySettings(enabled=True, max_triples_per_turn=budget)


def graph_scope_tag(agent_id: str | None) -> str:
    """Return the ``tags`` marker that scopes a triple to one agent.

    ``knowledge_graph`` has no ``agent_id`` column, so agent scoping rides in
    the existing JSON ``tags`` column. ``None`` maps to the shared pool, which
    mirrors the ``agent_id or None`` convention used by episodic retrieval.

    Args:
        agent_id: Owning agent id, or ``None`` for the shared pool.

    Returns:
        str: The reserved scope tag.
    """
    return f"{GRAPH_SCOPE_TAG_PREFIX}{agent_id}" if agent_id else GRAPH_SCOPE_SHARED


def _extract_scope_tag(tags: Sequence[str] | None) -> str | None:
    """Return the reserved scope tag inside ``tags``, or ``None`` if absent."""
    if not tags:
        return None
    for tag in tags:
        if tag == GRAPH_SCOPE_SHARED or tag.startswith(GRAPH_SCOPE_TAG_PREFIX):
            return tag
    return None


def _scope_tag_filter(column: Any, tag: str) -> Any:
    """Match a scope tag inside the JSON ``tags`` column.

    ``KnowledgeGraph.tags`` is a plain ``JSON`` column, so the SQLAlchemy
    ``.contains()`` operator is deprecated there and is scheduled to raise.
    Casting to text and matching the quoted tag works on both SQLite (JSON
    stored as text) and PostgreSQL (``json::text``), and the tag is escaped so
    an agent id containing ``%`` or ``_`` cannot widen the match.

    Args:
        column: The JSON column expression to filter.
        tag: Reserved scope tag from :func:`graph_scope_tag`.

    Returns:
        Any: A SQLAlchemy binary expression.
    """
    escaped = tag.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return column.cast(String).like(f'%"{escaped}"%', escape="\\")


def _clamp_query_limit(limit: Any, default: int = GRAPH_QUERY_DEFAULT_LIMIT) -> int:
    """Clamp a caller-supplied read budget into ``0..GRAPH_QUERY_HARD_LIMIT``."""
    value = _as_int(limit, default)
    return max(0, min(value, GRAPH_QUERY_HARD_LIMIT))


def _split_sentences(text: str) -> list[str]:
    """Split text on sentence terminators, keeping the terminator attached."""
    return [part.strip() for part in re.split(r"(?<=[.!?;\n])", text) if part.strip()]


def _normalize_entity(raw: str) -> str:
    """Normalize one extracted entity.

    Lowercases, cuts the window at the first clause boundary, strips
    determiners/prepositions/auxiliaries from both ends, removes edge
    punctuation, collapses whitespace, and caps the word count.

    Args:
        raw: Candidate entity text as it appeared in the sentence.

    Returns:
        str: The normalized entity, or "" when nothing usable remains. An
        entity must hold at least one letter, so pure numbers are rejected.
    """
    window: list[str] = []
    for word in re.split(r"\s+", raw.strip().lower()):
        if not word:
            continue
        if word in _GRAPH_CLAUSE_BREAKS and window:
            break
        window.append(word.strip(_GRAPH_EDGE_PUNCT))
    words = [w for w in window if w]
    while words and words[0] in _GRAPH_EDGE_STOPWORDS:
        words.pop(0)
    while words and words[-1] in _GRAPH_EDGE_STOPWORDS:
        words.pop()
    while words and words[0] in _GRAPH_FIRST_PERSON_SUBJECTS:
        words.pop(0)
    while words and words[-1] in _GRAPH_FIRST_PERSON_SUBJECTS:
        words.pop()
    words = words[:_GRAPH_ENTITY_MAX_WORDS]
    if not words or not any(any(c.isalpha() for c in w) for w in words):
        return ""
    entity = " ".join(words)
    if len(entity) < 2 or len(entity) > 200:
        return ""
    return entity


def _subject_is_usable(subject: str) -> bool:
    """Reject bare pronouns and clause-connective words as a subject.

    The backwards token read stops at the first non-word character, so a frame
    like "climber uses x and depends on y" can otherwise surface "and" as the
    subject of ``depends_on``.
    """
    return (
        bool(subject)
        and subject not in _GRAPH_FIRST_PERSON_SUBJECTS
        and subject not in _GRAPH_CLAUSE_BREAKS
    )


def extract_triples(content: str, max_triples: int) -> list[GraphTriple]:
    """Extract candidate triples from stored memory content, deterministically.

    This is the intentional seam for a stronger extractor: it takes plain text
    and returns a bounded, ordered list, so an LLM-backed or embedding-backed
    implementation can replace it without touching the write path. The current
    implementation is stdlib-only and pattern based, because no other feature in
    this codebase calls the model from the memory layer and adding one would be
    a scope explosion.

    Grammar: for every sentence, locate a closed set of verb frames (see
    ``_GRAPH_VERB_FRAMES``) and read the object as the up-to-four word run
    following the verb. First-person subjects are normalized to the literal
    entity ``user``; third-person subjects are read backwards from the frame.

    Known limitations, stated plainly: no coreference (a later "she" resolves to
    nobody), no entity typing, no canonicalization across turns beyond
    lowercasing, and a closed verb list, so relations outside that list are not
    captured. A bare pronoun subject is skipped rather than guessed, and a
    first-person verb only matches when the frame lists an alias, so "I
    integrate with Kafka" is missed while "we maintain the pipeline" is not.
    The output is therefore noisy-but-useful provenance, not ground truth, which
    is why triples land at ``GRAPH_EXTRACT_CONFIDENCE`` and are never
    ``verified``.

    Args:
        content: Episodic memory content, e.g. the "User: ... Assistant: ..." text.
        max_triples: Upper bound on returned triples; a hard cap is applied by
            the caller, and <= 0 yields an empty list.

    Returns:
        list[GraphTriple]: Deduplicated triples. Sentences are visited in order
        and, within a sentence, frames in the fixed ``_GRAPH_VERB_FRAMES`` order,
        so a small budget is spent deterministically on the earliest and
        highest-priority relations rather than on whichever frame matched first.
    """
    if not content or max_triples <= 0:
        return []
    triples: list[GraphTriple] = []
    seen: set[tuple[str, str, str]] = set()

    for sentence in _split_sentences(content):
        lowered = _GRAPH_TRANSCRIPT_LABEL.sub("", sentence).lower()
        for predicate, alias, verb in _GRAPH_VERB_FRAMES:
            if len(triples) >= max_triples:
                return triples
            for obj_start, subject in _iter_subject_candidates(lowered, alias, verb):
                tail = lowered[obj_start:]
                obj = _normalize_entity(tail)
                if not _subject_is_usable(subject) or not obj:
                    continue
                key = (subject, predicate, obj)
                if key in seen:
                    continue
                seen.add(key)
                triples.append(
                    GraphTriple(
                        subject=subject,
                        predicate=predicate,
                        object=obj,
                        context=sentence[:280],
                    )
                )
                break
    return triples


def _iter_subject_candidates(
    sentence: str,
    alias: str,
    verb: str,
) -> list[tuple[int, str]]:
    """Yield ``(object_start, normalized_subject)`` pairs for one verb frame.

    A frame with a first-person alias (``"i work at"``) can only match that
    alias, and the subject becomes the literal entity ``user``. Otherwise the
    text immediately before the verb is read backwards as the subject, which is
    what makes "(climber) uses (sqlalchemy)" work without understanding
    English. The index returned is where the object starts, so the caller can
    read the object span without re-deriving it.

    Args:
        sentence: Lowercased sentence text.
        alias: First-person marker, or "" for a third-person frame.
        verb: The verb phrase, lowercase, or "" when the alias ends the frame.

    Returns:
        list[tuple[int, str]]: Candidates in order of occurrence. A frame with
        several third-person subjects yields the first usable one per verb
        occurrence, so one sentence contributes at most one triple per frame.
    """
    separator = " " if verb else ""
    candidates: list[tuple[int, str]] = []
    if alias:
        # "I" and "we" both normalize to the single ``user`` subject.
        for marker in ("i", "we") if alias == "i" else (alias,):
            start = 0
            while True:
                found = sentence.find(marker, start)
                if found < 0:
                    break
                start = found + len(marker)
                if found and sentence[found - 1] not in {" ", ",", ";"}:
                    continue
                if not sentence[start:].startswith(separator + verb):
                    continue
                obj_start = start + len(separator) + len(verb)
                if sentence[obj_start:obj_start + 1] not in {"", " ", "\t", ",", "."}:
                    continue
                candidates.append((obj_start, _GRAPH_USER_SUBJECT))
        candidates.sort(key=lambda item: item[0])
        return candidates

    start = 0
    while True:
        found = sentence.find(verb, start)
        if found < 0:
            break
        start = found + len(verb)
        if not _is_word_start(sentence, found, verb):
            continue
        if sentence[start:start + 1] not in {"", " ", "\t"}:
            continue
        if not _normalize_entity(sentence[start:]):
            continue
        if _closest_word(sentence, found) in _GRAPH_FIRST_PERSON_SUBJECTS:
            # The subject slot holds a pronoun, so this occurrence belongs to
            # the first-person frame of the same relation, not to this one.
            continue
        subject = _normalize_entity(_text_before(sentence, found))
        if not _subject_is_usable(subject):
            continue
        candidates.append((start, subject))
    return candidates


def _closest_word(sentence: str, index: int) -> str:
    """Return the single word immediately before ``index``, lowercased."""
    end = index
    while end > 0 and not _is_entity_char(sentence[end - 1]):
        end -= 1
    start = end
    while start > 0 and _is_entity_char(sentence[start - 1]):
        start -= 1
    return sentence[start:end]


def _text_before(sentence: str, index: int) -> str:
    """Return the up-to-``_GRAPH_ENTITY_MAX_WORDS`` words before ``index``.

    Read backwards so the words land in reading order, which lets a two-word
    subject such as "payments service" survive.
    """
    tokens: list[str] = []
    end = index
    while end > 0 and not _is_entity_char(sentence[end - 1]):
        end -= 1
    while len(tokens) < _GRAPH_ENTITY_MAX_WORDS and end > 0:
        start = end
        while start > 0 and _is_entity_char(sentence[start - 1]):
            start -= 1
        if start == end:
            break
        tokens.append(sentence[start:end])
        end = start
        while end > 0 and not _is_entity_char(sentence[end - 1]):
            end -= 1
    return " ".join(reversed(tokens))


def _is_entity_char(char: str) -> bool:
    """Report whether ``char`` can appear inside an entity token."""
    return char.isalnum() or char in {"'", "-", "_", "."}


def _is_word_start(sentence: str, found: int, verb: str) -> bool:
    """Report whether ``verb`` at ``found`` is a whole word, not a suffix match.

    Guards against "redis uses" matching inside "prefers".
    """
    if found == 0:
        return False
    before = sentence[found - 1]
    if not (before.isalpha() or before == "_"):
        return True
    return bool(before.isdigit() or verb[0].isdigit())



class PersistentMemoryService:
    """Service layer for persistent agent memory operations.

    Replaces the in-memory LongTermMemory with PostgreSQL-backed
    persistent storage that survives server restarts.
    """

    # ─── Episodic Memory ────────────────────────────────────────────────

    async def create_episodic_memory(
        self,
        user_id: str,
        content: str,
        agent_id: str | None = None,
        memory_type: str = "conversation",
        importance: float = 0.5,
        tags: list[str] | None = None,
        source_session_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> EpisodicMemory:
        """Store a new episodic memory."""
        async with async_session() as db:
            memory = EpisodicMemory(
                user_id=user_id,
                content=content,
                summary=content[:200],
                agent_id=agent_id,
                memory_type=memory_type,
                importance=importance,
                tags=tags or [],
                source_session_id=source_session_id,
                metadata_=metadata or {},
            )
            db.add(memory)
            await db.commit()
            await db.refresh(memory)
        try:
            await vector_memory.add(
                collection="episodic",
                doc_id=str(memory.id),
                text=memory.content,
                metadata={
                    "user_id": user_id,
                    "agent_id": agent_id or "",
                    "memory_type": memory_type,
                    "source_session_id": source_session_id or "",
                },
            )
        except Exception as exc:
            logger.warning("episodic_vector_write_failed", error=str(exc))
        return memory

    async def retrieve_memories(
        self,
        user_id: str,
        query: str = "",
        limit: int = 10,
        min_importance: float = 0.0,
        session_id: str | None = None,
        agent_id: str | None = None,
        memory_type: str | None = None,
    ) -> list[EpisodicMemory]:
        """Retrieve relevant memories for a user.

        Uses vector similarity search when available, falls back to keyword search.

        ``agent_id`` optionally narrows retrieval to a single agent's memories
        (mem0-style agent scope). When ``None``, all of the user's agents share
        one pool, preserving the historical behavior.

        ``memory_type`` optionally restricts results to one classification
        (e.g. "lesson"), letting callers build type-specific injection such as
        keyword-triggered lessons. ``None`` keeps the legacy all-types behavior.
        """
        async with async_session() as db:
            if query:
                try:
                    vector_where = {"user_id": user_id}
                    if agent_id is not None:
                        vector_where["agent_id"] = agent_id or ""
                    if memory_type is not None:
                        vector_where["memory_type"] = memory_type
                    vector_results = await vector_memory.search(
                        collection="episodic",
                        query=query,
                        top_k=limit * 3,
                        where=vector_where,
                    )
                except Exception:
                    vector_results = []

                if vector_results:
                    vector_ids = [r["id"] for r in vector_results]
                    conditions = [
                        EpisodicMemory.user_id == user_id,
                        EpisodicMemory.id.in_(vector_ids),
                        EpisodicMemory.importance >= min_importance,
                    ]
                    if agent_id is not None:
                        conditions.append(EpisodicMemory.agent_id == agent_id)
                    if memory_type is not None:
                        conditions.append(EpisodicMemory.memory_type == memory_type)
                    result = await db.execute(
                        select(EpisodicMemory).where(and_(*conditions))
                    )
                    memory_map = {m.id: m for m in result.scalars().all()}
                    ordered = []
                    for vid in vector_ids:
                        if vid in memory_map:
                            mem = memory_map[vid]
                            mem.access_count += 1
                            mem.last_accessed_at = datetime.now(UTC)
                            ordered.append(mem)
                    for mem in ordered[:limit]:
                        log = MemoryRetrievalLog(
                            memory_id=mem.id,
                            user_id=user_id,
                            session_id=session_id,
                            retrieval_query=query[:500],
                        )
                        db.add(log)
                    await db.commit()
                    return ordered[:limit]

            # Fallback: keyword search
            conditions = [
                EpisodicMemory.user_id == user_id,
                EpisodicMemory.importance >= min_importance,
            ]
            if agent_id is not None:
                conditions.append(EpisodicMemory.agent_id == agent_id)
            if memory_type is not None:
                conditions.append(EpisodicMemory.memory_type == memory_type)
            result = await db.execute(
                select(EpisodicMemory)
                .where(and_(*conditions))
                .order_by(
                    desc(EpisodicMemory.importance * EpisodicMemory.recency_score),
                )
                .limit(limit * 3)
            )
            memories = list(result.scalars().all())

            if query:
                query_lower = query.lower()
                scored = []
                for mem in memories:
                    score = mem.importance * mem.recency_score
                    content_lower = mem.content.lower()
                    if any(word in content_lower for word in query_lower.split() if len(word) > 3):
                        score *= 1.5
                        mem.access_count += 1
                        mem.last_accessed_at = datetime.now(UTC)
                    scored.append((score, mem))

                scored.sort(key=lambda x: x[0], reverse=True)
                result_memories = [m for _, m in scored[:limit]]
            else:
                result_memories = memories[:limit]

            for mem in result_memories:
                log = MemoryRetrievalLog(
                    memory_id=mem.id,
                    user_id=user_id,
                    session_id=session_id,
                    retrieval_query=query[:500],
                )
                db.add(log)

            await db.commit()
            return result_memories

    async def format_memories_for_prompt(
        self,
        user_id: str,
        query: str = "",
        max_memories: int = 5,
        agent_id: str | None = None,
    ) -> str:
        """Format memories for injection into system prompt.

        ``agent_id`` forwards the mem0-style agent scope to retrieval. When
        ``None``, all of the user's agents share one pool (historical default).
        """
        memories = await self.retrieve_memories(user_id, query=query, limit=max_memories, agent_id=agent_id)
        if not memories:
            return ""

        lines = ["## Relevant Memories:"]
        lines.extend(f"- [{mem.memory_type}] {mem.content}" for mem in memories)
        return "\n".join(lines)

    async def decay_recency_scores(self, decay_factor: float = 0.95) -> int:
        """Apply time-based decay to all recency scores.

        Should be called periodically (e.g., daily via scheduler).
        Memories that aren't accessed lose relevance over time.
        """
        async with async_session() as db:
            result = await db.execute(select(EpisodicMemory))
            memories = result.scalars().all()
            for mem in memories:
                mem.recency_score *= decay_factor
            await db.commit()
            return len(memories)

    async def cleanup_old_memories(
        self,
        user_id: str,
        keep_count: int = 200,
        min_score: float = 0.01,
    ) -> int:
        """Remove low-scoring memories to prevent unbounded growth."""
        async with async_session() as db:
            # Get count
            result = await db.execute(
                select(func.count()).where(EpisodicMemory.user_id == user_id)
            )
            count = result.scalar() or 0

            if count <= keep_count:
                return 0

            # Delete lowest-scoring memories above the keep threshold
            result = await db.execute(
                select(EpisodicMemory)
                .where(EpisodicMemory.user_id == user_id)
                .where(EpisodicMemory.recency_score < min_score)
                .order_by(EpisodicMemory.importance * EpisodicMemory.recency_score)
                .limit(count - keep_count)
            )
            to_delete = result.scalars().all()
            for mem in to_delete:
                await db.delete(mem)

            await db.commit()
            return len(to_delete)

    async def auto_archive_old_memories(
        self,
        user_id: str,
        max_episodic_age_days: int = 30,
        min_importance: float = 0.3,
        batch_size: int = 50,
    ) -> dict[str, int]:
        """Move old low-importance episodic memories to archival with embeddings.

        Returns stats: {"archived": N, "skipped": N, "failed": N}
        """
        stats: dict[str, int] = {"archived": 0, "skipped": 0, "failed": 0}
        async with async_session() as db:
            cutoff = datetime.now(UTC).timestamp() - (max_episodic_age_days * 86400)
            result = await db.execute(
                select(EpisodicMemory)
                .where(
                    and_(
                        EpisodicMemory.user_id == user_id,
                        EpisodicMemory.importance < min_importance,
                        EpisodicMemory.created_at < datetime.fromtimestamp(cutoff, tz=UTC),
                    )
                )
                .limit(batch_size)
            )
            old_memories = result.scalars().all()

            for mem in old_memories:
                try:
                    archive_id = f"auto-{datetime.now(UTC).strftime('%Y-%m-%d')}"
                    await self.create_archival_passage(
                        user_id=user_id,
                        text=mem.content,
                        archive_id=archive_id,
                        tags=mem.tags,
                        metadata=mem.metadata_,
                    )
                    await db.delete(mem)
                    stats["archived"] += 1
                except Exception:
                    stats["failed"] += 1

            await db.commit()
            return stats

    # ─── Knowledge Graph ─────────────────────────────────────────────────

    async def add_triple(
        self,
        user_id: str,
        subject: str,
        predicate: str,
        object_: str,
        confidence: float = 0.8,
        context: str = "",
        source: str = "conversation",
        tags: Sequence[str] | None = None,
    ) -> KnowledgeGraph:
        """Add a knowledge graph triple.

        Args:
            user_id: Owning user.
            subject: Subject entity.
            predicate: Relation.
            object_: Object entity.
            confidence: Confidence, raised monotonically on a repeat write.
            context: Source sentence.
            source: Provenance label.
            tags: Optional tags. When it contains a reserved scope tag from
                :func:`graph_scope_tag`, the repeat-write check only merges rows
                in the same scope, so one agent never absorbs another agent's
                triple of the same value.

        Returns:
            KnowledgeGraph: The new or updated row.
        """
        scope = _extract_scope_tag(tags)
        async with async_session() as db:
            # Check for existing triple. Several rows can differ only by scope,
            # so candidates are filtered in Python instead of scalar_one_or_none.
            result = await db.execute(
                select(KnowledgeGraph).where(
                    and_(
                        KnowledgeGraph.user_id == user_id,
                        KnowledgeGraph.subject == subject,
                        KnowledgeGraph.predicate == predicate,
                        KnowledgeGraph.object_ == object_,
                    )
                )
            )
            candidates = list(result.scalars().all())
            if scope is None:
                existing = candidates[0] if candidates else None
            else:
                existing = next(
                    (row for row in candidates if scope in (row.tags or [])),
                    None,
                )
            if existing:
                existing.confidence = max(existing.confidence, confidence)
                existing.updated_at = datetime.now(UTC)
                await db.commit()
                return existing

            triple = KnowledgeGraph(
                user_id=user_id,
                subject=subject,
                predicate=predicate,
                object_=object_,
                confidence=confidence,
                source=source,
                context=context,
                tags=list(tags or []),
            )
            db.add(triple)
            await db.commit()
            await db.refresh(triple)
            return triple

    async def query_graph(
        self,
        user_id: str,
        subject: str | None = None,
        predicate: str | None = None,
        object_: str | None = None,
        limit: int = 20,
    ) -> list[KnowledgeGraph]:
        """Query knowledge graph with optional filters.

        The result count is hard-bounded by ``GRAPH_QUERY_HARD_LIMIT`` so a
        caller-supplied ``limit`` can never turn this into a full table scan
        dump. ``limit <= 0`` returns nothing without touching the database.

        Args:
            user_id: Owning user.
            subject: Optional exact subject filter.
            predicate: Optional exact predicate filter.
            object_: Optional exact object filter.
            limit: Requested row count, clamped to the hard maximum.

        Returns:
            list[KnowledgeGraph]: Up to the clamped limit of rows.
        """
        bounded = _clamp_query_limit(limit, default=20)
        if bounded <= 0:
            return []
        async with async_session() as db:
            query = select(KnowledgeGraph).where(KnowledgeGraph.user_id == user_id)

            if subject:
                query = query.where(KnowledgeGraph.subject == subject)
            if predicate:
                query = query.where(KnowledgeGraph.predicate == predicate)
            if object_:
                query = query.where(KnowledgeGraph.object_ == object_)

            query = query.order_by(desc(KnowledgeGraph.confidence)).limit(bounded)
            result = await db.execute(query)
            return list(result.scalars().all())

    async def get_entity_relations(
        self,
        user_id: str,
        entity: str,
        limit: int = 10,
    ) -> list[KnowledgeGraph]:
        """Get all relations for a specific entity (both as subject and object).

        ``limit`` is clamped by ``GRAPH_QUERY_HARD_LIMIT``; ``limit <= 0``
        returns nothing without touching the database.
        """
        bounded = _clamp_query_limit(limit, default=10)
        if bounded <= 0:
            return []
        async with async_session() as db:
            result = await db.execute(
                select(KnowledgeGraph).where(
                    and_(
                        KnowledgeGraph.user_id == user_id,
                        KnowledgeGraph.subject == entity,
                    )
                ).order_by(desc(KnowledgeGraph.confidence)).limit(bounded)
            )
            return list(result.scalars().all())

    async def format_graph_for_prompt(
        self,
        user_id: str,
        entity: str,
        limit: int = 10,
    ) -> str:
        """Format knowledge graph relations for prompt injection."""
        relations = await self.get_entity_relations(user_id, entity, limit=limit)
        if not relations:
            return ""

        lines = [f"## Knowledge about \"{entity}\":"]
        lines.extend(f"- {r.subject} -[{r.predicate}]-> {r.object_}" for r in relations)
        return "\n".join(lines)

    # ─── Graph memory (opt-in, bounded) ─────────────────────────────────────

    async def get_graph_memory_settings(self, agent_id: str | None) -> GraphMemorySettings:
        """Resolve the graph-memory opt-in for an agent by reading its config.

        This is the only database work the graph path performs before deciding
        whether to run at all: one primary-key lookup of ``agents.memory_config``.
        Callers that already hold the config can use
        :func:`resolve_graph_memory_settings` directly and skip this read.

        Args:
            agent_id: Agent to resolve, or ``None`` for the shared pool.

        Returns:
            GraphMemorySettings: Resolved settings; disabled when the agent does
            not exist or did not opt in.
        """
        if not agent_id:
            return GraphMemorySettings(enabled=False)
        try:
            from app.storage import async_session
            from app.storage.database import Agent

            async with async_session() as db:
                agent = await db.get(Agent, agent_id)
                return resolve_graph_memory_settings(
                    agent.memory_config if agent is not None else None
                )
        except Exception as exc:
            logger.warning("graph_memory_config_read_failed", error=str(exc))
            return GraphMemorySettings(enabled=False)

    async def record_graph_memory(
        self,
        user_id: str,
        content: str,
        memory_config: Any = None,
        agent_id: str | None = None,
        source: str = "graph_extract",
    ) -> dict[str, int]:
        """Extract and persist triples from one turn's memory content.

        Gated by the caller's ``memory_config``: when the agent did not opt in
        the call returns immediately without opening a session, so the disabled
        path performs no database work. When enabled, at most
        ``max_triples_per_turn`` triples (already clamped by
        :func:`resolve_graph_memory_settings`) are written, each tagged with the
        caller's agent scope.

        Never raises: extraction and writes are wrapped so a graph failure
        cannot surface in the conversation request path.

        Args:
            user_id: Owning user.
            content: Episodic memory content to mine, e.g. the
                "User: ... Assistant: ..." text produced by
                :meth:`create_episodic_memory`.
            memory_config: The agent's raw ``memory_config`` value, or a
                resolved :class:`GraphMemorySettings`.
            agent_id: Owning agent, or ``None`` for the shared pool.
            source: Provenance label stored on each triple.

        Returns:
            dict[str, int]: Stats with keys ``enabled``, ``extracted``,
            ``stored``, ``failed``. All zero when disabled.
        """
        stats = {"enabled": 0, "extracted": 0, "stored": 0, "failed": 0}
        settings = resolve_graph_memory_settings(memory_config)
        if not settings.enabled:
            return stats
        stats["enabled"] = 1
        try:
            triples = extract_triples(content, settings.max_triples_per_turn)
            stats["extracted"] = len(triples)
            for triple in triples:
                try:
                    await self.add_triple(
                        user_id=user_id,
                        subject=triple.subject,
                        predicate=triple.predicate,
                        object_=triple.object,
                        confidence=triple.confidence,
                        context=triple.context,
                        source=source,
                        tags=[graph_scope_tag(agent_id)],
                    )
                    stats["stored"] += 1
                except Exception as exc:
                    stats["failed"] += 1
                    logger.warning(
                        "graph_triple_write_failed",
                        error=str(exc),
                        subject=triple.subject,
                        predicate=triple.predicate,
                    )
        except Exception as exc:
            logger.warning("graph_memory_extraction_failed", error=str(exc))
        return stats

    async def query_agent_graph(
        self,
        user_id: str,
        agent_id: str | None = None,
        memory_config: Any = None,
        subject: str | None = None,
        limit: int = GRAPH_QUERY_DEFAULT_LIMIT,
    ) -> list[KnowledgeGraph]:
        """Read the triples of one agent scope, bounded and empty-table cheap.

        Applies the same opt-in gate as :meth:`record_graph_memory`, so a
        disabled agent performs no graph read at all. The row count is clamped
        by ``GRAPH_QUERY_HARD_LIMIT``, and the query is a single indexed
        ``SELECT`` that returns an empty list cheaply when nothing was written.

        Args:
            user_id: Owning user.
            agent_id: Agent scope, or ``None`` for the shared pool.
            memory_config: The agent's raw ``memory_config`` value, or a
                resolved :class:`GraphMemorySettings`.
            subject: Optional exact subject filter.
            limit: Requested row count, clamped to the hard maximum.

        Returns:
            list[KnowledgeGraph]: Up to the clamped limit of scoped rows.
        """
        if not resolve_graph_memory_settings(memory_config).enabled:
            return []
        bounded = _clamp_query_limit(limit)
        if bounded <= 0:
            return []
        conditions = [
            KnowledgeGraph.user_id == user_id,
            _scope_tag_filter(KnowledgeGraph.tags, graph_scope_tag(agent_id)),
        ]
        if subject:
            conditions.append(KnowledgeGraph.subject == subject)
        try:
            async with async_session() as db:
                result = await db.execute(
                    select(KnowledgeGraph)
                    .where(and_(*conditions))
                    .order_by(desc(KnowledgeGraph.confidence))
                    .limit(bounded)
                )
                return list(result.scalars().all())
        except Exception as exc:
            logger.warning("graph_memory_query_failed", error=str(exc))
            return []

    async def format_graph_context_for_prompt(
        self,
        user_id: str,
        agent_id: str | None = None,
        memory_config: Any = None,
        subject: str | None = None,
        limit: int = GRAPH_QUERY_DEFAULT_LIMIT,
    ) -> str:
        """Render the agent's graph context for a SYSTEM message.

        Returns "" when the agent is not opted in, when the table is empty, or
        when the read fails, so a caller can inject the result unconditionally.

        Args:
            user_id: Owning user.
            agent_id: Agent scope, or ``None`` for the shared pool.
            memory_config: The agent's raw ``memory_config`` value, or a
                resolved :class:`GraphMemorySettings`.
            subject: Optional exact subject filter.
            limit: Requested row count, clamped to the hard maximum.

        Returns:
            str: A prompt block, or "" when there is nothing to inject.
        """
        relations = await self.query_agent_graph(
            user_id=user_id,
            agent_id=agent_id,
            memory_config=memory_config,
            subject=subject,
            limit=limit,
        )
        if not relations:
            return ""
        lines = ["## Knowledge Graph (facts previously extracted from this agent):"]
        lines.extend(
            f"- {r.subject} -[{r.predicate}]-> {r.object_}" for r in relations
        )
        return "\n".join(lines)

    # ─── User Profile ────────────────────────────────────────────────────

    async def get_or_create_profile(self, user_id: str) -> UserProfile:
        """Get existing profile or create a new one."""
        async with async_session() as db:
            result = await db.execute(
                select(UserProfile).where(UserProfile.user_id == user_id)
            )
            profile = result.scalar_one_or_none()
            if not profile:
                profile = UserProfile(user_id=user_id)
                db.add(profile)
                await db.commit()
                await db.refresh(profile)
            return profile

    async def add_user_fact(
        self,
        user_id: str,
        fact: str,
        category: str = "general",
        confidence: float = 0.8,
    ) -> UserProfile:
        """Add a persistent fact about the user."""
        profile = await self.get_or_create_profile(user_id)
        profile.facts.append({
            "category": category,
            "content": fact,
            "confidence": confidence,
            "added_at": datetime.now(UTC).isoformat(),
        })
        # Keep facts list manageable
        if len(profile.facts) > 100:
            profile.facts = profile.facts[-100:]

        async with async_session() as db:
            await db.merge(profile)
            await db.commit()
            return profile

    async def update_preferences(
        self,
        user_id: str,
        **kwargs: Any,
    ) -> UserProfile:
        """Update user preferences."""
        profile = await self.get_or_create_profile(user_id)
        for key, value in kwargs.items():
            if hasattr(profile, key) and value is not None:
                setattr(profile, key, value)

        async with async_session() as db:
            await db.merge(profile)
            await db.commit()
            return profile

    async def record_interaction(
        self,
        user_id: str,
        message_count: int = 1,
    ) -> None:
        """Record a user interaction for behavioral tracking."""
        profile = await self.get_or_create_profile(user_id)
        now = datetime.now(UTC)
        profile.total_sessions += 1
        profile.total_messages += message_count
        profile.last_interaction = now
        if not profile.first_interaction:
            profile.first_interaction = now

        async with async_session() as db:
            await db.merge(profile)
            await db.commit()

    async def format_profile_for_prompt(self, user_id: str) -> str:
        """Format user profile for system prompt injection."""
        profile = await self.get_or_create_profile(user_id)
        lines: list[str] = []

        # Inviolable rules (highest priority)
        if profile.inviolable:
            lines.append("[INVIOLABLE RULES — MUST FOLLOW]")
        lines = [ f"- {rule}" for rule in profile.inviolable ]

        # User values
        if profile.values:
            lines.append("## User Values")
        lines = [ f"- {v}" for v in profile.values ]

        # User principles
        if profile.principles:
            lines.append("## User Principles")
            for p in profile.principles:
                lines.append(f"- {p}")
            lines.append("")

        facts = profile.facts[-10:]  # Last 10 facts
        if facts:
            lines.append("## User Information:")
            for f in facts:
                lines.append(f"- [{f.get('category', 'general')}] {f.get('content', '')}")

        if profile.preferred_model:
            lines.append(f"- Preferred model: {profile.preferred_model}")
        if profile.preferred_language:
            lines.append(f"- Preferred language: {profile.preferred_language}")

        return "\n".join(lines) if lines else ""

    # ─── Auto-Extraction ─────────────────────────────────────────────────

    async def auto_extract_from_session(
        self,
        user_id: str,
        session_id: str,
        messages: list[dict[str, str]],
        agent_id: str | None = None,
    ) -> dict[str, int]:
        """Extract memories and knowledge from a completed conversation.

        Uses simple heuristics. In production, this would use an LLM
        to extract structured memories from the conversation.
        """
        stats = {"memories": 0, "facts": 0, "triples": 0}

        # Extract key decisions and preferences
        for msg in messages:
            content = msg.get("content", "")
            if not content or len(content) < 20:
                continue

            # Simple heuristic: messages containing "I prefer", "I like", "remember"
            lower = content.lower()
            if any(signal in lower for signal in ["i prefer", "i like", "i want", "remember that", "my name is", "i work"]):
                await self.create_episodic_memory(
                    user_id=user_id,
                    content=content[:500],
                    agent_id=agent_id,
                    memory_type="preference",
                    importance=0.7,
                    source_session_id=session_id,
                )
                stats["memories"] += 1

                # Extract as user fact
                if "my name is" in lower:
                    name_part = content[lower.index("my name is") + 11:].strip().split()[0:3]
                    name = " ".join(name_part).strip(".,!?")
                    if name:
                        await self.add_user_fact(user_id, f"Name: {name}", "personal", 0.9)
                        stats["facts"] += 1

                elif "i work" in lower:
                    work_part = content[lower.index("i work") + 7:].strip()[:100]
                    if work_part:
                        await self.add_user_fact(user_id, f"Work: {work_part}", "work", 0.8)
                        stats["facts"] += 1

        return stats

    # ─── Archival Memory ──────────────────────────────────────────────────────

    async def create_archival_passage(
        self,
        user_id: str,
        text: str,
        archive_id: str,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        embedding: list[float] | None = None,
    ) -> ArchivalPassage:
        """Store a new archival passage."""
        async with async_session() as db:
            passage = ArchivalPassage(
                user_id=user_id,
                text=text,
                archive_id=archive_id,
                tags=tags or [],
                metadata_=metadata or {},
                embedding=embedding,
            )
            db.add(passage)
            await db.commit()
            await db.refresh(passage)
        try:
            await vector_memory.add(
                collection="archival",
                doc_id=str(passage.id),
                text=text,
                metadata={
                    "user_id": user_id,
                    "archive_id": archive_id,
                    "tags": tags or [],
                },
            )
        except Exception as exc:
            logger.warning("archival_vector_write_failed", error=str(exc))
        return passage

    async def search_archival_memories(
        self,
        user_id: str,
        query: str,
        limit: int = 10,
        archive_id: str | None = None,
    ) -> list[ArchivalPassage]:
        """Search archival memories by semantic similarity.

        Uses vector search when available, falls back to LIKE search.
        """
        async with async_session() as db:
            vector_passages: list[ArchivalPassage] = []
            if query:
                try:
                    vector_results = await vector_memory.search(
                        collection="archival",
                        query=query,
                        top_k=limit,
                        where={"user_id": user_id},
                    )
                except Exception:
                    vector_results = []

                if vector_results:
                    vector_ids = [r["id"] for r in vector_results]
                    vector_query = select(ArchivalPassage).where(
                        ArchivalPassage.user_id == user_id,
                        ArchivalPassage.id.in_(vector_ids),
                    )
                    if archive_id:
                        vector_query = vector_query.where(ArchivalPassage.archive_id == archive_id)
                    result = await db.execute(vector_query)
                    passage_map = {p.id: p for p in result.scalars().all()}
                    for vid in vector_ids:
                        passage = passage_map.get(vid)
                        if passage:
                            passage.access_count += 1
                            passage.last_accessed_at = datetime.now(UTC)
                            vector_passages.append(passage)

            # Fallback: LIKE search (always run, merged with vector hits)
            base_query = select(ArchivalPassage).where(ArchivalPassage.user_id == user_id)
            if archive_id:
                base_query = base_query.where(ArchivalPassage.archive_id == archive_id)
            if query:
                base_query = base_query.where(ArchivalPassage.text.ilike(f"%{query}%"))
            base_query = base_query.order_by(ArchivalPassage.access_count.desc(), ArchivalPassage.created_at.desc()).limit(limit)
            result = await db.execute(base_query)
            like_passages = list(result.scalars().all())

            seen: set[str] = set()
            merged: list[ArchivalPassage] = []
            for passage in [*vector_passages, *like_passages]:
                if passage.id in seen:
                    continue
                seen.add(passage.id)
                merged.append(passage)
            merged = merged[:limit]

            if vector_passages:
                for p in vector_passages:
                    await vector_memory.update_access("archival", p.id)
            await db.commit()
            return merged

    async def get_archival_by_tags(
        self,
        user_id: str,
        tags: list[str],
        limit: int = 20,
    ) -> list[ArchivalPassage]:
        """Get archival passages matching any of the given tags."""
        async with async_session() as db:
            query = select(ArchivalPassage).where(ArchivalPassage.user_id == user_id)
            for tag in tags:
                query = query.where(ArchivalPassage.tags.contains([tag]))
            query = query.limit(limit)
            result = await db.execute(query)
            return list(result.scalars().all())

    async def decay_recency_by_access(self) -> int:
        """Decay recency scores based on days since last access.

        Formula: recency_score = 1.0 / (1.0 + days_since_access)
        """
        async with async_session() as db:
            result = await db.execute(select(EpisodicMemory))
            memories = result.scalars().all()
            now = datetime.now(UTC)
            updated = 0
            for mem in memories:
                if mem.last_accessed_at:
                    days = (now - mem.last_accessed_at.replace(tzinfo=UTC)).days
                    mem.recency_score = 1.0 / (1.0 + days)
                    updated += 1
            await db.commit()
            return updated


# Global singleton
persistent_memory = PersistentMemoryService()
