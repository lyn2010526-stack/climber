"""Markdown frontmatter 元信息解析（base_deps）。

改写自 agentic-kb-lite `src/parser/md_meta_parser.py` 的设计思路：
解析 Markdown 的 frontmatter，读取 skill、规则文档元信息
（name、description、tags、skill 分类等）。

非原样复制，实现为原创的正则/YAML 轻量解析。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

# 匹配 Markdown frontmatter 定界块（首尾各自三个短横线）
_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n?", re.DOTALL)
_YAML_LINE_RE = re.compile(r"^([a-zA-Z_][\w.-]*)\s*:\s*(.*)$")

COMMON_META_KEYS = {
    "name", "description", "tags", "skill", "version", "author", "language",
    "category", "type", "title", "summary", "rules", "dependencies", "license",
}


@dataclass
class DocMeta:
    """解析出的文档元信息。"""

    has_frontmatter: bool = False
    fields: dict[str, Any] = field(default_factory=dict)
    title: str = ""
    description: str = ""
    tags: list[str] = field(default_factory=list)
    doc_type: str = ""                 # skill | rule | code | text
    raw_frontmatter: str = ""

    def to_memory_item_fields(self) -> dict[str, Any]:
        """转成记忆项所需的元信息字段。"""
        return {
            "title": self.title or self.fields.get("name", ""),
            "doc_type": self.doc_type,
            "tags": self.tags,
            "meta": self.fields,
        }


class MarkdownMetaParser:
    """Markdown frontmatter 解析器（skill/规则文档）。"""

    def parse(self, markdown_text: str, default_doc_type: str = "text") -> DocMeta:
        meta = DocMeta(doc_type=default_doc_type)
        if not markdown_text:
            return meta
        m = _FRONTMATTER_RE.match(markdown_text)
        if not m:
            return meta

        meta.has_frontmatter = True
        meta.raw_frontmatter = m.group(1)
        fields: dict[str, Any] = {}
        for line in meta.raw_frontmatter.splitlines():
            lm = _YAML_LINE_RE.match(line.strip())
            if not lm:
                continue
            key, value = lm.group(1), lm.group(2).strip().strip("'\"")
            if key in {"tags"} or (value.startswith("[") and value.endswith("]")):
                # 列表解析
                if value.startswith("["):
                    items = [v.strip().strip("'\"") for v in value[1:-1].split(",")]
                else:
                    items = [v.strip().strip("'\"") for v in value.split(",")]
                fields[key] = [i for i in items if i]
            else:
                fields[key] = value
        meta.fields = fields
        meta.title = fields.get("name", fields.get("title", "")) or ""
        meta.description = fields.get("description", fields.get("summary", "")) or ""
        meta.tags = fields.get("tags", []) or []
        # doc_type 推断
        if fields.get("type"):
            meta.doc_type = fields["type"]
        elif "skill" in fields or fields.get("name", "").lower().startswith("skill"):
            meta.doc_type = "skill"
        return meta


def parse_markdown_meta(markdown_text: str, default_doc_type: str = "text") -> dict[str, Any]:
    """便捷入口，返回 dict（供技能/规则加载器调用）。"""
    parser = MarkdownMetaParser()
    meta = parser.parse(markdown_text, default_doc_type)
    return {
        "has_frontmatter": meta.has_frontmatter,
        "title": meta.title,
        "description": meta.description,
        "tags": meta.tags,
        "doc_type": meta.doc_type,
        "fields": meta.fields,
    }
