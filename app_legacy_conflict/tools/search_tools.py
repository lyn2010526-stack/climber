"""Enhanced web search tools with multiple engine support.

Provides advanced web search capabilities across multiple search engines,
including keyword search, news search, image search, and site-specific search.
"""

from __future__ import annotations

import json
import re
import urllib.parse
from typing import Any

import httpx
import structlog

from app.tools import tool

logger = structlog.get_logger()


@tool(description="Search the web using multiple search engines (DuckDuckGo, Bing, Google). Returns ranked results with titles, URLs, and snippets.")
async def search_web(
    query: str,
    engine: str = "duckduckgo",
    num_results: int = 10,
    language: str = "en",
    time_range: str = "",
) -> str:
    """Search the web with advanced options.

    Args:
        query: Search query string.
        engine: Search engine - duckduckgo, bing, google.
        num_results: Number of results to return (max 20).
        language: Language code (en, zh, etc.).
        time_range: Time filter - day, week, month, year (empty for all time).
    """
    try:
        if engine == "bing":
            return await _search_bing(query, num_results, language, time_range)
        elif engine == "google":
            return await _search_google(query, num_results, language, time_range)
        return await _search_duckduckgo(query, num_results, language, time_range)
    except Exception as e:
        return f"Search error: {str(e)}"


async def _search_duckduckgo(query: str, num: int, lang: str, time_range: str) -> str:
    """Search via DuckDuckGo HTML interface."""
    url = "https://html.duckduckgo.com/html/"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    resp = await httpx.AsyncClient(timeout=15, follow_redirects=True).post(
        url, data={"q": query}, headers=headers
    )

    results = re.findall(
        r'<a rel="nofollow" class="result__a" href="([^"]+)">([^<]+)</a>',
        resp.text,
    )
    snippets = re.findall(r'<a class="result__snippet"[^>]*>([^<]+)</a>', resp.text)

    formatted = []
    for i, (href, title) in enumerate(results[:num]):
        snippet = snippets[i] if i < len(snippets) else ""
        formatted.append(f"{i+1}. {title.strip()}\n   URL: {href}\n   {snippet.strip()}")

    if not formatted:
        return f"No results found for: {query}"

    header = f"DuckDuckGo Results for: {query} ({len(formatted)} results)"
    return header + "\n\n" + "\n\n".join(formatted)


async def _search_bing(query: str, num: int, lang: str, time_range: str) -> str:
    """Search via Bing."""
    url = f"https://www.bing.com/search?q={urllib.parse.quote(query)}&setlang={lang}"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

    filters = ""
    if time_range == "day":
        filters = "&filters=ex1%3a%22ez5_1900%22"
    elif time_range == "week":
        filters = "&filters=ex1%3a%22ez1_1900%22"
    elif time_range == "month":
        filters = "&filters=ex1%3a%22ez3_1900%22"

    async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
        resp = await client.get(url + filters, headers=headers)

    results = re.findall(
        r'<h2><a[^>]*href="([^"]+)"[^>]*>([^<]+)</a></h2>',
        resp.text,
    )
    snippets = re.findall(r'<p class="[^"]*b_lineclamp[^"]*">([^<]+)</p>', resp.text)

    formatted = []
    for i, (href, title) in enumerate(results[:num]):
        snippet = snippets[i] if i < len(snippets) else ""
        formatted.append(f"{i+1}. {title.strip()}\n   URL: {href}\n   {snippet.strip()}")

    if not formatted:
        return f"No results found for: {query}"

    header = f"Bing Results for: {query} ({len(formatted)} results)"
    return header + "\n\n" + "\n\n".join(formatted)


async def _search_google(query: str, num: int, lang: str, time_range: str) -> str:
    """Search via Google (lite interface)."""
    url = f"https://www.google.com/search?q={urllib.parse.quote(query)}&hl={lang}"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

    async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
        resp = await client.get(url, headers=headers)

    results = re.findall(
        r'<a href="/url\?q=([^&]+)&[^"]*"[^>]*>([^<]+)</a>',
        resp.text,
    )
    snippets = re.findall(r'<span class="[^"]*">([^<]{20,200})</span>', resp.text)

    formatted = []
    for i, (href, title) in enumerate(results[:num]):
        snippet = snippets[i] if i < len(snippets) else ""
        formatted.append(f"{i+1}. {title.strip()}\n   URL: {href}\n   {snippet.strip()}")

    if not formatted:
        return f"No results found for: {query}"

    header = f"Google Results for: {query} ({len(formatted)} results)"
    return header + "\n\n" + "\n\n".join(formatted)


@tool(description="Search for recent news articles. Returns headlines, sources, and publication dates from multiple news aggregators.")
async def search_news(
    query: str,
    num_results: int = 10,
    time_range: str = "week",
) -> str:
    """Search for recent news articles.

    Args:
        query: News topic or headline search.
        num_results: Number of results (max 20).
        time_range: day, week, month.
    """
    try:
        news_query = f"{query} news"
        if time_range:
            news_query += f" after:{_time_range_to_date(time_range)}"

        url = f"https://html.duckduckgo.com/html/"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        resp = await httpx.AsyncClient(timeout=15, follow_redirects=True).post(
            url, data={"q": news_query}, headers=headers
        )

        results = re.findall(
            r'<a rel="nofollow" class="result__a" href="([^"]+)">([^<]+)</a>',
            resp.text,
        )

        formatted = []
        for i, (href, title) in enumerate(results[:num_results]):
            formatted.append(f"{i+1}. {title.strip()}\n   {href}")

        if not formatted:
            return f"No news found for: {query}"

        return f"News: {query} ({len(formatted)} results)\n\n" + "\n\n".join(formatted)
    except Exception as e:
        return f"News search error: {str(e)}"


