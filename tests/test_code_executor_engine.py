"""Tests for app.engine.code_executor module."""

from __future__ import annotations

import ast
import pytest

from app.engine.code_executor import (
    BlockedOperationError,
    ExecutionResult,
    ExecutionStatus,
    IterationLimitError,
    SafeExecutor,
)


class TestExecutionStatus:
    """Tests for ExecutionStatus."""

    def test_status_values(self):
        assert ExecutionStatus.SUCCESS == "success"
        assert ExecutionStatus.ERROR == "error"
        assert ExecutionStatus.TIMEOUT == "timeout"
        assert ExecutionStatus.BLOCKED == "blocked"


class TestExecutionResult:
    """Tests for ExecutionResult."""

    def test_creation(self):
        result = ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            output=42,
            stdout=["hello"],
            iterations=5,
        )
        assert result.status == ExecutionStatus.SUCCESS
        assert result.output == 42
        assert result.stdout == ["hello"]
        assert result.iterations == 5
        assert result.error is None


class TestSafeExecutorInit:
    """Tests for SafeExecutor initialization."""

    def test_default_init(self):
        executor = SafeExecutor()
        assert executor.tools == {}
        assert executor.max_iterations == 1000
        assert executor.max_depth == 50
        assert executor.state == {}

    def test_custom_init(self):
        tools = {"print": print}
        executor = SafeExecutor(tools=tools, max_iterations=500, max_depth=20)
        assert executor.tools == tools
        assert executor.max_iterations == 500
        assert executor.max_depth == 20


class TestSafeExecutorBasic:
    """Basic execution tests."""

    def test_simple_arithmetic(self):
        executor = SafeExecutor()
        result = executor.execute("result = 1 + 2")
        assert result.status == ExecutionStatus.SUCCESS

    def test_variable_assignment(self):
        executor = SafeExecutor()
        result = executor.execute("x = 42")
        assert result.status == ExecutionStatus.SUCCESS
        assert executor.state["x"] == 42

    def test_multiple_statements(self):
        executor = SafeExecutor()
        result = executor.execute("a = 1\nb = 2\nc = a + b")
        assert result.status == ExecutionStatus.SUCCESS
        assert executor.state["c"] == 3

    def test_string_operations(self):
        executor = SafeExecutor()
        result = executor.execute('name = "world"\ngreeting = f"hello {name}"')
        assert result.status == ExecutionStatus.SUCCESS

    def test_list_operations(self):
        executor = SafeExecutor()
        result = executor.execute("items = [1, 2, 3]\nresult = [x * 2 for x in items]")
        assert result.status == ExecutionStatus.SUCCESS

    def test_dict_operations(self):
        executor = SafeExecutor()
        result = executor.execute("d = {'a': 1, 'b': 2}")
        assert result.status == ExecutionStatus.SUCCESS

    def test_function_call(self):
        executor = SafeExecutor()
        result = executor.execute("result = len([1, 2, 3])")
        assert result.status == ExecutionStatus.SUCCESS

    def test_nested_expression(self):
        executor = SafeExecutor()
        result = executor.execute("result = (1 + 2) * (3 + 4)")
        assert result.status == ExecutionStatus.SUCCESS

    def test_if_statement(self):
        executor = SafeExecutor()
        result = executor.execute("x = 10\nif x > 5:\n    result = 'big'\nelse:\n    result = 'small'")
        assert result.status == ExecutionStatus.SUCCESS

    def test_for_loop(self):
        executor = SafeExecutor()
        result = executor.execute("total = 0\nfor i in range(5):\n    total += i\nresult = total")
        assert result.status == ExecutionStatus.SUCCESS

    def test_while_loop(self):
        executor = SafeExecutor()
        result = executor.execute("count = 0\nwhile count < 5:\n    count += 1\nresult = count")
        assert result.status == ExecutionStatus.SUCCESS

    def test_function_def(self):
        executor = SafeExecutor()
        result = executor.execute("def add(a, b):\n    return a + b\nresult = add(3, 4)")
        assert result.status == ExecutionStatus.SUCCESS

    def test_lambda(self):
        executor = SafeExecutor()
        result = executor.execute("f = lambda x: x * 2\nresult = f(5)")
        assert result.status == ExecutionStatus.SUCCESS

    def test_comprehension(self):
        executor = SafeExecutor()
        result = executor.execute("result = [x ** 2 for x in range(5)]")
        assert result.status == ExecutionStatus.SUCCESS

    def test_dict_comprehension(self):
        executor = SafeExecutor()
        result = executor.execute("result = {str(x): x for x in range(3)}")
        assert result.status == ExecutionStatus.SUCCESS

    def test_set_comprehension(self):
        executor = SafeExecutor()
        result = executor.execute("result = {x % 3 for x in range(10)}")
        assert result.status == ExecutionStatus.SUCCESS


