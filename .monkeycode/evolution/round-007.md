# Round 007 — 全面安全加固

- Date: 2026-08-23
- Checkpoint: CP-20260822T083000Z-R6 (continuing)

## Changes

### app/tools/mcp_plugins/dynamic_tool.py
- Added `_validate_code_safety()` with AST-level validation before `exec()`
- Blocks dangerous imports and calls
- Added validation on `_load()` to reject stored tools with unsafe code

### app/tools/mcp_plugins/sandbox_runtime.py
- Replaced `create_subprocess_shell` with `create_subprocess_exec` + `shlex.split()`
- Expanded BLOCKED_PATTERNS from 10 to 30+ patterns (matching HAZARD_COMMANDS from security_sandbox.py)

### app/tools/file_conversion_tools.py
- Added `_validate_conversion_path()` with Path.resolve() + relative_to() ancestry check
- Added path validation to 9 standalone tool functions: convert_file, csv_to_json, json_to_csv, markdown_to_html, html_to_markdown, xml_to_json, json_to_xml, convert_yaml_json, convert_excel, to_markdown_table, to_html_table

### app/tools/builtins.py
- Added HAZARD_COMMANDS validation to `container_exec()` before passing to container shell

### app/core/agent_engine.py
- Cached `get_tool()` result to avoid repeated lookup in `_validate_tool_call`

## Test Results
- AST validation: 9/9 dangerous patterns rejected
- Path validation: 4/4 scenarios correct (workspace, tmp, outside, sibling)
- Full regression: 186 passed, 3 skipped
- Ruff: clean

## Open-source Research: Hermes Agent (NousResearch)
- Key transferable designs: GEPA self-evolution pipeline, three-layer memory, self-healing skills, trajectory compression, four-phase risk-graded evolution
