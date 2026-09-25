"""Small helpers for one-shot LLM calls through the AgentEngine.

Used by the simulation node's LLM planner/reviewer so a sub-agent can
be invoked inside a workflow without creating a persistent session or
exposing tool access. Text-only, no tool calling, bounded output.
"""

from __future__ import annotations

from typing import Any


def response_usage(response: Any) -> dict[str, int | None]:
    """Read reported counters only; zero defaults are not evidence of usage."""
    raw = getattr(response, "usage", None)
    raw = raw if isinstance(raw, dict) else {}

    def count(*names: str) -> int | None:
        for name in names:
            value = raw.get(name, getattr(response, name, None))
            if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
                return value
        return None

    prompt = count("prompt_tokens", "input_tokens")
    completion = count("completion_tokens", "output_tokens")
    total = count("total_tokens")
    if total is None and prompt is not None and completion is not None:
        total = prompt + completion
    if total is None:
        reported = getattr(response, "tokens_used", None)
        if isinstance(reported, int) and not isinstance(reported, bool) and reported > 0:
            total = reported
    return {"prompt_tokens": prompt, "completion_tokens": completion, "total_tokens": total}


def merge_stream_chunk(result: Any, chunk: Any) -> str:
    """Honor explicit cumulative snapshots; return only the unseen suffix."""
    snapshot = getattr(chunk, "accumulated_content", "") or ""
    if snapshot:
        if not snapshot.startswith(result.content):
            raise ValueError("Streaming snapshot diverged from emitted content")
        delta = snapshot[len(result.content):]
        result.content = snapshot
    else:
        delta = getattr(chunk, "content", "") or ""
        result.content += delta
    usage = dict(getattr(result, "usage", {}) or {})
    usage.update({key: value for key, value in response_usage(chunk).items() if value is not None})
    result.usage = usage
    result.tokens_used = usage.get("total_tokens", 0)
    if getattr(chunk, "finish_reason", None):
        result.finish_reason = chunk.finish_reason
    for name in ("input_cost", "output_cost", "total_cost"):
        value = getattr(chunk, name, None)
        if value is not None:
            setattr(result, name, value)
    return delta


async def run_llm_single(
    agent_engine: Any,
    provider: str,
    model_id: str,
    api_key: str,
    system_prompt: str,
    prompt: str,
    base_url: str | None = None,
    max_chars: int = 8000,
) -> str:
    """Run one LLM completion and return its text.

    Returns an empty string on failure so callers can fall back
    gracefully instead of crashing the enclosing workflow node.
    """
    try:
        session = agent_engine.create_session(
            agent_id="sim-subagent",
            user_id="system",
            provider=provider,
            model_id=model_id,
            api_key=api_key,
            base_url=base_url,
            system_prompt=system_prompt,
        )
        result = await agent_engine.run_agent(session, prompt)
        output = (result.get("output") or "") if isinstance(result, dict) else str(result or "")
    except Exception:
        return ""
    return output[:max_chars]
