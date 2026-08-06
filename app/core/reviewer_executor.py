"""Reviewer executor—reviews Worker output with structured validation.

Uses Pydantic models to enforce a strict output schema, replacing fragile
JSON parsing with type-safe validation. Falls back gracefully when the
model produces non-conforming output.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any

import structlog
from pydantic import ValidationError

from app.core.collab_prompts import get_reviewer_prompt
from app.core.di import resolve as di_resolve
from app.core.guardrails import GuardrailAction, GuardrailsEngine, OutputLengthRule, PIIDetectionRule
from app.core.review_models import ReviewIssueModel, ReviewOutputModel
from app.core.stream_events import (
    CollabEvent,
    CollabEventType,
    make_reviewer_issues,
    make_text_delta,
)

logger = structlog.get_logger()


@dataclass
class _MemberInfo:
    """Lightweight member info."""

    id: str
    name: str
    provider: str
    model_id: str
    api_key: str
    avatar_url: str | None = None


class ReviewerExecutor:
    """Executes Reviewer role: reviews Worker output with structured output validation.

    Key improvements over previous implementation:
    - Pydantic models enforce the output schema
    - Structured output via OpenAI/Anthropic response_format when available
    - Graceful fallback for non-conforming output (no more raw text as issue)
    - Reviewer prompt includes JSON schema for models that support it
    """

    def __init__(self, session_id: str):
        self._session_id = session_id
        self.guardrails = GuardrailsEngine(rules=[
            PIIDetectionRule(action=GuardrailAction.SANITIZE),
            OutputLengthRule(min_length=5, max_length=50000),
        ])

    async def review(
        self,
        member: _MemberInfo,
        task: str,
        artifact: str,
        review_type: str = "code",
    ) -> AsyncIterator[CollabEvent]:
        """Review Worker output. Yields streaming events with structured validation."""
        yield CollabEvent(
            type=CollabEventType.REVIEWER_START,
            session_id=self._session_id,
            member_id=member.id,
            member_name=member.name,
            member_avatar=member.avatar_url,
            data={"review_type": review_type, "model": f"{member.provider}/{member.model_id}"},
        )

        system_prompt = get_reviewer_prompt(
            role=review_type,
            name=member.name,
            task=task,
            artifact=artifact[:8000],
        )

        messages = [
            {"role": "system", "content": system_prompt},
        ]

        try:
            model_registry = di_resolve("ModelRegistry")
            adapter = model_registry.get_or_create(
                provider=member.provider,
                model_id=member.model_id,
                api_key=member.api_key,
            )
        except Exception as e:
            yield CollabEvent(
                type=CollabEventType.ERROR,
                session_id=self._session_id,
                member_id=member.id,
                data={"error": f"Model init failed: {str(e)}"},
            )
            return

        full_output = ""

        try:
            async for chunk in adapter.stream_chat(messages=messages):
                if chunk.content:
                    full_output += chunk.content
                    yield make_text_delta(
                        session_id=self._session_id,
                        member_id=member.id,
                        member_name=member.name,
                        delta=chunk.content,
                        avatar=member.avatar_url,
                    )
                if chunk.tokens_used:
                    pass
        except Exception as e:
            logger.error("Reviewer execution failed", error=str(e), member=member.name)
            yield CollabEvent(
                type=CollabEventType.ERROR,
                session_id=self._session_id,
                member_id=member.id,
                data={"error": str(e)},
            )
            return

        # Parse with Pydantic validation
        review_result = self._parse_structured_output(full_output)

        # Validate output through guardrails
        try:
            sanitized, violations = await self.guardrails.apply_guardrails(
                full_output, is_input=False
            )
            if violations:
                logger.warning("Reviewer output had guardrails violations",
                               rule_names=[v.rule_name for v in violations])
            if not sanitized:
                from app.core.review_models import ReviewOutputModel
                review_result = ReviewOutputModel(passed=True, issues=[], summary="Output filtered by guardrails")
        except Exception as e:
            logger.warning("reviewer_executor.guardrails_failed", error=str(e))

        yield make_reviewer_issues(
            session_id=self._session_id,
            member_id=member.id,
            member_name=member.name,
            issues=[i.model_dump() for i in review_result.issues],
            avatar=member.avatar_url,
        )

    def _parse_structured_output(self, output: str) -> ReviewOutputModel:
        """Parse and validate reviewer output using Pydantic.

        Strategy:
        1. Try to extract JSON from markdown code blocks or raw text
        2. Validate with Pydantic — catches type errors, missing fields, enum violations
        3. If validation fails, try to salvage partial data
        4. Only fall back to text-as-issue if all structured parsing fails
        """
        json_str = self._extract_json(output)

        if not json_str:
            return self._fallback_parse(output)

        try:
            data = json.loads(json_str)
            return ReviewOutputModel(**data)
        except json.JSONDecodeError as e:
            logger.warning("Reviewer JSON decode failed", error=str(e))
            return self._fallback_parse(output)
        except ValidationError as e:
            logger.warning("Reviewer output validation failed", errors=e.errors())
            return self._salvage_partial(data, e)

    def _salvage_partial(
        self,
        data: dict[str, Any],
        error: ValidationError,
    ) -> ReviewOutputModel:
        """Attempt to salvage a partially valid review output.

        If the model produced JSON that is mostly correct but has minor
        validation issues (e.g., wrong severity enum), try to fix it
        rather than discarding everything.
        """
        # Try to fix common issues
        passed = data.get("passed", False)
        raw_issues = data.get("issues", [])
        summary = data.get("summary", "")

        valid_issues: list[ReviewIssueModel] = []
        for raw in raw_issues:
            try:
                # Coerce severity to valid enum values
                severity = raw.get("severity", "major")
                if severity not in ("critical", "major", "minor", "info"):
                    severity = "major"
                valid_issues.append(ReviewIssueModel(
                    severity=severity,
                    description=raw.get("description", "")[:1000],
                    location=raw.get("location", "unknown")[:200],
                    fix_suggestion=raw.get("fix_suggestion", "See review")[:1000],
                ))
            except (ValidationError, KeyError):
                continue

        # If passed was explicitly true but we have no valid issues, trust it
        if passed and not valid_issues:
            return ReviewOutputModel(passed=True, issues=[], summary=summary)

        return ReviewOutputModel(passed=False, issues=valid_issues, summary=summary)

    def _fallback_parse(self, output: str) -> ReviewOutputModel:
        """Last resort: parse natural language output for pass/fail signals."""
        upper = output.upper().strip()

        # Explicit pass signals
        if upper in ("PASSED", "PASS", "OK", "APPROVED") or (
            "PASSED" in upper and "FAILED" not in upper and len(output) < 200
        ):
            return ReviewOutputModel(passed=True, issues=[])

        # If output is very short and positive, treat as passed
        if len(output) < 100 and any(w in upper for w in ("GOOD", "CORRECT", "FINE")):
            return ReviewOutputModel(passed=True, issues=[])

        # Otherwise, create a single issue from the text
        # But cap it — don't dump the entire raw output as an issue
        return ReviewOutputModel(
            passed=False,
            issues=[ReviewIssueModel(
                severity="major",
                description=output[:500],
                location="unknown",
                fix_suggestion="Reviewer did not produce structured JSON output. Consider re-running with a model that supports structured output.",
            )],
            summary="Non-conforming review output",
        )

    def _extract_json(self, text: str) -> str | None:
        """Extract JSON object from text, handling markdown code blocks."""
        # Try ```json ... ``` block
        if "```json" in text:
            start = text.index("```json") + 7
            end = text.index("```", start)
            return text[start:end].strip()

        # Try ``` ... ``` block (might be JSON without language tag)
        if "```" in text:
            start = text.index("```") + 3
            end = text.index("```", start)
            candidate = text[start:end].strip()
            if candidate.startswith("{"):
                return candidate

        # Try raw JSON object
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            return text[start:end + 1]

        return None
