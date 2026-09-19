"""Zero-key online research pipeline.

Fetches pages for a query, cleans and chunks the text, ranks chunks with
local BM25 and emits a structured report. No search API and no API keys are
required: candidate URLs are derived from the query (Wikipedia heuristic plus
DuckDuckGo's public HTML page), and each page is fetched either through the
Playwright browser tools or, as a fallback, through urllib from the standard
library.

Every network or browser step degrades silently; when no source is reachable
the report is marked ``ok: False`` instead of raising.
"""

from __future__ import annotations

import asyncio
import contextlib
import html
import os
import re
from datetime import UTC, datetime
from html.parser import HTMLParser
from typing import Any
from urllib.parse import parse_qs, quote_plus, urlparse
from urllib.request import Request, urlopen

import structlog

from app.core.enhanced_rag import compute_bm25
from app.core.web_content_cleaner import clean_web_content
from app.tools.rag import chunk_text

logger = structlog.get_logger(__name__)

_USER_AGENT = "Mozilla/5.0 (compatible; climber-research/1.0)"
_MAX_BYTES = 512_000
_MAX_CANDIDATES = 8
_CHUNK_SIZE = 500
_CHUNK_OVERLAP = 50
_KEY_POINTS = 3
_POINT_LIMIT = 240

_WIKI_TEMPLATE = "https://en.wikipedia.org/wiki/{topic}"
_DDG_TEMPLATE = "https://html.duckduckgo.com/html/?q={q}"

_BLOCKED_HOSTS = {
    "facebook.com",
    "www.facebook.com",
    "instagram.com",
    "www.instagram.com",
    "twitter.com",
    "www.twitter.com",
    "x.com",
    "www.x.com",
    "tiktok.com",
    "www.tiktok.com",
    "youtube.com",
    "www.youtube.com",
    "mailto:",
}

_STATIC_EXTS = (".pdf", ".jpg", ".jpeg", ".png", ".gif", ".webp", ".zip", ".mp4", ".mp3")

_SESSION_ID = "research"


class _TextExtractor(HTMLParser):
    """Strip markup and collect visible text."""

    def __init__(self) -> None:
        super().__init__()
        self._parts: list[str] = []
        self._skip = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in ("script", "style", "noscript", "svg"):
            self._skip += 1
        elif tag in ("p", "div", "br", "li", "h1", "h2", "h3", "h4", "tr"):
            self._parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in ("script", "style", "noscript", "svg"):
            self._skip = max(0, self._skip - 1)

    def handle_data(self, data: str) -> None:
        if self._skip == 0 and data.strip():
            self._parts.append(data)

    def text(self) -> str:
        raw = " ".join(self._parts)
        raw = re.sub(r"[ \t]+", " ", raw)
        return re.sub(r" *\n *", "\n", raw).strip()


class _LinkExtractor(HTMLParser):
    """Collect all anchor hrefs seen in an HTML document."""

    def __init__(self) -> None:
        super().__init__()
        self.links: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "a":
            return
        href = dict(attrs).get("href")
        if href:
            self.links.append(html.unescape(href))


def _loop_running() -> bool:
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return False
    return True


def _browser_available() -> bool:
    """Whether a Playwright Chromium binary is actually installed."""
    try:
        from playwright.sync_api import sync_playwright
    except Exception:
        return False
    try:
        with sync_playwright() as p:
            path = p.chromium.executable_path
            return bool(path) and os.path.exists(path)
    except Exception:
        return False


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _to_plain_text(raw: str) -> str:
    if "<" not in raw:
        return raw.strip()
    parser = _TextExtractor()
    try:
        parser.feed(raw)
    except Exception:
        return raw.strip()
    return parser.text()


