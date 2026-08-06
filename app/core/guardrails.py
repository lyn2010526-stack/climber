"""Guardrails engine for input/output validation and safety checks."""

from __future__ import annotations

import json
import re
from enum import StrEnum
from typing import Any

from pydantic import BaseModel


class ActionType(StrEnum):
    ALLOW = "allow"
    BLOCK = "block"
    SANITIZE = "sanitize"
    WARN = "warn"


class GuardrailResult(BaseModel):
    action: ActionType
    original: str
    sanitized: str
    rule_name: str
    reason: str | None = None


class PIIDetectionRule:
    name = "pii_detection"
    description = "Detect and redact personally identifiable information"

    async def check(self, text: str) -> GuardrailResult | None:
        patterns = {
            "email": (r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", "EMAIL_REDACTED"),
            "phone": (r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b", "PHONE_REDACTED"),
            "ssn": (r"\b\d{3}-\d{2}-\d{4}\b", "SSN_REDACTED"),
            "api_key": (r"sk-[a-zA-Z0-9]{32,}", "API_KEY_REDACTED"),
        }
        sanitized = text
        found = False
        for pattern, replacement in patterns.values():
            if re.search(pattern, sanitized):
                sanitized = re.sub(pattern, replacement, sanitized)
                found = True
        if found:
            return GuardrailResult(action=ActionType.SANITIZE, original=text, sanitized=sanitized, rule_name=self.name, reason="PII detected")
        return None


class PromptInjectionRule:
    name = "prompt_injection"
    description = "Detect prompt injection attempts"

    async def check(self, text: str) -> GuardrailResult | None:
        injection_patterns = [
            r"ignore (all )?previous instructions",
            r"disregard .* instructions",
            r"you are now",
            r"new instructions:",
            r"system prompt:",
            r"\[INST\]",
            r"<\|im_start\|>",
        ]
        for pattern in injection_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return GuardrailResult(action=ActionType.BLOCK, original=text, sanitized="", rule_name=self.name, reason="Prompt injection detected")
        return None


class OutputLengthRule:
    name = "output_length"
    description = "Enforce maximum output length"

    def __init__(self, max_length: int = 10000, min_length: int = 0):
        self.max_length = max_length
        self.min_length = min_length

    async def check(self, text: str) -> GuardrailResult | None:
        if len(text) > self.max_length:
            truncated = text[:self.max_length] + "...[TRUNCATED]"
            return GuardrailResult(action=ActionType.SANITIZE, original=text, sanitized=truncated, rule_name=self.name, reason=f"Output exceeded {self.max_length} characters")
        if self.min_length > 0 and len(text) < self.min_length:
            return GuardrailResult(action=ActionType.WARN, original=text, sanitized=text, rule_name=self.name, reason=f"Output shorter than {self.min_length} characters")
        return None


class JSONFormatRule:
    name = "json_format"
    description = "Ensure output is valid JSON"

    async def check(self, text: str) -> GuardrailResult | None:
        stripped = text.strip()
        if stripped.startswith("{") or stripped.startswith("["):
            try:
                json.loads(stripped)
                return None
            except json.JSONDecodeError:
                return GuardrailResult(action=ActionType.WARN, original=text, sanitized=text, rule_name=self.name, reason="Invalid JSON format")
        start = text.find("{")
        if start != -1:
            end = text.find("}", start) + 1
            candidate = text[start:end]
            try:
                json.loads(candidate)
                return None
            except json.JSONDecodeError:
                pass
        start = text.find("[")
        if start != -1:
            end = text.find("]", start) + 1
            candidate = text[start:end]
            try:
                json.loads(candidate)
                return None
            except json.JSONDecodeError:
                pass
        return GuardrailResult(action=ActionType.WARN, original=text, sanitized=text, rule_name=self.name, reason="Invalid JSON format")


class GuardrailsEngine:
    def __init__(self):
        self.rules: list[Any] = []

    def add_rule(self, rule: Any) -> None:
        self.rules.append(rule)

    async def check(self, text: str) -> GuardrailResult | None:
        for rule in self.rules:
            result = await rule.check(text)
            if result:
                return result
        return None

    async def apply_guardrails(self, text: str, is_input: bool = False) -> tuple[str, list[GuardrailResult]]:
        violations = []
        current = text
        if is_input:
            injection_rule = PromptInjectionRule()
            result = await injection_rule.check(current)
            if result:
                violations.append(result)
                return result.sanitized, violations
        for rule in self.rules:
            result = await rule.check(current)
            if result:
                violations.append(result)
                if result.action == ActionType.SANITIZE:
                    current = result.sanitized
                elif result.action == ActionType.BLOCK:
                    return result.sanitized, violations
        return current, violations


default_guardrails = GuardrailsEngine()
default_guardrails.add_rule(PIIDetectionRule())
default_guardrails.add_rule(PromptInjectionRule())
default_guardrails.add_rule(OutputLengthRule())
