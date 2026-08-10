"""Workflow templates — reusable patterns for common agent workflows."""

from __future__ import annotations

from app.workflow import (
    NodeType,
    Workflow,
    WorkflowEdge,
    WorkflowNode,
)


class WorkflowTemplates:
    """Pre-built workflow templates for common patterns."""

    @staticmethod
    def simple_qa(provider: str, model_id: str, api_key: str, system_prompt: str = "") -> Workflow:
        """Single LLM call — simplest workflow."""
        nodes = [
            WorkflowNode(id="start", type=NodeType.START, name="Start"),
            WorkflowNode(
                id="llm", type=NodeType.LLM, name="Answer",
                config={
                    "provider": provider,
                    "model_id": model_id,
                    "api_key": api_key,
                    "prompt": "{{question}}",
                    "system_prompt": system_prompt or "You are a helpful assistant.",
                },
                inputs={"question": "start.question"},
            ),
            WorkflowNode(id="end", type=NodeType.END, name="End", inputs={"result": "llm.response"}),
        ]
        edges = [
            WorkflowEdge(source="start", target="llm"),
            WorkflowEdge(source="llm", target="end"),
        ]
        return Workflow(
            name="Simple QA",
            description="Single LLM call for answering questions",
            nodes=nodes,
            edges=edges,
        )

    @staticmethod
    def tool_use(tool_name: str, provider: str, model_id: str, api_key: str) -> Workflow:
        """LLM decides when to use a tool, executes it, returns result."""
        nodes = [
            WorkflowNode(id="start", type=NodeType.START, name="Start"),
            WorkflowNode(
                id="think", type=NodeType.LLM, name="Think",
                config={
                    "provider": provider,
                    "model_id": model_id,
                    "api_key": api_key,
                    "prompt": "{{question}}",
                    "system_prompt": "Decide if you need to use the tool. If yes, call it.",
                },
                inputs={"question": "start.question"},
            ),
            WorkflowNode(
                id="check", type=NodeType.CONDITION, name="Tool Needed?",
                config={
                    "variable": "think.response",
                    "operator": "contains",
                    "value": "use_tool",
                },
            ),
            WorkflowNode(
                id="tool", type=NodeType.TOOL, name="Execute Tool",
                config={
                    "tool_name": tool_name,
                    "tool_inputs": {"input": "start.question"},
                },
            ),
            WorkflowNode(
                id="final", type=NodeType.LLM, name="Final Answer",
                config={
                    "provider": provider,
                    "model_id": model_id,
                    "api_key": api_key,
                    "prompt": "Based on the tool result: {{result}}, answer the question.",
                    "system_prompt": "Provide a final answer based on the tool output.",
                },
                inputs={"result": "tool.result"},
            ),
            WorkflowNode(id="end", type=NodeType.END, name="End", inputs={"output": "think.response"}),
        ]
        edges = [
            WorkflowEdge(source="start", target="think"),
            WorkflowEdge(source="think", target="check"),
            WorkflowEdge(source="check", target="tool", condition="true"),
            WorkflowEdge(source="check", target="end", condition="false"),
            WorkflowEdge(source="tool", target="final"),
            WorkflowEdge(source="final", target="end"),
        ]
        return Workflow(
            name="Tool Use",
            description="LLM decides when to call a tool and processes results",
            nodes=nodes,
            edges=edges,
        )

    @staticmethod
    def chain_of_thought(provider: str, model_id: str, api_key: str, steps: int = 3) -> Workflow:
        """Chain-of-thought: multi-step reasoning with intermediate outputs."""
        nodes = [WorkflowNode(id="start", type=NodeType.START, name="Start")]
        edges: list[WorkflowEdge] = []

        prev_id = "start"
        for i in range(steps):
            node_id = f"step_{i}"
            nodes.append(WorkflowNode(
                id=node_id,
                type=NodeType.LLM,
                name=f"Step {i + 1}",
                config={
                    "provider": provider,
                    "model_id": model_id,
                    "api_key": api_key,
                    "prompt": (
                        "{{question}}" if i == 0
                        else f"Based on previous reasoning:\n{{{{step_{i-1}.response}}}}\n\nContinue reasoning step {i + 1}."
                    ),
                    "system_prompt": (
                        f"You are reasoning step {i + 1} of {steps}. "
                        "Think carefully and show your work."
                    ),
                },
                inputs=(
                    {"question": "start.question"} if i == 0
                    else {"question": f"step_{i-1}.response"}
                ),
            ))
            edges.append(WorkflowEdge(source=prev_id, target=node_id))
            prev_id = node_id

        nodes.append(WorkflowNode(
            id="end", type=NodeType.END, name="End",
            inputs={"reasoning": f"{prev_id}.response"},
        ))
        edges.append(WorkflowEdge(source=prev_id, target="end"))

        return Workflow(
            name="Chain of Thought",
            description=f"Multi-step reasoning in {steps} steps",
            nodes=nodes,
            edges=edges,
        )

    @staticmethod
    def map_reduce(provider: str, model_id: str, api_key: str) -> Workflow:
        """Map-reduce: process items in parallel, then aggregate."""
        nodes = [
            WorkflowNode(id="start", type=NodeType.START, name="Start"),
            WorkflowNode(
                id="map", type=NodeType.ITERATOR, name="Map Items",
                config={
                    "collection": "start.items",
                    "item_var": "item",
                    "max_iterations": 50,
                    "transform": "str(item)",
                },
                inputs={"items": "start.items"},
            ),
            WorkflowNode(
                id="reduce", type=NodeType.LLM, name="Reduce/Aggregate",
                config={
                    "provider": provider,
                    "model_id": model_id,
                    "api_key": api_key,
                    "prompt": "Aggregate these results:\n{{results}}",
                    "system_prompt": "Combine and summarize the mapped results.",
                },
                inputs={"results": "map.results"},
            ),
            WorkflowNode(id="end", type=NodeType.END, name="End", inputs={"output": "reduce.response"}),
        ]
        edges = [
            WorkflowEdge(source="start", target="map"),
            WorkflowEdge(source="map", target="reduce"),
            WorkflowEdge(source="reduce", target="end"),
        ]
        return Workflow(
            name="Map Reduce",
            description="Process items in parallel then aggregate results",
            nodes=nodes,
            edges=edges,
        )

    @staticmethod
    def conditional_branch(
        provider: str, model_id: str, api_key: str,
        condition_var: str, condition_value: str,
        true_prompt: str, false_prompt: str,
    ) -> Workflow:
        """Branch execution based on a condition."""
        nodes = [
            WorkflowNode(id="start", type=NodeType.START, name="Start"),
            WorkflowNode(
                id="check", type=NodeType.CONDITION, name="Check Condition",
                config={
                    "variable": condition_var,
                    "operator": "equals",
                    "value": condition_value,
                },
            ),
            WorkflowNode(
                id="true_branch", type=NodeType.LLM, name="True Branch",
                config={
                    "provider": provider,
                    "model_id": model_id,
                    "api_key": api_key,
                    "prompt": true_prompt,
                    "system_prompt": "Handle the true condition.",
                },
            ),
            WorkflowNode(
                id="false_branch", type=NodeType.LLM, name="False Branch",
                config={
                    "provider": provider,
                    "model_id": model_id,
                    "api_key": api_key,
                    "prompt": false_prompt,
                    "system_prompt": "Handle the false condition.",
                },
            ),
            WorkflowNode(id="end", type=NodeType.END, name="End", inputs={"output": "start.input"}),
        ]
        edges = [
            WorkflowEdge(source="start", target="check"),
            WorkflowEdge(source="check", target="true_branch", condition="true"),
            WorkflowEdge(source="check", target="false_branch", condition="false"),
            WorkflowEdge(source="true_branch", target="end"),
            WorkflowEdge(source="false_branch", target="end"),
        ]
        return Workflow(
            name="Conditional Branch",
            description="Execute different paths based on a condition",
            nodes=nodes,
            edges=edges,
        )

    @staticmethod
    def list_templates() -> list[dict[str, str]]:
        """List available templates."""
        return [
            {"id": "simple_qa", "name": "Simple QA", "description": "Single LLM call"},
            {"id": "tool_use", "name": "Tool Use", "description": "LLM with tool calling"},
            {"id": "chain_of_thought", "name": "Chain of Thought", "description": "Multi-step reasoning"},
            {"id": "map_reduce", "name": "Map Reduce", "description": "Parallel processing + aggregation"},
            {"id": "conditional_branch", "name": "Conditional Branch", "description": "If-else branching"},
        ]