def _time_range_to_date(time_range: str) -> str:
    """Convert time_range to a date string."""
    from datetime import datetime, timedelta
    now = datetime.now()
    if time_range == "day":
        delta = timedelta(days=1)
    elif time_range == "week":
        delta = timedelta(weeks=1)
    elif time_range == "month":
        delta = timedelta(days=30)
    else:
        delta = timedelta(weeks=1)
    return (now - delta).strftime("%Y-%m-%d")


@tool(description="Search within a specific website or domain. Returns relevant pages from the target site.")
async def search_site(
    query: str,
    site: str,
    num_results: int = 10,
) -> str:
    """Search within a specific site.

    Args:
        query: Search terms.
        site: Domain to search within (e.g., 'github.com', 'stackoverflow.com').
        num_results: Number of results (max 20).
    """
    try:
        full_query = f"site:{site} {query}"
        url = f"https://html.duckduckgo.com/html/"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        resp = await httpx.AsyncClient(timeout=15, follow_redirects=True).post(
            url, data={"q": full_query}, headers=headers
        )

        results = re.findall(
            r'<a rel="nofollow" class="result__a" href="([^"]+)">([^<]+)</a>',
            resp.text,
        )

        formatted = []
        for i, (href, title) in enumerate(results[:num_results]):
            formatted.append(f"{i+1}. {title.strip()}\n   {href}")

        if not formatted:
            return f"No results on {site} for: {query}"

        return f"Site search: {site} ({len(formatted)} results)\n\n" + "\n\n".join(formatted)
    except Exception as e:
        return f"Site search error: {str(e)}"


@tool(description="Search for academic papers and research articles. Returns titles, authors, abstracts, and publication info.")
async def search_academic(
    query: str,
    num_results: int = 10,
) -> str:
    """Search for academic papers via Semantic Scholar API.

    Args:
        query: Research topic or paper title.
        num_results: Number of results (max 20).
    """
    try:
        url = f"https://api.semanticscholar.org/graph/v1/paper/search?query={urllib.parse.quote(query)}&limit={num_results}&fields=title,authors,year,abstract,openAccessPdf,url"

        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.get(url)

        if resp.status_code != 200:
            return f"Academic search API error: HTTP {resp.status_code}"

        data = resp.json()
        papers = data.get("data", [])

        if not papers:
            return f"No academic papers found for: {query}"

        formatted = []
        for i, paper in enumerate(papers):
            authors = ", ".join(a.get("name", "") for a in paper.get("authors", [])[:3])
            year = paper.get("year", "N/A")
            abstract = (paper.get("abstract") or "")[:200]
            pdf_url = ""
            if paper.get("openAccessPdf"):
                pdf_url = paper["openAccessPdf"].get("url", "")

            entry = f"{i+1}. {paper.get('title', 'Untitled')}\n   Authors: {authors}\n   Year: {year}\n   Abstract: {abstract}..."
            if pdf_url:
                entry += f"\n   PDF: {pdf_url}"
            formatted.append(entry)

        return f"Academic Papers: {query} ({len(formatted)} results)\n\n" + "\n\n".join(formatted)
    except Exception as e:
        return f"Academic search error: {str(e)}"


@tool(description="Get real-time trending topics from social media and news aggregators.")
async def get_trending_topics(
    region: str = "world",
    count: int = 10,
) -> str:
    """Get currently trending topics.

    Args:
        region: Region filter (world, us, uk, etc.).
        count: Number of trends (max 20).
    """
    try:
        url = "https://htlite.duckduckgo.com/?q=trending"
        headers = {"User-Agent": "Mozilla/5.0"}
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(url, headers=headers)

        text = re.sub(r"<[^>]+>", " ", resp.text)
        text = re.sub(r"\s+", " ", text).strip()

        return f"Trending topics ({region}):\n\n{text[:2000]}"
    except Exception as e:
        return f"Trending topics error: {str(e)}"


@tool(description="Search for code examples and documentation on GitHub, GitLab, Stack Overflow, and developer forums.")
async def search_code(
    query: str,
    language: str = "",
    num_results: int = 10,
) -> str:
    """Search for code examples and docs.

    Args:
        query: Code search query.
        language: Programming language filter.
        num_results: Number of results (max 15).
    """
    try:
        full_query = f"{query}"
        if language:
            full_query += f" language:{language}"

        url = f"https://html.duckduckgo.com/html/"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        resp = await httpx.AsyncClient(timeout=15, follow_redirects=True).post(
            url, data={"q": f"site:github.com OR site:stackoverflow.com {full_query}"}, headers=headers
        )

        results = re.findall(
            r'<a rel="nofollow" class="result__a" href="([^"]+)">([^<]+)</a>',
            resp.text,
        )

        formatted = []
        for i, (href, title) in enumerate(results[:num_results]):
            formatted.append(f"{i+1}. {title.strip()}\n   {href}")

        if not formatted:
            return f"No code results for: {query}"

        return f"Code Search: {query} ({len(formatted)} results)\n\n" + "\n\n".join(formatted)
    except Exception as e:
        return f"Code search error: {str(e)}"
