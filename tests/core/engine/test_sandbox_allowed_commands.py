"""``SandboxConfig.allowed_commands`` must actually gate command execution.

Context: ``SandboxExecutor._is_command_safe`` only consulted
``blocked_patterns``. ``allowed_commands`` was decorative, so every executable
that no regex happened to match was permitted.

``SandboxExecutor`` is the production-live executor for ``allowed_commands``:
``app/main.py`` registers it in the DI container and ``run_command`` /
``stream_command`` / ``POST /terminal/execute`` all resolve it and call
``execute()``.

Pinned here:
- an allowlisted executable passes the allowlist gate
- a non-allowlisted executable is refused, and the reason names both the
  executable and the allowlist it was checked against
- absolute-path, ``./``-prefixed, quoted and bare-name spellings of the same
  binary resolve to one allowlist entry
- compound commands carrying a shell operator are refused rather than judged
  on their first token
- the pre-existing hazard / blocked-pattern checks still fire for an
  allowlisted executable invoked with dangerous arguments
- the long-standing ``echo hello`` shape still executes for real
"""

from __future__ import annotations

import pytest

from app.core.sandbox import SandboxConfig, SandboxExecutor


@pytest.fixture
def sandbox() -> SandboxExecutor:
    """An executor using the shipped default configuration."""
    return SandboxExecutor(SandboxConfig())


# ─── the allowlist allows what it lists ─────────────────────────────────────


def test_allowlisted_executable_passes(sandbox: SandboxExecutor) -> None:
    allowed, reason = sandbox._check_allowed_commands("ls -la")
    assert allowed is True, reason
    assert reason == ""


def test_echo_hello_shape_still_allowed(sandbox: SandboxExecutor) -> None:
    """The most common command must keep working after enforcement lands."""
    allowed, reason = sandbox._check_allowed_commands("echo hello")
    assert allowed is True, reason


def test_allowlisted_executable_passes_full_safety_check(
    sandbox: SandboxExecutor,
) -> None:
    is_safe, reason = sandbox._is_command_safe("echo hello", "/tmp")
    assert is_safe is True, reason
    assert reason == ""


@pytest.mark.parametrize(
    "command",
    [
        "python3 -c 'print(1)'",
        "python script.py",
        "grep -rn pattern .",
        "touch new_file.txt",
    ],
)
def test_realistic_allowlisted_commands_pass(
    sandbox: SandboxExecutor, command: str
) -> None:
    allowed, reason = sandbox._check_allowed_commands(command)
    assert allowed is True, reason


# ─── the allowlist denies what it omits ─────────────────────────────────────


@pytest.mark.parametrize(
    "command",
    [
        "rm -rf /",           # rm is not in the sandbox allowlist
        "curl http://example.com",
        "git status",
        "shutdown now",
        "bash script.sh",
        "chmod 777 /tmp/x",
    ],
)
def test_non_allowlisted_executable_denied(
    sandbox: SandboxExecutor, command: str
) -> None:
    allowed, reason = sandbox._check_allowed_commands(command)
    assert allowed is False, f"{command!r} bypassed the allowlist"
    assert "allowed_commands" in reason


def test_denial_reason_names_the_executable(sandbox: SandboxExecutor) -> None:
    _, reason = sandbox._check_allowed_commands("evilbinary --payload")
    assert "'evilbinary'" in reason


def test_denial_reason_names_the_allowlist_source(
    sandbox: SandboxExecutor,
) -> None:
    """The operator has to learn which knob to turn, not just that it failed."""
    _, reason = sandbox._check_allowed_commands("evilbinary --payload")
    assert "SandboxConfig.allowed_commands" in reason
    for entry in ("echo", "python3", "ls"):
        assert entry in reason


def test_denial_is_surfaced_by_execute(sandbox: SandboxExecutor) -> None:
    """execute() must return the refusal, not run the binary."""
    is_safe, reason = sandbox._is_command_safe("evilbinary --payload", "/tmp")
    assert is_safe is False
    assert "evilbinary" in reason


