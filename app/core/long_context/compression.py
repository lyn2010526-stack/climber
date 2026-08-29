"""Context compression pipeline.

Everything entering the context is compressed:
- tool results: extract key fields, drop redundant structure, JSON to single line
- screenshots: prefer a VLM text description (<= 200 chars) unless exact
  positioning is needed
- UI trees: filter invisible elements, keep only interactive ones
- code: only diffs or relevant functions, never full files
- long text: content over 500 chars is distilled into a bullet list
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any


def compress_json_single_line(payload: Any) -> str:
    """Compress a JSON structure into a compact single line."""
    try:
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"), default=str)
    except (TypeError, ValueError):
        return str(payload)


def extract_key_fields(payload: Any, keep: list[str] | None = None) -> dict[str, Any]:
    """Keep only the key fields of a dict, dropping the rest."""
    if not isinstance(payload, dict):
        return {"value": payload}
    if keep is None:
        return payload
    return {k: payload[k] for k in keep if k in payload}


class CompressionPipeline:
    """Applies per-type compression rules to content entering the context."""

    def __init__(
        self,
        vlm_describer: Callable[..., Any] | None = None,
        long_text_threshold: int = 500,
        screenshot_desc_max_chars: int = 200,
        distiller: Callable[[str], str] | None = None,
    ) -> None:
        self._vlm_describer = vlm_describer
        self._long_text_threshold = long_text_threshold
        self._screenshot_desc_max_chars = screenshot_desc_max_chars
        self._distiller = distiller

    async def compress(self, kind: str, content: Any, **kwargs: Any) -> str:
        """Compress content based on its kind.

        Args:
            kind: one of tool_result | screenshot | ui_tree | code | text
        """
        if kind == "tool_result":
            return self._compress_tool_result(content)
        if kind == "screenshot":
            return await self._compress_screenshot(content)
        if kind == "ui_tree":
            return self._compress_ui_tree(content)
        if kind == "code":
            return self._compress_code(content)
        if kind == "text":
            return self._compress_text(content)
        return str(content)

    def _compress_tool_result(self, content: Any) -> str:
        if isinstance(content, (dict, list)):
            keep = None
            if isinstance(content, dict) and "keep" in content:
                keep = content.pop("keep")
                return compress_json_single_line(extract_key_fields(content, keep))
            return compress_json_single_line(content)
        return str(content)

    async def _compress_screenshot(self, content: Any) -> str:
        if self._vlm_describer is None:
            return f"[screenshot: {content}]"
        result = await self._vlm_describer(content)
        if isinstance(result, str):
            return result[: self._screenshot_desc_max_chars]
        return str(result)[: self._screenshot_desc_max_chars]

    def _compress_ui_tree(self, content: Any) -> str:
        """Filter invisible nodes; keep only interactive elements."""
        if isinstance(content, str):
            return content
        interactive_attrs = ("clickable", "scrollable", "editable", "enabled")
        if isinstance(content, list):
            kept = [
                n for n in content
                if isinstance(n, dict) and n.get("visible", True) is not False
                and any(n.get(a) for a in interactive_attrs)
            ]
            return json.dumps(kept, ensure_ascii=False, default=str)
        return json.dumps(content, ensure_ascii=False, default=str)

    def _compress_code(self, content: Any) -> str:
        if isinstance(content, str) and len(content) > 4000:
            return content[:4000] + "\n... [code truncated: pass diffs, not full files]"
        return str(content)

    def _compress_text(self, content: str) -> str:
        if len(content) <= self._long_text_threshold:
            return content
        if self._distiller is not None:
            return self._distiller(content)
        return self._bullet_distill(content)

    @staticmethod
    def _bullet_distill(text: str, max_bullets: int = 8) -> str:
        sentences = [s.strip() for s in text.replace("\n", " ").split(". ") if s.strip()]
        bullets = "\n".join(f"- {s}." for s in sentences[:max_bullets])
        return f"<distilled>\n{bullets}\n</distilled>"


_default_pipeline: CompressionPipeline | None = None


def get_compression_pipeline() -> CompressionPipeline:
    global _default_pipeline
    if _default_pipeline is None:
        _default_pipeline = CompressionPipeline()
    return _default_pipeline
