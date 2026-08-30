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
import inspect
import json
import time
from types import SimpleNamespace
from typing import Any

import structlog

from app.core.agent_engine import AgentEngine
from app.core.workflow_recovery import ErrorType, classify_error
from app.models.registry import ModelRegistry
from app.workflow import (
    NodeStatus,
    NodeType,
    Workflow,
    WorkflowEdge,
    WorkflowNode,
    WorkflowResult,
)
from app.workflow.registry import node_registry

_SAFE_EVAL_BUILTINS = {
    "len": len, "str": str, "int": int, "float": float,
    "bool": bool, "list": list, "dict": dict, "range": range,
    "enumerate": enumerate, "abs": abs, "round": round,
    "isinstance": isinstance, "min": min, "max": max,
    "sum": sum, "sorted": sorted, "zip": zip, "map": map,
    "filter": filter, "True": True, "False": False, "None": None,
    "json": json,
}

_SAFE_NODES = (
    ast.Expression, ast.BinOp, ast.UnaryOp, ast.BoolOp, ast.Compare,
    ast.Call, ast.Constant, ast.Name, ast.Load, ast.Attribute,
    ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Mod, ast.Pow,
    ast.USub, ast.UAdd, ast.Not, ast.And, ast.Or,
    ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE,
    ast.Is, ast.IsNot, ast.In, ast.NotIn,
    ast.List, ast.Tuple, ast.Dict, ast.Subscript, ast.Slice,
    ast.IfExp, ast.Index, ast.FormattedValue, ast.JoinedStr,
    ast.DictComp, ast.ListComp, ast.SetComp, ast.GeneratorExp,
    ast.comprehension,
)


def _validate_ast(node: ast.AST) -> None:
    for child in ast.walk(node):
        if not isinstance(child, _SAFE_NODES):
            raise ValueError(f"Unsafe expression node: {type(child).__name__}")
        if isinstance(child, ast.Name) and child.id not in _SAFE_EVAL_BUILTINS and child.id not in {"__builtins__"}:
            pass


def safe_eval(expression: str, local_vars: dict[str, Any]) -> Any:
    """Safely evaluate a Python expression using AST validation.

    Note: This is designed for a sandboxed workflow environment where
    only pre-validated AST nodes are permitted. The eval() call is
    restricted to a controlled builtin set and should not be used
    with untrusted input in production.
    """
    tree = ast.parse(expression, mode="eval")
    _validate_ast(tree)
    return eval(compile(tree, "<workflow>", "eval"), {"__builtins__": _SAFE_EVAL_BUILTINS}, local_vars)  # noqa: S307 - AST-validated sandboxed eval


def _validate_code_ast(node: ast.AST) -> None:
    allowed_nodes = (*_SAFE_NODES, ast.Module, ast.Assign, ast.AugAssign, ast.AnnAssign, ast.For, ast.While, ast.If, ast.Return, ast.Break, ast.Continue, ast.FunctionDef, ast.AsyncFunctionDef, ast.arg, ast.arguments, ast.Return, ast.Pass, ast.Assert, ast.Raise, ast.Import, ast.ImportFrom, ast.Expr, ast.Store, ast.NameConstant)
    for child in ast.walk(node):
        if not isinstance(child, allowed_nodes):
            raise ValueError(f"Unsafe code node: {type(child).__name__}")
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if child.name.startswith("_"):
                raise ValueError(f"Private function definition not allowed: {child.name}")
        if isinstance(child, (ast.Import, ast.ImportFrom)):
            if child.module and child.module not in {"json", "math", "datetime", "re", "collections"}:
                raise ValueError(f"Unsafe import: {child.module}")


def safe_exec(code: str, local_vars: dict[str, Any]) -> dict[str, Any]:
    tree = ast.parse(code, mode="exec")
    _validate_code_ast(tree)
    exec_globals: dict[str, Any] = {"__builtins__": _SAFE_EVAL_BUILTINS}
    exec(compile(tree, "<workflow>", "exec"), exec_globals, local_vars)  # noqa: S102 - sandboxed AST-validated exec
    return local_vars

logger = structlog.get_logger()


