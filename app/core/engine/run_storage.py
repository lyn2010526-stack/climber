"""Durable run bookkeeping using the existing storage models."""

from __future__ import annotations

import math
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from uuid import uuid4

from app.core.engine.session_runner import response_usage


def _now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class RunStorage:
    def __init__(self, session_factory=None):
        if session_factory is None:
            from app.storage import async_session
            session_factory = async_session
        self.session_factory = session_factory

    async def begin(self, session):
        from app.storage.database import Agent, Session, Turn

        async with self.session_factory() as db:
            row = await db.get(Session, session.session_id)
            if row is not None and row.user_id != session.user_id:
                raise ValueError("Session belongs to another user")
            if row is None:
                agent = await db.get(Agent, session.agent_id) if session.agent_id else None
                row = Session(id=session.session_id, agent_id=agent.id if agent else None,
                              user_id=session.user_id, total_tokens=0)
                db.add(row)
                await db.flush()
            turn = await db.get(Turn, session.current_turn_id) if session.current_turn_id else None
            if turn is not None and turn.session_id != session.session_id:
                raise ValueError("Turn belongs to another session")
            if turn is None or (turn.status in {"completed", "failed", "cancelled", "stopped"}
                                and not session._resume_interrupted):
                turn = Turn(id=str(uuid4()), session_id=session.session_id, started_at=_now(),
                            metadata_={}, tokens_used=0)
                db.add(turn)
            turn.status = "running"
            turn.started_at = turn.started_at or _now()
            turn.completed_at = None
            turn.error = turn.error_message = None
            row.status = "running"
            session.current_turn_id = turn.id
            session._run_tokens = turn.tokens_used or 0
            session._run_cost_status = (turn.metadata_ or {}).get("cost_status", "unknown")
            session._run_usage_status = (turn.metadata_ or {}).get("usage_status", "unknown")
            await db.commit()

    async def record_response(self, session, response, iteration, *, complete=True):
        from app.middleware.metrics import TOKEN_USAGE
        from app.storage.database import Session, Turn, UsageLog
        from app.storage.models_cost import CostRecord

        usage = response_usage(response)
        # Existing schemas require numeric cost columns. Unknown costs live in
        # Turn metadata; only authoritative priced responses create CostRecord.
        costs = [getattr(response, name, None) for name in ("input_cost", "output_cost", "total_cost")]
        known_cost = complete and all(isinstance(value, (int, float)) and not isinstance(value, bool)
                         and math.isfinite(value) and value >= 0 for value in costs)
        if known_cost:
            known_cost = math.isclose(costs[0] + costs[1], costs[2], rel_tol=1e-9, abs_tol=1e-12)
        entry = {"iteration": iteration, "usage": usage, "response_complete": complete,
                 "cost_status": "known" if known_cost else "unknown",
                 "cost": costs[2] if known_cost else None,
                 "cost_source": "model_response" if known_cost else None}
        # Legacy NOT NULL integer columns cannot represent unknown counters.
        # Keep partial observations in Turn metadata instead of inventing zeros.
        complete_usage = all(value is not None for value in usage.values())
        entry["unknown_usage_fields"] = [key for key, value in usage.items() if value is None]
        entry["usage_log_status"] = "written" if complete_usage else "incomplete_usage"
        entry["cost_record_status"] = ("written" if known_cost and complete_usage
                                       else "incomplete_usage" if known_cost else "unknown_cost")
        async with self.session_factory() as db:
            turn = await db.get(Turn, session.current_turn_id)
            row = await db.get(Session, session.session_id)
            if turn is None or row is None:
                raise RuntimeError("Run bookkeeping must start before recording usage")
            metadata = dict(turn.metadata_ or {})
            calls = list(metadata.get("model_calls", []))
            call_id = str(uuid4())
            entry["id"] = call_id
            # Never split total tokens using an assumed ratio.
            if complete_usage:
                await db.execute(UsageLog.__table__.insert().values(
                    id=call_id, user_id=session.user_id, session_id=session.session_id,
                    provider=session.provider, model_id=session.model_id, **usage))
            if known_cost and complete_usage:
                await db.execute(CostRecord.__table__.insert().values(
                    id=call_id, user_id=session.user_id, session_id=session.session_id,
                    provider=session.provider, model_id=session.model_id, **usage,
                    input_cost=costs[0], output_cost=costs[1], total_cost=costs[2]))
            calls.append(entry)
            metadata["model_calls"] = calls
            metadata["cost_status"] = "known" if all(c["cost_status"] == "known" for c in calls) else "unknown"
            metadata["usage_status"] = "known" if all(c["usage"]["total_tokens"] is not None
                and c.get("response_complete", True) for c in calls) else "unknown"
            turn.metadata_ = metadata
            total = usage["total_tokens"] or 0
            turn.tokens_used = (turn.tokens_used or 0) + total
            row.total_tokens = (row.total_tokens or 0) + total
            session._run_tokens = turn.tokens_used
            session._run_cost_status = metadata["cost_status"]
            session._run_usage_status = metadata["usage_status"]
            await db.commit()
        for kind, field in (("prompt", "prompt_tokens"), ("completion", "completion_tokens"), ("total", "total_tokens")):
            if usage[field] is not None:
                TOKEN_USAGE.labels(provider=session.provider, model_id=session.model_id, type=kind).inc(usage[field])

    async def finish(self, session):
        from app.storage.database import Session, Turn

        async with self.session_factory() as db:
            row = await db.get(Session, session.session_id)
            turn = await db.get(Turn, session.current_turn_id)
            status = session.status.value
            row.status = turn.status = status
            row.iteration_count = turn.iteration_count = session._last_iteration
            turn.completed_at = _now()
            result = getattr(session, "_last_result", None)
            turn.result = result.content if result else None
            turn.error = turn.error_message = session._last_error
            turn.checkpoint_id = getattr(session, "_last_checkpoint_id", None)
            metadata = dict(turn.metadata_ or {})
            metadata["outcome"] = getattr(session, "_run_status_override", None) or status
            metadata.setdefault("cost_status", "unknown")
            metadata.setdefault("usage_status", "unknown")
            turn.metadata_ = metadata
            await db.commit()


@asynccontextmanager
async def track_run(session, store):
    from app.middleware.metrics import ACTIVE_SESSIONS, AGENT_ITERATION_COUNT, AGENT_RUN_TOTAL

    await store.begin(session)
    initial_iteration = session._last_iteration if session._resume_interrupted else 0
    session._last_error = None
    ACTIVE_SESSIONS.inc()
    try:
        yield
    except BaseException as exc:
        session._last_error = str(exc) or type(exc).__name__
        session._restore_status("cancelled" if not isinstance(exc, Exception) else "failed")
        raise
    finally:
        if session.status.value in {"pending", "running", "paused"}:
            session._restore_status("cancelled")
        try:
            await store.finish(session)
        finally:
            ACTIVE_SESSIONS.dec()
            AGENT_RUN_TOTAL.labels(provider=session.provider, model_id=session.model_id,
                                   status=session.status.value).inc()
            AGENT_ITERATION_COUNT.observe(max(0, session._last_iteration - initial_iteration))
