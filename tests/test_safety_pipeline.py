"""TDD: Safety Pipeline L1 — all P0 gaps must be blocked."""

import os
import tempfile
from pathlib import Path

os.environ.setdefault("APP_TESTING", "true")

from app.core.safety_pipeline import StaticAnalyzer, SafetyResult, RiskLevel


def test_blocks_hazardous_command():
    sa = StaticAnalyzer()
    result = sa.check_command("rm -rf /")
    assert not result.allowed
    assert result.layer == "L1"


def test_blocks_base64_encoded_bypass():
    """G1: base64-encoded rm -rf must be detected."""
    import base64
    encoded = base64.b64encode(b"rm -rf /home/user").decode()
    sa = StaticAnalyzer()
    result = sa.check_command(encoded)
    assert not result.allowed, f"base64 bypass not detected: {encoded}"


def test_blocks_hex_encoded_bypass():
    """G1: hex-encoded command must be detected."""
    hex_cmd = "726d202d7266202f686f6d65"  # "rm -rf /home"
    sa = StaticAnalyzer()
    result = sa.check_command(hex_cmd)
    assert not result.allowed, f"hex bypass not detected: {hex_cmd}"


def test_blocks_path_traversal():
    """G2: path traversal via ../ must be blocked."""
    sa = StaticAnalyzer()
    with tempfile.TemporaryDirectory() as tmp:
        result = sa.check_path(f"{tmp}/../../etc/passwd", allowed_dirs=[tmp])
        assert not result.allowed, "path traversal not blocked"


def test_blocks_symlink_traversal():
    """G2: symlink outside allowed dirs must be blocked."""
    sa = StaticAnalyzer()
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "secret_link"
        try:
            target.symlink_to("/etc/passwd")
        except OSError:
            return  # skip if symlinks not supported
        result = sa.check_path(str(target), allowed_dirs=[tmp])
        assert not result.allowed, "symlink traversal not blocked"


def test_blocks_shell_injection():
    """G3: shell metacharacters outside quotes must be blocked."""
    sa = StaticAnalyzer()
    result = sa.check_command("ls ; rm -rf /")
    assert not result.allowed
    assert not result.allowed


def test_blocks_pipe_injection():
    """G3: pipe to shell must be blocked."""
    sa = StaticAnalyzer()
    result = sa.check_command("cat /etc/passwd | bash")
    assert not result.allowed


def test_blocks_subshell():
    """G3: $(...) subshell must be blocked."""
    sa = StaticAnalyzer()
    result = sa.check_command("echo $(rm -rf /)")
    assert not result.allowed


def test_allows_safe_command():
    sa = StaticAnalyzer()
    result = sa.check_command("python3 script.py --arg value")
    assert result.allowed


def test_allows_safe_path():
    sa = StaticAnalyzer()
    with tempfile.TemporaryDirectory() as tmp:
        safe = Path(tmp) / "subdir" / "file.txt"
        safe.parent.mkdir()
        safe.write_text("ok")
        result = sa.check_path(str(safe), allowed_dirs=[tmp])
        assert result.allowed


def test_blocks_blocked_system_paths():
    sa = StaticAnalyzer()
    result = sa.check_path("/etc/shadow", allowed_dirs=["/tmp"])
    assert not result.allowed


def test_validates_json_schema():
    sa = StaticAnalyzer()
    schema = {
        "type": "object",
        "properties": {
            "path": {"type": "string"},
            "count": {"type": "integer"},
        },
        "required": ["path"],
    }
    result = sa.validate_schema(schema, {"path": "/tmp", "count": 5})
    assert result.allowed

    result = sa.validate_schema(schema, {"count": 5})
    assert not result.allowed  # missing required

    result = sa.validate_schema(schema, {"path": 123})
    assert not result.allowed  # wrong type


def test_risk_assessment():
    sa = StaticAnalyzer()
    assert sa.assess_risk("rm -rf /") == RiskLevel.CRITICAL
    assert sa.assess_risk("ls -la") == RiskLevel.LOW
    assert sa.assess_risk("git push") == RiskLevel.MEDIUM


def test_quoted_metacharacters_allowed():
    """Metacharacters inside quotes should NOT be flagged."""
    sa = StaticAnalyzer()
    result = sa.check_command("echo 'hello; world'")
    assert result.allowed, "quoted semicolars should be safe"