class WorkflowEngine:
    """Executes workflow DAGs with full conditional branching and iteration."""

    def __init__(self, engine: AgentEngine, model_registry: ModelRegistry | None = None):
        self.agent_engine = engine
        self.model_registry = model_registry

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

    async def execute_single_node(
        self,
        node: WorkflowNode,
        inputs: dict[str, Any] | None = None,
        user_id: str = "system",
    ) -> dict[str, Any]:
        """Execute one node using the same fail-closed dispatch as a full DAG."""
        started = time.time()
        inputs = inputs or {}
        if node.type == NodeType.START:
            node.output = inputs
            node.status = NodeStatus.COMPLETED
        else:
            start = WorkflowNode(id="__single_input__", type=NodeType.START, name="Input", output=inputs)
            workflow = Workflow(
                name="Single node run",
                nodes=[start, node],
                edges=[WorkflowEdge(source=start.id, target=node.id)],
            )
            await self._execute_node(node, workflow, inputs, user_id, set())
        return {
            "node_id": node.id,
            "status": node.status.value,
            "output": node.output,
            "error": node.error,
            "execution_time_ms": (time.time() - started) * 1000,
        }

    async def _execute_node(
        self,
        node: WorkflowNode,
        workflow: Workflow,
        user_inputs: dict[str, str],
        user_id: str,
        skipped_nodes: set[str],
    ) -> None:
        """Execute a single workflow node with retry and failure strategies."""
        node.status = NodeStatus.RUNNING

        retry_cfg = node.config.get("retry") or {}
        max_retries = int(retry_cfg.get("max_retries", 0))
        base_delay = float(retry_cfg.get("base_delay", 1.0))
        max_delay = float(retry_cfg.get("max_delay", 60.0))

        attempt = 0
        while True:
            try:
                output = await self._dispatch_node(node, workflow, user_inputs, user_id, skipped_nodes)
                node.output = output
                node.status = NodeStatus.COMPLETED
                if attempt:
                    node.error = ""
                return
            except Exception as e:
                node.error = str(e)
                error_type = classify_error(e)
                if error_type != ErrorType.PERMANENT and attempt < max_retries:
                    delay = min(base_delay * (2 ** attempt), max_delay)
                    logger.warning(
                        "Node failed, retrying",
                        node=node.name,
                        attempt=attempt + 1,
                        max_retries=max_retries,
                        error=str(e),
                        delay=delay,
                    )
                    if delay > 0:
                        await asyncio.sleep(delay)
                    attempt += 1
                    continue
                break

        if self._handle_node_failure(node, workflow, skipped_nodes):
            return

        node.status = NodeStatus.FAILED
        logger.error("Node execution failed", node=node.name, error=node.error)

    async def _dispatch_node(
        self,
        node: WorkflowNode,
        workflow: Workflow,
        user_inputs: dict[str, str],
        user_id: str,
        skipped_nodes: set[str],
    ) -> Any:
        """Run one node attempt: resolve inputs and execute by type."""
        resolved_inputs = self._resolve_inputs(node, workflow)

        if node.type == NodeType.LLM:
            return await self._execute_llm_node(node, resolved_inputs, user_id)
        if node.type == NodeType.TOOL:
            return await self._execute_tool_node(
                node,
                resolved_inputs,
                workflow_id=workflow.id,
                user_id=user_id,
            )
        if node.type == NodeType.CONDITION:
            output, skip_targets = self._execute_condition_node(
                node, resolved_inputs, workflow,
            )
            # Mark downstream nodes for skipping
            for target_id in skip_targets:
                self._skip_downstream(target_id, node.id, workflow, skipped_nodes)
            return output
        if node.type == NodeType.ITERATOR:
            return await self._execute_iterator_node(
                node, resolved_inputs, user_id, skipped_nodes,
            )
        if node.type == NodeType.CODE:
            return self._execute_code_node(node, resolved_inputs)
        if node.type in {NodeType.START, NodeType.END}:
            return resolved_inputs
        node_type = node.type.value if hasattr(node.type, "value") else str(node.type)
        executor = node_registry.get_executor(node_type)
        if executor is None:
            raise ValueError(f"Unknown workflow node type: {node_type}")
        output = executor(
            node,
            resolved_inputs,
            {"workflow": workflow, "user_id": user_id, "user_inputs": user_inputs},
        )
        return await output if inspect.isawaitable(output) else output

    def _handle_node_failure(
        self,
        node: WorkflowNode,
        workflow: Workflow,
        skipped_nodes: set[str],
    ) -> bool:
        """Apply the node's on_failure strategy.

        Returns True when the failure was handled (workflow may continue):
        - default_value: degrade to a configured fallback output
        - fail_branch: route to edges marked condition="fail", skip the rest
        """
        strategy = node.config.get("on_failure", "fail")

        if strategy == "default_value":
            node.output = node.config.get("default_value")
            node.status = NodeStatus.COMPLETED
            logger.warning("Node degraded to default value", node=node.name, error=node.error)
            return True

        if strategy == "fail_branch":
            successors = workflow.get_successors(node.id)
            fail_targets = {e.target for e in successors if e.condition == "fail"}
            if fail_targets:
                for edge in successors:
                    if edge.target not in fail_targets:
                        self._skip_downstream(edge.target, node.id, workflow, skipped_nodes)
                node.status = NodeStatus.COMPLETED
                logger.warning("Node routed to fail branch", node=node.name, error=node.error)
                return True

        return False

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

        # Skip the branch node itself when no live alternative path leads to it
        other_preds = [
            p for p in workflow.get_predecessors(branch_node_id)
            if p != condition_node_id and p not in skipped_nodes
        ]
        if not other_preds:
            skipped_nodes.add(branch_node_id)

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
        provider = node.config.get("provider", "openai")
        model_id = node.config.get("model_id", "gpt-4")
        api_key = node.config.get("api_key", "")
        prompt_template = node.config.get("prompt") or str(inputs.get("prompt", ""))
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
        workflow_id: str = "workflow",
        user_id: str = "system",
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
        approval_session = SimpleNamespace(
            session_id=workflow_id,
            user_id=user_id,
            permission_config=self.agent_engine.get_permission_config(),
            _stop_requested=False,
            _pending_approval_count=0,
        )
        executor = ParallelToolExecutor(self.agent_engine.tool_registry, session=approval_session)
        tool_result = await executor.execute_all([{
            "id": f"wf-{node.id}",
            "function": {
                "name": tool_name,
                "arguments": resolved_tool_inputs,
            },
        }])
        tool_result = tool_result[0]
        if not tool_result.success:
            raise RuntimeError(tool_result.error or f"Tool execution failed: {tool_name}")

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
            if edge_condition == "true" and not condition_result:
                skip_targets.append(edge.target)
            elif edge_condition == "false" and condition_result:
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
        try:
            max_iterations = int(node.config.get("max_iterations", 100))
        except (TypeError, ValueError) as exc:
            raise ValueError("iterator max_iterations must be an integer") from exc
        if not 1 <= max_iterations <= 10_000:
            raise ValueError("iterator max_iterations must be between 1 and 10000")
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

    def _execute_code_node(
        self,
        node: WorkflowNode,
        inputs: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute a code node with sandboxed Python."""
        code = node.config.get("code", "")

        # Render template variables in code
        rendered_code = self._render_template(code, inputs)

        # Sandboxed execution — expose both individual vars and "inputs" dict
        local_vars: dict[str, Any] = {"inputs": inputs, **inputs}
        try:
            safe_exec(rendered_code, local_vars)
        except Exception as e:
            return {
                "result": f"Error: {e}",
                "node_id": node.id,
                "node_name": node.name,
            }

        # Extract result
        result = local_vars.get("result", local_vars)

        return {
            "result": result,
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

        # Route typed edge handles, while retaining whole-output merging for legacy edges.
        incoming_edges = [edge for edge in workflow.edges if edge.target == node.id]
        for edge in incoming_edges:
            pred_node = workflow.get_node(edge.source)
            if pred_node and pred_node.output is not None:
                if edge.source_handle and edge.target_handle:
                    if isinstance(pred_node.output, dict) and edge.source_handle in pred_node.output:
                        resolved[edge.target_handle] = pred_node.output[edge.source_handle]
                    else:
                        resolved[edge.target_handle] = pred_node.output
                elif isinstance(pred_node.output, dict):
                    for k, v in pred_node.output.items():
                        resolved[k] = v
                else:
                    resolved[edge.source] = pred_node.output

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

    def _collect_results(self, workflow: Workflow) -> dict[str, Any]:
        """Collect all node outputs."""
        results: dict[str, Any] = {}
        for node in workflow.nodes:
            if node.output is not None:
                results[node.id] = {
                    "name": node.name,
                    "type": node.type.value if hasattr(node.type, "value") else str(node.type),
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
