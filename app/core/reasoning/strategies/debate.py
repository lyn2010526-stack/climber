"""DebateStrategy — multi-agent debate for consensus convergence.

Implements three-agent debate (Proponent, Opponent, Judge) where agents
iteratively argue until consensus is reached or max rounds exhausted.


Architecture:
- Proponent: proposes and defends a solution
- Opponent: critiques and proposes alternatives
- Judge: evaluates both sides, decides consensus
- Iterate until convergence or max_rounds
- Return the judge's final synthesis as the best candidate
"""

from __future__ import annotations

import json
import time
from typing import Any

import structlog

from app.core.reasoning.base import (
    Candidate,
    CritiqueResult,
    ReasoningRequest,
    RoundTrace,
)
from app.core.reasoning.components.scorer import CandidateScorer
from app.core.reasoning.prompts.debate_prompts import (
    CONVERGENCE_CHECK_PROMPT,
    DEBATE_USER_PROMPT,
    JUDGE_SYSTEM_PROMPT,
    OPPONENT_SYSTEM_PROMPT,
    PROPONENT_SYSTEM_PROMPT,
    REBUTTAL_PROMPT,
)

logger = structlog.get_logger()


class DebateAgent:
    """Lightweight multi-agent wrapper with independent message history.

    Each DebateAgent maintains its own conversation context, enabling
    true multi-agent behavior where agents remember prior exchanges
    and build on them across debate rounds.
    """

    def __init__(
        self,
        role: str,
        system_prompt: str,
        model_adapter: Any,
        max_history: int = 20,
    ) -> None:
        self.role = role
        self.system_prompt = system_prompt
        self.model_adapter = model_adapter
        self.max_history = max_history
        self.messages: list[dict[str, str]] = []
        self.total_tokens = 0

    def reset(self) -> None:
        """Clear conversation history (keep system prompt)."""
        self.messages = []

    async def chat(self, user_message: str, temperature: float = 0.7, max_tokens: int = 4000) -> str:
        """Send a message and get a response, maintaining conversation history."""
        self.messages.append({"role": "user", "content": user_message})

        try:
            result = await self.model_adapter.chat(
                [{"role": "system", "content": self.system_prompt}] + self.messages[-self.max_history:],
                temperature=temperature,
                max_tokens=max_tokens,
            )
            response = result.content
            self.total_tokens += getattr(result, "usage", {}).get("total_tokens", 0)
        except Exception as exc:
            logger.error("debate_agent_chat_failed", role=self.role, error=str(exc))
            response = f"[{self.role} encountered an error: {type(exc).__name__}]"

        self.messages.append({"role": "assistant", "content": response})
        return response

    def get_context_summary(self, last_n: int = 4) -> str:
        """Return a summary of recent conversation for context passing."""
        recent = self.messages[-last_n:]
        return "\n".join(
            f"[{self.role}]: {m['content'][:200]}"
            for m in recent
        )


