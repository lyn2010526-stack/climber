"""LLM planner — natural-language requirement → experiment plan.

Corresponds to the MatSciAgent "NL requirement → candidate structures"
step and CircuitAgent's "abstract engineering metric → simulation
parameter" translation: an LLM sub-agent reads a natural-language goal
and the target tool's JSON-schema parameter definitions, and emits a
structured plan (objective + sweep dims + base parameters). The result is
then fed through the deterministic ``plan_from_schema`` builder so the
LLM only proposes a search space — it never constructs tool calls.

The LLM output is strictly validated: only keys the tool schema knows
are accepted, only numeric/string values allowed, and the sweep is
capped by ``max_experiments``. A malformed plan falls back to a default
single-candidate plan rather than erroring the whole run.
"""

from __future__ import annotations

import json
import re
from collections.abc import Awaitable, Callable
from typing import Any

import structlog

from app.simulation.models import ExperimentSpec
from app.simulation.planner import ExperimentPlan, ParamDim, plan_from_schema

logger = structlog.get_logger()

LLMPlanFn = Callable[[str, str], Awaitable[str]]

_SYSTEM_PROMPT = (
    "You are an experimental designer. Convert a natural-language "
    "engineering goal into a structured parameter search plan for the "
    "given simulation tool. Return ONLY a JSON object, no prose:\n"
    "{\"objective\": \"<one line>\", "
    "\"sweep\": {<param_name>: {\"values\": [...]} or {\"min\": <num>, \"max\": <num>, \"steps\": <int>}}, "
    "\"base\": {<fixed param_name>: <value>}}\n"
    "Only use parameter names from the tool schema. Keep the total "
    "combination count small (aim under 32 experiments)."
)

_USER_TEMPLATE = (
    "Engineering goal: {goal}\n\n"
    "Target tool: {tool_name}\n"
    "Tool parameter schema:\n{schema}\n\n"
    "Emit the search plan JSON now."
)


def _extract_json(text: str) -> dict[str, Any] | None:
    """Pull the first JSON object out of an LLM reply."""
    if not text:
        return None
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    candidate = fenced.group(1) if fenced else text
    match = re.search(r"\{.*\}", candidate, re.DOTALL)
    if not match:
        return None
    try:
        parsed = json.loads(match.group(0))
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def _known_param_names(tool_def: Any) -> set[str]:
    """Extract known parameter names from a ToolDefinition or dict."""
    if isinstance(tool_def, dict):
        props = (tool_def.get("parameters") or {}).get("properties", {})
    elif tool_def is not None and getattr(tool_def, "parameters", None):
        props = (tool_def.parameters or {}).get("properties", {})
    else:
        props = {}
    return set(props)


def _validate_plan_dict(raw: dict[str, Any], tool_def: Any) -> dict[str, Any] | None:
    """Validate and normalize the LLM plan against the tool schema."""
    known_params = _known_param_names(tool_def)
    sweep = raw.get("sweep")
    if not isinstance(sweep, dict):
        return None

    cleaned_sweep: dict[str, Any] = {}
    for name, dim in sweep.items():
        if known_params and name not in known_params:
            continue
        if not isinstance(dim, dict):
            if isinstance(dim, list) and len(dim) <= 64:
                cleaned_sweep[name] = {"values": dim[:64]}
            continue
        if "values" in dim and isinstance(dim["values"], list) and 0 < len(dim["values"]) <= 64:
            cleaned_sweep[name] = {"values": dim["values"][:64]}
        elif {"min", "max"} <= set(dim):
            try:
                lo, hi = float(dim["min"]), float(dim["max"])
            except (TypeError, ValueError):
                continue
            if lo > hi:
                lo, hi = hi, lo
            steps = max(2, min(int(dim.get("steps", 10)), 32))
            cleaned_sweep[name] = {"min": lo, "max": hi, "steps": steps}

    base = raw.get("base")
    if not isinstance(base, dict):
        base = {}
    if known_params:
        base = {k: v for k, v in base.items() if k in known_params}

    objective = raw.get("objective")
    if not isinstance(objective, str) or not objective.strip():
        objective = ""

    return {
        "objective": objective.strip(),
        "sweep": cleaned_sweep,
        "base": base,
    }


class LLMExperimentPlanner:
    """Plan an experiment sweep from a natural-language requirement."""

    def __init__(
        self,
        llm_call: LLMPlanFn,
        tool_name: str,
        tool_def: Any,
        max_experiments: int = 64,
        default_parameters: dict[str, Any] | None = None,
    ):
        self._llm_call = llm_call
        self.tool_name = tool_name
        self._tool_def = tool_def
        self.max_experiments = max_experiments
        self.default_parameters = dict(default_parameters or {})

    async def plan(self, requirement: str) -> ExperimentPlan:
        schema_text = json.dumps(
            self._tool_schema(),
            ensure_ascii=False,
        )
        prompt = _USER_TEMPLATE.format(
            goal=requirement,
            tool_name=self.tool_name,
            schema=schema_text,
        )
        raw_text = ""
        try:
            raw_text = await self._llm_call(prompt, _SYSTEM_PROMPT)
        except Exception as e:
            logger.warning("llm_planner_call_failed", error=str(e))

        raw = _extract_json(raw_text)
        if raw is None:
            logger.warning("llm_planner_no_json", tool=self.tool_name)
            return self._fallback_plan()

        validated = _validate_plan_dict(raw, self._tool_def)
        if validated is None or not validated["sweep"]:
            logger.warning("llm_planner_invalid_plan", tool=self.tool_name)
            return self._fallback_plan()

        return plan_from_schema(
            validated,
            tool_name=self.tool_name,
            max_experiments=self.max_experiments,
        )

    def _tool_schema(self) -> dict[str, Any]:
        """Return the tool's JSON parameter schema in dict form."""
        if isinstance(self._tool_def, dict):
            return self._tool_def.get("parameters") or {}
        if self._tool_def is not None:
            return (self._tool_def.parameters or {}) if getattr(self._tool_def, "parameters", None) else {}
        return {}

    def _fallback_plan(self) -> ExperimentPlan:
        """A safe single-candidate plan so a bad LLM output never blocks."""
        return plan_from_schema(
            {"objective": "", "sweep": {}, "base": self.default_parameters},
            tool_name=self.tool_name,
            max_experiments=1,
        )
