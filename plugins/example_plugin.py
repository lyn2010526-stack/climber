"""Example plugin — demonstrates the plugin system.

This plugin adds tools for working with dates, text, and hashing.
Copy this file to the plugins/ directory to activate.
"""


def register(tools, skills):
    """Register all tools and skills provided by this plugin."""
    import hashlib
    import json
    from datetime import datetime, timedelta

    @tools.tool(description="Convert a date string to different format")
    async def format_date(date_str: str, input_format: str = "%Y-%m-%d", output_format: str = "%B %d, %Y") -> str:
        try:
            dt = datetime.strptime(date_str, input_format)
            return dt.strftime(output_format)
        except ValueError as e:
            return f"Date parse error: {e}"

    @tools.tool(description="Add or subtract days from a date")
    async def date_math(date_str: str, days: int, date_format: str = "%Y-%m-%d") -> str:
        try:
            dt = datetime.strptime(date_str, date_format)
            result = dt + timedelta(days=days)
            return result.strftime(date_format)
        except ValueError as e:
            return f"Date error: {e}"

    @tools.tool(description="Generate SHA256 hash of text")
    async def sha256_hash(text: str) -> str:
        return hashlib.sha256(text.encode()).hexdigest()

    @tools.tool(description="Generate MD5 hash of text")
    async def md5_hash(text: str) -> str:
        return hashlib.md5(text.encode()).hexdigest()

    @tools.tool(description="Count words, characters, and lines in text")
    async def text_stats(text: str) -> str:
        words = len(text.split())
        chars = len(text)
        lines = len(text.splitlines())
        return json.dumps({"words": words, "characters": chars, "lines": lines})

    @tools.tool(description="Convert text to slug (URL-friendly)")
    async def slugify(text: str) -> str:
        import re
        slug = text.lower().strip()
        slug = re.sub(r"[^\w\s-]", "", slug)
        slug = re.sub(r"[-\s]+", "-", slug)
        return slug