def _detect_title(raw: str, url: str) -> str:
    match = re.search(r"<title[^>]*>(.*?)</title>", raw, re.IGNORECASE | re.DOTALL)
    if match:
        title = html.unescape(match.group(1)).strip()
        if title:
            return re.sub(r"\s+", " ", title)
    match = re.search(r"<h1[^>]*>(.*?)</h1>", raw, re.IGNORECASE | re.DOTALL)
    if match:
        title = html.unescape(match.group(1)).strip()
        if title:
            return re.sub(r"\s+", " ", title)
    return url


def _title_from_browser_summary(summary: str) -> str:
    for line in summary.splitlines():
        if line.startswith("Title:"):
            return line[len("Title:"):].strip()
    return ""


def _is_plausible_url(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        return False
    if any(parsed.netloc.endswith(host) for host in _BLOCKED_HOSTS):
        return False
    path = parsed.path.lower()
    return not any(path.endswith(ext) for ext in _STATIC_EXTS)


def _resolve_search_link(href: str) -> str | None:
    if not _is_plausible_url(href):
        return None
    parsed = urlparse(href)
    if parsed.netloc.endswith("duckduckgo.com"):
        target = parse_qs(parsed.query).get("uddg", [None])[0]
        if target and _is_plausible_url(target):
            return target
        return None
    return href


def _extract_links(raw: str) -> list[str]:
    if "<" not in raw:
        return []
    parser = _LinkExtractor()
    try:
        parser.feed(raw)
    except Exception:
        return []
    seen: set[str] = set()
    links: list[str] = []
    for href in parser.links:
        resolved = _resolve_search_link(href)
        if resolved and resolved not in seen:
            seen.add(resolved)
            links.append(resolved)
    return links


def _topic_from_query(query: str) -> str:
    topic = re.sub(r"[^\w\s-]", " ", query or "")
    topic = re.sub(r"\s+", " ", topic).strip()
    if not topic:
        return ""
    return topic.title().replace(" ", "_")


def _fetch_url_sync(url: str, timeout_s: int) -> str:
    """Fetch a URL with urllib (standard library only). Raises on failure."""
    request = Request(url, headers={"User-Agent": _USER_AGENT, "Accept-Language": "en,en-US;q=0.9"})
    with urlopen(request, timeout=timeout_s) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        payload = response.read(_MAX_BYTES)
    return payload.decode(charset, errors="replace")


def _candidate_urls(query: str, timeout_s: int) -> list[str]:
    """Derive target URLs for a query without any search API."""
    query = (query or "").strip()
    urls: list[str] = []
    if re.match(r"^https?://", query):
        urls.append(query)
    topic = _topic_from_query(query)
    if topic:
        urls.append(_WIKI_TEMPLATE.format(topic=topic))
    try:
        ddg = _fetch_url_sync(_DDG_TEMPLATE.format(q=quote_plus(query)), min(timeout_s, 10))
        for link in _extract_links(ddg):
            if link not in urls:
                urls.append(link)
    except Exception as exc:
        logger.debug("research_candidate_discovery_failed", error=str(exc))
    return urls[:_MAX_CANDIDATES]


def _build_finding(query: str, url: str, title: str, body: str) -> dict[str, Any] | None:
    """Clean, chunk, BM25-score a page and emit one finding dict."""
    cleaned = clean_web_content(body, body)
    if not cleaned.strip():
        return None
    chunks = chunk_text(cleaned, chunk_size=_CHUNK_SIZE, overlap=_CHUNK_OVERLAP)
    scores = compute_bm25(query, chunks)
    ranked = sorted(range(len(chunks)), key=lambda i: scores[i], reverse=True)
    top = ranked[:_KEY_POINTS]
    key_points: list[str] = []
    for index in top:
        point = re.sub(r"\s+", " ", chunks[index]).strip()
        point = point[:_POINT_LIMIT]
        if point and point not in key_points:
            key_points.append(point)
    rel_score = round(sum(scores[i] for i in top) / len(top), 3) if top else 0.0
    return {
        "source": url,
        "title": title or url,
        "key_points": key_points,
        "rel_score": rel_score,
    }


def _collect_sync(candidates: list[str], query: str, timeout_s: int) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for url in candidates:
        try:
            raw = _fetch_url_sync(url, timeout_s)
        except Exception as exc:
            logger.debug("research_fetch_failed", url=url, error=str(exc))
            continue
        finding = _build_finding(query, url, _detect_title(raw, url), _to_plain_text(raw))
        if finding:
            findings.append(finding)
    return findings


async def _collect_browser(candidates: list[str], query: str, timeout_s: int) -> list[dict[str, Any]]:
    from app.tools import browser_tools

    findings: list[dict[str, Any]] = []
    try:
        for url in candidates:
            try:
                summary = await asyncio.wait_for(
                    browser_tools.browser_navigate(url, session_id=_SESSION_ID), timeout=timeout_s
                )
                body = await asyncio.wait_for(
                    browser_tools.browser_extract_text(session_id=_SESSION_ID), timeout=timeout_s
                )
            except Exception as exc:
                logger.debug("research_browser_fetch_failed", url=url, error=str(exc))
                continue
            title = _title_from_browser_summary(summary)
            finding = _build_finding(query, url, title, body)
            if finding:
                findings.append(finding)
    finally:
        with contextlib.suppress(Exception):
            await browser_tools.close_all_sessions()
    return findings


def run_research(query: str, sources: int = 3, timeout_s: int = 30) -> dict[str, Any]:
    """Run the research pipeline synchronously and return a report dict.

    Never raises: every step degrades silently. When no source is reachable
    the returned dict has ``ok: False`` and ``summary: "no sources reachable"``.
    """
    query = (query or "").strip()
    try:
        candidates = _candidate_urls(query, timeout_s)
    except Exception as exc:
        logger.warning("research_candidate_generation_failed", error=str(exc))
        candidates = []

    findings: list[dict[str, Any]] = []
    try:
        if _browser_available() and not _loop_running() and candidates:
            findings = asyncio.run(_collect_browser(candidates, query, timeout_s))
        else:
            findings = _collect_sync(candidates, query, timeout_s)
    except Exception as exc:
        logger.error("research_pipeline_failed", error=str(exc))
        findings = []

    findings.sort(key=lambda f: f["rel_score"], reverse=True)
    findings = findings[: max(1, int(sources))]
    ok = bool(findings)

    if ok:
        top = findings[0]
        points = "；".join(top["key_points"][:2])
        summary = (
            f"针对“{query}”的联网调研共采集 {len(findings)} 个可用来源。"
            f"相关度最高的来源是《{top['title']}》，其要点包括：{points}。"
            "其余发现与来源详见下方列表。"
        )
    else:
        summary = "no sources reachable"

    return {
        "ok": ok,
        "query": query,
        "summary": summary,
        "findings": findings,
        "sources": [f["source"] for f in findings],
        "generated_at": _now(),
    }


def research_report_text(result: dict[str, Any]) -> str:
    """Render a run_research() dict as a Markdown report."""
    query = result.get("query", "")
    lines = [f"# 调研报告：{query}", ""]

    summary = result.get("summary") or ""
    if summary:
        lines.append("## 摘要")
        lines.append("")
        lines.append(summary)
        lines.append("")

    findings = result.get("findings") or []
    lines.append("## 调研发现")
    lines.append("")
    if not findings:
        lines.append("_暂无可展示的调研发现。_")
        lines.append("")
    for finding in findings:
        lines.append(f"### {finding.get('title', finding.get('source', ''))}")
        lines.append(f"- 来源：{finding.get('source', '')}（相关度 {finding.get('rel_score', 0.0)}）")
        for point in finding.get("key_points", []):
            lines.append(f"- {point}")
        lines.append("")

    sources = result.get("sources") or []
    lines.append("## 来源列表")
    lines.append("")
    if not sources:
        lines.append("_无可用来源。_")
        lines.append("")
    for index, source in enumerate(sources, start=1):
        lines.append(f"{index}. {source}")

    return "\n".join(lines)
