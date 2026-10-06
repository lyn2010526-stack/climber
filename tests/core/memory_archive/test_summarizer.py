"""Unit tests for the L0/L1 summarization primitives.

Covers the rule-based generators, the character clamps (which must preserve
Markdown structure), the OpenViking abstract-from-overview extraction, and the
LLM-first/rule-fallback policy of :class:`TextSummarizer`.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

from app.config import settings
from app.core.memory_archive.summarizer import (
    L0_MAX_CHARS,
    L1_MAX_CHARS,
    SummarizerError,
    TextSummarizer,
    _first_sentence,
    clamp,
    extract_abstract_from_overview,
    llm_enabled,
    rule_abstract,
    rule_overview,
)

if TYPE_CHECKING:
    import pytest

OVERVIEW_SOURCE = (
    "# auth directory\n\n"
    "OAuth 2.0 flows protect the API surface.\n\n"
    "## login\n"
    "The login endpoint accepts username and password.\n\n"
    "## tokens\n"
    "Refresh tokens are rotated on every use.\n"
)


def _run(coro: Any) -> Any:
    return asyncio.run(coro)


def test_rule_overview_builds_skeleton_and_keeps_newlines() -> None:
    overview = rule_overview(OVERVIEW_SOURCE)
    assert overview.startswith("# Directory Overview")
    assert "\n## login" in overview
    assert "\n## tokens" in overview
    assert "OAuth 2.0 flows protect" in overview


def test_rule_abstract_returns_leading_idea() -> None:
    abstract = rule_abstract(OVERVIEW_SOURCE)
    assert len(abstract) <= L0_MAX_CHARS
    assert "OAuth 2.0 flows" in abstract


def test_clamp_preserves_structure_and_strips_edges() -> None:
    text = "  ## login\nalpha beta gamma.\n  "
    trimmed = clamp(text, 4000)
    assert trimmed == "## login\nalpha beta gamma."


def test_clamp_truncates_with_ellipsis() -> None:
    text = "word " * 100
    result = clamp(text, 20)
    assert len(result) <= 20
    assert result.endswith("...")
    assert "\n" not in result  # truncation keeps a single line


def test_extract_abstract_from_overview_takes_intro_paragraph() -> None:
    overview = "# Directory Overview\n\nOAuth 2.0 flows protect the API surface.\n\n## login\n..."
    abstract = extract_abstract_from_overview(overview)
    assert "OAuth 2.0 flows protect the API surface" in abstract


def test_extract_abstract_empty_when_no_intro_paragraph() -> None:
    overview = "# Directory Overview\n\n## login\nOnly headings follow.\n"
    assert extract_abstract_from_overview(overview) == ""


def test_first_sentence_stops_at_boundary() -> None:
    sentence = _first_sentence(
        "One sentence that is long enough to keep. Another one follows."
    )
    assert sentence == "One sentence that is long enough to keep."


def test_first_sentence_keeps_more_when_first_is_short() -> None:
    text = "Hi there. The longer explanation keeps enough detail to be useful."
    assert _first_sentence(text) == text


def test_llm_enabled_tracks_configuration(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "user_llm_api_key", "")
    monkeypatch.setattr(settings, "user_llm_base_url", "")
    assert llm_enabled() is False


def test_text_summarizer_rule_mode_is_deterministic_and_bounded() -> None:
    summarizer = TextSummarizer(use_llm=False)
    assert summarizer.llm_available() is False
    abstract, overview = _run(summarizer.generate_pair(OVERVIEW_SOURCE))
    assert len(abstract) <= L0_MAX_CHARS
    assert len(overview) <= L1_MAX_CHARS
    again, _ = _run(summarizer.generate_pair(OVERVIEW_SOURCE))
    assert abstract == again


def test_text_summarizer_llm_failure_falls_back_to_rules(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def boom(*args: Any, **kwargs: Any) -> str:
        raise SummarizerError("boom")

    monkeypatch.setattr(
        "app.core.memory_archive.summarizer.llm_completion", boom
    )
    summarizer = TextSummarizer(use_llm=True)
    abstract, overview = _run(summarizer.generate_pair(OVERVIEW_SOURCE))
    assert abstract
    assert overview.startswith("# Directory Overview")
