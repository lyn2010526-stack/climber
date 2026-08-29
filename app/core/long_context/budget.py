"""32K fixed-context budget allocation with priority-based trimming.

| component        | budget | load mode              |
|------------------|--------|------------------------|
| system prompt    | 4K     | fixed resident         |
| long-term memory | 2K     | every session start    |
| skill index      | 2K     | every session start    |
| history summary  | 4K     | rolling update         |
| recent turns     | 12K    | sliding window         |
| RAG results      | 4K     | per-turn retrieval     |
| tool results     | 4K     | immediate injection    |

Total must never exceed the cap; when it does, trim in priority order:
tool results > recent turns > RAG > summary > skill index > long-term memory.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ContextBudget:
    """Fixed budget for each context component, in tokens."""

    system_prompt: int = 4096
    long_term_memory: int = 2048
    skill_index: int = 2048
    history_summary: int = 4096
    recent_turns: int = 12288
    rag_results: int = 4096
    tool_results: int = 4096

    @property
    def total(self) -> int:
        return (
            self.system_prompt
            + self.long_term_memory
            + self.skill_index
            + self.history_summary
            + self.recent_turns
            + self.rag_results
            + self.tool_results
        )

    # Trim priority: lowest priority first.
    PRIORITY_ORDER = (
        "tool_results",
        "recent_turns",
        "rag_results",
        "history_summary",
        "skill_index",
        "long_term_memory",
    )


def estimate_tokens(text: str) -> int:
    """Rough token estimate (chars / 4)."""
    return max(1, len(text) // 4)


@dataclass
class BudgetUsage:
    component: str
    allocated: int
    used: int
    trimmed: bool = False


class ContextBudgetManager:
    """Enforces the fixed context budget with priority trimming."""

    def __init__(self, budget: ContextBudget | None = None) -> None:
        self.budget = budget or ContextBudget()

    def allocate(
        self,
        system_prompt: str = "",
        long_term_memory: str = "",
        skill_index: str = "",
        history_summary: str = "",
        recent_turns: list[str] = field(default_factory=list),
        rag_results: list[str] = field(default_factory=list),
        tool_results: list[str] = field(default_factory=list),
    ) -> dict[str, Any]:
        """Allocate texts to each component, trimming lowest-priority first.

        Returns a dict with per-component content (possibly trimmed), total
        token usage, and a list of BudgetUsage entries.
        """
        # First measure everything.
        payloads: dict[str, str] = {
            "system_prompt": system_prompt,
            "long_term_memory": long_term_memory,
            "skill_index": skill_index,
            "history_summary": history_summary,
        }
        payloads["recent_turns"] = "\n".join(recent_turns)
        payloads["rag_results"] = "\n".join(rag_results)
        payloads["tool_results"] = "\n".join(tool_results)

        budgets = {
            "system_prompt": self.budget.system_prompt,
            "long_term_memory": self.budget.long_term_memory,
            "skill_index": self.budget.skill_index,
            "history_summary": self.budget.history_summary,
            "recent_turns": self.budget.recent_turns,
            "rag_results": self.budget.rag_results,
            "tool_results": self.budget.tool_results,
        }

        used: dict[str, int] = {c: estimate_tokens(text) for c, text in payloads.items()}
        total_used = sum(used.values())

        # Trim from lowest priority upward until within budget (or exhausted).
        for component in ContextBudget.PRIORITY_ORDER:
            if total_used <= self.budget.total:
                break
            over = total_used - self.budget.total
            component_used = used[component]
            if component_used <= 0:
                continue
            # Reduce this component by min(over, 80% of its current usage).
            reduction = min(over, int(component_used * 0.8))
            if reduction <= 0:
                continue
            trimmed_len = max(0, len(payloads[component]) - reduction * 4)
            payloads[component] = payloads[component][:trimmed_len]
            used[component] = estimate_tokens(payloads[component])
            total_used = sum(used.values())

        usages = [
            BudgetUsage(component=c, allocated=budgets[c], used=used[c],
                        trimmed=used[c] > budgets[c])
            for c in budgets
        ]
        return {
            "components": payloads,
            "usage": usages,
            "total_tokens": total_used,
            "budget_total": self.budget.total,
            "over_budget": total_used > self.budget.total,
        }

    def fits(self, token_count: int) -> bool:
        return token_count <= self.budget.total
