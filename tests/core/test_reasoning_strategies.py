"""Tests for reasoning strategy bug fixes (deep_refine / debate)."""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from app.core.reasoning.base import ReasoningMode, ReasoningRequest
from app.core.reasoning.prompts.debate_prompts import (
    JUDGE_SYSTEM_PROMPT,
    OPPONENT_SYSTEM_PROMPT,
    PROPONENT_SYSTEM_PROMPT,
)
from app.core.reasoning.strategies.debate import DebateAgent, DebateStrategy
from app.core.reasoning.strategies.deep_refine import DeepRefineStrategy


class FakeRegistry:
    """Minimal model registry returning a single fake adapter."""

    def __init__(self, adapter) -> None:
        self._adapter = adapter

    def get_default(self):
        return self._adapter

    def get_or_create(self, name):
        return self._adapter


class _Chunk:
    def __init__(self, content: str) -> None:
        self.content = content


class _Result:
    def __init__(self, content: str, tokens_used: int = 0) -> None:
        self.content = content
        self.tokens_used = tokens_used


class FakeDeepRefineModel:
    """Stateful fake adapter for DeepRefineStrategy.

    stream_chat() yields the initial solution; chat() distinguishes
    critique / reflection / improvement calls from the prompt content.
    """

    def __init__(self, initial: str, critiques: list[dict], improvements: list[str]) -> None:
        self.initial = initial
        self._critiques = list(critiques)
        self._improvements = list(improvements)
        self.improve_calls: list[str] = []

    async def stream_chat(self, messages=None, **kwargs):
        yield _Chunk(self.initial)

    async def chat(self, messages, **kwargs):
        user_text = "\n".join(m.get("content", "") for m in messages)
        if "Produce an improved output addressing every issue" in user_text:
            improved = self._improvements.pop(0)
            self.improve_calls.append(improved)
            return _Result(improved)
        if "Generate a structured reflection" in user_text:
            return _Result(json.dumps({
                "failure_reason": "some gap",
                "lesson": "check completeness",
                "suggested_approach": "be more explicit",
            }))
        if "Evaluate this output against the task" in user_text:
            return _Result(json.dumps(self._critiques.pop(0)))
        raise AssertionError(f"unexpected chat call: {user_text[:120]!r}")


def _role(system_prompt: str) -> str:
    if system_prompt == JUDGE_SYSTEM_PROMPT:
        return "judge"
    if system_prompt == PROPONENT_SYSTEM_PROMPT:
        return "proponent"
    if system_prompt == OPPONENT_SYSTEM_PROMPT:
        return "opponent"
    raise AssertionError(f"unexpected system prompt: {system_prompt[:80]!r}")


class FakeDebateModel:
    """Fake adapter for DebateStrategy.

    chat() routes responses by exact system prompt (role) and records every
    call so tests can inspect the debate_history each agent received.
    """

    def __init__(self, judge_responses: list[dict]) -> None:
        self._judge_responses = list(judge_responses)
        self.calls: list[tuple[str, str, str]] = []

    async def chat(self, messages, **kwargs):
        system = messages[0]["content"] if messages else ""
        user = messages[-1]["content"]
        role = _role(system)
        self.calls.append((role, system, user))
        if role == "proponent":
            if "Opponent's argument" in user:
                return _Result("proponent rebuttal", tokens_used=5)
            return _Result("proponent initial position", tokens_used=3)
        if role == "opponent":
            if "Opponent's argument" in user:
                return _Result("opponent rebuttal", tokens_used=4)
            return _Result("opponent initial position", tokens_used=2)
        return _Result(json.dumps(self._judge_responses.pop(0)), tokens_used=7)


def _extract_debate_history(user_text: str) -> str:
    marker = "Previous rounds of debate:\n"
    start = user_text.index(marker) + len(marker)
    return user_text[start:]


