# Round 006 — Degraded Read Boundary + Native Symlink Fix

- Date: 2026-08-23
- Checkpoint: CP-20260822T083000Z-R6
- Security score: 88 → 78 (post-review with new findings)

## Changes

### agent_engine.py
- Added `_get_degraded_sandbox()`: builds fallback SecuritySandbox from env vars when init failed
- Modified sandbox-None branch in `_validate_tool_call`:
  - Rejected command tools, media tools, write tools explicitly
  - File read tools: validated path against degraded sandbox before allowing
  - Added `dir` param to path fallback (fixing list_directory bypass)
- Added `_MEDIA_TOOLS = {"process_video", "process_image"}` to route through sandbox.validate_command()
- Added `_FILE_TOOLS` entries: `list_files` ("directory","read"), `native_list_dir` ("path","read")
- Media tools now validated through sandbox.validate_command() when sandbox is present
- Merged command/media validation branches to reduce duplication
- Moved `import os` to top-level imports

### native_tools.py
- Added `_resolve_within_workspace()`: Path.resolve() + relative_to() for symlink-safe ancestry check
- Updated `_validate_path_within_workspace()`: uses resolve + relative_to instead of startswith
- Updated `_validate_file_path()`: uses `_resolve_within_workspace` instead of _ALLOWED_FILE_ROOTS startswith
- Added validation call to `native_list_dir()` (was missing)
- Fixed `_BLOCKED_PREFIXES`: normalized trailing slashes, added trailing `/` to `/proc`, `/sys`, `/dev` to prevent `/procxfoo` false positive
- Removed dead `_ALLOWED_FILE_ROOTS`
- Moved `from pathlib import Path` to top-level imports

### tests/test_evolution_round6_security.py
- Registered process_video/process_image in _build_engine() (fixing wrong code path)
- Removed duplicate test_write_file_denied_explicitly_when_sandbox_none
- 15 tests covering degraded read boundary, symlink escape, sibling prefix, media tools, write rejection

### tests/test_security_fixes_tools.py
- Updated `test_dotdot_in_path_blocked` assertion to accept new message format

### tests/test_evolution_round6_security.py
- 16 tests covering degraded read boundary, symlink escape, sibling prefix, media tools, write rejection

## Test Results
- Round 6 focused: 16/16 passed
- Round 4 edges: 31/31 passed
- Security regressions: 99 passed, 3 skipped
- Full focused regression: 169 passed, 3 skipped
- Ruff: clean

## Security Review Findings (score 78/100)
1. MEDIUM: process_video/image sandbox bypass — FIXED (added to _MEDIA_TOOLS)
2. LOW: Write-mode bypass in sandbox-None — FIXED (explicit rejection)
3. LOW: download_file lacks internal path validation — deferred
4. INFO: _get_degraded_sandbox trusts CLIMBER_SANDBOX_WORKDIR env var — accepted
5. INFO: native_run redirect operators not blocked — mitigated by main sandbox

## Still Open
- Security score 78 < 90: ordinary optimization still gated
- No writable isolated A/B worktree forks (documented limitation)
- Docker daemon unavailable
- codex-harness repo not found
