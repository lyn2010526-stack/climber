"""Coverage checker — edge cases, risks, and hidden assumptions.

Implements Constitutional AI (Anthropic, 2022) principle-driven verification
combined with NeMo Guardrails (NVIDIA) structured risk matrices.
"""

from __future__ import annotations

import asyncio
import json
import time
from typing import Any

import structlog
from pydantic import ValidationError

from app.core.reasoning.base import (
    Assumption,
    Candidate,
    CoverageReport,
    EdgeCase,
    Risk,
)

logger = structlog.get_logger()

_TASK_TYPE_CHECKLISTS: dict[str, list[str]] = {
    "code": [
        "empty_input",
        "null_input",
        "large_input",
        "invalid_type",
        "concurrent_access",
        "timeout_handling",
        "memory_leak_check",
        "error_propagation",
        "security_injection",
    ],
    "analysis": [
        "data_quality",
        "missing_data_handling",
        "bias_detection",
        "causation_vs_correlation",
        "sample_size_validity",
        "confounding_variables",
    ],
    "design": [
        "scalability",
        "maintainability",
        "security",
        "backward_compatibility",
        "failure_recovery",
        "observability",
    ],
}

_DEFAULT_CHECKLIST = [
    "correctness_verified",
    "completeness_checked",
    "edge_cases_covered",
    "risks_identified",
    "assumptions_validated",
]

_COVERAGE_SCHEMA = {
    "type": "object",
    "required": ["edge_cases", "risks", "assumptions", "blind_spots"],
    "properties": {
        "edge_cases": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["description", "category"],
                "properties": {
                    "description": {"type": "string"},
                    "category": {"type": "string"},
                    "tested": {"type": "boolean"},
                    "result": {"type": "string"},
                },
            },
        },
        "risks": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["description"],
                "properties": {
                    "description": {"type": "string"},
                    "probability": {"type": "string", "enum": ["low", "medium", "high"]},
                    "impact": {"type": "string", "enum": ["low", "medium", "high"]},
                    "mitigation": {"type": "string"},
                },
            },
        },
        "assumptions": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["statement"],
                "properties": {
                    "statement": {"type": "string"},
                    "validated": {"type": "boolean"},
                    "evidence": {"type": "string"},
                    "risk_if_wrong": {"type": "string"},
                },
            },
        },
        "blind_spots": {"type": "array", "items": {"type": "string"}},
    },
}