class DebateStrategy:
    """Debate strategy: Proponent vs Opponent with Judge arbitration."""

    name = "debate"

    def __init__(self) -> None:
        self._scorer = CandidateScorer()

    async def execute(
        self,
        request: ReasoningRequest,
        self_refine: Any,
        model_registry: Any,
    ) -> list[Candidate]:
        """Execute multi-agent debate with independent agent instances."""
        model_adapter = self._get_model(model_registry)
        start = time.monotonic()

        logger.info(
            "debate_start",
            task=request.task[:100],
            max_rounds=request.max_refine_rounds,
        )

        context = request.context.get("debate_context", "")

        proponent = DebateAgent(
            role="Proponent",
            system_prompt=PROPONENT_SYSTEM_PROMPT,
            model_adapter=model_adapter,
        )
        opponent = DebateAgent(
            role="Opponent",
            system_prompt=OPPONENT_SYSTEM_PROMPT,
            model_adapter=model_adapter,
        )
        judge = DebateAgent(
            role="Judge",
            system_prompt=JUDGE_SYSTEM_PROMPT,
            model_adapter=model_adapter,
        )

        proponent_position = await proponent.chat(
            DEBATE_USER_PROMPT.format(task=request.task, context=context),
        )
        opponent_position = await opponent.chat(
            DEBATE_USER_PROMPT.format(task=request.task, context=context),
        )

        traces: list[RoundTrace] = [RoundTrace(
            round_num=0,
            action="initial_positions",
            input_summary=request.task[:100],
            output_summary="Both sides presented initial positions",
        )]

        consensus_reached = False
        final_solution = proponent_position
        winner = "proponent"

        for round_num in range(1, request.max_refine_rounds + 1):
            round_start = time.monotonic()

            proponent_history = opponent.get_context_summary(last_n=4)
            new_proponent = await proponent.chat(
                REBUTTAL_PROMPT.format(
                    task=request.task,
                    your_role="Proponent",
                    opponent_argument=opponent_position[:2000],
                    debate_history=proponent_history[:3000],
                ),
            )
            proponent_position = new_proponent

            opponent_history = proponent.get_context_summary(last_n=4)
            new_opponent = await opponent.chat(
                REBUTTAL_PROMPT.format(
                    task=request.task,
                    your_role="Opponent",
                    opponent_argument=proponent_position[:2000],
                    debate_history=opponent_history[:3000],
                ),
            )
            opponent_position = new_opponent

            judge_history = f"{proponent.get_context_summary(last_n=3)}\n{opponent.get_context_summary(last_n=3)}"
            judge_prompt = CONVERGENCE_CHECK_PROMPT.format(
                task=request.task,
                proponent_position=proponent_position[:2000],
                opponent_position=opponent_position[:2000],
                debate_history=judge_history[:4000],
            )
            judge_response = await judge.chat(judge_prompt, temperature=0.2, max_tokens=2000)

            try:
                judge_result = json.loads(judge_response.strip())
            except json.JSONDecodeError:
                judge_result = {
                    "converged": False,
                    "reason": "Judge returned non-JSON response",
                    "quality_score": 2,
                    "winner": "proponent",
                    "final_solution": proponent_position,
                }

            duration = (time.monotonic() - round_start) * 1000
            traces.append(RoundTrace(
                round_num=round_num,
                action="debate_round",
                input_summary=f"Round {round_num}",
                output_summary=(
                    f"consensus={judge_result.get('converged', False)}, "
                    f"winner={judge_result.get('winner', 'unknown')}"
                ),
                duration_ms=duration,
            ))

            if judge_result.get("converged", False):
                consensus_reached = True
                final_solution = judge_result.get("final_solution", proponent_position)
                winner = judge_result.get("winner", "synthesis")
                logger.info("debate_converged", round=round_num, winner=winner)
                break

            final_solution = judge_result.get("final_solution", proponent_position)
            winner = judge_result.get("winner", "proponent")

        elapsed = (time.monotonic() - start) * 1000

        total_tokens = proponent.total_tokens + opponent.total_tokens + judge.total_tokens

        logger.info(
            "debate_complete",
            rounds=len(traces),
            consensus=consensus_reached,
            winner=winner,
            duration_ms=round(elapsed, 1),
            total_tokens=total_tokens,
        )

        return [Candidate(
            id="debate_01",
            strategy=self.name,
            path_type=f"debate_{winner}",
            content=final_solution,
            reasoning_chain=[rt.output_summary for rt in traces],
            confidence=0.9 if consensus_reached else 0.7,
            critique=CritiqueResult(
                passed=consensus_reached,
                summary=f"Debate {'converged' if consensus_reached else 'max rounds'} — winner: {winner}",
            ),
            round_created=len(traces),
            duration_ms=round(elapsed, 1),
            token_usage={"total_tokens": total_tokens},
            metadata={
                "consensus_reached": consensus_reached,
                "winner": winner,
                "total_debate_rounds": len(traces),
                "agent_tokens": {
                    "proponent": proponent.total_tokens,
                    "opponent": opponent.total_tokens,
                    "judge": judge.total_tokens,
                },
            },
        )]

    def _get_model(self, model_registry: Any) -> Any:
        """Get model adapter from registry."""
        return model_registry.get_default()
