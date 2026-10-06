"""Summarization helpers for the L0/L1 semantic sidecar layers.

L0 (.. _abstract) is a short retrieval-friendly summary capped at
``L0_MAX_CHARS``; L1 (.. _overview) is a broader directory overview capped at
``L1_MAX_CHARS``. Generation prefers the project LLM configured through the
``USER_LLM_*`` settings and degrades to deterministic rule-based summaries,
so the layer keeps working with no credentials and no network.
"""

from __future__ import annotations

import re

import httpx
import structlog

from app.config import settings

logger = structlog.get_logger()

L0_MAX_CHARS = 256
L1_MAX_CHARS = 4000
_LLM_TIMEOUT_S = 15

_HEADING_RE = re.compile(r"^#{1,6}\s+(.*)$")


class SummarizerError(RuntimeError):
    """Raised when the configured LLM path is unavailable or fails."""


def _llm_settings() -> tuple[str, str, str]:
    key = (settings.user_llm_api_key or "").strip()
    base = (settings.user_llm_base_url or "").strip().rstrip("/")
    model = (settings.user_llm_model or "gpt-4o-mini").strip()
    return key, base, model


def llm_enabled() -> bool:
    key, base_url, _model = _llm_settings()
    return bool(key and base_url)


async def llm_completion(prompt: str, *, system: str = "You are a concise summarizer.") -> str:
    """Run one OpenAI-compatible completion and return the reply text.

    Raises:
        SummarizerError: When no key/base URL is configured or the call fails.
    """
    key, base_url, model = _llm_settings()
    if not key or not base_url:
        raise SummarizerError("LLM credentials are not configured")
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2,
    }
    async with httpx.AsyncClient(timeout=_LLM_TIMEOUT_S) as client:
        try:
            response = await client.post(
                f"{base_url}/chat/completions",
                json=payload,
                headers={"Authorization": f"Bearer {key}"},
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise SummarizerError(f"LLM request failed: {exc}") from exc
    data = response.json()
    choices = data.get("choices") or []
    if not choices:
        raise SummarizerError("empty LLM response")
    text = ((choices[0].get("message") or {}).get("content") or "").strip()
    if not text:
        raise SummarizerError("blank LLM response")
    return text


def clamp(text: str, max_chars: int) -> str:
    """Trim leading/trailing space and truncate while preserving structure.

    The ellipsis counts toward ``max_chars`` so the result never exceeds the
    configured layer cap.
    """
    text = text.strip()
    if len(text) <= max_chars:
        return text
    return f"{text[: max_chars - 3].rstrip()}..."


def _first_sentence(text: str, limit: int = 320) -> str:
    text = " ".join(text.split())
    if not text:
        return ""
    boundary = max(text.rfind(". "), text.rfind("! "), text.rfind("? "))
    cut = boundary + 1 if boundary >= 0 else len(text)
    sentence = text[: cut + 1].strip()
    if len(sentence) < 24:
        sentence = text
    return sentence[:limit].rstrip()


def _sanitize_heading(heading: str) -> str:
    return " ".join(heading.strip("# ").split())[:120]


def _split_sections(text: str) -> list[tuple[str, str]]:
    """Split markdown text into (heading, body) sections by heading level."""
    sections: list[tuple[str, str]] = []
    current_heading = ""
    current_body: list[str] = []
    for line in text.splitlines():
        match = _HEADING_RE.match(line.strip())
        if match:
            if current_body:
                sections.append((current_heading, "\n".join(current_body)))
            current_heading = match.group(1).strip()
            current_body = []
        else:
            current_body.append(line)
    if current_heading or current_body:
        sections.append((current_heading, "\n".join(current_body)))
    return sections


def rule_overview(text: str, max_chars: int = L1_MAX_CHARS) -> str:
    """Build a skeleton overview from headings and first sentences."""
    sections = _split_sections(text)
    parts: list[str] = []
    for heading, body in sections:
        title = _sanitize_heading(heading)
        description = _first_sentence(body)
        if title:
            parts.append(f"## {title}\n{description}" if description else f"## {title}")
        elif description:
            parts.append(description)
    if not parts:
        parts.append(_first_sentence(text))
    overview = "# Directory Overview\n\n" + "\n\n".join(part for part in parts if part)
    return clamp(overview, max_chars)


def rule_abstract(text: str, max_chars: int = L0_MAX_CHARS) -> str:
    """Build a short abstract from the leading idea of the text."""
    for _heading, body in _split_sections(text):
        if body.strip():
            seed = _first_sentence(body)
            if seed:
                return clamp(seed, max_chars)
    return clamp(_first_sentence(text), max_chars)


def extract_abstract_from_overview(overview: str, max_chars: int = L0_MAX_CHARS) -> str:
    """Extract the L0 brief description from an L1 overview body.

    The abstract is the first paragraph after the H1 title and before the
    first ``##`` heading, matching the OpenViking extraction rule.
    """
    buffer: list[str] = []
    in_intro = False
    for line in overview.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if not in_intro:
            if stripped.startswith("# "):
                in_intro = True
            continue
        if stripped.startswith("##"):
            break
        buffer.append(stripped)
    return clamp(" ".join(buffer), max_chars)


class TextSummarizer:
    """L0/L1 summary generation with an LLM-first, rule-fallback policy.

    Args:
        use_llm: Force the LLM path on/off. Defaults to the configured
            ``USER_LLM_*`` availability.
    """

    def __init__(self, *, use_llm: bool | None = None) -> None:
        self._use_llm = use_llm

    def llm_available(self) -> bool:
        if self._use_llm is False:
            return False
        if self._use_llm is True:
            return True
        return llm_enabled()

    async def abstract(self, text: str, *, scope: str = "", max_chars: int = L0_MAX_CHARS) -> str:
        return clamp(await self._generate(text, mode="abstract", scope=scope), max_chars)

    async def overview(self, text: str, *, scope: str = "", max_chars: int = L1_MAX_CHARS) -> str:
        return clamp(await self._generate(text, mode="overview", scope=scope), max_chars)

    async def generate_pair(self, text: str, *, scope: str = "") -> tuple[str, str]:
        """Generate (L0 abstract, L1 overview); L0 is extracted from L1.

        Mirrors the OpenViking generation order: overview first, abstract
        extracted from its brief-description paragraph, with a direct abstract
        fallback when the L1 body has no intro paragraph.
        """
        overview = await self.overview(text, scope=scope)
        abstract = extract_abstract_from_overview(overview)
        if not abstract:
            abstract = await self.abstract(text, scope=scope)
        return abstract, overview

    async def _generate(self, text: str, *, mode: str, scope: str) -> str:
        if self.llm_available():
            try:
                body = await llm_completion(
                    _prompt(text, mode=mode, scope=scope),
                    system=("You summarize a directory for an agent memory."),
                )
                if body:
                    return body
            except Exception as exc:
                logger.warning("llm_summary_fallback", mode=mode, scope=scope, error=str(exc))
        if mode == "overview":
            return rule_overview(text)
        return rule_abstract(text)


def _prompt(text: str, *, mode: str, scope: str) -> str:
    instruction = (
        "produce a one-line abstract (at most 256 characters)" if mode == "abstract"
        else "outline the directory contents and quick navigation (at most 4000 characters)"
    )
    return (
        f"You are summarizing part of an agent memory catalog. Scope: {scope or '(root)'}.\n"
        f"Plain Markdown only, no frontmatter, {instruction}. The source text follows.\n\n{text[:12000]}"
    )
