"""Memory Block — a single memory file with YAML frontmatter metadata.

Each memory block is a markdown file with structured metadata:
---
description: <human-readable description>
created: <ISO timestamp>
updated: <ISO timestamp>
category: <system|reference|skills|conversations>
importance: <0.0-1.0>
tags: [tag1, tag2]
---

<body content>
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

FRONTMATTER_PATTERN = re.compile(
    r"^---\s*\n(.*?)\n---\s*\n(.*)",
    re.DOTALL,
)


@dataclass
class MemoryBlock:
    """A single memory file with metadata.

    Attributes:
        path: Relative path within the memory filesystem (e.g. "system/persona.md")
        content: The markdown body content (without frontmatter)
        description: Human-readable description of this memory block
        metadata: Additional metadata (created, updated, category, importance, tags, etc.)
    """

    path: str
    content: str = ""
    description: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        now = datetime.now(UTC).isoformat()
        if "created" not in self.metadata:
            self.metadata["created"] = now
        if "updated" not in self.metadata:
            self.metadata["updated"] = now
        if "id" not in self.metadata:
            self.metadata["id"] = str(uuid4())
        if "category" not in self.metadata:
            self._infer_category()

    def _infer_category(self) -> None:
        """Infer category from a recognized path prefix.

        Only catalogued top-level directories map to a category; unknown
        prefixes leave the category unset rather than mislabeling the block
        as ``reference``.
        """
        if self.path:
            parts = self.path.split("/")
            if parts[0] in ("system", "reference", "skills", "conversations"):
                self.metadata["category"] = parts[0]

    def to_markdown(self) -> str:
        """Serialize to markdown with YAML frontmatter."""
        meta = dict(self.metadata)
        meta["updated"] = datetime.now(UTC).isoformat()

        if self.description:
            meta["description"] = self.description

        lines = ["---"]
        lines.extend(_serialize_yaml(meta, indent=0))
        lines.append("---")
        lines.append("")
        lines.append(self.content.strip())
        lines.append("")
        return "\n".join(lines)

    @classmethod
    def from_markdown(cls, path: str, md: str) -> MemoryBlock:
        """Parse a markdown string with YAML frontmatter into a MemoryBlock."""
        match = FRONTMATTER_PATTERN.match(md)
        if match:
            meta = _parse_yaml(match.group(1))
            content = match.group(2).strip()
        else:
            meta = {}
            content = md.strip()

        description = meta.pop("description", "")
        return cls(
            path=path,
            content=content,
            description=description,
            metadata=meta,
        )

    @classmethod
    def new(
        cls,
        path: str,
        content: str,
        description: str = "",
        category: str = "",
        importance: float = 0.5,
        tags: list[str] | None = None,
    ) -> MemoryBlock:
        """Factory method to create a new MemoryBlock with standard metadata."""
        now = datetime.now(UTC).isoformat()
        meta: dict[str, Any] = {
            "id": str(uuid4()),
            "created": now,
            "updated": now,
            "importance": importance,
        }
        if category:
            meta["category"] = category
        if tags:
            meta["tags"] = tags
        return cls(
            path=path,
            content=content,
            description=description,
            metadata=meta,
        )


def _serialize_yaml(data: dict[str, Any], indent: int = 0) -> list[str]:
    """Simple YAML serializer for flat metadata dicts."""
    lines: list[str] = []
    prefix = "  " * indent
    for key, value in data.items():
        if isinstance(value, list):
            if not value:
                lines.append(f"{prefix}{key}: []")
            else:
                lines.append(f"{prefix}{key}:")
                lines.extend(f"{prefix}  - {_yaml_scalar(str(item))}" for item in value)
        elif isinstance(value, dict):
            lines.append(f"{prefix}{key}:")
            lines.extend(_serialize_yaml(value, indent + 1))
        elif isinstance(value, bool):
            lines.append(f"{prefix}{key}: {'true' if value else 'false'}")
        elif isinstance(value, (int, float)):
            lines.append(f"{prefix}{key}: {value}")
        elif value is None:
            lines.append(f"{prefix}{key}: null")
        else:
            lines.append(f"{prefix}{key}: {_yaml_scalar(value)}")
    return lines


def _yaml_scalar(value: str) -> str:
    """Quote a string so it round-trips losslessly through the YAML parser.

    Quoting applies when the value is empty, could otherwise be re-read as a
    different type (bool/int/float/null), or contains characters that plain
    YAML scalars interpret structurally.
    """
    if value == "":
        return '""'
    if value != value.strip():
        return _quote(value)
    lowered = value.lower()
    if lowered in {"true", "false", "null", "~"}:
        return _quote(value)
    if value[0] in "-?:,[]{}#&*!|>'\"%@`" or " " in value:
        return _quote(value)
    if "\n" in value or any(c in value for c in ":{}[]&*?|-><!%@`#,\"\\"):
        return _quote(value)
    try:
        int(value)
    except ValueError:
        return value
    return _quote(value)


def _quote(value: str) -> str:
    """Quote a string value with double quotes, escaping embedded escapes."""
    escaped = value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
    return f'"{escaped}"'


def _parse_yaml(text: str) -> dict[str, Any]:
    """Simple YAML parser for flat metadata (no nested structures except lists)."""
    result: dict[str, Any] = {}
    current_key: str | None = None
    current_list: list[str] = []

    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        if stripped.startswith("- "):
            if current_key is not None:
                current_list.append(_parse_yaml_value(stripped[2:].strip()))
            continue

        if ":" in stripped:
            key, _, value = stripped.partition(":")
            key = key.strip()
            value = value.strip()

            if current_key is not None and current_list:
                result[current_key] = current_list
                current_list = []

            if value == "":
                current_key = key
            else:
                current_key = None
                result[key] = _parse_yaml_value(value)

    if current_key is not None and current_list:
        result[current_key] = current_list

    return result


def _parse_yaml_value(value: str) -> Any:
    """Parse a single YAML scalar value (lossless for quoted strings)."""
    if len(value) >= 2 and value[0] == '"' and value[-1] == '"':
        return _unescape(value[1:-1])
    if len(value) >= 2 and value[0] == "'" and value[-1] == "'":
        return value[1:-1].replace("''", "'")
    if value.lower() == "true":
        return True
    if value.lower() == "false":
        return False
    if value.lower() in ("null", "~"):
        return None
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        pass
    return value


def _unescape(value: str) -> str:
    """Unescape double-quoted YAML escapes (\", \\, \\n)."""
    out: list[str] = []
    i = 0
    n = len(value)
    while i < n:
        char = value[i]
        if char == "\\" and i + 1 < n:
            nxt = value[i + 1]
            if nxt == "n":
                out.append("\n")
            elif nxt in ('"', "\\"):
                out.append(nxt)
            else:
                out.append(nxt)
            i += 2
        else:
            out.append(char)
            i += 1
    return "".join(out)
