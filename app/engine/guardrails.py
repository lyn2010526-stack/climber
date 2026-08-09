"""Task guardrails for output validation and quality enforcement.

Provides multiple guardrail types that can be chained together:
- OutputPydantic: validates output against a Pydantic model
- LLMGuardrail: uses an LLM to judge output quality
- FunctionGuardrail: uses a custom function for validation
- GuardrailChain: chains multiple guardrails with retry logic
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from typing import Any, Callable

import structlog
from pydantic import BaseModel, ValidationError

logger = structlog.get_logger()


class GuardrailResult(BaseModel):
    """Result of a guardrail validation."""

    valid: bool
    feedback: str | None = None
    retry: bool = True
    metadata: dict[str, Any] = {}


class BaseGuardrail(ABC):
    """Abstract base class for all guardrails."""

    @abstractmethod
    async def validate(self, output: str) -> GuardrailResult:
        """Validate an output string and return the result."""
        ...


class OutputPydantic(BaseGuardrail):
    """Force output to match a Pydantic model.

    Attempts to parse the output as JSON and validate it against
    the provided Pydantic model class.
    """

    def __init__(self, model: type[BaseModel], strict: bool = False):
        self.model = model
        self.strict = strict

    async def validate(self, output: str) -> GuardrailResult:
        """Validate output against the Pydantic model."""
        try:
            cleaned = output.strip()

            if cleaned.startswith("```"):
                lines = cleaned.split("\n")
                cleaned = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

            data = json.loads(cleaned)
            instance = self.model(**data)

            return GuardrailResult(
                valid=True,
                metadata={"parsed": instance.model_dump()},
            )
        except json.JSONDecodeError as e:
            if self.strict:
                return GuardrailResult(
                    valid=False,
                    feedback=f"Output is not valid JSON: {e}. Return valid JSON matching the schema.",
                    retry=True,
                )
            return GuardrailResult(
                valid=False,
                feedback=f"JSON parsing failed: {e}",
                retry=True,
            )
        except ValidationError as e:
            errors = e.errors()
            error_msgs = "; ".join(
                f"{err['loc']}: {err['msg']}" for err in errors
            )
            schema = self.model.model_json_schema()
            return GuardrailResult(
                valid=False,
                feedback=(
                    f"Output does not match required schema: {error_msgs}. "
                    f"Expected schema: {json.dumps(schema, indent=2)}"
                ),
                retry=True,
            )


class LLMGuardrail(BaseGuardrail):
    """LLM-based output validation.

    Uses a language model to judge whether the output meets
    specified criteria.
    """

    def __init__(
        self,
        criteria: str,
        llm_client: Any = None,
        min_score: float = 0.7,
    ):
        self.criteria = criteria
        self.llm_client = llm_client
        self.min_score = min_score

    async def validate(self, output: str) -> GuardrailResult:
        """Validate output using LLM judgment."""
        if not self.llm_client:
            logger.warning("llm_guardrail_no_client", criteria=self.criteria)
            return GuardrailResult(valid=True)

        prompt = (
            f"Evaluate whether the following output meets the specified criteria.\n\n"
            f"## Criteria\n{self.criteria}\n\n"
            f"## Output\n{output[:4000]}\n\n"
            f"Respond with JSON: {{\"passes\": boolean, \"score\": 0.0-1.0, \"feedback\": \"...\"}}"
        )

        try:
            response = await self.llm_client.generate(prompt)
            cleaned = response.strip()
            if cleaned.startswith("```"):
                lines = cleaned.split("\n")
                cleaned = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

            result = json.loads(cleaned)
            passes = result.get("passes", False)
            score = result.get("score", 0.0)
            feedback = result.get("feedback", "")

            return GuardrailResult(
                valid=passes and score >= self.min_score,
                feedback=feedback if not passes else None,
                retry=not passes,
                metadata={"score": score},
            )
        except Exception as e:
            logger.error("llm_guardrail_error", error=str(e))
            return GuardrailResult(valid=True)


class FunctionGuardrail(BaseGuardrail):
    """Function-based output validation.

    Uses a custom callable to validate output. The function should
    return a tuple of (is_valid, feedback).
    """

    def __init__(
        self,
        func: Callable[[str], tuple[bool, Any]],
        name: str = "function_guardrail",
    ):
        self.func = func
        self.name = name

    async def validate(self, output: str) -> GuardrailResult:
        """Validate output using the provided function."""
        try:
            result = self.func(output)

            if isinstance(result, bool):
                return GuardrailResult(
                    valid=result,
                    feedback=None if result else f"Validation failed: {self.name}",
                    retry=not result,
                )

            is_valid, feedback = result
            return GuardrailResult(
                valid=is_valid,
                feedback=str(feedback) if feedback else None,
                retry=not is_valid,
            )
        except Exception as e:
            logger.error("function_guardrail_error", name=self.name, error=str(e))
            return GuardrailResult(
                valid=False,
                feedback=f"Guardrail '{self.name}' raised an exception: {e}",
                retry=False,
            )


class GuardrailChain(BaseGuardrail):
    """Chain multiple guardrails with retry logic.

    Runs guardrails in sequence. If any guardrail fails and allows retry,
    the output is sent back for re-processing up to max_retries times.
    """

    def __init__(
        self,
        guardrails: list[BaseGuardrail],
        max_retries: int = 3,
        stop_on_first_failure: bool = True,
    ):
        self.guardrails = guardrails
        self.max_retries = max_retries
        self.stop_on_first_failure = stop_on_first_failure

    async def validate(self, output: str) -> GuardrailResult:
        """Run all guardrails in sequence."""
        all_feedback: list[str] = []
        all_metadata: dict[str, Any] = {}

        for guardrail in self.guardrails:
            result = await guardrail.validate(output)
            all_metadata.update(result.metadata)

            if not result.valid:
                if result.feedback:
                    all_feedback.append(result.feedback)

                if self.stop_on_first_failure:
                    return GuardrailResult(
                        valid=False,
                        feedback=" | ".join(all_feedback),
                        retry=result.retry,
                        metadata=all_metadata,
                    )

        if all_feedback:
            return GuardrailResult(
                valid=False,
                feedback=" | ".join(all_feedback),
                retry=True,
                metadata=all_metadata,
            )

        return GuardrailResult(valid=True, metadata=all_metadata)

    async def validate_with_retry(
        self,
        output: str,
        regenerate_fn: Callable[[str, str], Any] | None = None,
    ) -> tuple[str, GuardrailResult]:
        """Validate with automatic retry using a regeneration function.

        If validation fails and regenerate_fn is provided, calls it with
        the output and feedback to get an improved version.
        """
        current_output = output

        for attempt in range(self.max_retries + 1):
            result = await self.validate(current_output)

            if result.valid:
                return current_output, result

            if attempt < self.max_retries and regenerate_fn and result.retry:
                feedback = result.feedback or "Output did not pass validation."
                try:
                    new_output = await regenerate_fn(current_output, feedback)
                    if isinstance(new_output, str):
                        current_output = new_output
                    else:
                        break
                except Exception as e:
                    logger.error("guardrail_regenerate_error", error=str(e))
                    break
            else:
                break

        return current_output, GuardrailResult(
            valid=False,
            feedback=result.feedback,
            retry=False,
            metadata=result.metadata,
        )