# ─── path and quoting spellings resolve to one entry ────────────────────────


@pytest.fixture
def echo_only() -> SandboxExecutor:
    """An executor whose allowlist holds a single binary named 'echo'."""
    return SandboxExecutor(SandboxConfig(allowed_commands=["echo"]))


@pytest.mark.parametrize(
    "command",
    [
        "echo hi",
        "  echo hi  ",              # leading / trailing whitespace
        "\techo hi",
        "/bin/echo hi",            # absolute path form
        "/usr/bin/echo hi",        # absolute path form
        "./echo hi",               # relative path form
        '"/bin/echo" hi',          # quoted absolute path form
        "'/bin/echo' hi",          # single-quoted absolute path form
    ],
)
def test_absolute_and_bare_forms_both_handled(
    echo_only: SandboxExecutor, command: str
) -> None:
    """One allowlist entry covers every spelling of the same binary."""
    allowed, reason = echo_only._check_allowed_commands(command)
    assert allowed is True, reason


@pytest.mark.parametrize(
    "command",
    [
        "/opt/vendor/tool --version",
        "./vendor/tool --version",
        '"vendor/tool" --version',
    ],
)
def test_denied_binary_is_reported_by_base_name(
    echo_only: SandboxExecutor, command: str
) -> None:
    """The refusal names the base name, proving path normalization ran."""
    allowed, reason = echo_only._check_allowed_commands(command)
    assert allowed is False
    assert "'tool'" in reason
    assert "/opt/vendor/tool" not in reason


def test_env_assignment_prefix_does_not_hide_the_executable(
    sandbox: SandboxExecutor,
) -> None:
    """A shell strips VAR=value before the program name; so must the check."""
    allowed, reason = sandbox._check_allowed_commands("FOO=bar echo hi")
    assert allowed is True, reason
    assert "FOO=bar" not in reason


def test_env_assignment_prefix_does_not_grant_allowlist_entry(
    echo_only: SandboxExecutor,
) -> None:
    _, reason = echo_only._check_allowed_commands("FOO=bar evilbinary")
    assert "'evilbinary'" in reason


# ─── compound commands are refused, not judged on their first token ─────────


@pytest.mark.parametrize(
    ("command", "operator"),
    [
        ("echo hi && rm -rf /", "&&"),
        ("echo hi && echo bye", "&&"),
        ("ls;rm -rf /", ";"),
        ("ls ; rm -rf /", ";"),
        ("cat notes.txt | wc -l", "|"),
        ("echo hi | tee out.txt", "|"),
        ("ls > out.txt", ">"),
        ("ls 2>&1", ">&"),
        ("cat < in.txt", "<"),
        ("(cd /tmp && ls)", "&&"),
        ("echo hi &", "&"),
        ("echo hi || ls", "||"),
    ],
)
def test_compound_command_is_refused(
    sandbox: SandboxExecutor, command: str, operator: str
) -> None:
    """``echo hi && rm -rf /`` must not pass on its first token alone."""
    is_safe, reason = sandbox._is_command_safe(command, "/tmp")
    assert is_safe is False, f"{command!r} was judged on its first token"
    assert operator in reason
    assert "compound command" in reason


def test_compound_command_refusal_precedes_allowlist_evaluation(
    sandbox: SandboxExecutor,
) -> None:
    """A dangerous second stage is reported as a compound command."""
    _, reason = sandbox._is_command_safe("echo hi && evilbinary", "/tmp")
    assert "compound command" in reason


def test_multi_line_command_is_refused(sandbox: SandboxExecutor) -> None:
    _, reason = sandbox._is_command_safe("echo hi\nevilbinary", "/tmp")
    assert "multi-line" in reason


def test_backtick_substitution_is_refused(sandbox: SandboxExecutor) -> None:
    _, reason = sandbox._is_command_safe("echo `id`", "/tmp")
    assert "backtick" in reason


def test_unbalanced_quotes_are_refused(sandbox: SandboxExecutor) -> None:
    _, reason = sandbox._is_command_safe('echo "unclosed', "/tmp")
    assert "invalid shell syntax" in reason


