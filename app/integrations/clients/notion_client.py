"""Notion integration client."""
from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import quote

from ._http import IntegrationError, request_json, require_config, response_id, validate_text


@dataclass
class NotionConfig:
    token: str = ""
    database_id: str = ""
    data_source_id: str = ""
    timeout: float = 15.0


class NotionClient:
    def __init__(self, config: NotionConfig | None = None):
        self.config = config or NotionConfig()

    async def create_page(self, title: str, content: str = "") -> dict:
        """Create a database page and return the API object plus the legacy title.

        Contracts: https://developers.notion.com/reference/post-page
        https://developers.notion.com/guides/get-started/upgrade-guide-2025-09-03
        A database with multiple sources requires an explicit data_source_id.
        Content is plain text, split into paragraph blocks without truncation.
        """
        require_config("Notion", token=self.config.token)
        source_id = self.config.data_source_id
        if not source_id:
            require_config("Notion", database_id=self.config.database_id)
        else:
            require_config("Notion", data_source_id=source_id)
        if self.config.database_id:
            require_config("Notion", database_id=self.config.database_id)
        validate_text(title, "title", 2000)
        validate_text(content, "content", 200000, allow_empty=True)
        # Pin the documented database/data-source split instead of relying on defaults.
        headers = {
            "Authorization": f"Bearer {self.config.token}",
            "Notion-Version": "2025-09-03",
        }
        if self.config.database_id:
            database = await request_json(
                "Notion", "GET",
                f"https://api.notion.com/v1/databases/{quote(self.config.database_id, safe='')}",
                headers=headers, timeout=self.config.timeout,
            )
            sources = database.get("data_sources")
            if (database.get("object") != "database" or not isinstance(sources, list)
                    or any(not isinstance(item, dict) for item in sources)):
                raise IntegrationError("Notion", "invalid database data_sources response")
            source_ids = [response_id(item, "id", "Notion") for item in sources]
            if source_id:
                if source_id not in source_ids:
                    raise ValueError("data_source_id does not belong to database_id")
            elif len(source_ids) == 1:
                source_id = source_ids[0]
            else:
                raise NotImplementedError(
                    "Notion: unsupported ambiguous database; provide an explicit data_source_id"
                )
        schema = await request_json(
            "Notion", "GET",
            f"https://api.notion.com/v1/data_sources/{quote(source_id, safe='')}",
            headers=headers, timeout=self.config.timeout,
        )
        properties = schema.get("properties")
        if schema.get("object") != "data_source" or not isinstance(properties, dict):
            raise IntegrationError("Notion", "invalid data source schema response")
        title_fields = [
            name for name, prop in properties.items()
            if isinstance(prop, dict) and prop.get("type") == "title"
        ]
        if len(title_fields) != 1:
            raise NotImplementedError("Notion: unsupported schema; expected one title property")
        payload = {
            "parent": {"data_source_id": source_id},
            "properties": {
                title_fields[0]: {"title": [{"type": "text", "text": {"content": title}}]},
            },
        }
        if content:
            payload["children"] = [
                {"object": "block", "type": "paragraph", "paragraph": {"rich_text": [
                    {"type": "text", "text": {"content": content[start:start + 2000]}}
                ]}}
                for start in range(0, len(content), 2000)
            ]
        data = await request_json(
            "Notion", "POST", "https://api.notion.com/v1/pages",
            headers=headers, timeout=self.config.timeout, payload=payload,
        )
        if data.get("object") != "page":
            raise IntegrationError("Notion", "response is not a page; outcome unknown")
        response_id(data, "id", "Notion")
        return {**data, "title": title}
