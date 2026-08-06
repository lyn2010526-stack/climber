"""AST-walking interpreter for safe code execution.

Provides a whitelist-based interpreter that evaluates Python AST nodes directly,
allowing secure execution of user-generated code without eval/exec.

Inspired by HuggingFace smolagents' LocalPythonInterpreter.
"""

from __future__ import annotations

import ast
import operator
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

import structlog

logger = structlog.get_logger()


class ExecutionStatus(str):
    SUCCESS = "success"
    ERROR = "error"
    TIMEOUT = "timeout"
    BLOCKED = "blocked"


@dataclass
class ExecutionResult:
    """Result of code execution."""
    status: str
    output: Any = None
    error: str | None = None
    stdout: list[str] = field(default_factory=list)
    iterations: int = 0


class SafeExecutorError(Exception):
    """Base exception for SafeExecutor errors."""


class BlockedOperationError(SafeExecutorError):
    """Raised when a blocked operation is attempted."""


class IterationLimitError(SafeExecutorError):
    """Raised when iteration limit is exceeded."""


class SafeExecutor:
    """AST-walking interpreter for safe code execution.

    Executes Python code by walking its AST and evaluating only whitelisted
    node types. Dangerous operations (file system, network, imports of
    blocked modules) are prohibited by design.
    """

    ALLOWED_NODES = (
        ast.Module,
        ast.Expression,
        ast.Interactive,
        ast.Suite,
        ast.FunctionDef,
        ast.AsyncFunctionDef,
        ast.ClassDef,
        ast.Return,
        ast.Delete,
        ast.Assign,
        ast.AugAssign,
        ast.AnnAssign,
        ast.For,
        ast.AsyncFor,
        ast.While,
        ast.If,
        ast.With,
        ast.AsyncWith,
        ast.Raise,
        ast.Try,
        ast.Assert,
        ast.Import,
        ast.ImportFrom,
        ast.Global,
        ast.Nonlocal,
        ast.Expr,
        ast.Pass,
        ast.Break,
        ast.Continue,
        ast.BoolOp,
        ast.NamedExpr,
        ast.BinOp,
        ast.UnaryOp,
        ast.Lambda,
        ast.IfExp,  # ternary expression
        ast.Dict,
        ast.Set,
        ast.ListComp,
        ast.SetComp,
        ast.DictComp,
        ast.GeneratorExp,
        ast.Await,
        ast.Yield,
        ast.YieldFrom,
        ast.Compare,
        ast.Call,
        ast.FormattedValue,
        ast.JoinedStr,
        ast.Constant,
        ast.Attribute,
        ast.Subscript,
        ast.Starred,
        ast.Name,
        ast.List,
        ast.Tuple,
        ast.Slice,
        ast.Load,
        ast.Store,
        ast.Del,
        ast.And,
        ast.Or,
        ast.Add,
        ast.Sub,
        ast.Mult,
        ast.MatMult,
        ast.Div,
        ast.Mod,
        ast.Pow,
        ast.LShift,
        ast.RShift,
        ast.BitOr,
        ast.BitXor,
        ast.BitAnd,
        ast.FloorDiv,
        ast.Invert,
        ast.Not,
        ast.UAdd,
        ast.USub,
        ast.Eq,
        ast.NotEq,
        ast.Lt,
        ast.LtE,
        ast.Gt,
        ast.GtE,
        ast.Is,
        ast.IsNot,
        ast.In,
        ast.NotIn,
        ast.comprehension,
        ast.ExceptHandler,
        ast.arguments,
        ast.arg,
        ast.keyword,
        ast.alias,
        ast.withitem,
        ast.Match,
        ast.match_case,
        ast.MatchValue,
        ast.MatchSingleton,
        ast.MatchSequence,
        ast.MatchMapping,
        ast.MatchClass,
        ast.MatchStar,
        ast.MatchAs,
        ast.MatchOr,
    )

    BLOCKED_MODULES = frozenset({
        "os", "sys", "subprocess", "socket", "shutil",
        "pathlib", "importlib", "ctypes", "multiprocessing",
        "signal", "pty", "fcntl", "resource", "pickle",
        "marshal", "shelve", "dbm", "sqlite3", "http",
        "urllib", "ftplib", "smtplib", "telnetlib",
        "xmlrpc", "wsgiref", "socketserver",
    })

    BLOCKED_FUNCTIONS = frozenset({
        "eval", "exec", "compile", "__import__",
        "globals", "locals", "vars", "dir",
        "getattr", "setattr", "delattr",
        "hasattr", "classmethod", "staticmethod",
        "property", "super", "type",
        "open", "print" if False else "",
    }) - {""}

    BLOCKED_DUNDERS = frozenset({
        "__dict__", "__class__", "__bases__", "__subclasses__",
        "__init_subclass__", "__setattr__", "__delattr__",
        "__getattribute__", "__mro__", "__code__", "__globals__",
        "__closure__", "__defaults__", "__kwdefaults__",
        "__module__", "__qualname__", "__annotations__",
        "__loader__", "__spec__", "__package__", "__path__",
        "__file__", "__builtins__", "__import__",
    })

    BINARY_OPERATORS = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.FloorDiv: operator.floordiv,
        ast.Mod: operator.mod,
        ast.Pow: operator.pow,
        ast.LShift: operator.lshift,
        ast.RShift: operator.rshift,
        ast.BitOr: operator.or_,
        ast.BitXor: operator.xor,
        ast.BitAnd: operator.and_,
        ast.MatMult: operator.matmul,
    }

    UNARY_OPERATORS = {
        ast.Invert: operator.invert,
        ast.Not: operator.not_,
        ast.UAdd: operator.pos,
        ast.USub: operator.neg,
    }

    COMPARE_OPERATORS = {
        ast.Eq: operator.eq,
        ast.NotEq: operator.ne,
        ast.Lt: operator.lt,
        ast.LtE: operator.le,
        ast.Gt: operator.gt,
        ast.GtE: operator.ge,
        ast.Is: operator.is_,
        ast.IsNot: operator.is_not,
        ast.In: lambda a, b: a in b,
        ast.NotIn: lambda a, b: a not in b,
    }

    def __init__(
        self,
        tools: dict[str, Callable] | None = None,
        max_iterations: int = 1000,
        max_depth: int = 50,
    ):
        self.tools = tools or {}
        self.max_iterations = max_iterations
        self.max_depth = max_depth
        self.state: dict[str, Any] = {}
        self._stdout: list[str] = []
        self._iteration_count = 0
        self._depth = 0

    def execute(self, code: str) -> ExecutionResult:
        """Execute code string safely and return result."""
        self._stdout = []
        self._iteration_count = 0

        try:
            tree = ast.parse(code, mode="exec")
        except SyntaxError as e:
            return ExecutionResult(
                status=ExecutionStatus.ERROR,
                error=f"SyntaxError: {e}",
            )

        try:
            result = self._eval_node(tree)
            return ExecutionResult(
                status=ExecutionStatus.SUCCESS,
                output=result,
                stdout=list(self._stdout),
                iterations=self._iteration_count,
            )
        except BlockedOperationError as e:
            logger.warning("executor.blocked_operation", error=str(e))
            return ExecutionResult(
                status=ExecutionStatus.BLOCKED,
                error=str(e),
                stdout=list(self._stdout),
                iterations=self._iteration_count,
            )
        except IterationLimitError as e:
            logger.warning("executor.iteration_limit", error=str(e))
            return ExecutionResult(
                status=ExecutionStatus.TIMEOUT,
                error=str(e),
                stdout=list(self._stdout),
                iterations=self._iteration_count,
            )
        except Exception as e:
            logger.error("executor.execution_error", error=str(e))
            return ExecutionResult(
                status=ExecutionStatus.ERROR,
                error=f"{type(e).__name__}: {e}",
                stdout=list(self._stdout),
                iterations=self._iteration_count,
            )

    def _check_iteration(self) -> None:
        """Enforce iteration limit."""
        self._iteration_count += 1
        if self._iteration_count > self.max_iterations:
            raise IterationLimitError(
                f"Exceeded max iterations ({self.max_iterations})"
            )

    def _eval_node(self, node: ast.AST) -> Any:
        """Recursively evaluate an AST node."""
        self._check_iteration()
        self._depth += 1

        if self._depth > self.max_depth:
            self._depth -= 1
            raise SafeExecutorError(f"Exceeded max depth ({self.max_depth})")

        try:
            return self._eval_node_impl(node)
        finally:
            self._depth -= 1

    def _eval_node_impl(self, node: ast.AST) -> Any:
        """Dispatch to the appropriate handler for each node type."""

        if isinstance(node, ast.Module):
            return self._eval_module(node)

        if isinstance(node, ast.Expression):
            return self._eval_node(node.body)

        if isinstance(node, ast.Interactive):
            return self._eval_module(node)

        if isinstance(node, ast.Suite):
            return self._eval_body(node.body)

        if isinstance(node, ast.Expr):
            return self._eval_node(node.value)

        if isinstance(node, ast.FunctionDef):
            return self._eval_function_def(node)

        if isinstance(node, ast.AsyncFunctionDef):
            raise BlockedOperationError("Async functions are not allowed")

        if isinstance(node, ast.Return):
            value = self._eval_node(node.value) if node.value else None
            raise _ReturnSignal(value)

        if isinstance(node, ast.Delete):
            return self._eval_delete(node)

        if isinstance(node, ast.Assign):
            return self._eval_assign(node)

        if isinstance(node, ast.AugAssign):
            return self._eval_aug_assign(node)

        if isinstance(node, ast.AnnAssign):
            return self._eval_ann_assign(node)

        if isinstance(node, ast.For):
            return self._eval_for(node)

        if isinstance(node, ast.AsyncFor):
            raise BlockedOperationError("Async for is not allowed")

        if isinstance(node, ast.While):
            return self._eval_while(node)

        if isinstance(node, ast.If):
            return self._eval_if(node)

        if isinstance(node, ast.With):
            return self._eval_with(node)

        if isinstance(node, ast.AsyncWith):
            raise BlockedOperationError("Async with is not allowed")

        if isinstance(node, ast.Raise):
            exc = self._eval_node(node.exc) if node.exc else None
            cause = self._eval_node(node.cause) if node.cause else None
            if cause is not None:
                raise exc from cause
            raise exc

        if isinstance(node, ast.Try):
            return self._eval_try(node)

        if isinstance(node, ast.Assert):
            test = self._eval_node(node.test)
            if not test:
                msg = self._eval_node(node.msg) if node.msg else ""
                raise AssertionError(msg)
            return None

        if isinstance(node, ast.Import):
            return self._eval_import(node)

        if isinstance(node, ast.ImportFrom):
            return self._eval_import_from(node)

        if isinstance(node, ast.Global):
            pass
            return None

        if isinstance(node, ast.Nonlocal):
            raise BlockedOperationError("nonlocal is not allowed")

        if isinstance(node, ast.Pass):
            return None

        if isinstance(node, ast.Break):
            raise _BreakSignal()

        if isinstance(node, ast.Continue):
            raise _ContinueSignal()

        if isinstance(node, ast.Name):
            return self._eval_name(node)

        if isinstance(node, ast.Constant):
            return node.value

        if isinstance(node, ast.List):
            return [self._eval_node(elt) for elt in node.elts]

        if isinstance(node, ast.Tuple):
            return tuple(self._eval_node(elt) for elt in node.elts)

        if isinstance(node, ast.Set):
            return {self._eval_node(elt) for elt in node.elts}

        if isinstance(node, ast.Dict):
            return {
                self._eval_node(k): self._eval_node(v)
                for k, v in zip(node.keys, node.values, strict=True)
            }

        if isinstance(node, ast.BinOp):
            left = self._eval_node(node.left)
            right = self._eval_node(node.right)
            op_type = type(node.op)
            handler = self.BINARY_OPERATORS.get(op_type)
            if handler is None:
                raise BlockedOperationError(f"Binary operator {op_type.__name__} not allowed")
            return handler(left, right)

        if isinstance(node, ast.UnaryOp):
            operand = self._eval_node(node.operand)
            op_type = type(node.op)
            handler = self.UNARY_OPERATORS.get(op_type)
            if handler is None:
                raise BlockedOperationError(f"Unary operator {op_type.__name__} not allowed")
            return handler(operand)

        if isinstance(node, ast.BoolOp):
            return self._eval_bool_op(node)

        if isinstance(node, ast.Compare):
            return self._eval_compare(node)

        if isinstance(node, ast.IfExp):
            test = self._eval_node(node.test)
            if test:
                return self._eval_node(node.body)
            return self._eval_node(node.orelse)

        if isinstance(node, ast.Call):
            return self._eval_call(node)

        if isinstance(node, ast.Attribute):
            return self._eval_attribute(node)

        if isinstance(node, ast.Subscript):
            return self._eval_subscript(node)

        if isinstance(node, ast.Slice):
            lower = self._eval_node(node.lower) if node.lower else None
            upper = self._eval_node(node.upper) if node.upper else None
            step = self._eval_node(node.step) if node.step else None
            return slice(lower, upper, step)

        if isinstance(node, ast.ListComp):
            return self._eval_list_comp(node)

        if isinstance(node, ast.SetComp):
            return self._eval_set_comp(node)

        if isinstance(node, ast.DictComp):
            return self._eval_dict_comp(node)

        if isinstance(node, ast.GeneratorExp):
            return self._eval_generator_exp(node)

        if isinstance(node, ast.Lambda):
            return self._eval_lambda(node)

        if isinstance(node, ast.FormattedValue):
            return self._eval_node(node.value)

        if isinstance(node, ast.JoinedStr):
            parts = [self._eval_node(v) for v in node.values]
            return "".join(str(p) for p in parts)

        if isinstance(node, ast.Starred):
            return self._eval_node(node.value)

        if isinstance(node, ast.NamedExpr):
            value = self._eval_node(node.value)
            self.state[node.target.id] = value
            return value

        if isinstance(node, ast.ClassDef):
            return self._eval_class_def(node)

        if isinstance(node, ast.Yield):
            raise BlockedOperationError("yield is not allowed")

        if isinstance(node, ast.YieldFrom):
            raise BlockedOperationError("yield from is not allowed")

        if isinstance(node, ast.Await):
            raise BlockedOperationError("await is not allowed")

        if isinstance(node, ast.Match):
            raise BlockedOperationError("match statements are not allowed")

        raise BlockedOperationError(
            f"AST node type {type(node).__name__} is not allowed"
        )

    def _eval_module(self, node: ast.Module | ast.Interactive) -> Any:
        """Evaluate a module body."""
        result = None
        for stmt in node.body:
            result = self._eval_node(stmt)
        return result

    def _eval_body(self, body: list[ast.stmt]) -> Any:
        """Evaluate a list of statements."""
        result = None
        for stmt in body:
            result = self._eval_node(stmt)
        return result

    def _eval_name(self, node: ast.Name) -> Any:
        """Evaluate a name reference."""
        name = node.id
        if name in self.state:
            return self.state[name]
        if name in self.tools:
            return self.tools[name]
        if name in __builtins__:
            builtin = __builtins__[name] if isinstance(__builtins__, dict) else getattr(__builtins__, name, None)
            if name in self.BLOCKED_FUNCTIONS:
                raise BlockedOperationError(f"Built-in function '{name}' is blocked")
            if builtin is not None:
                return builtin
        raise NameError(f"name '{name}' is not defined")

    def _eval_assign(self, node: ast.Assign) -> Any:
        """Evaluate an assignment statement."""
        value = self._eval_node(node.value)
        for target in node.targets:
            self._assign_target(target, value)
        return value

    def _eval_aug_assign(self, node: ast.AugAssign) -> Any:
        """Evaluate augmented assignment (+=, -=, etc.)."""
        current = self._eval_node(node.target)
        value = self._eval_node(node.value)
        op_type = type(node.op)
        handler = self.BINARY_OPERATORS.get(op_type)
        if handler is None:
            raise BlockedOperationError(f"Augmented assign {op_type.__name__} not allowed")
        result = handler(current, value)
        self._assign_target(node.target, result)
        return result

    def _eval_ann_assign(self, node: ast.AnnAssign) -> Any:
        """Evaluate annotated assignment."""
        if node.value is not None:
            value = self._eval_node(node.value)
            self._assign_target(node.target, value)
            return value
        return None

    def _assign_target(self, target: ast.expr, value: Any) -> None:
        """Assign value to an assignment target."""
        if isinstance(target, ast.Name):
            self.state[target.id] = value
        elif isinstance(target, (ast.Tuple, ast.List)):
            if not hasattr(value, "__iter__"):
                raise TypeError(f"Cannot unpack non-iterable: {type(value).__name__}")
            items = list(value)
            if len(items) != len(target.elts):
                raise ValueError(
                    f"Expected {len(target.elts)} values, got {len(items)}"
                )
            for elt, val in zip(target.elts, items, strict=True):
                self._assign_target(elt, val)
        elif isinstance(target, ast.Subscript):
            obj = self._eval_node(target.value)
            key = self._eval_node(target.slice)
            obj[key] = value
        elif isinstance(target, ast.Attribute):
            raise BlockedOperationError("Cannot assign to attribute")
        elif isinstance(target, ast.Starred):
            self._assign_target(target.value, value)
        else:
            raise BlockedOperationError(
                f"Cannot assign to {type(target).__name__}"
            )

    def _eval_if(self, node: ast.If) -> Any:
        """Evaluate an if statement."""
        test = self._eval_node(node.test)
        if test:
            return self._eval_body(node.body)
        return self._eval_body(node.orelse)

    def _eval_for(self, node: ast.For) -> Any:
        """Evaluate a for loop."""
        iterable = self._eval_node(node.iter)
        result = None
        for item in iterable:
            self._assign_target(node.target, item)
            try:
                result = self._eval_body(node.body)
            except _ContinueSignal:
                continue
            except _BreakSignal:
                break
        else:
            result = self._eval_body(node.orelse)
        return result

    def _eval_while(self, node: ast.While) -> Any:
        """Evaluate a while loop."""
        result = None
        while self._eval_node(node.test):
            try:
                result = self._eval_body(node.body)
            except _ContinueSignal:
                continue
            except _BreakSignal:
                break
        else:
            result = self._eval_body(node.orelse)
        return result

    def _eval_with(self, node: ast.With) -> Any:
        """Evaluate a with statement."""
        for item in node.items:
            ctx_expr = self._eval_node(item.context_expr)
            if item.optional_vars:
                self._assign_target(item.optional_vars, ctx_expr)
        return self._eval_body(node.body)

    def _eval_try(self, node: ast.Try) -> Any:
        """Evaluate a try/except block."""
        try:
            return self._eval_body(node.body)
        except Exception as exc:
            for handler in node.handlers:
                if handler.type is None:
                    self.state[handler.name] = exc if handler.name else None
                    return self._eval_body(handler.body)
                exc_type = self._eval_node(handler.type)
                if isinstance(exc, exc_type):
                    if handler.name:
                        self.state[handler.name] = exc
                    return self._eval_body(handler.body)
            raise
        finally:
            if node.finalbody:
                self._eval_body(node.finalbody)

    def _eval_function_def(self, node: ast.FunctionDef) -> _Function:
        """Define a function."""
        func = _Function(node, self)
        self.state[node.name] = func
        return func

    def _eval_lambda(self, node: ast.Lambda) -> _Function:
        """Create a lambda function."""
        return _Lambda(node, self)

    def _eval_call(self, node: ast.Call) -> Any:
        """Evaluate a function call."""
        func = self._eval_node(node.func)

        args = [self._eval_node(arg) for arg in node.args]
        kwargs = {kw.arg: self._eval_node(kw.value) for kw in node.keywords if kw.arg}
        if any(kw.arg is None for kw in node.keywords):
            dict_val = self._eval_node(
                next(kw.value for kw in node.keywords if kw.arg is None)
            )
            kwargs.update(dict_val)

        return func(*args, **kwargs)

    def _eval_attribute(self, node: ast.Attribute) -> Any:
        """Evaluate an attribute access."""
        obj = self._eval_node(node.value)
        attr = node.attr

        if attr in self.BLOCKED_DUNDERS:
            raise BlockedOperationError(f"Access to '{attr}' is blocked")

        return getattr(obj, attr)

    def _eval_subscript(self, node: ast.Subscript) -> Any:
        """Evaluate a subscript access."""
        obj = self._eval_node(node.value)
        key = self._eval_node(node.slice)
        return obj[key]

    def _eval_bool_op(self, node: ast.BoolOp) -> Any:
        """Evaluate a boolean operation (and, or)."""
        if isinstance(node.op, ast.And):
            result = True
            for value in node.values:
                result = self._eval_node(value)
                if not result:
                    return result
            return result

        if isinstance(node.op, ast.Or):
            result = False
            for value in node.values:
                result = self._eval_node(value)
                if result:
                    return result
            return result

        raise BlockedOperationError(f"BoolOp {type(node.op).__name__} not supported")

    def _eval_compare(self, node: ast.Compare) -> bool:
        """Evaluate a comparison expression."""
        left = self._eval_node(node.left)
        for op, comparator in zip(node.ops, node.comparators, strict=True):
            right = self._eval_node(comparator)
            op_type = type(op)
            handler = self.COMPARE_OPERATORS.get(op_type)
            if handler is None:
                raise BlockedOperationError(f"Compare {op_type.__name__} not allowed")
            if not handler(left, right):
                return False
            left = right
        return True

    def _eval_import(self, node: ast.Import) -> Any:
        """Evaluate import statement."""
        for alias in node.names:
            top = alias.name.split(".")[0]
            if top in self.BLOCKED_MODULES:
                raise BlockedOperationError(
                    f"Import of module '{alias.name}' is blocked"
                )
        raise BlockedOperationError("import statements are not allowed")

    def _eval_import_from(self, node: ast.ImportFrom) -> Any:
        """Evaluate from-import statement."""
        if node.module:
            top = node.module.split(".")[0]
            if top in self.BLOCKED_MODULES:
                raise BlockedOperationError(
                    f"Import from module '{node.module}' is blocked"
                )
        raise BlockedOperationError("import statements are not allowed")

    def _eval_delete(self, node: ast.Delete) -> None:
        """Evaluate a delete statement."""
        for target in node.targets:
            if isinstance(target, ast.Name):
                if target.id in self.state:
                    del self.state[target.id]
                else:
                    raise NameError(f"name '{target.id}' is not defined")
            elif isinstance(target, ast.Subscript):
                obj = self._eval_node(target.value)
                key = self._eval_node(target.slice)
                del obj[key]
            elif isinstance(target, ast.Attribute):
                obj = self._eval_node(target.value)
                delattr(obj, target.attr)
            else:
                raise BlockedOperationError(f"Cannot delete {type(target).__name__}")

    def _eval_class_def(self, node: ast.ClassDef) -> _ClassDef:
        """Define a class."""
        return _ClassDef(node, self)

    def _eval_list_comp(self, node: ast.ListComp) -> list:
        """Evaluate a list comprehension."""
        return list(self._eval_comprehension(node.generators, 0, node.elt))

    def _eval_set_comp(self, node: ast.SetComp) -> set:
        """Evaluate a set comprehension."""
        return set(self._eval_comprehension(node.generators, 0, node.elt))

    def _eval_dict_comp(self, node: ast.DictComp) -> dict:
        """Evaluate a dict comprehension."""
        result = {}
        for key, value in self._eval_comprehension(node.generators, 0, (node.key, node.value)):
            result[key] = value
        return result

    def _eval_generator_exp(self, node: ast.GeneratorExp):
        """Evaluate a generator expression."""
        yield from self._eval_comprehension(node.generators, 0, node.elt)

    def _eval_comprehension(
        self, generators: list[ast.comprehension], gen_index: int, element: ast.expr | tuple
    ):
        """Recursively evaluate comprehension generators."""
        if gen_index >= len(generators):
            if isinstance(element, tuple):
                key = self._eval_node(element[0])
                value = self._eval_node(element[1])
                yield (key, value)
            else:
                yield self._eval_node(element)
            return

        gen = generators[gen_index]
        iterable = self._eval_node(gen.iter)

        for item in iterable:
            self._assign_target(gen.target, item)
            conditions_pass = True
            for if_clause in gen.ifs:
                if not self._eval_node(if_clause):
                    conditions_pass = False
                    break
            if conditions_pass:
                yield from self._eval_comprehension(generators, gen_index + 1, element)


