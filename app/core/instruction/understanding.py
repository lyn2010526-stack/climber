"""A deterministic, lossless first pass for user instruction understanding.

This module deliberately performs extraction only.  A later model or profile
adapter may append candidates and evidence through the extension fields, while
the verbatim instruction remains the source of truth.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any, Iterable


_CONSTRAINT_PATTERNS = (
    r"(?:只能|仅能|必须|需要|要求|不要|不得|禁止|优先|至少|最多|限定|只许)[^，。；;\n]*",
    r"(?:must|should|only|do not|don't|never|at least|at most)\b[^,.;\n]*",
)
_TARGET_PREFIXES = (
    "实现", "新增", "添加", "修复", "修改", "重构", "删除", "创建", "设计", "分析",
    "检查", "解释", "总结", "部署", "运行", "测试", "更新", "优化", "完成", "把", "将",
    "implement", "add", "fix", "update", "refactor", "create", "design", "analyze",
    "explain", "summarize", "deploy", "run", "test", "build", "make",
)
_METAPHOR_MARKERS = ("磨亮", "点燃", "开门", "铺路", "破冰", "降温", "加速", "收口", "抬头")

# Lines that are conversational fillers rather than instructions. Anything not
# in this set is treated as carrying the user's goal.
_ACKNOWLEDGEMENTS = frozenset(
    {
        "继续",
        "好的",
        "好",
        "嗯",
        "哦",
        "行",
        "可以",
        "ok",
        "okay",
        "yes",
        "no",
        "thanks",
        "thank you",
        "hello",
        "hi",
        "hey",
        "你好",
        "在吗",
        "继续吧",
        "接着来",
        "go on",
        "next",
        "下一步",
    }
)


@dataclass(frozen=True, slots=True)
class InstructionCandidate:
    """A target candidate with provenance and deterministic confidence."""

    text: str
    source: str = "deterministic"
    confidence: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class InstructionUnderstanding:
    """Structured understanding suitable for a trace ``task_spec``."""

    raw_text: str
    main_goal: str | None
    constraints: tuple[str, ...] = ()
    implicit_conditions: tuple[str, ...] = ()
    ambiguities: tuple[str, ...] = ()
    confidence: float = 0.0
    clarification_questions: tuple[str, ...] = ()
    plain_language_summary: str = ""
    progress: str = "understood"
    candidates: tuple[InstructionCandidate, ...] = ()
    context: str | None = None

    @property
    def goal_missing(self) -> bool:
        return self.main_goal is None

    def to_task_spec(self) -> dict[str, Any]:
        """Return storage-ready metadata without exposing hidden reasoning."""
        return {
            "raw_text": self.raw_text,
            "main_goal": self.main_goal,
            "constraints": list(self.constraints),
            "implicit_conditions": list(self.implicit_conditions),
            "ambiguities": list(self.ambiguities),
            "confidence": self.confidence,
            "clarification_questions": list(self.clarification_questions),
            "plain_language_summary": self.plain_language_summary,
            "progress": self.progress,
            "candidates": [candidate.to_dict() for candidate in self.candidates],
            "context": self.context,
        }

    def to_trace_payload(self, *, session_id: str | None = None, user_id: str | None = None) -> dict[str, Any]:
        """Build the payload accepted by ``repository_instruction_traces.create_trace``."""
        return {
            "session_id": session_id,
            "user_id": user_id,
            "raw_text": self.raw_text,
            "intent_summary": self.plain_language_summary,
            "task_spec": self.to_task_spec(),
            "goal_preserved": self.main_goal is not None and not self.ambiguities,
        }


class InstructionUnderstandingService:
    """Extract instruction structure using local, deterministic heuristics."""

    def understand(
        self,
        raw_text: str,
        context: str | None = None,
        supplemental_candidates: Iterable[InstructionCandidate] | None = None,
    ) -> InstructionUnderstanding:
        candidates = list(self._target_candidates(raw_text))
        deterministic_candidates = list(candidates)
        if supplemental_candidates:
            candidates.extend(supplemental_candidates)

        goal = deterministic_candidates[0].text if deterministic_candidates else (
            candidates[0].text if candidates else None
        )
        constraints = tuple(self._extract_constraints(raw_text))
        ambiguities = tuple(self._extract_ambiguities(raw_text, goal))
        missing = goal is None
        questions = ("请说明这次操作要达成的主目标。",) if missing else ()
        if ambiguities:
            questions += ("请明确以下表达的具体含义：" + "、".join(ambiguities),)
        confidence = self._confidence(goal, constraints, ambiguities, context)
        progress = "needs_clarification" if missing or ambiguities else "understood"
        summary = self._summary(goal, constraints, progress)
        return InstructionUnderstanding(
            raw_text=raw_text,
            main_goal=goal,
            constraints=constraints,
            implicit_conditions=self._implicit_conditions(raw_text, context),
            ambiguities=ambiguities,
            confidence=confidence,
            clarification_questions=questions,
            plain_language_summary=summary,
            progress=progress,
            candidates=tuple(candidates),
            context=context,
        )

    def _target_candidates(self, raw_text: str) -> list[InstructionCandidate]:
        """Treat every content line as a goal candidate unless it is an ack.

        A whitelist of action verbs both missed legitimate goals ("写一个快速
        排序", "ship it") and could never cover every language, so the rule is
        inverted: a line the user typed is their instruction. Only greetings,
        acknowledgements and other pure conversational fillers carry no goal,
        and prefix matches still raise confidence because an explicit action
        verb makes the goal unambiguous.
        """
        lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
        candidates: list[InstructionCandidate] = []
        for line in lines:
            if line.lower().rstrip("！!？?。.~") in _ACKNOWLEDGEMENTS:
                continue
            first_word = line.split(maxsplit=1)[0].lower().rstrip("：:")
            if any(line.lower().startswith(prefix.lower()) for prefix in _TARGET_PREFIXES):
                candidates.append(InstructionCandidate(line, "deterministic", 0.86))
            elif first_word in {"请", "please", "帮我", "help"} and len(line) > len(first_word) + 1:
                candidates.append(InstructionCandidate(line, "deterministic", 0.72))
            else:
                candidates.append(InstructionCandidate(line, "deterministic", 0.6))
        return candidates

    def _extract_constraints(self, raw_text: str) -> list[str]:
        found: list[str] = []
        for pattern in _CONSTRAINT_PATTERNS:
            found.extend(match.group(0).strip(" ，,；;") for match in re.finditer(pattern, raw_text, re.I))
        return list(dict.fromkeys(item for item in found if item))

    def _extract_ambiguities(self, raw_text: str, goal: str | None) -> list[str]:
        found = [marker for marker in _METAPHOR_MARKERS if marker in raw_text]
        if goal and any(char in goal for char in ("这", "那", "它", "这里", "那里")):
            found.append("指代对象")
        return list(dict.fromkeys(found))

    def _implicit_conditions(self, raw_text: str, context: str | None) -> tuple[str, ...]:
        conditions = []
        if context:
            conditions.append("需要结合提供的上下文")
        if "继续" in raw_text or "再" in raw_text:
            conditions.append("依赖前序对话或当前进度")
        return tuple(conditions)

    def _confidence(
        self, goal: str | None, constraints: tuple[str, ...], ambiguities: tuple[str, ...], context: str | None
    ) -> float:
        score = 0.2 if goal is None else 0.65
        score += min(0.15, len(constraints) * 0.05)
        score += 0.1 if context else 0.0
        score -= min(0.3, len(ambiguities) * 0.15)
        return round(max(0.0, min(1.0, score)), 2)

    def _summary(self, goal: str | None, constraints: tuple[str, ...], progress: str) -> str:
        if goal is None:
            return "尚未识别到主目标，需要补充目标。"
        summary = f"目标：{goal}。"
        if constraints:
            summary += "约束：" + "；".join(constraints) + "。"
        summary += f"进度：{progress}。"
        return summary


def understand_instruction(
    raw_text: str,
    context: str | None = None,
    supplemental_candidates: Iterable[InstructionCandidate] | None = None,
) -> InstructionUnderstanding:
    """Convenience entry point for callers that do not need a service instance."""
    return InstructionUnderstandingService().understand(raw_text, context, supplemental_candidates)
