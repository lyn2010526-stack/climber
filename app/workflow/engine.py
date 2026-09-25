"""Workflow engine with DAG execution, conditional branching, and iteration.

Features:
- Topological sort for execution order
- Parallel layer execution
- Conditional branching (skip branches that don't match)
- Iterator nodes for looping over collections
- Variable resolution between nodes
- Template rendering with variable substitution
"""

from __future__ import annotations

import ast
import asyncio
import json
import time
from typing import Any

import structlog

from app.core.agent_engine import AgentEngine
from app.models.registry import ModelRegistry
from app.tools import ToolRegistry
from app.workflow import (
    NodeStatus,
    NodeType,
    Workflow,
    WorkflowNode,
    WorkflowResult,
)
from app.workflow.code_sandbox import run_code_sandboxed
from app.workflow.safe_code import (
    safe_eval,
    safe_exec,
    validate_code_ast as _validate_code_ast,
)

logger = structlog.get_logger()


class WorkflowEngine:
    """Executes workflow DAGs with full conditional branching and iteration."""

    def __init__(
        self,
        engine: AgentEngine,
        model_registry: ModelRegistry | None = None,
        tool_registry: ToolRegistry | None = None,
    ):
        self.agent_engine = engine
        self.model_registry = model_registry
        self.tool_registry = tool_registry

    def _resolve_registry(self) -> ToolRegistry:
        """Return the tool registry used for dispatch.

        Prefers an explicitly injected registry, then the application DI
        global (which main.py fills via register_builtins), then the
        module-level global registry, and finally a fresh empty registry.
        This keeps real tools (e.g. simulate_experiment) available to
        Flow and API workflow runs that do not pass a registry directly.
        """
        if self.tool_registry is not None:
            return self.tool_registry
        try:
            from app.core.di import resolve as di_resolve

            return di_resolve("ToolRegistry")
        except KeyError:
            pass
        try:
            from app.tools import tool_registry as module_global

            return module_global
        except Exception:
            pass
        return ToolRegistry()

    async def execute(
        self,
        workflow: Workflow,
        user_inputs: dict[str, str] | None = None,
        user_id: str = "system",
    ) -> WorkflowResult:
        """Execute a workflow DAG with conditional branching."""
        start_time = time.time()
        user_inputs = user_inputs or {}

        try:
            layers = workflow.topological_sort()
        except ValueError as e:
            return WorkflowResult(
                workflow_id=workflow.id,
                status="failed",
                error=str(e),
            )

        # Set start node
        start_node = next(
            (n for n in workflow.nodes if n.type == NodeType.START), None
        )
        if start_node:
            start_node.output = user_inputs
            start_node.status = NodeStatus.COMPLETED

        # Track which nodes are skipped due to conditional branching
        skipped_nodes: set[str] = set()

        for layer in layers:
            nodes_in_layer: list[WorkflowNode] = []

            for nid in layer:
                node = workflow.get_node(nid)
                if node is None:
                    continue
                if start_node and nid == start_node.id:
                    continue
                if nid in skipped_nodes:
                    continue
                nodes_in_layer.append(node)

            if not nodes_in_layer:
                continue

            # Execute all nodes in this layer in parallel
            tasks = [
                self._execute_node(node, workflow, user_inputs, user_id, skipped_nodes)
                for node in nodes_in_layer
            ]
            await asyncio.gather(*tasks)

            # Check for failures
            for node in nodes_in_layer:
                if node.status == NodeStatus.FAILED:
                    return WorkflowResult(
                        workflow_id=workflow.id,
                        status="failed",
                        error=f"Node '{node.name}' failed: {node.error}",
                        node_results=self._collect_results(workflow),
                        execution_time_ms=(time.time() - start_time) * 1000,
                    )

        execution_time = (time.time() - start_time) * 1000
        return WorkflowResult(
            workflow_id=workflow.id,
            status="completed",
            outputs=self._get_final_output(workflow),
            node_results=self._collect_results(workflow),
            execution_time_ms=execution_time,
        )

    async def _execute_node(
        self,
        node: WorkflowNode,
        workflow: Workflow,
        user_inputs: dict[str, str],
        user_id: str,
        skipped_nodes: set[str],
    ) -> None:
        """Execute a single workflow node with conditional branching."""
        node.status = NodeStatus.RUNNING

        try:
            # Resolve inputs from predecessor outputs
            resolved_inputs = self._resolve_inputs(node, workflow)

            if node.type == NodeType.LLM:
                output = await self._execute_llm_node(node, resolved_inputs, user_id)
            elif node.type == NodeType.TOOL:
                output = await self._execute_tool_node(node, resolved_inputs)
            elif node.type == NodeType.CONDITION:
                output, skip_targets = self._execute_condition_node(
                    node, resolved_inputs, workflow,
                )
                # Mark downstream nodes for skipping
                for target_id in skip_targets:
                    self._skip_downstream(target_id, node.id, workflow, skipped_nodes)
            elif node.type == NodeType.ITERATOR:
                output = await self._execute_iterator_node(
                    node, resolved_inputs, user_id, skipped_nodes,
                )
            elif node.type == NodeType.CODE:
                output = await self._execute_code_node(node, resolved_inputs)
            elif node.type == NodeType.SIMULATION:
                output = await self._execute_simulation_node(node, resolved_inputs)
            elif node.type == NodeType.END:
                output = resolved_inputs
            else:
                output = resolved_inputs

            node.output = output
            node.status = NodeStatus.COMPLETED
        except Exception as e:
            node.status = NodeStatus.FAILED
            node.error = str(e)
            logger.error("Node execution failed", node=node.name, error=str(e))

    def _skip_downstream(
        self,
        branch_node_id: str,
        condition_node_id: str,
        workflow: Workflow,
        skipped_nodes: set[str],
    ) -> None:
        """Mark nodes on a non-matching branch as skipped.

        When a condition node evaluates to false, all nodes that are
        exclusively reachable through the false branch should be skipped.
        """
        # Find all successors of the branch node
        branch_successors = workflow.get_successors(branch_node_id)
        for edge in branch_successors:
            succ_id = edge.target
            if succ_id == condition_node_id:
                continue
            # Only skip if not reachable from condition node via other paths
            if not self._is_reachable_from(condition_node_id, succ_id, workflow, exclude_node=branch_node_id):
                skipped_nodes.add(succ_id)

    def _is_reachable_from(
        self,
        source: str,
        target: str,
        workflow: Workflow,
        exclude_node: str | None = None,
    ) -> bool:
        """Check if target is reachable from source, optionally excluding a node."""
        visited: set[str] = set()
        queue = [source]

        while queue:
            current = queue.pop(0)
            if current == target:
                return True
            if current in visited:
                continue
            visited.add(current)

            for edge in workflow.get_successors(current):
                if edge.target != exclude_node and edge.target not in visited:
                    queue.append(edge.target)

        return False

    async def _execute_llm_node(
        self,
        node: WorkflowNode,
        inputs: dict[str, Any],
        user_id: str,
    ) -> dict[str, Any]:
        """Execute an LLM node."""
        import os

        provider = node.config.get("provider", "openai")
        model_id = node.config.get("model_id", "gpt-4")
        # Prefer env-var reference over plaintext key stored in workflow config
        api_key_env = node.config.get("api_key_env", "")
        api_key = os.environ.get(api_key_env, "") if api_key_env else node.config.get("api_key", "")
        prompt_template = node.config.get("prompt", "")
        system_prompt = node.config.get("system_prompt", "")

        prompt = self._render_template(prompt_template, inputs)

        session = self.agent_engine.create_session(
            agent_id=f"workflow-{node.id}",
            user_id=user_id,
            provider=provider,
            model_id=model_id,
            api_key=api_key,
            system_prompt=system_prompt,
        )

        full_response_parts: list[str] = []
        async for event in self.agent_engine.run(session, prompt):
            if event.type.value == "text":
                full_response_parts.append(event.data.get("content", ""))

        return {
            "response": "".join(full_response_parts),
            "node_id": node.id,
            "node_name": node.name,
        }

    async def _execute_tool_node(
        self,
        node: WorkflowNode,
        inputs: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute a tool node."""
        tool_name = node.config.get("tool_name", "")
        tool_inputs = node.config.get("tool_inputs", {})

        # Resolve template references in tool inputs
        resolved_tool_inputs: dict[str, Any] = {}
        for k, v in tool_inputs.items():
            if isinstance(v, str):
                resolved_tool_inputs[k] = self._render_template(str(v), inputs)
            else:
                resolved_tool_inputs[k] = v

        from app.core.parallel import ParallelToolExecutor
        registry = self._resolve_registry()
        sandbox = getattr(self.agent_engine, "sandbox", None)
        permission_overlay = getattr(self.agent_engine, "permission_overlay", None)
        capabilities = node.config.get("tool_capabilities")

        from app.core.engine.tool_capabilities import build_workflow_tool_validator
        validator = build_workflow_tool_validator(
            registry,
            sandbox=sandbox,
            permission_overlay=permission_overlay,
            capabilities=capabilities,
        )
        executor = ParallelToolExecutor(registry, validator=validator)
        tool_result = await executor.execute_all([{
            "id": f"wf-{node.id}",
            "function": {
                "name": tool_name,
                "arguments": resolved_tool_inputs,
            },
        }])
        tool_result = tool_result[0]

        if not tool_result.success:
            raise RuntimeError(tool_result.error or f"Tool '{tool_name}' execution failed")

        return {
            "result": tool_result.result,
            "tool_name": tool_name,
            "node_id": node.id,
            "node_name": node.name,
        }

    def _execute_condition_node(
        self,
        node: WorkflowNode,
        inputs: dict[str, Any],
        workflow: Workflow | None = None,
    ) -> tuple[dict[str, Any], list[str]] | dict[str, Any]:
        """Evaluate a condition node and determine which branches to skip.

        When workflow is provided, returns (output, skip_target_ids).
        When called without workflow (direct evaluation), returns just the output dict.
        """
        variable = node.config.get("variable", "")
        operator = node.config.get("operator", "equals")
        value = node.config.get("value", "")

        # Support both "variable" and "field" config keys
        if not variable:
            variable = node.config.get("field", "")

        # Resolve variable value from inputs
        actual_value = self._resolve_variable(variable, inputs)

        # Evaluate condition
        condition_result = self._evaluate_condition(actual_value, operator, value)

        # If no workflow context, return just the result (backward compat)
        if workflow is None:
            return {
                "condition_result": condition_result,
                "variable": actual_value,
                "operator": operator,
                "expected": value,
                "node_id": node.id,
                "node_name": node.name,
            }

        # Determine which edges to follow
        edges = workflow.get_successors(node.id)
        skip_targets: list[str] = []

        for edge in edges:
            edge_condition = edge.condition
            if (edge_condition == "true" and not condition_result) or (edge_condition == "false" and condition_result):
                skip_targets.append(edge.target)

        return {
            "condition_result": condition_result,
            "variable": actual_value,
            "operator": operator,
            "expected": value,
            "node_id": node.id,
            "node_name": node.name,
        }, skip_targets

    def _evaluate_condition(self, actual: Any, operator: str, expected: str) -> bool:
        """Evaluate a condition."""
        if actual is None:
            actual = ""

        actual_str = str(actual)

        if operator == "equals":
            return actual_str == expected
        if operator == "not_equals":
            return actual_str != expected
        if operator == "contains":
            return expected in actual_str
        if operator == "not_contains":
            return expected not in actual_str
        if operator == "starts_with":
            return actual_str.startswith(expected)
        if operator == "ends_with":
            return actual_str.endswith(expected)
        if operator == "not_empty":
            return bool(actual_str.strip())
        if operator == "empty":
            return not actual_str.strip()
        if operator == "greater_than":
            try:
                return float(actual_str) > float(expected)
            except (ValueError, TypeError):
                return False
        elif operator == "less_than":
            try:
                return float(actual_str) < float(expected)
            except (ValueError, TypeError):
                return False
        elif operator == "regex":
            import re
            if len(expected) > 500:
                return False
            # Reject catastrophic nested quantifiers like (a+)+ or (a*)*
            if re.search(r"\([^()]*[+*{][^()]*\)[+*{]", expected):
                return False
            try:
                return bool(re.search(expected, actual_str))
            except re.error:
                return False
        else:
            return actual_str == expected

    async def _execute_iterator_node(
        self,
        node: WorkflowNode,
        inputs: dict[str, Any],
        user_id: str,
        skipped_nodes: set[str],
    ) -> dict[str, Any]:
        """Execute an iterator node — loop over a collection and apply a transformation.

        Config:
        - collection: variable reference to the list to iterate
        - item_var: name for the loop variable (default: "item")
        - max_iterations: safety limit (default: 100)
        - transform: Python expression to apply per item (uses 'item' and 'index')
        """
        collection_var = node.config.get("collection", "")
        item_var = node.config.get("item_var", "item")
        max_iterations = node.config.get("max_iterations", 100)
        transform = node.config.get("transform", "item")

        # Resolve the collection
        collection = self._resolve_variable(collection_var, inputs)
        if not isinstance(collection, list):
            try:
                collection = json.loads(str(collection))
                if not isinstance(collection, list):
                    collection = [collection]
            except (json.JSONDecodeError, TypeError):
                collection = []

        results: list[Any] = []

        for i, item in enumerate(collection[:max_iterations]):
            local_vars = {item_var: item, "index": i, **inputs}
            try:
                result = safe_eval(transform, local_vars)
                results.append(result)
            except Exception as e:
                results.append(f"Error at index {i}: {e}")

        return {
            "iterations": len(results),
            "results": results,
            "node_id": node.id,
            "node_name": node.name,
        }

    async def _execute_code_node(
        self,
        node: WorkflowNode,
        inputs: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute a code node in a resource-limited subprocess sandbox."""
        code = node.config.get("code", "")

        # Validate the author's static code BEFORE any substitution
        try:
            tree = ast.parse(code, mode="exec")
            _validate_code_ast(tree)
        except Exception as e:
            return {
                "result": f"Error: {e}",
                "node_id": node.id,
                "node_name": node.name,
            }

        # Render template variables as safe repr() literals (injection-proof)
        rendered_code = self._render_code_template(code, inputs)

        # Re-validate after substitution to catch any unsafe constructs
        try:
            tree = ast.parse(rendered_code, mode="exec")
            _validate_code_ast(tree)
        except Exception as e:
            return {
                "result": f"Error: {e}",
                "node_id": node.id,
                "node_name": node.name,
            }

        timeout = node.config.get("timeout_seconds", 5)
        outcome = await run_code_sandboxed(rendered_code, inputs, timeout_seconds=timeout)
        if not outcome.get("ok"):
            return {
                "result": f"Error: {outcome.get('error', 'Code node failed')}",
                "node_id": node.id,
                "node_name": node.name,
            }

        return {
            "result": outcome.get("result"),
            "node_id": node.id,
            "node_name": node.name,
        }

    async def _execute_simulation_node(
        self,
        node: WorkflowNode,
        inputs: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute a simulation-experiment node via the SimulationHarness.

        Config:
        - tool_name: the (MCP or native) simulation tool to dispatch
        - schema: optional plan schema (sweep/base/objective). When an
          ``llm_mode`` is enabled and the tool schema is available, the
          goal is planned by an LLM sub-agent instead.
        - goal: the natural-language engineering requirement
        - max_rounds: per-experiment retry budget
        - policy: optional ParameterPolicy dict for pre-dispatch allowlist
        - ledger_dir: optional directory for the reproducible JSONL ledger
        - orchestrator_mode: when true, run the full 总指挥 close-loop
          (ScienceSimulationAgent) — select tool, plan, run, aggregate
          review, refine and repeat up to ``plan_rounds``.
        - plan_rounds: max aggregate loop iterations (default 3).
        """
        from app.simulation.harness import HarnessOptions, SimulationHarness
        from app.simulation.review import HarnessReviewer, ParameterPolicy

        tool_name = node.config.get("tool_name", "")
        schema = node.config.get("schema", {})
        if isinstance(schema, str):
            schema = json.loads(schema) if schema.strip() else {}
        max_rounds = int(node.config.get("max_rounds", 8))
        ledger_dir = node.config.get("ledger_dir") or None
        goal = str(inputs.get("goal", node.config.get("goal", "")))
        plan_rounds = int(node.config.get("plan_rounds", 3))
        orchestrator_mode = bool(node.config.get("orchestrator_mode", False))

        registry = self._resolve_registry()
        sandbox = getattr(self.agent_engine, "sandbox", None)
        permission_overlay = getattr(self.agent_engine, "permission_overlay", None)
        capabilities = node.config.get("tool_capabilities")

        from app.core.engine.tool_capabilities import build_workflow_tool_validator
        validator = build_workflow_tool_validator(
            registry,
            sandbox=sandbox,
            permission_overlay=permission_overlay,
            capabilities=capabilities,
        )

        policy = None
        policy_cfg = node.config.get("policy")
        if policy_cfg:
            policy = ParameterPolicy(
                allowed=policy_cfg.get("allowed"),
                ranges=policy_cfg.get("ranges", {}),
                disallowed_values=policy_cfg.get("disallowed_values", {}),
                require=policy_cfg.get("require", []),
            )

        ledger = None
        if ledger_dir:
            from app.simulation.ledger import ExperimentLedger
            ledger = ExperimentLedger(ledger_dir)

        llm_call = None
        if node.config.get("llm_mode") or orchestrator_mode:
            provider = node.config.get("provider", "openai")
            model_id = node.config.get("model_id", "gpt-4")
            import os as _os
            api_key_env = node.config.get("api_key_env", "")
            api_key = _os.environ.get(api_key_env, "") if api_key_env else node.config.get("api_key", "")

            async def _llm_call(prompt: str, system_prompt: str):
                from app.core.engine.session_runner import run_llm_single
                return await run_llm_single(
                    self.agent_engine, provider, model_id, api_key,
                    system_prompt, prompt,
                )

        if orchestrator_mode:
            from app.simulation.orchestrator import (
                OrchestratorOptions,
                ScienceSimulationAgent,
            )

            agent = ScienceSimulationAgent(
                registry,
                options=OrchestratorOptions(
                    max_plan_rounds=plan_rounds,
                    harness_options=HarnessOptions(
                        max_rounds=max_rounds, policy=policy,
                    ),
                    default_tool=tool_name,
                ),
                llm_call=_llm_call,
                ledger=ledger,
                validate_tool_call=validator,
            )
            result = await agent.run(goal)
            return {
                "accepted": result.accepted,
                "rejected": result.rejected,
                "satisfied": result.satisfied,
                "rounds": len(result.rounds),
                "final_report": result.final_report,
                "ledger_path": result.ledger_path,
                "node_id": node.id,
                "node_name": node.name,
            }

        harness = SimulationHarness(
            registry,
            reviewer=HarnessReviewer(),
            options=HarnessOptions(max_rounds=max_rounds, policy=policy),
            ledger=ledger,
            validate_tool_call=validator,
        )

        llm_planner = None
        if node.config.get("llm_mode"):
            tool_def = registry.get_tool(tool_name) if registry else None
            from app.simulation.llm_planner import LLMExperimentPlanner
            llm_planner = LLMExperimentPlanner(
                llm_call=_llm_call,
                tool_name=tool_name,
                tool_def=tool_def,
            )

        result = await harness.run_requirement(goal, tool_name, schema, llm_planner=llm_planner)

        return {
            "accepted": result.accepted,
            "rejected": result.rejected,
            "reports": [r.model_dump() for r in result.reports],
            "ledger_path": result.ledger_path,
            "node_id": node.id,
            "node_name": node.name,
        }

    def _resolve_inputs(
        self,
        node: WorkflowNode,
        workflow: Workflow,
    ) -> dict[str, Any]:
        """Resolve input references from predecessor outputs.

        First merges all predecessor outputs into the resolved dict,
        then applies explicit node.inputs references (which can override).
        """
        resolved: dict[str, Any] = {}

        # Auto-merge predecessor outputs
        predecessors = workflow.get_predecessors(node.id)
        for pred_id in predecessors:
            pred_node = workflow.get_node(pred_id)
            if pred_node and pred_node.output is not None:
                if isinstance(pred_node.output, dict):
                    for k, v in pred_node.output.items():
                        resolved[k] = v
                else:
                    resolved[pred_id] = pred_node.output

        # Apply explicit input references (override auto-merged)
        for key, ref in node.inputs.items():
            # Format: "node_id.output_key" or "node_id"
            if "." in ref:
                node_id, output_key = ref.split(".", 1)
            else:
                node_id = ref
                output_key = None

            pred_node = workflow.get_node(node_id)
            if pred_node and pred_node.output is not None:
                if output_key:
                    if isinstance(pred_node.output, dict):
                        resolved[key] = pred_node.output.get(output_key)
                    else:
                        resolved[key] = pred_node.output
                else:
                    if isinstance(pred_node.output, dict):
                        resolved[key] = pred_node.output.get("result", pred_node.output)
                    else:
                        resolved[key] = pred_node.output

        return resolved

    def _resolve_variable(self, variable: str, inputs: dict[str, Any]) -> Any:
        """Resolve a variable reference like 'node_id.key' from inputs."""
        if not variable:
            return None

        if "." in variable:
            parts = variable.split(".", 1)
            node_output = inputs.get(parts[0], {})
            if isinstance(node_output, dict):
                return node_output.get(parts[1])
            return node_output

        return inputs.get(variable)

    def _render_template(self, template: str, variables: dict[str, Any]) -> str:
        """Simple template rendering: {{variable_name}}."""
        result = template
        for key, value in variables.items():
            placeholder = "{{" + key + "}}"
            result = result.replace(placeholder, str(value) if value is not None else "")
        return result

    def _render_code_template(self, template: str, variables: dict[str, Any]) -> str:
        """Render templates for code nodes using repr() so values become safe
        literals instead of raw text — prevents input values from injecting
        code structure into the executed source."""
        result = template
        for key, value in variables.items():
            placeholder = "{{" + key + "}}"
            result = result.replace(placeholder, repr(value) if value is not None else "None")
        return result

    def _collect_results(self, workflow: Workflow) -> dict[str, Any]:
        """Collect all node outputs."""
        results: dict[str, Any] = {}
        for node in workflow.nodes:
            if node.output is not None:
                results[node.id] = {
                    "name": node.name,
                    "type": node.type.value,
                    "output": node.output,
                    "status": node.status.value,
                }
        return results

    def _get_final_output(self, workflow: Workflow) -> dict[str, Any]:
        """Get the final output from end nodes."""
        end_nodes = [n for n in workflow.nodes if n.type == NodeType.END]
        if not end_nodes:
            # Return last completed node output
            completed = [n for n in workflow.nodes if n.status == NodeStatus.COMPLETED]
            if completed:
                last = completed[-1]
                return {"result": last.output, "node": last.name}
            return {}

        outputs: dict[str, Any] = {}
        for node in end_nodes:
            if node.output is not None:
                outputs[node.name] = node.output
        return outputs



