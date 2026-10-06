"""Coverage tests for app.core.error_analyzer.

Exercises the real ``ErrorAnalyzer.analyze`` call path over the supported
error shapes (Python tracebacks, shell, HTTP, permission, timeout, network,
file-not-found) plus the internal classifier branches.
"""

from __future__ import annotations

from app.core.error_analyzer import ErrorAnalysis, ErrorAnalyzer, ErrorType


def test_error_type_enum_values() -> None:
    assert ErrorType.SYNTAX_ERROR == "syntax_error"
    assert ErrorType.RUNTIME_ERROR == "runtime_error"
    assert ErrorType.PERMISSION_ERROR == "permission_error"
    assert ErrorType.IMPORT_ERROR == "import_error"
    assert ErrorType.NETWORK_ERROR == "network_error"
    assert ErrorType.FILE_NOT_FOUND == "file_not_found"
    assert ErrorType.TIMEOUT == "timeout"
    assert ErrorType.AUTHENTICATION_ERROR == "authentication_error"
    assert ErrorType.VALIDATION_ERROR == "validation_error"
    assert ErrorType.UNKNOWN == "unknown"


def test_error_analysis_to_dict() -> None:
    analysis = ErrorAnalysis(
        error_type=ErrorType.RUNTIME_ERROR,
        message="boom",
        file_path="a.py",
        line_number=7,
        cause="c",
        confidence=0.5,
        raw_error="raw",
        context={"k": "v"},
    )
    data = analysis.to_dict()
    assert data == {
        "error_type": "runtime_error",
        "message": "boom",
        "file_path": "a.py",
        "line_number": 7,
        "cause": "c",
        "confidence": 0.5,
    }
    # raw_error / context are intentionally not exported
    assert "raw_error" not in data
    assert "context" not in data


def test_analyze_empty_returns_unknown() -> None:
    result = ErrorAnalyzer().analyze("   ")
    assert result.error_type is ErrorType.UNKNOWN
    assert result.message == "empty error"
    assert result.raw_error == ""


def test_analyze_python_traceback_extracts_file_and_line() -> None:
    raw = (
        "Traceback (most recent call last):\n"
        '  File "/app/mod/x.py", line 10, in <module>\n'
        "    run()\n"
        '  File "/app/mod/y.py", line 42, in run\n'
        "    raise RuntimeError('bad thing')\n"
        "RuntimeError: bad thing"
    )
    result = ErrorAnalyzer().analyze(raw, {"tool": "run"})
    assert result.error_type is ErrorType.RUNTIME_ERROR
    assert result.file_path == "/app/mod/y.py"
    assert result.line_number == 42
    assert result.cause == "bad thing"
    assert result.raw_error == raw
    assert result.context == {"tool": "run"}


def test_analyze_python_traceback_without_file_lines() -> None:
    raw = "Traceback (most recent call last):\nsomething without file info\nValueError: nope"
    result = ErrorAnalyzer().analyze(raw)
    assert result.file_path is None
    assert result.line_number is None
    assert result.error_type is ErrorType.RUNTIME_ERROR  # classifier reads message body


def test_analyze_python_traceback_classification_syntax() -> None:
    raw = (
        "Traceback (most recent call last):\n"
        '  File "a.py", line 1\n'
        "SyntaxError: invalid syntax (also SyntaxError again)"
    )
    assert ErrorAnalyzer().analyze(raw).error_type is ErrorType.SYNTAX_ERROR


def test_analyze_python_traceback_classification_import() -> None:
    raw = (
        "Traceback (most recent call last):\n"
        '  File "a.py", line 1\n'
        "ModuleNotFoundError: no module (ImportError alias)"
    )
    assert ErrorAnalyzer().analyze(raw).error_type is ErrorType.IMPORT_ERROR


def test_analyze_python_traceback_classification_permission() -> None:
    raw = (
        "Traceback (most recent call last):\n"
        '  File "a.py", line 1\n'
        "PermissionError: PermissionError denied"
    )
    assert ErrorAnalyzer().analyze(raw).error_type is ErrorType.PERMISSION_ERROR


def test_analyze_python_traceback_classification_file_not_found() -> None:
    raw = (
        "Traceback (most recent call last):\n"
        '  File "a.py", line 1\n'
        "FileNotFoundError: FileNotFoundError"
    )
    assert ErrorAnalyzer().analyze(raw).error_type is ErrorType.FILE_NOT_FOUND


