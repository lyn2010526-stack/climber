"""Web content cleaning and main-content extraction.

The legacy ``clean_web_content(html, text)`` line filter is preserved exactly
for callers that pass already-flattened text. A stdlib-only DOM path adds
article-body selection for callers that pass real HTML, with a graceful
fallback to the legacy filter whenever no confident candidate is found.
"""

from __future__ import annotations

import re
from html.parser import HTMLParser

_BLOCK_TAGS = {"article", "main", "section", "div", "p", "h1", "h2", "h3", "li", "blockquote", "pre", "td"}
_POSITIVE_TAGS = {"article", "main", "p", "h1", "h2", "h3", "li", "blockquote", "pre"}
_NEGATIVE_TAGS = {"nav", "header", "footer", "aside", "form", "script", "style", "noscript", "svg", "template", "button"}


def clean_web_content(html: str, text: str) -> str:
    """Remove ads, navigation, footers, and other noise from web content.

    When ``html`` carries real markup, route through ``extract_main_content``
    for DOM-level article selection; otherwise apply the legacy line filter to
    ``text`` (unchanged behavior for existing callers).
    """
    if html and "<" in html:
        extracted = extract_main_content(html, fallback_text=text)
        if extracted:
            return extracted
    return _filter_lines(text)


def extract_main_content(text: str, *, fallback_text: str = "") -> str:
    """Extract the main content area from a web page.

    Accepts HTML markup or already-flattened text. Returns the extracted body,
    falling back to the legacy line filter when markup is absent or no
    confident candidate is found.
    """
    if not text or "<" not in text:
        return _filter_lines(text)
    try:
        parser = _MainContentParser()
        parser.feed(text)
        parser.close()
    except Exception:
        return _filter_lines(fallback_text or text)
    candidate = _select_best_block(parser.blocks)
    if not candidate:
        return _filter_lines(fallback_text or _plain_text(text))
    return _filter_lines(candidate)


def _filter_lines(text: str) -> str:
    lines = text.splitlines()
    filtered: list[str] = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if _is_noise(stripped):
            continue
        filtered.append(stripped)
    return "\n".join(filtered)


class _Block:
    __slots__ = ("depth", "tag", "text_parts")

    def __init__(self, tag: str, depth: int) -> None:
        self.tag = tag
        self.text_parts: list[str] = []
        self.depth = depth


class _MainContentParser(HTMLParser):
    """Collect visible text grouped into candidate content blocks."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.blocks: list[_Block] = []
        self._stack: list[_Block] = []
        self._suppress = 0
        self._depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self._depth += 1
        if tag in _NEGATIVE_TAGS:
            self._suppress += 1
            return
        if tag in _BLOCK_TAGS and not self._suppress:
            block = _Block(tag, self._depth)
            self.blocks.append(block)
            self._stack.append(block)

    def handle_endtag(self, tag: str) -> None:
        if tag in _NEGATIVE_TAGS:
            if self._suppress:
                self._suppress -= 1
        elif tag in _BLOCK_TAGS:
            for index in range(len(self._stack) - 1, -1, -1):
                if self._stack[index].tag == tag:
                    del self._stack[index:]
                    break
        self._depth = max(0, self._depth - 1)

    def handle_data(self, data: str) -> None:
        if self._suppress or not data.strip():
            return
        for block in self._stack:
            block.text_parts.append(data)


def _select_best_block(blocks: list[_Block]) -> str:
    """Pick the highest-scoring candidate block's visible text.

    Score favors longer text with positive-semantic tags and richer
    punctuation (prose density), which approximates article-body selection.
    """
    best_score = 0.0
    best_text = ""
    for block in blocks:
        text = " ".join(part.strip() for part in block.text_parts if part.strip())
        if len(text) < 40:
            continue
        words = len(re.findall(r"\w+", text))
        punctuation = sum(text.count(ch) for ch in ".。,，!?！？;；")
        positive = 1.0 if block.tag in _POSITIVE_TAGS else 0.0
        score = len(text) + words * 0.2 + punctuation * 3.0 + positive * 20.0
        if block.tag in {"h1", "h2", "h3"}:
            score *= 0.4
        if score > best_score:
            best_score = score
            best_text = text
    return best_text


def _plain_text(html: str) -> str:
    """Flatten markup to visible text without article selection."""
    parser = _PlainTextParser()
    try:
        parser.feed(html)
        parser.close()
    except Exception:
        return html
    return "\n".join(parser.parts)


class _PlainTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._suppress = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in _NEGATIVE_TAGS:
            self._suppress += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in _NEGATIVE_TAGS and self._suppress:
            self._suppress -= 1

    def handle_data(self, data: str) -> None:
        if not self._suppress and data.strip():
            self.parts.append(data.strip())


def _is_noise(line: str) -> bool:
    noise_patterns = [
        r"^(cookie|accept cookies|同意|接受 cookies?)",
        r"^(subscribe|newsletter|订阅|news letter)",
        r"^(advertisement|广告|赞助|sponsored)",
        r"^(follow us|关注我们|关注)",
        r"^(share this|分享|转发)",
        r"^(related|相关|推荐阅读)",
        r"^(comments|评论|留言)",
        r"^(login|sign in|登录|注册|sign up)",
        r"^(skip to|跳转到)",
        r"^(menu|导航|navigation)",
    ]
    lower = line.lower()
    if any(re.search(pattern, lower) for pattern in noise_patterns):
        return True
    # Extremely short single-character lines are noise, but short meaningful
    # text (titles, short answers) must be preserved.
    return len(line.strip()) <= 1