class CoverageChecker:
    """Validates reasoning output coverage across edge cases, risks, and assumptions."""

    async def check(
        self,
        task: str,
        candidates: list[Candidate],
        model_adapter: Any,
        task_type: str = "general",
        timeout: float = 60.0,
    ) -> CoverageReport:
        start = time.monotonic()
        checklist_items = _TASK_TYPE_CHECKLISTS.get(task_type, _DEFAULT_CHECKLIST)
        checklist: dict[str, bool] = {item: False for item in checklist_items}

        combined_content = self._combine_candidates(candidates)

        try:
            raw_report = await self._call_llm(task, combined_content, candidates, model_adapter, timeout)
        except Exception as exc:
            logger.error(
                "Coverage LLM call failed",
                error=str(exc),
                provider=getattr(model_adapter, "provider", "unknown"),
            )
            return self._build_partial_report(checklist, candidates)

        edge_cases = self._parse_edge_cases(raw_report.get("edge_cases", []))
        risks = self._parse_risks(raw_report.get("risks", []))
        assumptions = self._parse_assumptions(raw_report.get("assumptions", []))
        blind_spots = self._parse_blind_spots(raw_report.get("blind_spots", []), candidates)

        self._cross_reference_edge_cases(edge_cases, candidates, checklist)
        self._cross_reference_assumptions(assumptions, candidates, checklist)

        score = self._compute_score(checklist, edge_cases, assumptions)

        duration = (time.monotonic() - start) * 1000
        logger.info(
            "Coverage check complete",
            score=score,
            edge_cases=len(edge_cases),
            risks=len(risks),
            blind_spots=len(blind_spots),
            duration_ms=f"{duration:.0f}",
        )

        return CoverageReport(
            edge_cases=edge_cases,
            risks=risks,
            assumptions=assumptions,
            blind_spots=blind_spots,
            score=score,
            checklist=checklist,
        )

    async def _call_llm(
        self,
        task: str,
        combined_content: str,
        candidates: list[Candidate],
        model_adapter: Any,
        timeout: float = 60.0,
    ) -> dict[str, Any]:
        prompt = self._build_prompt(task, combined_content, candidates)
        messages = [
            {"role": "system", "content": "You are a thorough coverage analyst."},
            {"role": "user", "content": prompt},
        ]
        try:
            result = await asyncio.wait_for(
                model_adapter.chat(
                    messages,
                    response_format={"type": "json_object"},
                    temperature=0.2,
                    max_tokens=4000,
                ),
                timeout=timeout,
            )
            return self._extract_json(result.content)
        except TimeoutError:
            logger.warning("Coverage LLM call timed out", timeout=timeout)
            return {}
        except Exception as exc:
            logger.error("Coverage LLM call failed", error=str(exc))
            return {}

    def _build_prompt(
        self,
        task: str,
        combined_content: str,
        candidates: list[Candidate],
    ) -> str:
        candidate_summaries = "\n\n".join(
            f"[Candidate {c.id}] (strategy={c.strategy}, confidence={c.confidence:.2f})\n{c.content[:1500]}"
            for c in candidates
        )
        return (
            f"Analyze the following reasoning output(s) for the given task.\n\n"
            f"TASK:\n{task}\n\n"
            f"OUTPUTS:\n{candidate_summaries}\n\n"
            f"Your analysis must cover:\n"
            f"1. Edge cases — scenarios not adequately addressed\n"
            f"2. Risks — potential failures with probability and impact\n"
            f"3. Hidden assumptions — unstated premises that could be wrong\n"
            f"4. Blind spots — aspects no candidate addressed\n\n"
            f"Respond with JSON matching this schema:\n"
            f"{json.dumps(_COVERAGE_SCHEMA, indent=2)}"
        )

    def _extract_json(self, raw: str) -> dict[str, Any]:
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            cleaned = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
        if cleaned.startswith("json"):
            cleaned = cleaned[4:].strip()

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            start_idx = cleaned.find("{")
            end_idx = cleaned.rfind("}")
            if start_idx == -1 or end_idx == -1:
                return {}
            return json.loads(cleaned[start_idx : end_idx + 1])

    def _parse_edge_cases(self, raw_items: list[dict[str, Any]]) -> list[EdgeCase]:
        edge_cases: list[EdgeCase] = []
        for item in raw_items:
            try:
                edge_cases.append(
                    EdgeCase(
                        description=item.get("description", ""),
                        category=item.get("category", "general"),
                        tested=bool(item.get("tested", False)),
                        result=item.get("result", ""),
                    )
                )
            except (ValidationError, TypeError):
                continue
        return edge_cases

    def _parse_risks(self, raw_items: list[dict[str, Any]]) -> list[Risk]:
        risks: list[Risk] = []
        valid_levels = {"low", "medium", "high"}
        for item in raw_items:
            prob = item.get("probability", "low")
            imp = item.get("impact", "low")
            if prob not in valid_levels:
                prob = "low"
            if imp not in valid_levels:
                imp = "low"
            try:
                risks.append(
                    Risk(
                        description=item.get("description", ""),
                        probability=prob,
                        impact=imp,
                        mitigation=item.get("mitigation", ""),
                    )
                )
            except (ValidationError, TypeError):
                continue
        return risks

    def _parse_assumptions(self, raw_items: list[dict[str, Any]]) -> list[Assumption]:
        assumptions: list[Assumption] = []
        for item in raw_items:
            try:
                assumptions.append(
                    Assumption(
                        statement=item.get("statement", ""),
                        validated=bool(item.get("validated", False)),
                        evidence=item.get("evidence", ""),
                        risk_if_wrong=item.get("risk_if_wrong", ""),
                    )
                )
            except (ValidationError, TypeError):
                continue
        return assumptions

    def _parse_blind_spots(
        self,
        raw_spots: list[str],
        candidates: list[Candidate],
    ) -> list[str]:
        seen: set[str] = set()
        spots: list[str] = []
        combined = " ".join(c.content.lower() for c in candidates)
        for spot in raw_spots:
            normalized = spot.strip().lower()
            if normalized and normalized not in seen and normalized not in combined:
                seen.add(normalized)
                spots.append(spot.strip())
        return spots

    def _cross_reference_edge_cases(
        self,
        edge_cases: list[EdgeCase],
        candidates: list[Candidate],
        checklist: dict[str, bool],
    ) -> None:
        all_content = " ".join(c.content.lower() for c in candidates)
        for ec in edge_cases:
            keywords = ec.description.lower().split()[:3]
            if any(kw in all_content for kw in keywords if len(kw) > 3):
                ec.tested = True
                ec.result = "addressed_in_output"

        tested_categories = {ec.category for ec in edge_cases if ec.tested}
        for key in checklist:
            if key in tested_categories or key in all_content:
                checklist[key] = True

    def _cross_reference_assumptions(
        self,
        assumptions: list[Assumption],
        candidates: list[Candidate],
        checklist: dict[str, bool],
    ) -> None:
        all_content = " ".join(c.content.lower() for c in candidates)
        for assumption in assumptions:
            keywords = assumption.statement.lower().split()[:4]
            if any(kw in all_content for kw in keywords if len(kw) > 4):
                assumption.validated = True
                assumption.evidence = "Referenced in candidate output"

    def _compute_score(
        self,
        checklist: dict[str, bool],
        edge_cases: list[EdgeCase],
        assumptions: list[Assumption],
    ) -> float:
        if not checklist and not edge_cases and not assumptions:
            return 0.0

        checklist_score = 0.0
        if checklist:
            checklist_score = sum(1 for v in checklist.values() if v) / len(checklist)

        edge_score = 0.0
        if edge_cases:
            edge_score = sum(1 for ec in edge_cases if ec.tested) / len(edge_cases)

        assumption_score = 0.0
        if assumptions:
            assumption_score = sum(1 for a in assumptions if a.validated) / len(assumptions)

        weights = (0.4, 0.35, 0.25)
        raw = weights[0] * checklist_score + weights[1] * edge_score + weights[2] * assumption_score
        return round(min(1.0, max(0.0, raw)), 4)

    def _combine_candidates(self, candidates: list[Candidate]) -> str:
        return "\n\n---\n\n".join(
            f"[Candidate {c.id}]\n{c.content}" for c in candidates if c.content
        )

    def _build_partial_report(
        self,
        checklist: dict[str, bool],
        candidates: list[Candidate],
    ) -> CoverageReport:
        all_content = " ".join(c.content.lower() for c in candidates)
        for key in checklist:
            if key in all_content:
                checklist[key] = True

        score = sum(1 for v in checklist.values() if v) / max(len(checklist), 1)
        return CoverageReport(
            edge_cases=[],
            risks=[],
            assumptions=[],
            blind_spots=["LLM coverage analysis unavailable"],
            score=round(score, 4),
            checklist=checklist,
        )