class _ReturnSignal(Exception):
    """Control-flow signal for function returns."""

    def __init__(self, value: Any):
        self.value = value


class _BreakSignal(Exception):
    """Control-flow signal for break."""


class _ContinueSignal(Exception):
    """Control-flow signal for continue."""


class _Function:
    """A user-defined function."""

    def __init__(self, node: ast.FunctionDef, executor: SafeExecutor):
        self.node = node
        self.executor = executor
        self.name = node.name

    def __call__(self, *args, **kwargs) -> Any:
        """Call the function with given arguments."""
        func = self.node
        params = func.args

        # Bind positional args
        num_pos = len(params.args)
        if len(args) > num_pos and params.vararg is None:
            raise TypeError(
                f"{self.name}() takes {num_pos} positional arguments "
                f"but {len(args)} were given"
            )

        local_state: dict[str, Any] = {}

        # Regular positional args
        for i, param in enumerate(params.args):
            if i < len(args):
                local_state[param.arg] = args[i]
            elif param.arg in kwargs:
                local_state[param.arg] = kwargs[param.arg]
            elif params.defaults and i >= num_pos - len(params.defaults):
                default_idx = i - (num_pos - len(params.defaults))
                local_state[param.arg] = self.executor._eval_node(
                    params.defaults[default_idx]
                )
            else:
                raise TypeError(f"{self.name}() missing argument: '{param.arg}'")

        # *args
        if params.vararg:
            extra_args = args[num_pos:]
            local_state[params.vararg.arg] = extra_args

        # **kwargs
        if params.kwarg:
            extra_kwargs = {
                k: v for k, v in kwargs.items()
                if k not in local_state
            }
            local_state[params.kwarg.arg] = extra_kwargs

        # kwonly args
        for kwonly, default in zip(params.kwonlyargs, params.kw_defaults, strict=True):
            if kwonly.arg in kwargs:
                local_state[kwonly.arg] = kwargs[kwonly.arg]
            elif default is not None:
                local_state[kwonly.arg] = self.executor._eval_node(default)
            else:
                raise TypeError(f"{self.name}() missing keyword argument: '{kwonly.arg}'")

        # Execute function body with isolated scope
        saved_state = self.executor.state
        self.executor.state = {**self.executor.state, **local_state}
        try:
            for stmt in func.body:
                try:
                    self.executor._eval_node(stmt)
                except _ReturnSignal as ret:
                    return ret.value
            return None
        finally:
            self.executor.state = saved_state


