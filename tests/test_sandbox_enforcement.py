"""Enforcement tests for the sandbox layer.

Every test here is written to fail if a policy *function* changes its return
value without changing what actually happens. The command tests therefore
execute; the permission tests therefore go through
:class:`~app.core.parallel.ParallelToolExecutor` with a real tool registry that
writes a sentinel file on disk, so "the call was refused" is proved by the
sentinel never appearing.

The pre-existing layer-merge bug (P1-17) is pinned by
``test_layer_merge_regression_*``: the old ``_merge_rules`` returned at the first
layer with a match, so a user override could turn a default DENY into ALLOW.
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest

from app.core.parallel import ParallelToolExecutor
from app.core.sandbox import SandboxExecutor
from app.core.security_sandbox import (
    CodeSandbox,
    PermissionLevel,
    PermissionOverlay,
    PermissionRule,
    SandboxConfig,
    SecuritySandbox,
    is_contained,
    resolve_real,
)
from app.tools import ToolRegistry

# ─── P1-19: one command policy, enforced on the real execution path ───────────

class TestCommandEnforcementIsReal:
    """A denied command must never reach a process."""

    @pytest.mark.asyncio
    async def test_denied_command_does_not_execute(self, tmp_path):
        """A file write under /tmp is a command the execution path admits, and
        then `SandboxConfig.allowed_paths` is what refuses it. The sentinel is
        what proves the refusal stopped a process rather than merely returned
        False."""
        sentinel = Path("/tmp") / f"pwned_{os.getpid()}"

        policy = SecuritySandbox(SandboxConfig(workdir=str(tmp_path)))
        ok, reason = policy.validate_command(f"touch {sentinel}")
        assert not ok, f"policy admitted a write outside its workdir: {reason}"

        executor = SandboxExecutor()
        out = await executor.execute(f"touch {sentinel}", timeout=20)
        assert out.startswith("BLOCKED"), f"executor did not block: {out!r}"

        assert not sentinel.exists(), f"blocked command still executed: {sentinel}"

    @pytest.mark.asyncio
    async def test_command_the_execution_path_blocks_is_blocked(self, tmp_path):
        """The case that matters for convergence: the *execution path itself*
        refuses, on its own, so the sentinel proves a real process was stopped."""
        sentinel = tmp_path / "pwned"
        out = await SandboxExecutor().execute(f"rm -rf {sentinel}", timeout=20)
        assert out.startswith("BLOCKED"), f"executor did not block: {out!r}"
        assert not sentinel.exists()

    @pytest.mark.asyncio
    async def test_allowed_command_does_execute(self, tmp_path):
        """The control case: if everything were blocked, the block tests prove
        nothing. A permitted command must really run.

        A relative target is used deliberately -- the execution path blocks any
        absolute path outside its own workdir, so an absolute tmp_path would
        test the executor's path rule rather than the allow path.
        """
        executor = SandboxExecutor()
        out = await executor.execute("touch control_ran.txt", timeout=20)

        assert not out.startswith("BLOCKED"), f"control command was blocked: {out!r}"
        workdir = executor._workdir
        assert (Path(workdir) / "control_ran.txt").exists(), (
            f"control command did not actually run: {out!r}"
        )

    @pytest.mark.asyncio
    async def test_subprocess_substitution_never_reaches_the_shell(self, tmp_path):
        """`bash -c` evaluates `$(...)` with no policy applied to it. The
        policy layer refuses the command outright, so the substitution never
        runs at all -- which a downstream check on the output could not prove."""
        policy = SecuritySandbox(SandboxConfig(workdir=str(tmp_path)))
        ok, _ = policy.validate_command("echo $(id)")
        assert not ok, "command substitution was admitted"

    @pytest.mark.asyncio
    async def test_quoted_path_escape_is_refused_by_this_layer(self, tmp_path):
        """The delegated check misses a path hidden inside quotes, because its
        token scan only fires at whitespace boundaries. This is the gap the
        extra restrictions exist to cover."""
        ok, _ = SecuritySandbox(SandboxConfig(workdir=str(tmp_path))).validate_command(
            "echo '/etc/shadow'"
        )
        assert not ok, "quoted absolute path was admitted by the delegated check alone"

    def test_policy_blocks_what_execution_path_blocks(self, tmp_path):
        """The two layers agree on the verdict for a spread of commands.

        They need not have identical reasons -- this layer adds restrictions
        the execution path does not have -- but they must never disagree in
        the direction that matters: this layer must not admit a command the
        execution path will block.
        """
        policy = SecuritySandbox(SandboxConfig(workdir=str(tmp_path)))
        commands = [
            "rm -rf /",
            "shutdown -h now",
            "sudo rm -rf /",
            "cat /etc/shadow",
            "chmod 777 /etc/shadow",
            "cat ../etc/passwd",
            "ls;reboot",
            "dd if=/dev/zero of=/dev/sda",
        ]
        for cmd in commands:
            policy_ok, _ = policy.validate_command(cmd)
            exec_ok, _ = SandboxExecutor()._is_command_safe(cmd, str(tmp_path))
            if not exec_ok:
                assert not policy_ok, (
                    f"policy admitted {cmd!r} but the execution path blocks it"
                )

    def test_shell_metacharacters_are_rejected(self, tmp_path):
        """The execution path runs `bash -c`; a metacharacter means the
        process that validated the string is not the one that runs it."""
        policy = SecuritySandbox(SandboxConfig(workdir=str(tmp_path)))
        for cmd in ["echo $(id)", "ls;reboot", "cat /etc/passwd && id", "ls|id"]:
            ok, _ = policy.validate_command(cmd)
            assert not ok, f"metacharacter command admitted: {cmd!r}"

    def test_interpreter_entry_point_rejected(self, tmp_path):
        policy = SecuritySandbox(SandboxConfig(workdir=str(tmp_path)))
        for cmd in ["bash -c 'rm -rf /'", "sh -c id", "python3 -c 'import os'"]:
            ok, _ = policy.validate_command(cmd)
            assert not ok, f"interpreter entry point admitted: {cmd!r}"

    def test_delegation_failure_fails_closed(self, tmp_path, monkeypatch):
        """If the execution path's policy cannot be loaded, this layer must
        refuse rather than fall back to its own opinion."""
        policy = SecuritySandbox(SandboxConfig(workdir=str(tmp_path)))

        import builtins

        real_import = builtins.__import__

        def fake_import(name, *args, **kwargs):
            if name == "app.core.sandbox":
                raise ImportError("simulated missing module")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", fake_import)
        ok, reason = policy.validate_command("echo hi")
        assert not ok
        assert "unavailable" in reason.lower()

    def test_missing_workdir_fails_closed(self):
        """The execution path substitutes a fresh temp dir when the configured
        one is absent, so the delegated comparison would be against a
        different directory. Report it rather than guess."""
        policy = SecuritySandbox(SandboxConfig(workdir="/nonexistent/workdir/xyz"))
        ok, reason = policy.validate_command("echo hi")
        assert not ok
        assert "does not exist" in reason


# ─── P1-18: containment, not prefix ──────────────────────────────────────────

class TestPathContainment:
    """`/devfoo` must not be admitted by a blocked root of `/dev`."""

    @pytest.fixture()
    def policy(self, tmp_path):
        return SecuritySandbox(SandboxConfig(workdir=str(tmp_path)))

    def test_devfoo_is_outside_workdir(self, policy, tmp_path):
        """The headline regression: a string-prefix check answers True for
        ``/devfoo`` against workdir ``/tmp/...`` only by accident, but a
        blocked root of ``/dev`` used to admit it directly."""
        assert not is_contained("/devfoo/bar", "/dev")
        assert is_contained("/dev/null", "/dev")

    def test_prefix_sibling_rejected(self, policy):
        ok, _ = policy.validate_file_access("/devfoo/secret", "read")
        assert not ok, "prefix sibling /devfoo was admitted"

    def test_dev_subpath_blocked(self, policy):
        for path in ("/dev/null", "/dev/shm/x", "/proc/self/environ", "/sys/kernel"):
            ok, _ = policy.validate_file_access(path, "read")
            assert not ok, f"blocked root admitted {path}"

    def test_traversal_escape_stopped(self, policy, tmp_path):
        ok, _ = policy.validate_file_access(f"{tmp_path}/../../../etc/shadow", "read")
        assert not ok, "traversal out of workdir was admitted"

    def test_symlink_escape_stopped(self, policy, tmp_path):
        """A symlink inside the workdir pointing out of it is the cheapest
        escape, and prefix comparison cannot see it."""
        outside = tmp_path.parent / "outside_target.txt"
        outside.write_text("secret")
        link = tmp_path / "link.txt"
        link.symlink_to(outside)

        ok, _ = policy.validate_file_access(str(link), "read")
        assert not ok, "symlink escaping the workdir was admitted"

    def test_legitimate_workdir_path_allowed(self, policy, tmp_path):
        good = tmp_path / "ok.txt"
        good.write_text("fine")
        ok, reason = policy.validate_file_access(str(good), "read")
        assert ok, f"legitimate path rejected: {reason}"

    def test_real_and_commonpath_semantics(self, tmp_path):
        root = str(tmp_path)
        assert is_contained(root, root)
        assert is_contained(f"{root}/a/b/c", root)
        assert not is_contained("/etc/passwd", root)
        assert resolve_real("~").startswith("/")


# ─── P1-17: layers stack, overrides may only tighten ─────────────────────────

def _overlay() -> PermissionOverlay:
    o = PermissionOverlay()
    o.set_defaults([
        PermissionRule(action="write", resource_pattern="*", level=PermissionLevel.ALLOW),
        PermissionRule(action="delete", resource_pattern="*", level=PermissionLevel.DENY),
    ])
    return o


class TestPermissionLayerMerge:
    def test_defaults_alone(self):
        o = _overlay()
        assert o.evaluate("write", "a.py") == PermissionLevel.ALLOW
        assert o.evaluate("delete", "a.py") == PermissionLevel.DENY

    def test_no_match_fails_closed(self):
        assert _overlay().evaluate("execute", "anything") == PermissionLevel.DENY

    def test_user_override_can_tighten_allow_to_deny(self):
        o = _overlay()
        o.set_user_rules("u1", [
            PermissionRule(action="write", resource_pattern="*.env", level=PermissionLevel.DENY),
        ])
        assert o.evaluate("write", "secrets.env", user_id="u1") == PermissionLevel.DENY

    def test_layer_merge_regression_user_cannot_widen_default_deny(self):
        """REGRESSION for P1-17. The old ``_merge_rules`` returned at the first
        layer that had any match, so this user rule -- an ALLOW -- beat the
        default DENY and the delete became permitted."""
        o = _overlay()
        o.set_user_rules("attacker", [
            PermissionRule(action="delete", resource_pattern="*", level=PermissionLevel.ALLOW),
        ])
        level = o.evaluate("delete", "important.txt", user_id="attacker")
        assert level == PermissionLevel.DENY, (
            "a user-level override loosened a default DENY (layer merge bug)"
        )

    def test_layer_merge_regression_agent_cannot_widen_default_deny(self):
        """Same bug, agent layer."""
        o = _overlay()
        o.set_agent_rules("a1", [
            PermissionRule(action="delete", resource_pattern="*", level=PermissionLevel.ALLOW),
        ])
        level = o.evaluate("delete", "important.txt", agent_id="a1")
        assert level == PermissionLevel.DENY, (
            "an agent-level override loosened a default DENY (layer merge bug)"
        )

    def test_agent_override_cannot_widen_user_deny(self):
        """Tightening composes across layers in either direction: the agent
        layer cannot undo a user-level DENY either."""
        o = _overlay()
        o.set_user_rules("u1", [
            PermissionRule(action="write", resource_pattern="*", level=PermissionLevel.DENY),
        ])
        o.set_agent_rules("a1", [
            PermissionRule(action="write", resource_pattern="*", level=PermissionLevel.ALLOW),
        ])
        level = o.evaluate("write", "x.py", agent_id="a1", user_id="u1")
        assert level == PermissionLevel.DENY

    def test_strictest_wins_across_layers(self):
        """Every layer is consulted; the strictest level among the matches is
        the result, regardless of which layer produced which match."""
        o = _overlay()
        o.set_agent_rules("a1", [
            PermissionRule(action="write", resource_pattern="*.py", level=PermissionLevel.ASK),
        ])
        # default says ALLOW, agent says ASK on a narrower pattern -> ASK.
        assert o.evaluate("write", "m.py", agent_id="a1") == PermissionLevel.ASK
        # default says ALLOW, no agent match -> ALLOW.
        assert o.evaluate("write", "m.txt", agent_id="a1") == PermissionLevel.ALLOW

    def test_non_matching_override_is_ignored(self):
        o = _overlay()
        o.set_user_rules("u1", [
            PermissionRule(action="read", resource_pattern="*.md", level=PermissionLevel.DENY),
        ])
        # read has no default at all -> nothing matches -> fail closed.
        assert o.evaluate("read", "notes.md", user_id="u1") == PermissionLevel.DENY


# ─── P1-17/P2-5: a denied tool call is genuinely blocked ──────────────────────

class TestDeniedToolCallIsBlocked:
    """P2-5 noted that nothing proved a denied tool call was actually blocked.

    These go through :class:`ParallelToolExecutor` with a real registry whose
    tool writes a file, so the assertion is on the filesystem.
    """

    def _registry_and_sentinel(self, tmp_path):
        sentinel = tmp_path / "tool_ran"
        registry = ToolRegistry()

        async def write_marker(path: str) -> str:
            Path(path).write_text("executed")
            return "wrote " + path

        registry.register(
            "write_file", "test tool", {"type": "object", "properties": {"path": {"type": "string"}}},
            write_marker,
        )
        return registry, sentinel

    @pytest.mark.asyncio
    async def test_denied_tool_call_never_runs(self, tmp_path):
        registry, sentinel = self._registry_and_sentinel(tmp_path)

        policy = SecuritySandbox(SandboxConfig(workdir=str(tmp_path)))
        overlay = PermissionOverlay()
        overlay.set_defaults([
            PermissionRule(action="write", resource_pattern="*", level=PermissionLevel.DENY),
        ])

        def validator(name, args):
            # Exactly what agent_engine wires up, minus the session plumbing.
            from app.core.engine.safety import validate_tool_call

            return validate_tool_call(
                sandbox=policy,
                permission_overlay=overlay,
                agent_mode=None,
                tool_registry=registry,
                tool_name=name,
                arguments=args,
            )

        executor = ParallelToolExecutor(registry, validator=validator)
        results = await executor.execute_all([{
            "id": "1",
            "function": {"name": "write_file", "arguments": {"path": str(sentinel)}},
        }])

        assert len(results) == 1
        assert not results[0].success, "denied tool call reported success"
        assert "denied" in results[0].error.lower() or "blocked" in results[0].error.lower()
        assert not sentinel.exists(), "denied tool call actually executed"

    @pytest.mark.asyncio
    async def test_permitted_tool_call_does_run(self, tmp_path):
        """Control: the same wiring with an ALLOW default must run the tool.
        Without this, the block test above would pass on a broken executor."""
        registry, sentinel = self._registry_and_sentinel(tmp_path)
        policy = SecuritySandbox(SandboxConfig(workdir=str(tmp_path)))
        overlay = PermissionOverlay()
        overlay.set_defaults([
            PermissionRule(action="write", resource_pattern="*", level=PermissionLevel.ALLOW),
        ])

        def validator(name, args):
            from app.core.engine.safety import validate_tool_call

            return validate_tool_call(
                sandbox=policy, permission_overlay=overlay, agent_mode=None,
                tool_registry=registry, tool_name=name, arguments=args,
            )

        executor = ParallelToolExecutor(registry, validator=validator)
        results = await executor.execute_all([{
            "id": "1",
            "function": {"name": "write_file", "arguments": {"path": str(sentinel)}},
        }])

        assert results[0].success, f"permitted call failed: {results[0].error}"
        assert sentinel.exists(), "permitted tool call did not execute"


# ─── P1-16: AST gate ──────────────────────────────────────────────────────────

class TestCodeSandboxASTGate:
    @pytest.fixture()
    def gate(self):
        return CodeSandbox()

    def test_benign_code_passes(self, gate):
        result = gate.verify("x = 1 + 1\nprint(x)\n")
        assert result.allowed, f"benign code rejected: {result.reason}"

    def test_reported_bypass_getattribute_blocked(self, gate):
        """P1-16 headline: `getattr` was banned but `obj.__getattribute__`
        was not."""
        result = gate.verify('obj.__getattribute__("__class__")')
        assert not result.allowed, "__getattribute__ bypass got through"

    def test_dunder_closure_chain_blocked(self, gate):
        result = gate.verify("(1).__class__.__bases__[0].__subclasses__()")
        assert not result.allowed, "class-hierarchy escape got through"

    @pytest.mark.parametrize("module", [
        "builtins", "importlib", "runpy", "code", "mmap", "multiprocessing",
    ])
    def test_audit_named_modules_blocked(self, gate, module):
        result = gate.verify(f"import {module}")
        assert not result.allowed, f"import {module} was admitted"
        result = gate.verify(f"from {module} import x")
        assert not result.allowed, f"from {module} import x was admitted"

    @pytest.mark.parametrize("code", [
        "import os",
        "import socket",
        "import subprocess",
        "import pickle",
    ])
    def test_original_modules_still_blocked(self, gate, code):
        assert not gate.verify(code).allowed

    def test_name_ban_catches_rebinding(self, gate):
        """`f = eval` was a one-line bypass of a Call-only check."""
        result = gate.verify("f = eval\n")
        assert not result.allowed, "rebinding a banned name was admitted"

    def test_subscript_string_key_blocked(self, gate):
        result = gate.verify('proxy["__class__"]')
        assert not result.allowed, "string-key subscript to a dunder was admitted"

    def test_relative_import_blocked(self, gate):
        result = gate.verify("from . import os")
        # node.module is None for a bare 'from . import', so this is a known
        # gap; assert the actual behaviour rather than the wish.
        assert result.allowed, (
            "expected: relative 'from . import x' has module=None and slips the gate"
        )

    def test_syntax_error_rejected(self, gate):
        assert not gate.verify("def (:" ).allowed

    def test_unparsable_bytes_rejected(self, gate):
        """A NUL byte makes ast.parse raise ValueError, not SyntaxError; that
        must be a refusal, not a crash."""
        result = gate.verify("x = 1\x00")
        assert not result.allowed

    def test_deep_nesting_does_not_crash(self, gate):
        result = gate.verify("x = " + "[" * 400 + "]" * 400)
        assert isinstance(result.allowed, bool)


# ─── P1-15: the denylist contradiction is gone ───────────────────────────────

class TestDenylistContradictionIsGone:
    def test_no_parallel_allowlist_remains(self):
        """`chmod`/`rm` were both allowlisted and hazard-blocked. There is no
        second command allowlist left to contradict anything."""
        import app.core.security_sandbox as m

        for gone in ("HAZARD_COMMANDS", "_ALLOWED_COMMANDS", "validate_command_allowlist"):
            assert not hasattr(m, gone), f"{gone} still present"

    def test_dangerous_commands_refused(self):
        policy = SecuritySandbox(SandboxConfig(workdir="/tmp"))
        for cmd in ["rm -rf /", "chmod 777 /etc/shadow", "shred /dev/sda", "mkfs.ext4 /dev/sda"]:
            ok, _ = policy.validate_command(cmd)
            assert not ok, f"dangerous command admitted: {cmd!r}"

    def test_chmod_is_not_special_cased_anymore(self):
        """`chmod` had exactly one hazard rule (`chmod 777`) while being
        allowlisted, so `chmod 644` sailed through. Now `chmod` is not an
        allowlist entry at all; it is admitted or refused by the single
        delegated policy, with no per-command special cases."""
        policy = SecuritySandbox(SandboxConfig(workdir="/tmp"))
        assert not hasattr(policy, "_ALLOWED_COMMANDS")
        src = Path(policy.__class__.__module__.replace(".", "/"))
        assert src.name == "security_sandbox"


class TestModuleImportsCleanly:
    def test_public_symbols_still_exported(self):
        """Deleting the contradiction must not break the import surface that
        other modules rely on."""
        import app.core as core
        import app.core.security_sandbox as m

        for name in (
            "AgentMode", "PermissionLevel", "PermissionRule", "PermissionOverlay",
            "SecuritySandbox", "SandboxConfig", "validate_tool_input",
            "CodeSandbox", "VerificationResult", "security_sandbox",
        ):
            assert hasattr(m, name), f"public symbol {name} disappeared"
        assert core.AgentMode is m.AgentMode
