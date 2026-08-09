"""Web content cleaning and noise filtering.

"""

from __future__ import annotations

import re


def clean_web_content(html: str, text: str) -> str:
    """Remove ads, navigation, footers, and other noise from web content.

    """
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


def extract_main_content(text: str) -> str:
    """Extract the main content area from a web page."""
    cleaned = clean_web_content("", text)
    return cleaned


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
    for pattern in noise_patterns:
        if re.search(pattern, lower):
            return True
    return False
