"""Static checks for code submitted to the agent.

This AST gate is a denylist tripwire. A passing result means that the source
contains no names covered by this list; it does not provide process isolation,
resource limits, or a complete security boundary. Callers that need isolation
must use an OS-level sandbox as well.
"""

from __future__ import annotations


class VerificationResult:
    def __init__(self, allowed: bool, reason: str = ""):
        self.allowed = allowed
        self.reason = reason


class CodeSandbox:
    """AST denylist for obvious interpreter, filesystem, and import escapes."""

    FORBIDDEN_MODULES = {
        "builtins", "importlib", "runpy", "code", "mmap", "multiprocessing",
        "imp", "pkgutil", "zipimport", "os", "sys", "subprocess", "socket",
        "shutil", "pickle", "marshal", "ctypes", "signal", "pty", "fcntl",
        "ssl", "urllib", "http", "asyncio", "shelve", "dill", "gc",
    }
    FORBIDDEN_FUNCTIONS = {
        "eval", "exec", "open", "getattr", "setattr", "delattr", "globals",
        "locals", "compile", "__import__", "vars", "breakpoint", "input",
        "memoryview",
    }
    FORBIDDEN_DUNDER = {
        "__getattribute__", "__getattr__", "__setattr__", "__delattr__",
        "__class__", "__bases__", "__base__", "__mro__", "__subclasses__",
        "__init_subclass__", "__globals__", "__code__", "__builtins__",
        "__dict__", "__reduce__", "__reduce_ex__",
    }

    def verify(self, code: str) -> VerificationResult:
        try:
            import ast
            tree = ast.parse(code)
        except ImportError as exc:  # pragma: no cover
            return VerificationResult(False, f"AST unavailable: {exc}")
        except SyntaxError as exc:
            return VerificationResult(False, f"Syntax error: {exc}")
        except (ValueError, MemoryError, RecursionError) as exc:
            return VerificationResult(False, f"Unparsable source: {exc}")

        forbidden_names = self.FORBIDDEN_FUNCTIONS | self.FORBIDDEN_DUNDER
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    top = alias.name.split(".", 1)[0]
                    if top in self.FORBIDDEN_MODULES:
                        return VerificationResult(False, f"Forbidden module: {top}")
            elif isinstance(node, ast.ImportFrom) and node.module:
                top = node.module.split(".", 1)[0]
                if top in self.FORBIDDEN_MODULES:
                    return VerificationResult(False, f"Forbidden module: {top}")
            elif isinstance(node, ast.Name) and node.id in forbidden_names:
                return VerificationResult(False, f"Forbidden name: {node.id}")
            elif isinstance(node, ast.Attribute) and node.attr in self.FORBIDDEN_DUNDER:
                return VerificationResult(False, f"Forbidden attribute: {node.attr}")
            elif isinstance(node, ast.Subscript):
                key = node.slice
                if (
                    isinstance(key, ast.Constant)
                    and isinstance(key.value, str)
                    and key.value in self.FORBIDDEN_DUNDER
                ):
                    return VerificationResult(False, f"Forbidden attribute: {key.value}")

        return VerificationResult(True)
