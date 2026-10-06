"""Tests for the canary token mechanism (generation, insertion, leak detection)
and its penalty boost integration with the safety gate.
"""

from __future__ import annotations

import pytest

from app.core.metacognition.canary import (
    detect_canary_leak,
    generate_canary,
    insert_canary,
)
from app.core.metacognition.safety_gate import BLOCK_THRESHOLD, CANARY_LEAK_PENALTY, screen


def test_generate_canary_format() -> None:
    canary = generate_canary()
    assert canary.startswith("CANARY[")
    assert canary.endswith("]")
    body = canary[len("CANARY[") : -1]
    assert len(body) == 8
    int(body, 16)


def test_generate_canary_uniqueness() -> None:
    canaries = {generate_canary() for _ in range(1000)}
    assert len(canaries) == 1000


def test_insert_canary_appends_html_comment() -> None:
    canary = generate_canary()
    content = "private memory body"
    marked = insert_canary(content, canary)
    assert marked.startswith(content)
    assert marked.endswith(f"<!-- {canary} -->")


def test_insert_and_detect_roundtrip() -> None:
    canary = generate_canary()
    marked = insert_canary("secret plan notes", canary)
    assert detect_canary_leak(marked, canary) is True


def test_detect_canary_leak_negative_cases() -> None:
    canary = generate_canary()
    assert detect_canary_leak("no token in this output", canary) is False
    assert detect_canary_leak(insert_canary("body", canary), generate_canary()) is False
    assert detect_canary_leak("", canary) is False


def test_detect_canary_leak_requires_exact_substring() -> None:
    canary = generate_canary()
    assert detect_canary_leak(canary.lower(), canary) is False
    assert detect_canary_leak(canary[:-1], canary) is False


def test_detect_canary_leak_rejects_empty_canary() -> None:
    assert detect_canary_leak("any text", "") is False


def test_leaked_canary_boosts_penalty_to_block() -> None:
    canary = generate_canary()
    leaked_output = f"partial output ... <!-- {canary} -->"
    assert detect_canary_leak(leaked_output, canary) is True
    verdict = screen("benign memory content", canary_leaked=True)
    assert verdict.allowed is False
    assert verdict.penalty == pytest.approx(CANARY_LEAK_PENALTY)
    assert verdict.penalty >= BLOCK_THRESHOLD
    assert "canary_leak" in verdict.reasons
