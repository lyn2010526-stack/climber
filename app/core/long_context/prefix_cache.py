"""Prefix cache optimization.

Fixed content (system prompt, tool descriptions, skill index) is placed at the
front of the prompt so provider prefix caching (e.g. DeepSeek) hits. Sessions
keep the fixed prefix stable to maximize cache reuse.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class PrefixCache:
    """Stable fixed prefix assembled from resident content.

    The fixed block is rendered once and reused across turns/sessions. Only
    stable parts belong here; anything that changes per turn goes in the
    dynamic block after it.
    """

    system_prompt: str = ""
    tool_descriptions: str = ""
    skill_index: str = ""
    long_term_memory: str = ""

    def set_fixed(
        self,
        system_prompt: str = "",
        tool_descriptions: str = "",
        skill_index: str = "",
        long_term_memory: str = "",
    ) -> None:
        self.system_prompt = system_prompt
        self.tool_descriptions = tool_descriptions
        self.skill_index = skill_index
        self.long_term_memory = long_term_memory

    def render_fixed_prefix(self) -> str:
        """Assemble the fixed prefix in canonical order.

        Order: system prompt -> long-term memory -> skill index ->
        tool descriptions. Stable across turns to maximize prefix cache hits.
        """
        parts: list[str] = []
        if self.system_prompt:
            parts.append(f"<system>\n{self.system_prompt}\n</system>")
        if self.long_term_memory:
            parts.append(f"<memory>\n{self.long_term_memory}\n</memory>")
        if self.skill_index:
            parts.append(f"<skills>\n{self.skill_index}\n</skills>")
        if self.tool_descriptions:
            parts.append(f"<tools>\n{self.tool_descriptions}\n</tools>")
        return "\n\n".join(parts)

    def assemble(
        self,
        dynamic: dict[str, str],
    ) -> list[dict[str, str]]:
        """Assemble a prompt: fixed prefix first, then dynamic blocks."""
        messages: list[dict[str, str]] = []
        prefix = self.render_fixed_prefix()
        if prefix:
            messages.append({"role": "system", "content": prefix})
        # Dynamic block: summary + recent turns + rag + tool results.
        order = ("summary", "recent_turns", "rag_results", "tool_results")
        for key in order:
            value = dynamic.get(key, "")
            if value:
                messages.append(
                    {"role": "system", "content": f"<{key}>\n{value}\n</{key}>"}
                )
        return messages


_default_prefix_cache: PrefixCache | None = None


def get_prefix_cache() -> PrefixCache:
    global _default_prefix_cache
    if _default_prefix_cache is None:
        _default_prefix_cache = PrefixCache()
    return _default_prefix_cache
