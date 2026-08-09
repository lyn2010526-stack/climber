"""LangChain-style chain integration.

"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class Chain:
    """Simple chain that passes input through a sequence of steps."""

    def __init__(self, steps: list[Callable]):
        self.steps = steps

    async def run(self, initial_input: Any) -> Any:
        result = initial_input
        for step in self.steps:
            if asyncio.iscoroutinefunction(step):
                result = await step(result)
            else:
                result = step(result)
        return result


class LLMChain:
    """Chain that uses an LLM to transform input."""

    def __init__(self, engine: Any, prompt_template: str, output_key: str = "output"):
        self.engine = engine
        self.prompt_template = prompt_template
        self.output_key = output_key

    async def run(self, inputs: dict[str, Any], session: Any) -> dict[str, Any]:
        prompt = self.prompt_template.format(**inputs)
        response = await self.engine.run_agent(session, prompt)
        return {self.output_key: response.get("output", ""), **inputs}


class SequentialChain:
    """Chain multiple LLMChains sequentially, passing output as input to next."""

    def __init__(self, chains: list[LLMChain], input_variables: list[str], output_variables: list[str]):
        self.chains = chains
        self.input_variables = input_variables
        self.output_variables = output_variables

    async def run(self, inputs: dict[str, Any], session: Any) -> dict[str, Any]:
        result = inputs
        for chain in self.chains:
            result = await chain.run(result, session)
        return {k: result.get(k) for k in self.output_variables if k in result}


# Import asyncio at top
import asyncio
