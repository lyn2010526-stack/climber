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
import re
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
    ast.Call, ast.Constant, ast.Name, ast.Load, ast.Store, ast.Attribute,
    ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Mod, ast.Pow,
    ast.USub, ast.UAdd, ast.Not, ast.And, ast.Or,
    ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE,
    ast.Is, ast.IsNot, ast.In, ast.NotIn,
    ast.List, ast.Tuple, ast.Dict, ast.Subscript, ast.Slice,
    ast.IfExp, ast.Index, ast.FormattedValue, ast.JoinedStr,
    ast.DictComp, ast.ListComp, ast.SetComp, ast.GeneratorExp,
    ast.comprehension,
)


def _is_dangerous_attr(attr: str) -> bool:
    """Reject dunder and private attributes to prevent sandbox escapes.

    Blocks __class__, __bases__, __subclasses__, __globals__, __builtins__,
    __import__, __code__ and any other underscore-prefixed attribute that
    could traverse the Python object graph.
    """
    return attr.startswith("_")


def _validate_ast(node: ast.AST) -> None:
    for child in ast.walk(node):
        if not isinstance(child, _SAFE_NODES):
            raise ValueError(f"Unsafe expression node: {type(child).__name__}")
        if isinstance(child, ast.Attribute) and _is_dangerous_attr(child.attr):
            raise ValueError(f"Access to attribute '{child.attr}' is not allowed")


def safe_eval(expression: str, local_vars: dict[str, Any]) -> Any:
    """Safely evaluate a Python expression using AST validation.

    Note: This is designed for a sandboxed workflow environment where
    only pre-validated AST nodes are permitted. The eval() call is
    restricted to a controlled builtin set and should not be used
    with untrusted input in production.
    """
    try:
        tree = ast.parse(expression, mode="eval")
        _validate_ast(tree)
        return eval(compile(tree, "<workflow>", "eval"), {"__builtins__": _SAFE_EVAL_BUILTINS}, local_vars)
    except Exception:
        raise


def _validate_code_ast(node: ast.AST) -> None:
    allowed_nodes = _SAFE_NODES + (
        ast.Module,
        ast.Assign, ast.AugAssign, ast.AnnAssign,
        ast.For, ast.While, ast.If, ast.Return,
        ast.Break, ast.Continue,
        ast.FunctionDef, ast.AsyncFunctionDef,
        ast.arg, ast.arguments, ast.Return,
        ast.Pass, ast.Assert, ast.Raise,
        ast.Import, ast.ImportFrom,
        ast.Expr, ast.Store, ast.NameConstant,
    )
    for child in ast.walk(node):
        if not isinstance(child, allowed_nodes):
            raise ValueError(f"Unsafe code node: {type(child).__name__}")
        if isinstance(child, ast.Attribute) and _is_dangerous_attr(child.attr):
            raise ValueError(f"Access to attribute '{child.attr}' is not allowed")
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)) and child.name.startswith("_"):
            raise ValueError(f"Private function definition not allowed: {child.name}")
        if isinstance(child, (ast.Import, ast.ImportFrom)) and child.module and child.module not in {"json", "math", "datetime", "re", "collections"}:
            raise ValueError(f"Unsafe import: {child.module}")


def safe_exec(code: str, local_vars: dict[str, Any]) -> dict[str, Any]:
    try:
        tree = ast.parse(code, mode="exec")
        _validate_code_ast(tree)
        exec_globals: dict[str, Any] = {"__builtins__": _SAFE_EVAL_BUILTINS}
        exec(compile(tree, "<workflow>", "exec"), exec_globals, local_vars)
        return local_vars
    except Exception:
        raise

logger = structlog.get_logger()

# Canonical branch labels for conditional edges.
BRANCH_TRUE = "true"
BRANCH_FALSE = "false"
BRANCH_UNCONDITIONAL = ""

_TRUE_LABELS = frozenset({"true", "yes", "y", "1", "on", "pass", "passed", "ok", "success"})
_FALSE_LABELS = frozenset({"false", "no", "n", "0", "off", "fail", "failed", "error", "else"})
_LABEL_TOKENS = re.compile(r"[^a-z0-9]+")


def _normalise_branch_label(raw: Any) -> str:
    """Normalise an edge branch label to ``"true"``, ``"false"`` or ``""``.

    Creators spell the branch label differently: the visual editor emits the
    React Flow handle id, templates use the bare words, and hand-written graphs
    often namespace the handle (``"cond-true"``) or send a real boolean. Any
    unrecognised value is treated as unconditional so an unknown label never
    silently skips a branch.
    """
    if isinstance(raw, bool):
        return BRANCH_TRUE if raw else BRANCH_FALSE
    if raw is None:
        return BRANCH_UNCONDITIONAL

    text = str(raw).strip().lower()
    if not text:
        return BRANCH_UNCONDITIONAL
    if text in _TRUE_LABELS:
        return BRANCH_TRUE
    if text in _FALSE_LABELS:
        return BRANCH_FALSE

    tokens = [token for token in _LABEL_TOKENS.split(text) if token]
    if BRANCH_TRUE in tokens:
        return BRANCH_TRUE
    if BRANCH_FALSE in tokens:
        return BRANCH_FALSE
    return BRANCH_UNCONDITIONAL


