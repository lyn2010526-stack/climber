"""Static AST validation + restricted eval/exec primitives for workflow nodes.

Kept dependency-free (stdlib only) so the subprocess sandbox can import it
without booting the full agent stack. ``app.workflow.engine`` re-exports
``safe_eval`` and ``safe_exec`` for backwards compatibility.
"""

from __future__ import annotations

import ast
import json
import math
from typing import Any

_SAFE_EVAL_BUILTINS = {
    "len": len, "str": str, "int": int, "float": float,
    "bool": bool, "list": list, "dict": dict, "range": range,
    "enumerate": enumerate, "abs": abs, "round": round,
    "isinstance": isinstance, "min": min, "max": max,
    "sum": sum, "sorted": sorted, "zip": zip, "map": map,
    "filter": filter, "True": True, "False": False, "None": None,
    "json": json,
    "sqrt": math.sqrt, "pow": pow,
    "__import__": None,
}

_ALLOWED_IMPORT_MODULES = frozenset({"json", "math", "datetime", "re", "collections", "itertools", "statistics", "string"})


def _gated_import(name: str, globals: Any = None, locals: Any = None, fromlist: tuple[str, ...] = (), level: int = 0) -> Any:
    """Runtime __import__ that only allows modules from the static allowlist."""
    if level != 0:
        raise ImportError(f"Relative imports are not allowed: {'.' * level}{name}")
    root = name.split(".")[0]
    if root not in _ALLOWED_IMPORT_MODULES:
        raise ImportError(f"Unsafe import: {root}")
    return __import__(name, globals, locals, fromlist, level)


_SAFE_EVAL_BUILTINS["__import__"] = _gated_import

_SAFE_NODES = (
    ast.Expression, ast.BinOp, ast.UnaryOp, ast.BoolOp, ast.Compare,
    ast.Call, ast.Constant, ast.Name, ast.Load, ast.Store, ast.Attribute,
    ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Mod, ast.Pow,
    ast.USub, ast.UAdd, ast.Not, ast.And, ast.Or,
    ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE,
    ast.Is, ast.IsNot, ast.In, ast.NotIn,
    ast.List, ast.Tuple, ast.Dict, ast.Subscript, ast.Slice, ast.Set,
    ast.IfExp, ast.Index, ast.FormattedValue, ast.JoinedStr,
    ast.DictComp, ast.ListComp, ast.SetComp, ast.GeneratorExp,
    ast.comprehension,
)

_SAFE_CODE_NODES = _SAFE_NODES + (
    ast.Module,
    ast.Assign, ast.AugAssign, ast.AnnAssign,
    ast.For, ast.While, ast.If, ast.Return,
    ast.Break, ast.Continue,
    ast.FunctionDef, ast.AsyncFunctionDef,
    ast.arg, ast.arguments, ast.alias,
    ast.Pass, ast.Assert, ast.Raise,
    ast.Import, ast.ImportFrom,
    ast.Expr, ast.NameConstant,
)


def is_dangerous_attr(attr: str) -> bool:
    """Reject dunder and private attributes to prevent sandbox escapes."""
    return attr.startswith("_")


def validate_expression_ast(tree: ast.AST) -> None:
    for child in ast.walk(tree):
        if not isinstance(child, _SAFE_NODES):
            raise ValueError(f"Unsafe expression node: {type(child).__name__}")
        if isinstance(child, ast.Attribute) and is_dangerous_attr(child.attr):
            raise ValueError(f"Access to attribute '{child.attr}' is not allowed")
        if isinstance(child, ast.BinOp) and isinstance(child.op, ast.Pow):
            _reject_huge_pow(child)


def validate_code_ast(tree: ast.AST) -> None:
    for child in ast.walk(tree):
        if not isinstance(child, _SAFE_CODE_NODES):
            raise ValueError(f"Unsafe code node: {type(child).__name__}")
        if isinstance(child, ast.Attribute) and is_dangerous_attr(child.attr):
            raise ValueError(f"Access to attribute '{child.attr}' is not allowed")
        if isinstance(child, ast.BinOp) and isinstance(child.op, ast.Pow):
            _reject_huge_pow(child)
    for child in ast.walk(tree):
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)) and child.name.startswith("_"):
            raise ValueError(f"Private function definition not allowed: {child.name}")
        if isinstance(child, (ast.Import, ast.ImportFrom)):
            modules = []
            if isinstance(child, ast.Import):
                modules = [alias.name.split(".")[0] for alias in child.names]
            elif child.module:
                modules = [child.module.split(".")[0]]
            for module in modules:
                if module not in _ALLOWED_IMPORT_MODULES:
                    raise ValueError(f"Unsafe import: {module}")


def _reject_huge_pow(node: ast.BinOp) -> None:
    """Reject obviously explosive power expressions on literal operands."""
    right = node.right
    if isinstance(right, ast.UnaryOp) and isinstance(right.op, ast.UAdd):
        right = right.operand
    if isinstance(right, ast.Constant) and isinstance(right.value, int) and right.value > 64:
        left = node.left
        if isinstance(left, ast.Constant) and isinstance(left.value, (int, float)) and abs(left.value) > 1:
            raise ValueError("Power expression with large literal exponent is not allowed")


def safe_eval(expression: str, local_vars: dict[str, Any]) -> Any:
    """Safely evaluate a Python expression using AST validation."""
    tree = ast.parse(expression, mode="eval")
    validate_expression_ast(tree)
    return eval(compile(tree, "<workflow>", "eval"), {"__builtins__": _SAFE_EVAL_BUILTINS}, local_vars)


def safe_exec(code: str, local_vars: dict[str, Any]) -> dict[str, Any]:
    """Safely execute workflow code using AST validation and restricted builtins."""
    tree = ast.parse(code, mode="exec")
    validate_code_ast(tree)
    exec_globals: dict[str, Any] = {"__builtins__": _SAFE_EVAL_BUILTINS}
    exec(compile(tree, "<workflow>", "exec"), exec_globals, local_vars)
    return local_vars
