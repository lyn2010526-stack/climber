"""One model call per ambiguous instruction, with conservative validation."""

from __future__ import annotations

import asyncio
import json
from typing import Any

import structlog

from app.core.instruction import understand_instruction
from app.core.prompt_engine import PromptFragment, PromptLayer
from app.core.prompt_optimizer.config import OptimizerConfig
from app.core.prompt_optimizer.templates import ANALYSIS_TEMPLATE, REFERENCE_TEMPLATE

SOURCE = "prompt_optimizer"
logger = structlog.get_logger(__name__)


def validate_response(response: Any, original: str, max_tokens: int) -> dict[str, Any]:
    """Accept quoted evidence only; free-form model rewrites have no authority."""
    if response.tool_calls or response.finish_reason not in (None, "stop", "end_turn"):
        raise ValueError("incomplete_or_nontext_response")
    if not isinstance(response.content, str) or len(response.content) > max_tokens * 8:
        raise ValueError("response_budget_exceeded")
    data = json.loads(response.content)
    if not isinstance(data, dict) or set(data) != {"evidence", "questions", "missing_information"}:
        raise ValueError("invalid_response_schema")
    evidence, questions = data["evidence"], data["questions"]
    if (
        not isinstance(evidence, list)
        or not 1 <= len(evidence) <= 12
        or any(
            not isinstance(text, str) or not text.strip() or text not in original
            for text in evidence
        )
    ):
        raise ValueError("unsupported_evidence")
    if (
        not isinstance(questions, list)
        or len(questions) > 3
        or any(
            not isinstance(text, str) or not text.strip() or len(text) > 300 for text in questions
        )
        or type(data["missing_information"]) is not bool
    ):
        raise ValueError("invalid_clarification")
    return data


def clear_reference(session: Any) -> None:
    """Expire only our advisory system messages when a fresh turn begins."""
    session.messages[:] = [
        item
        for item in session.messages
        if not (item.get("role") == "system" and item.get("source") == SOURCE)
    ]


async def maybe_optimize_instruction(engine: Any, session: Any, original: str) -> None:
    """Keep raw messages intact; inject a bounded reference before the latest user message."""
    try:
        config = OptimizerConfig.from_env()
        if not config.enabled or not original.strip() or len(original) > config.max_input_chars:
            return
        if getattr(session, "mode", "") == "autonomous":
            return
        # The archive hook does not expose its parse; use the same lossless first pass.
        understanding = understand_instruction(original, context=session.session_id)
        if (
            understanding.progress != "needs_clarification"
            and understanding.confidence >= config.confidence_threshold
        ):
            return
        provider, model_id = session.provider, session.model_id
        if not provider or not model_id or (provider != "ollama" and not session.api_key):
            logger.info("prompt_optimizer_unconfigured")
            return
        adapter = engine.model_registry.get_or_create(
            provider=provider,
            model_id=model_id,
            api_key=session.api_key,
            base_url=session.base_url,
        )
        async with asyncio.timeout(config.timeout_seconds):
            response = await adapter.chat(
                messages=[
                    {"role": "system", "content": ANALYSIS_TEMPLATE.render()},
                    {
                        "role": "user",
                        "content": json.dumps(
                            {
                                "original": original,
                                "ambiguities": understanding.ambiguities,
                                "clarification_questions": understanding.clarification_questions,
                            },
                            ensure_ascii=False,
                        ),
                    },
                ],
                tools=None,
                max_tokens=config.max_tokens,
                temperature=0,
            )
        data = validate_response(response, original, config.max_tokens)
        evidence, questions = data["evidence"], data["questions"]
        questions = list(dict.fromkeys([*understanding.clarification_questions, *questions]))
        required = (
            bool(questions)
            or data["missing_information"]
            or understanding.progress == "needs_clarification"
        )
        if required and not questions:
            questions = ["请明确本次任务的目标对象、操作范围和完成标准。"]
        payload = json.dumps(
            {
                "source": SOURCE,
                "original": original,
                "evidence": evidence,
                "clarification_required": required,
                "questions": questions,
            },
            ensure_ascii=False,
        )
        fragment = PromptFragment(
            content=REFERENCE_TEMPLATE.render({"payload": payload}),
            layer=PromptLayer.DYNAMIC_RUNTIME,
            source=SOURCE,
        )
        # Per-turn fragments stay local rather than entering a shared engine registry.
        session.messages.insert(
            len(session.messages) - 1,
            {
                "role": "system",
                "content": fragment.render(),
                "source": fragment.source,
            },
        )
    except Exception as exc:
        # Exceptions may contain credentials or user text; log only their class.
        logger.warning("prompt_optimizer_degraded", error_type=type(exc).__name__)
