"""Notion integration client."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class NotionConfig:
    token: str = ""
    database_id: str = ""


class NotionClient:
    def __init__(self, config: NotionConfig | None = None) -> None:
        self.config = config or NotionConfig()

    async def create_page(self, title: str, content: str = "") -> dict[str, Any]:
        return {"id": "page-1", "title": title}