def test_analyze_python_traceback_classification_timeout() -> None:
    raw = (
        "Traceback (most recent call last):\n"
        '  File "a.py", line 1\n'
        "TimeoutError: asyncio.TimeoutError raised"
    )
    assert ErrorAnalyzer().analyze(raw).error_type is ErrorType.TIMEOUT


def test_analyze_python_traceback_classification_network() -> None:
    raw = (
        "Traceback (most recent call last):\n"
        '  File "a.py", line 1\n'
        "ConnectionError: HTTPError RequestException"
    )
    assert ErrorAnalyzer().analyze(raw).error_type is ErrorType.NETWORK_ERROR


def test_analyze_python_traceback_classification_auth() -> None:
    raw = (
        "Traceback (most recent call last):\n"
        '  File "a.py", line 1\n'
        "AuthenticationError: bad creds 401"
    )
    assert ErrorAnalyzer().analyze(raw).error_type is ErrorType.AUTHENTICATION_ERROR


def test_analyze_python_traceback_classification_validation() -> None:
    raw = (
        "Traceback (most recent call last):\n"
        '  File "a.py", line 1\n'
        "TypeError: ValueError KeyError IndexError"
    )
    assert ErrorAnalyzer().analyze(raw).error_type is ErrorType.VALIDATION_ERROR


def test_classify_python_error_direct_branches() -> None:
    analyzer = ErrorAnalyzer()
    assert analyzer._classify_python_error("IndentationError") is ErrorType.SYNTAX_ERROR
    assert analyzer._classify_python_error("ImportError") is ErrorType.IMPORT_ERROR
    assert analyzer._classify_python_error("Permission denied") is ErrorType.PERMISSION_ERROR
    assert analyzer._classify_python_error("FileNotFoundError") is ErrorType.FILE_NOT_FOUND
    assert analyzer._classify_python_error("TimeoutError") is ErrorType.TIMEOUT
    assert analyzer._classify_python_error("RequestException") is ErrorType.NETWORK_ERROR
    assert analyzer._classify_python_error("403 forbidden") is ErrorType.AUTHENTICATION_ERROR
    assert analyzer._classify_python_error("KeyError") is ErrorType.VALIDATION_ERROR
    assert analyzer._classify_python_error("totally different") is ErrorType.RUNTIME_ERROR


def test_analyze_permission_error() -> None:
    result = ErrorAnalyzer().analyze("cat: /x: Permission denied")
    assert result.error_type is ErrorType.PERMISSION_ERROR
    assert result.cause == "cat: /x: Permission denied"


def test_analyze_file_not_found() -> None:
    result = ErrorAnalyzer().analyze("open failed: No such file or directory")
    assert result.error_type is ErrorType.FILE_NOT_FOUND


def test_analyze_timeout() -> None:
    result = ErrorAnalyzer().analyze("operation timed out after 30s")
    assert result.error_type is ErrorType.TIMEOUT


def test_analyze_network_error() -> None:
    result = ErrorAnalyzer().analyze("Connection refused to host, ECONNREFUSED")
    assert result.error_type is ErrorType.NETWORK_ERROR


def test_analyze_http_401_is_auth() -> None:
    result = ErrorAnalyzer().analyze("HTTP 401 Unauthorized")
    assert result.error_type is ErrorType.AUTHENTICATION_ERROR


def test_analyze_http_other_is_unknown_but_matched() -> None:
    result = ErrorAnalyzer().analyze("HTTP 500 Internal Server Error")
    assert result.error_type is ErrorType.UNKNOWN
    assert result.message == "HTTP 500 Internal Server Error"


def test_analyze_shell_command_not_found_is_syntax() -> None:
    result = ErrorAnalyzer().analyze("bash: foobar: command not found")
    assert result.error_type is ErrorType.SYNTAX_ERROR


def test_analyze_shell_generic_is_runtime() -> None:
    result = ErrorAnalyzer().analyze("bash: line 1: exit code 3")
    assert result.error_type is ErrorType.RUNTIME_ERROR


def test_analyze_shell_is_a_directory() -> None:
    result = ErrorAnalyzer().analyze("bash: /tmp/x: Is a directory")
    assert result.error_type is ErrorType.RUNTIME_ERROR


def test_analyze_unknown_generic() -> None:
    result = ErrorAnalyzer().analyze("something strange happened")
    assert result.error_type is ErrorType.UNKNOWN
    assert result.cause == "something strange happened"
    assert result.context == {}
