"""MCP Plugin: Context Compression — semantic-preserving token reduction.

Compresses conversation history while preserving key information,
reducing token consumption for long-running tasks.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class CompressionResult:
    original_tokens: int
    compressed_tokens: int
    compressed_text: str
    ratio: float  # compressed / original
    dropped_items: list[str] = field(default_factory=list)


class ContextCompressor:
    """Semantic-preserving context compression."""

    def __init__(self, target_ratio: float = 0.4):
        self._target_ratio = target_ratio
        self._stop_words = {
            "the", "a", "an", "is", "are", "was", "were", "be", "been",
            "being", "have", "has", "had", "do", "does", "did", "will",
            "would", "could", "should", "may", "might", "can", "shall",
        }

    def estimate_tokens(self, text: str) -> int:
        """Fast token estimation: ~4 chars per token for English, ~2 for CJK."""
        if not text:
            return 0
        # Simple heuristic
        return max(1, len(text) // 4)

    def compress(self, text: str, preserve_lines: list[str] | None = None) -> CompressionResult:
        """Compress text while preserving key content."""
        original_tokens = self.estimate_tokens(text)
        preserve_set = set(preserve_lines or [])

        sections = self._split_sections(text)
        compressed_parts: list[str] = []
        dropped: list[str] = []

        for section in sections:
            header = section.get("header", "")
            body = section.get("body", "")

            # Always preserve marked lines
            if header in preserve_set:
                compressed_parts.append(body)
                continue

            # Decide compression level by section type
            if self._is_code_block(body):
                compressed_parts.append(self._compress_code(body))
            elif self._is_error_block(body):
                compressed_parts.append(body)  # Never compress errors
            elif self._is_result_block(body):
                compressed_parts.append(self._compress_result(body))
            else:
                compressed_parts.append(self._compress_prose(body))

        compressed_text = "\n\n".join(compressed_parts)
        compressed_tokens = self.estimate_tokens(compressed_text)

        if compressed_tokens == 0 and original_tokens > 0:
            compressed_tokens = 1
            compressed_text = "[COMPRESSED TO EMPTY — all content was redundant]"

        ratio = compressed_tokens / max(original_tokens, 1)

        return CompressionResult(
            original_tokens=original_tokens,
            compressed_tokens=compressed_tokens,
            compressed_text=compressed_text,
            ratio=ratio,
            dropped_items=dropped,
        )

    def compress_messages(
        self,
        messages: list[dict[str, Any]],
        keep_last_n: int = 4,
    ) -> tuple[list[dict[str, Any]], CompressionResult]:
        """Compress a message list, keeping last N messages intact."""
        if len(messages) <= keep_last_n:
            total_text = "\n".join(
                f"{m.get('role')}: {m.get('content', '')}" for m in messages
            )
            return messages, CompressionResult(
                original_tokens=self.estimate_tokens(total_text),
                compressed_tokens=self.estimate_tokens(total_text),
                compressed_text=total_text,
                ratio=1.0,
            )

        head = messages[:-keep_last_n]
        tail = messages[-keep_last_n:]

        # Compress head messages
        head_text = "\n".join(
            f"{m.get('role')}: {m.get('content', '')}" for m in head
        )
        result = self.compress(head_text)

        # Rebuild compressed messages from compressed text
        compressed_head_text = result.compressed_text
        if compressed_head_text and compressed_head_text != "[COMPRESSED TO EMPTY — all content was redundant]":
            summary_msg = {
                "role": "system",
                "content": f"[Previous conversation summary]: {compressed_head_text}",
            }
            return [summary_msg, *tail], result
        summary_msg = {
            "role": "system",
            "content": "[Previous conversation compressed — content was redundant]",
        }
        return [summary_msg, *tail], result

    def _split_sections(self, text: str) -> list[dict[str, str]]:
        """Split text into logical sections."""
        sections = []
        parts = re.split(r"\n(?=#{1,3}\s|```|ERROR|Result|Output)", text)

        for part in parts:
            lines = part.split("\n", 1)
            if len(lines) > 1:
                sections.append({"header": lines[0].strip(), "body": part})
            elif part.strip():
                sections.append({"header": "", "body": part})

        return sections

    def _is_code_block(self, text: str) -> bool:
        return text.strip().startswith("```") or "def " in text or "class " in text or "import " in text

    def _is_error_block(self, text: str) -> bool:
        indicators = ["Error:", "ERROR", "Traceback", "Exception", "FAILED", "error:"]
        return any(ind in text for ind in indicators)

    def _is_result_block(self, text: str) -> bool:
        indicators = ["Result:", "Output:", "Success:", "Done:", "→"]
        return any(text.strip().startswith(ind) for ind in indicators)

    def _compress_code(self, code: str) -> str:
        """Compress code by removing comments and blank lines."""
        lines = code.split("\n")
        kept = []
        in_fence = False

        for line in lines:
            stripped = line.strip()
            if stripped.startswith("```"):
                in_fence = not in_fence
                kept.append(line)
                continue
            if not in_fence:
                if stripped.startswith("#") or stripped.startswith("//"):
                    continue
                if stripped == "":
                    continue
            kept.append(line)

        return "\n".join(kept)

    def _compress_prose(self, text: str) -> str:
        """Compress prose by extracting key sentences."""
        sentences = re.split(r"(?<=[.!?])\s+", text)
        if len(sentences) <= 2:
            return text

        # Keep first sentence (context) and last sentence (conclusion)
        # Drop middle filler
        key_sentences = [sentences[0]]
        if len(sentences) > 2:
            # Keep sentences with important keywords
            for s in sentences[1:-1]:
                words = set(s.lower().split())
                if words - self._stop_words:
                    if any(kw in s.lower() for kw in [
                        "important", "must", "critical", "key", "note",
                        "result", "found", "error", "issue", "fix",
                    ]):
                        key_sentences.append(s)
        key_sentences.append(sentences[-1])

        return " ".join(key_sentences)

    def _compress_result(self, result: str) -> str:
        """Compress result blocks — keep concise."""
        lines = result.strip().split("\n")
        if len(lines) <= 5:
            return result
        return "\n".join(lines[:3]) + "\n..." + lines[-1]

    def get_tool_definitions(self) -> list[dict[str, Any]]:
        return [
            {
                "name": "compress_context",
                "description": "Compress conversation history to reduce token usage",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "text": {"type": "string", "description": "Text to compress"},
                        "preserve_lines": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Lines that must be preserved",
                        },
                    },
                    "required": ["text"],
                },
            },
        ]