class _Lambda:
    """A user-defined lambda function."""

    def __init__(self, node: ast.Lambda, executor: SafeExecutor):
        self.node = node
        self.executor = executor

    def __call__(self, *args, **kwargs) -> Any:
        """Call the lambda with given arguments."""
        params = self.node.args
        local_state: dict[str, Any] = {}

        for i, param in enumerate(params.args):
            if i < len(args):
                local_state[param.arg] = args[i]
            elif param.arg in kwargs:
                local_state[param.arg] = kwargs[param.arg]
            elif params.defaults and i >= len(params.args) - len(params.defaults):
                default_idx = i - (len(params.args) - len(params.defaults))
                local_state[param.arg] = self.executor._eval_node(
                    params.defaults[default_idx]
                )
            else:
                raise TypeError(f"lambda missing argument: '{param.arg}'")

        if params.vararg:
            local_state[params.vararg.arg] = args[len(params.args):]

        if params.kwarg:
            local_state[params.kwarg.arg] = {
                k: v for k, v in kwargs.items() if k not in local_state
            }

        saved_state = self.executor.state
        self.executor.state = {**self.executor.state, **local_state}
        try:
            return self.executor._eval_node(self.node.body)
        finally:
            self.executor.state = saved_state


class _ClassDef:
    """A simple class definition."""

    def __init__(self, node: ast.ClassDef, executor: SafeExecutor):
        self.node = node
        self.executor = executor

    def __call__(self, *args, **kwargs) -> Any:
        """Instantiate the class."""
        methods = {}
        for item in self.node.body:
            if isinstance(item, ast.FunctionDef):
                methods[item.name] = _InstanceMethod(item, self.executor)
        return _Instance(methods, args, kwargs)


