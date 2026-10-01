"""Safety gate for memory, profile, and evolution write paths.

Pure, deterministic screening and scoring primitives for the safety layer.
``screen`` scans text against known risk patterns (credential exposure,
destructive commands, privilege escalation, prompt-injection phrases,
injection payloads) and returns a ``SafetyVerdict`` with an accumulated
penalty; a canary leak event adds a fixed penalty boost. ``gated_fitness``
couples the composite fitness contract to that verdict so dangerous content
can never raise fitness. ``damped_boost`` adds damping to self-reinforcing
score boosts so repeated positive feedback cannot explode a metric.
``coupled_decay`` couples forgetting with decay: frequently written memories
decay along a stretched half-life, and only survivors of that curve stay out
of prune lists.

The module performs zero I/O and zero LLM calls; identical inputs always
produce identical outputs.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass

BLOCK_THRESHOLD: float = 0.5
CANARY_LEAK_PENALTY: float = 0.5
MAX_CONSECUTIVE_BOOSTS: int = 5
DEFAULT_SURVIVAL_THRESHOLD: float = 0.15
DEFAULT_HALF_LIFE_DAYS: float = 30.0

_RISK_DEFINITIONS: tuple[tuple[str, str, float], ...] = (
    (
        "credential_assignment",
        r"\b(?:api[_-]?key|apikey|secret[_-]?key|access[_-]?key|auth[_-]?token|"
        r"access[_-]?token|client[_-]?secret)\b\s*[:=]",
        0.6,
    ),
    (
        "password_assignment",
        r"\b(?:password|passwd|pwd)\b\s*[:=]\s*\S",
        0.6,
    ),
    (
        "credential_token_literal",
        r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{16,}\b|\bsk-[A-Za-z0-9]{16,}\b|"
        r"\bAKIA[0-9A-Z]{16}\b",
        0.8,
    ),
    (
        "private_key_block",
        r"-----BEGIN [A-Z ]*PRIVATE KEY-----",
        0.8,
    ),
    (
        "destructive_filesystem",
        r"\brm\s+(?:-{1,2}[A-Za-z-]+\s+)*-{1,2}[A-Za-z]*r[A-Za-z]*\b"
        r"|--no-preserve-root|\b(?:del|rmdir)\s+/[sq]",
        0.6,
    ),
    (
        "destructive_sql",
        r"\bDROP\s+(?:TABLE|DATABASE|SCHEMA)\b|\bTRUNCATE\s+TABLE\b",
        0.6,
    ),
    (
        "disk_format_command",
        r"\bmkfs(?:\.[a-z0-9]+)*\b|\bformat\s+[a-z]:|\bdd\s+if=/dev/",
        0.6,
    ),
    (
        "privilege_escalation",
        r"\bchmod\s+(?:-[A-Za-z]+\s+)*0?777\b|\bvisudo\b|/etc/sudoers",
        0.55,
    ),
    (
        "injection_payload",
        r"\bUNION\s+(?:ALL\s+)?SELECT\b|\bOR\s+1\s*=\s*1\b|'\s*OR\s*'?1'?\s*=\s*'"
        r"|--\s*$|;\s*DROP\s+TABLE\b",
        0.45,
    ),
    (
        "xss_payload",
        r"<script\b|javascript:|\bon(?:error|load)\s*=",
        0.45,
    ),
    (
        "reverse_shell",
        r"/dev/tcp/|\bnc(?:at)?\s+-e\b|\bsocat\s+exec\b|\bmeterpreter\b",
        0.8,
    ),
    (
        "path_traversal_payload",
        r"(?:\.\./){2,}\s*(?:etc|proc|windows|boot)|%2e%2e%2f%2e%2e",
        0.45,
    ),
    (
        "prompt_injection_phrase",
        r"\bignore\s+(?:all\s+)?(?:previous|prior|above)\s+(?:instructions|rules)\b"
        r"|\bdisregard\s+.{0,20}?(?:rules|instructions)\b"
        r"|\breveal\s+(?:your\s+)?(?:system\s+)?prompt\b"
        r"|\b(?:print|show|repeat)\s+(?:your\s+)?(?:system\s+)?(?:prompt|instructions)\b"
        r"|\byou\s+are\s+now\b"
        r"|\bpretend\s+to\s+be\b"
        r"|\boverride\s+(?:the\s+)?(?:safety|security|guardrails?)\b"
        r"|忽略(?:之前|以上|先前)的?(?:指令|规则|设定)"
        r"|无视(?:之前|以上)?.{0,10}?(?:指令|规则)"
        r"|(?:透露|泄露)(?:你的)?(?:系统)?提示词"
        r"|你的(?:系统)?提示词是什么"
        r"|扮演",
        0.6,
    ),
)

RISK_PATTERNS: tuple[tuple[str, float], ...] = tuple(
    (label, weight) for label, _, weight in _RISK_DEFINITIONS
)

_COMPILED_RISK_PATTERNS: tuple[tuple[str, re.Pattern[str], float], ...] = tuple(
    (label, re.compile(source, re.IGNORECASE | re.MULTILINE), weight)
    for label, source, weight in _RISK_DEFINITIONS
)


def _finite(value: float, name: str) -> float:
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{name} must be finite")
    return result


@dataclass(frozen=True, slots=True)
class SafetyVerdict:
    """Outcome of screening one piece of content.

    ``penalty`` is within [0, 1]; content is blocked once the penalty reaches
    ``BLOCK_THRESHOLD``. ``reasons`` lists the risk pattern labels that fired.
    """

    allowed: bool
    penalty: float
    reasons: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not 0.0 <= self.penalty <= 1.0:
            raise ValueError("penalty must be within [0, 1]")


def screen(text: str, *, canary_leaked: bool = False) -> SafetyVerdict:
    """Scan text against known risk patterns and accumulate penalties.

    Every matching pattern adds its weight to the penalty, capped at 1.0.
    A canary leak event adds ``CANARY_LEAK_PENALTY`` on top of pattern
    matches, so a leaked canary alone reaches ``BLOCK_THRESHOLD`` and fails
    closed. The content is rejected once the accumulated penalty reaches
    ``BLOCK_THRESHOLD``.
    """
    reasons: list[str] = []
    penalty = 0.0
    if canary_leaked:
        reasons.append("canary_leak")
        penalty += CANARY_LEAK_PENALTY
    if text:
        for label, pattern, weight in _COMPILED_RISK_PATTERNS:
            if pattern.search(text):
                reasons.append(label)
                penalty += weight
    penalty = round(min(1.0, penalty), 6)
    return SafetyVerdict(
        allowed=penalty < BLOCK_THRESHOLD,
        penalty=penalty,
        reasons=tuple(reasons),
    )


def gated_fitness(composite: float, verdict: SafetyVerdict) -> float:
    """Scale a composite fitness score by the safety verdict.

    Rejected content returns exactly 0.0 so dangerous memories can never
    raise fitness, no matter how strong the base score is. Accepted content
    is scaled down proportionally to the accumulated penalty.
    """
    if not verdict.allowed or verdict.penalty >= BLOCK_THRESHOLD:
        return 0.0
    return _finite(composite, "composite") * (1.0 - verdict.penalty)


def damped_boost(
    current: float,
    incoming: float,
    *,
    boost_count: int,
    damping: float = 0.6,
) -> float:
    """Apply the n-th consecutive positive boost with geometric damping.

    ``boost_count`` is the 1-based index of this boost within the current
    consecutive-boost streak: the raw delta ``incoming - current`` is scaled
    by ``damping ** boost_count``. After ``MAX_CONSECUTIVE_BOOSTS`` boosts in
    a row the increment collapses to zero, which caps self-reinforcing
    feedback loops. Non-positive deltas leave the value untouched.
    """
    damping = _finite(damping, "damping")
    current = _finite(current, "current")
    incoming = _finite(incoming, "incoming")
    if not 0.0 <= damping <= 1.0:
        raise ValueError("damping must be within [0, 1]")
    if boost_count < 1:
        raise ValueError("boost_count must be at least 1")
    delta = incoming - current
    if delta <= 0.0:
        return current
    if boost_count > MAX_CONSECUTIVE_BOOSTS:
        return current
    return current + delta * (damping**boost_count)


def _normalize_frequency(frequency: float) -> float:
    frequency = _finite(frequency, "write_frequency")
    if frequency <= 0.0:
        return 0.0
    return frequency / (1.0 + frequency)


def coupled_decay(
    age_days: float,
    write_frequency: float,
    importance: float,
    *,
    half_life_days: float = DEFAULT_HALF_LIFE_DAYS,
) -> float:
    """Return a survival score in [0, 1] coupling forgetting with decay.

    The survival curve is ``importance * 0.5 ** (age / effective_half_life)``
    where the write frequency, normalized into [0, 1) via ``f / (1 + f)``,
    stretches the half-life. Frequently written memories therefore decay more
    slowly and survive pruning longer; rarely written ones fall below the
    prune survival threshold sooner. Age, frequency, and importance are
    clamped into their valid ranges before scoring.
    """
    age_days = _finite(age_days, "age_days")
    importance = _finite(importance, "importance")
    half_life_days = _finite(half_life_days, "half_life_days")
    if half_life_days <= 0.0:
        raise ValueError("half_life_days must be positive")
    age = max(0.0, age_days)
    clamped_importance = min(1.0, max(0.0, importance))
    effective_half_life = half_life_days * (1.0 + _normalize_frequency(write_frequency))
    survival = clamped_importance * 0.5 ** (age / effective_half_life)
    return round(min(1.0, max(0.0, survival)), 6)
