"""Tests for output auditor."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.output_auditor import AuditConfig, AuditResult, OutputAuditor, get_output_auditor


class TestOutputAuditor:
    def test_disabled_audit_passes(self) -> None:
        auditor = OutputAuditor(AuditConfig(enabled=False))
        import asyncio
        result = asyncio.run(audit_disabled(auditor))
        assert result.passed is True
        assert result.overall_score == 1.0

    def test_empty_output_fails(self) -> None:
        auditor = OutputAuditor()
        import asyncio
        result = asyncio.run(
            auditor.audit("task", "", None)
        )
        assert result.passed is False
        assert result.recommendation == "retry"

    def test_whitespace_output_fails(self) -> None:
        auditor = OutputAuditor()
        import asyncio
        result = asyncio.run(
            auditor.audit("task", "   \n  ", None)
        )
        assert result.passed is False

    def test_goal_alignment_check(self) -> None:
        auditor = OutputAuditor()
        aligned = auditor._check_goal_alignment(
            "Extract database settings from config",
            "The database host is localhost, port 5432, name myapp. Config extracted successfully.",
            {},
        )
        assert aligned is True

    def test_goal_misalignment(self) -> None:
        auditor = OutputAuditor()
        aligned = auditor._check_goal_alignment(
            "Extract database settings from config",
            "The weather today is sunny with a high of 25 degrees Celsius outside",
            {},
        )
        assert aligned is False

    def test_goal_alignment_short_task(self) -> None:
        auditor = OutputAuditor()
        aligned = auditor._check_goal_alignment("Hi", "Hello there", {})
        assert aligned is True


async def audit_disabled(auditor: OutputAuditor) -> AuditResult:
    return await auditor.audit("task", "output", None)


class TestAuditResult:
    def test_defaults(self) -> None:
        r = AuditResult(
            passed=True,
            overall_score=0.8,
            dimension_scores={"correctness": 0.9},
            issues=[],
            summary="Good",
        )
        assert r.goal_aligned is True
        assert r.recommendation == ""


class TestGetOutputAuditor:
    def test_singleton(self) -> None:
        a = get_output_auditor()
        b = get_output_auditor()
        assert a is b