class _InstanceMethod:
    """A method bound to a class instance."""

    def __init__(self, node: ast.FunctionDef, executor: SafeExecutor):
        self.node = node
        self.executor = executor

    def __get__(self, instance, owner):
        if instance is None:
            return self
        return _BoundMethod(self.node, self.executor, instance)


class _BoundMethod:
    """A method bound to an instance."""

    def __init__(self, node: ast.FunctionDef, executor: SafeExecutor, instance: Any):
        self.node = node
        self.executor = executor
        self.instance = instance

    def __call__(self, *args, **kwargs):
        func = self.node
        params = func.args
        local_state: dict[str, Any] = {"self": self.instance}

        for i, param in enumerate(params.args):
            if param.arg == "self":
                continue
            if i - 1 < len(args):
                local_state[param.arg] = args[i - 1]
            elif param.arg in kwargs:
                local_state[param.arg] = kwargs[param.arg]
            else:
                raise TypeError(f"missing argument: '{param.arg}'")

        saved_state = self.executor.state
        self.executor.state = {**self.executor.state, **local_state}
        try:
            for stmt in func.body:
                try:
                    self.executor._eval_node(stmt)
                except _ReturnSignal as ret:
                    return ret.value
            return None
        finally:
            self.executor.state = saved_state


class _Instance:
    """An instance of a user-defined class."""

    def __init__(self, methods: dict, args: tuple, kwargs: dict):
        self.__dict__["_methods"] = methods
        self.__dict__["_args"] = args
        self.__dict__["_kwargs"] = kwargs

        if "__init__" in methods:
            self.__dict__["__init__"] = methods["__init__"].__get__(self, type(self))

    def __getattr__(self, name):
        if name in self._methods:
            return self._methods[name].__get__(self, type(self))
        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")

    def __setattr__(self, name, value):
        self.__dict__[name] = value
