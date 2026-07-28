"""Structured output models for reviewer feedback.

Uses Pydantic for validation, replacing fragile JSON parsing with type-safe
models that enforce the expected schema. Inspired by OpenAI's structured
output and Anthropic's tool-use enforcement.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ReviewIssueModel(BaseModel):
    """A single issue found during review.

    Enforces severity levels and requires actionable fix suggestions.
    """

    severity: Literal["critical", "major", "minor", "info"] = Field(
        ...,
        description="Issue severity: critical (blocks), major (should fix), minor (nice-to-have), info (observation)",
    )
    description: str = Field(
        ...,
        min_length=10,
        max_length=1000,
        description="Clear description of what is wrong",
    )
    location: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Where the issue is located (file:line, section name, etc.)",
    )
    fix_suggestion: str = Field(
        ...,
        min_length=10,
        max_length=1000,
        description="Actionable suggestion for how to fix the issue",
    )


class ReviewOutputModel(BaseModel):
    """Complete review output from a reviewer agent.

    This is the structured format reviewers must produce.
    Pydantic validates the JSON, and we provide clear error messages
    when the model output doesn't conform.
    """

    passed: bool = Field(
        ...,
        description="True if the artifact passes review with no blocking issues",
    )
    issues: list[ReviewIssueModel] = Field(
        default_factory=list,
        description="List of issues found (empty if passed=true)",
    )
    summary: str = Field(
        default="",
        max_length=500,
        description="Brief overall assessment of the artifact quality",
    )

    @property
    def critical_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "critical")

    @property
    def major_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "major")

    def to_feedback_string(self) -> str:
        """Convert issues to a formatted feedback string for the Worker."""
        if self.passed or not self.issues:
            return ""
        lines: list[str] = []
        if self.summary:
            lines.append(f"Review Summary: {self.summary}")
            lines.append("")
        for i, issue in enumerate(self.issues, 1):
            lines.append(f"{i}. [{issue.severity.upper()}] {issue.description}")
            lines.append(f"   Location: {issue.location}")
            lines.append(f"   Fix: {issue.fix_suggestion}")
        return "\n".join(lines)


REVIEW_OUTPUT_SCHEMA: dict = {
    "type": "object",
    "required": ["passed", "issues"],
    "properties": {
        "passed": {
            "type": "boolean",
            "description": "Whether the artifact passes review",
        },
        "issues": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["severity", "description", "location", "fix_suggestion"],
                "properties": {
                    "severity": {
                        "type": "string",
                        "enum": ["critical", "major", "minor", "info"],
                    },
                    "description": {
                        "type": "string",
                        "minLength": 10,
                        "maxLength": 1000,
                    },
                    "location": {
                        "type": "string",
                        "minLength": 1,
                        "maxLength": 200,
                    },
                    "fix_suggestion": {
                        "type": "string",
                        "minLength": 10,
                        "maxLength": 1000,
                    },
                },
            },
        },
        "summary": {
            "type": "string",
            "maxLength": 500,
        },
    },
}