@pytest.mark.asyncio
async def test_deep_refine_returns_last_improved_content():
    strategy = DeepRefineStrategy()
    fake = FakeDeepRefineModel(
        initial="initial",
        critiques=[
            {"passed": False, "scores": {"correctness": 2.0, "completeness": 2.0, "clarity": 2.0, "safety": 2.0, "actionability": 2.0}, "issues": [{"severity": "minor", "description": "round 1 issue"}]},
            {"passed": False, "scores": {"correctness": 3.0, "completeness": 3.0, "clarity": 3.0, "safety": 3.0, "actionability": 3.0}, "issues": [{"severity": "minor", "description": "round 2 issue"}]},
            {"passed": False, "scores": {"correctness": 3.9, "completeness": 3.9, "clarity": 3.9, "safety": 3.9, "actionability": 3.9}, "issues": [{"severity": "minor", "description": "round 3 issue"}]},
        ],
        improvements=["improved_v1", "improved_v2"],
    )
    request = ReasoningRequest(
        task="refine this answer",
        mode=ReasoningMode.DEEP_REFINE,
        max_refine_rounds=3,
    )

    candidates = await strategy.execute(request, self_refine=None, model_registry=FakeRegistry(fake))

    assert len(candidates) == 1
    candidate = candidates[0]
    assert fake.improve_calls == ["improved_v1", "improved_v2"]
    assert candidate.content == fake.improve_calls[-1]
    assert candidate.content == "improved_v2"
    assert candidate.confidence > 0.5


@pytest.mark.asyncio
async def test_debate_each_agent_reads_own_history():
    strategy = DebateStrategy()
    fake = FakeDebateModel(judge_responses=[
        {"converged": True, "winner": "synthesis", "final_solution": "consensus answer", "quality_score": 4},
    ])
    request = ReasoningRequest(task="debate this topic", mode=ReasoningMode.DEBATE, max_refine_rounds=1)

    candidates = await strategy.execute(request, self_refine=None, model_registry=FakeRegistry(fake))

    proponent_rebuttal = next(
        user for role, system, user in fake.calls
        if role == "proponent" and "Opponent's argument" in user
    )
    opponent_rebuttal = next(
        user for role, system, user in fake.calls
        if role == "opponent" and "Opponent's argument" in user
    )

    proponent_history = _extract_debate_history(proponent_rebuttal)
    assert "[Proponent]" in proponent_history
    assert "[Opponent]" not in proponent_history

    opponent_history = _extract_debate_history(opponent_rebuttal)
    assert "[Opponent]" in opponent_history
    assert "[Proponent]" not in opponent_history

    candidate = candidates[0]
    assert candidate.content == "consensus answer"
    assert candidate.metadata["agent_tokens"] == {
        "proponent": 3 + 5,
        "opponent": 2 + 4,
        "judge": 7,
    }


@pytest.mark.asyncio
async def test_debate_agent_tokens_accumulate_tokens_used():
    agent = DebateAgent(role="Proponent", system_prompt=PROPONENT_SYSTEM_PROMPT, model_adapter=FakeDebateModel([]))
    await agent.chat("request one")
    await agent.chat("Opponent's argument\nrespond to this")
    assert agent.total_tokens == 3 + 5


@pytest.mark.asyncio
async def test_debate_agent_tokens_fall_back_to_usage():
    class _UsageResult:
        def __init__(self, content: str, total: int) -> None:
            self.content = content
            self.usage = {"total_tokens": total}

    async def chat(messages, **kwargs):
        return _UsageResult("answer", total=24)

    agent = DebateAgent(role="Opponent", system_prompt=OPPONENT_SYSTEM_PROMPT, model_adapter=SimpleNamespace(chat=chat))
    response = await agent.chat("request")
    assert response == "answer"
    assert agent.total_tokens == 24


@pytest.mark.asyncio
async def test_debate_confidence_comes_from_scorer():
    strategy = DebateStrategy()
    strategy._scorer = SimpleNamespace(score_from_critique=lambda critique: 0.42)
    fake = FakeDebateModel(judge_responses=[
        {"converged": True, "winner": "synthesis", "final_solution": "consensus answer", "quality_score": 4},
    ])
    request = ReasoningRequest(task="debate this topic", mode=ReasoningMode.DEBATE, max_refine_rounds=1)

    candidates = await strategy.execute(request, self_refine=None, model_registry=FakeRegistry(fake))

    assert candidates[0].confidence == 0.42