def _edge_branch_label(edge: Any) -> str:
    """Read a successor edge's branch label.

    ``WorkflowEdge.condition`` is the single field every creator converges on,
    so only its spelling needs normalising.
    """
    return _normalise_branch_label(getattr(edge, "condition", ""))


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
                    node.status = NodeStatus.SKIPPED
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
                output = self._execute_code_node(node, resolved_inputs)
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

        The branch head is skipped first, then every node that becomes
        unreachable once that head is removed.
        """
        skipped_nodes.add(branch_node_id)
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
        conditional_only: bool = False,
    ) -> bool:
        """Check if target is reachable from source, optionally excluding a node.

        Args:
            source: Node to search from.
            target: Node to search for.
            workflow: The workflow being executed.
            exclude_node: Node that may not be traversed.
            conditional_only: When set, only unconditional edges are followed,
                which answers "is this node still fed by a taken branch?"

        Returns:
            True when target is reachable from source.
        """
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
                if conditional_only and _edge_branch_label(edge) != BRANCH_UNCONDITIONAL:
                    continue
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
        registry = self.tool_registry or ToolRegistry()
        executor = ParallelToolExecutor(registry)
        tool_result = await executor.execute_all([{
            "id": f"wf-{node.id}",
            "function": {
                "name": tool_name,
                "arguments": resolved_tool_inputs,
            },
        }])
        tool_result = tool_result[0]

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
        actual_value = self._resolve_variable(variable, inputs, workflow)

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
        branched = False

        for edge in edges:
            edge_condition = _edge_branch_label(edge)
            if edge_condition == BRANCH_UNCONDITIONAL:
                continue
            branched = True
            if (edge_condition == BRANCH_TRUE and not condition_result) or (
                edge_condition == BRANCH_FALSE and condition_result
            ):
                skip_targets.append(edge.target)

        if branched:
            skip_targets = self._unreachable_targets(skip_targets, node.id, workflow)

        return {
            "condition_result": condition_result,
            "variable": actual_value,
            "operator": operator,
            "expected": value,
            "node_id": node.id,
            "node_name": node.name,
        }, skip_targets

    def _unreachable_targets(
        self,
        skip_targets: list[str],
        condition_node_id: str,
        workflow: Workflow,
    ) -> list[str]:
        """Drop branch heads that stay reachable through a taken branch.

        A node fed by both the taken and the skipped branch still has to run,
        so it must not be skipped. Every other head on a losing branch, plus
        anything only reachable through it, is unreachable once the losing
        branch is cut.

        Args:
            skip_targets: Heads of the non-matching branches.
            condition_node_id: The condition node that branched.
            workflow: The workflow being executed.

        Returns:
            The subset of ``skip_targets`` that is truly unreachable.
        """
        retained: list[str] = []
        for target in skip_targets:
            if self._is_reachable_from(
                condition_node_id,
                target,
                workflow,
                exclude_node=target,
                conditional_only=True,
            ):
                continue
            retained.append(target)
        return retained

    def _evaluate_condition(self, actual: Any, operator: str, expected: str) -> bool:
        """Evaluate a condition."""
        if actual is None:
            actual = ""

        actual_str = str(actual)

        if operator == "equals":
            return actual_str == expected
        elif operator == "not_equals":
            return actual_str != expected
        elif operator == "contains":
            return expected in actual_str
        elif operator == "not_contains":
            return expected not in actual_str
        elif operator == "starts_with":
            return actual_str.startswith(expected)
        elif operator == "ends_with":
            return actual_str.endswith(expected)
        elif operator == "not_empty":
            return bool(actual_str.strip())
        elif operator == "empty":
            return not actual_str.strip()
        elif operator == "greater_than":
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

    def _execute_code_node(
        self,
        node: WorkflowNode,
        inputs: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute a code node with sandboxed Python."""
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

    def _resolve_variable(
        self,
        variable: str,
        inputs: dict[str, Any],
        workflow: Workflow | None = None,
    ) -> Any:
        """Resolve a variable reference like 'node_id.key' from inputs.

        Predecessor outputs are merged flat into ``inputs``, so a bare key such
        as ``"response"`` resolves directly. A qualified reference falls back to
        the named node's own output, which is how the editor and the built-in
        templates spell a condition variable.
        """
        if not variable:
            return None

        if "." in variable:
            node_id, output_key = variable.split(".", 1)
            node_output = inputs.get(node_id)
            if isinstance(node_output, dict):
                return node_output.get(output_key)
            if workflow is not None:
                source_node = workflow.get_node(node_id)
                source_output = source_node.output if source_node is not None else None
                if isinstance(source_output, dict):
                    return source_output.get(output_key)
                if source_output is not None:
                    return source_output
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