def test_empty_command_is_refused(sandbox: SandboxExecutor) -> None:
    _, reason = sandbox._is_command_safe("   ", "/tmp")
    assert "empty command" in reason


def test_quoted_operator_inside_an_argument_is_not_a_compound_command(
    sandbox: SandboxExecutor,
) -> None:
    """``echo 'a && b'`` passes one argument; the operator is data, not control."""
    allowed, reason = sandbox._check_allowed_commands("echo 'a && b'")
    assert allowed is True, reason


def test_shell_snippet_passed_to_an_interpreter_still_works(
    sandbox: SandboxExecutor,
) -> None:
    """``python -c '...'`` carries shell syntax as data and stays allowed."""
    allowed, reason = sandbox._check_allowed_commands(
        "python3 -c 'import os; print(os.getcwd())'"
    )
    assert allowed is True, reason


# ─── existing checks are untouched ──────────────────────────────────────────


@pytest.mark.parametrize(
    ("command", "expected_fragment"),
    [
        ("python3 -c \"chmod 777 /tmp/x\"", "chmod"),
        ("echo sudo id", "sudo"),
        ("python3 -c \"shutdown\"", "shutdown"),
        ("ls fdisk", "fdisk"),
        ("ls dd if=/dev/sda", "dd"),
        ("python3 -c 'print(1)' | sh", "compound command"),
    ],
)
def test_blocked_patterns_still_fire_for_allowlisted_executable(
    sandbox: SandboxExecutor, command: str, expected_fragment: str
) -> None:
    """Allowlisting the program must not admit its dangerous arguments."""
    is_safe, reason = sandbox._is_command_safe(command, "/tmp")
    assert is_safe is False
    assert expected_fragment in reason


def test_sensitive_path_check_still_fires(sandbox: SandboxExecutor) -> None:
    is_safe, reason = sandbox._is_command_safe("cat /etc/passwd", "/tmp")
    assert is_safe is False
    assert reason


def test_parent_traversal_check_still_fires(sandbox: SandboxExecutor) -> None:
    is_safe, reason = sandbox._is_command_safe("cat ../secrets.txt", "/tmp")
    assert is_safe is False
    assert "parent-directory traversal" in reason


# ─── a custom allowlist replaces the default ────────────────────────────────


def test_custom_allowlist_is_honoured() -> None:
    executor = SandboxExecutor(SandboxConfig(allowed_commands=["mytool"]))
    allowed, reason = executor._check_allowed_commands("/usr/local/bin/mytool run")
    assert allowed is True, reason
    _, denied = executor._check_allowed_commands("echo hi")
    assert "'echo'" in denied


def test_empty_allowlist_denies_everything() -> None:
    executor = SandboxExecutor(SandboxConfig(allowed_commands=[]))
    allowed, reason = executor._check_allowed_commands("echo hello")
    assert allowed is False
    assert "allowed_commands" in reason


# ─── end to end through execute() ───────────────────────────────────────────


@pytest.mark.asyncio
async def test_execute_runs_an_allowlisted_command(sandbox: SandboxExecutor) -> None:
    try:
        output = await sandbox.execute("echo hello")
    finally:
        sandbox.cleanup()
    assert "hello" in output
    assert not output.startswith("BLOCKED")


@pytest.mark.asyncio
async def test_execute_refuses_a_non_allowlisted_command(
    sandbox: SandboxExecutor,
) -> None:
    try:
        output = await sandbox.execute("evilbinary --payload")
    finally:
        sandbox.cleanup()
    assert output.startswith("BLOCKED")
    assert "evilbinary" in output
    assert "allowed_commands" in output


@pytest.mark.asyncio
async def test_execute_refuses_a_compound_command(sandbox: SandboxExecutor) -> None:
    try:
        output = await sandbox.execute("echo hi && rm -rf /")
    finally:
        sandbox.cleanup()
    assert output.startswith("BLOCKED")
    assert "compound command" in output