class TestSafeExecutorErrors:
    """Error handling tests."""

    def test_syntax_error(self):
        executor = SafeExecutor()
        result = executor.execute("2 +")
        assert result.status == ExecutionStatus.ERROR
        assert "SyntaxError" in result.error

    def test_runtime_error(self):
        executor = SafeExecutor()
        result = executor.execute("result = 1 / 0")
        assert result.status == ExecutionStatus.ERROR
        assert "ZeroDivisionError" in result.error

    def test_name_error(self):
        executor = SafeExecutor()
        result = executor.execute("result = undefined_var")
        assert result.status == ExecutionStatus.ERROR

    def test_type_error(self):
        executor = SafeExecutor()
        result = executor.execute("result = 1 + 'string'")
        assert result.status == ExecutionStatus.ERROR

    def test_blocked_import(self):
        executor = SafeExecutor()
        result = executor.execute("import os")
        assert result.status in (ExecutionStatus.BLOCKED, ExecutionStatus.ERROR)

    def test_blocked_subprocess(self):
        executor = SafeExecutor()
        result = executor.execute("import subprocess")
        assert result.status in (ExecutionStatus.BLOCKED, ExecutionStatus.ERROR)

    def test_blocked_open(self):
        executor = SafeExecutor()
        result = executor.execute("open('/etc/passwd')")
        assert result.status in (ExecutionStatus.BLOCKED, ExecutionStatus.ERROR)

    def test_blocked_eval(self):
        executor = SafeExecutor()
        result = executor.execute("eval('1 + 1')")
        assert result.status in (ExecutionStatus.BLOCKED, ExecutionStatus.ERROR)

    def test_blocked_exec(self):
        executor = SafeExecutor()
        result = executor.execute("exec('print(1)')")
        assert result.status in (ExecutionStatus.BLOCKED, ExecutionStatus.ERROR)

    def test_blocked_getattr_private(self):
        executor = SafeExecutor()
        result = executor.execute("x = (1).__class__.__bases__")
        assert result.status in (ExecutionStatus.BLOCKED, ExecutionStatus.ERROR)


class TestSafeExecutorIterationLimit:
    """Tests for iteration limit enforcement."""

    def test_infinite_loop_blocked(self):
        executor = SafeExecutor(max_iterations=100)
        result = executor.execute("while True:\n    pass")
        assert result.status == ExecutionStatus.TIMEOUT

    def test_finite_loop_ok(self):
        executor = SafeExecutor(max_iterations=1000)
        result = executor.execute("for i in range(10):\n    pass")
        assert result.status == ExecutionStatus.SUCCESS

    def test_iteration_count_recorded(self):
        executor = SafeExecutor(max_iterations=1000)
        result = executor.execute("for i in range(5):\n    pass")
        assert result.iterations > 0


class TestSafeExecutorTools:
    """Tests for tool integration."""

    def test_custom_tool(self):
        def my_tool(x, y):
            return x + y

        executor = SafeExecutor(tools={"my_tool": my_tool})
        result = executor.execute("result = my_tool(3, 4)")
        assert result.status == ExecutionStatus.SUCCESS
        assert executor.state["result"] == 7

    def test_multiple_tools(self):
        tools = {"add": lambda a, b: a + b, "mul": lambda a, b: a * b}
        executor = SafeExecutor(tools=tools)
        result = executor.execute("x = add(1, 2)\ny = mul(x, 3)")
        assert result.status == ExecutionStatus.SUCCESS
        assert executor.state["y"] == 9


class TestSafeExecutorEdgeCases:
    """Edge case tests."""

    def test_empty_code(self):
        executor = SafeExecutor()
        result = executor.execute("")
        assert result.status == ExecutionStatus.SUCCESS

    def test_only_comments(self):
        executor = SafeExecutor()
        result = executor.execute("# this is a comment\n")
        assert result.status == ExecutionStatus.SUCCESS

    def test_return_in_function(self):
        executor = SafeExecutor()
        result = executor.execute("def compute():\n    return 42\nresult = compute()")
        assert result.status == ExecutionStatus.SUCCESS
        assert executor.state["result"] == 42

    def test_break_in_loop(self):
        executor = SafeExecutor()
        result = executor.execute(
            "result = 0\nfor i in range(100):\n    if i == 5:\n        break\n    result = i"
        )
        assert result.status == ExecutionStatus.SUCCESS

    def test_continue_in_loop(self):
        executor = SafeExecutor()
        result = executor.execute(
            "result = 0\nfor i in range(10):\n    if i % 2 == 0:\n        continue\n    result += i"
        )
        assert result.status == ExecutionStatus.SUCCESS

    def test_try_except(self):
        executor = SafeExecutor()
        result = executor.execute(
            "try:\n    result = 1 / 0\nexcept ZeroDivisionError:\n    result = 'caught'"
        )
        assert result.status == ExecutionStatus.SUCCESS
        assert executor.state["result"] == "caught"

    def test_assert_passes(self):
        executor = SafeExecutor()
        result = executor.execute("assert 1 == 1\nresult = 'ok'")
        assert result.status == ExecutionStatus.SUCCESS

    def test_assert_fails(self):
        executor = SafeExecutor()
        result = executor.execute("assert 1 == 2")
        assert result.status == ExecutionStatus.ERROR

    def test_ternary(self):
        executor = SafeExecutor()
        result = executor.execute("x = 10\nresult = 'big' if x > 5 else 'small'")
        assert result.status == ExecutionStatus.SUCCESS

    def test_nested_function(self):
        executor = SafeExecutor()
        result = executor.execute(
            "def outer():\n    def inner():\n        return 42\n    return inner()\nresult = outer()"
        )
        assert result.status == ExecutionStatus.SUCCESS

    def test_global_statement(self):
        executor = SafeExecutor()
        result = executor.execute(
            "x = 10\ndef modify():\n    global x\n    x = 20\nmodify()\nresult = x"
        )
        assert result.status == ExecutionStatus.SUCCESS
