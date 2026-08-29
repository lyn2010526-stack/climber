# Agent Evolution Round 4

## Required Record

【第4轮】版本v0.4.0|检查点CP-20260822T062500Z-R4|综合分64.6(+1.5)|七维分：认知57 工具66 记忆46 推理56 协作68 安全86 开源73|端到端100%|本轮研究标杆：OpenAI Codex-canonical writable roots and approval boundary|核心问题Top3：字符串前缀路径包含可越界；AUTO忽略显式拒绝；权限API公开BYPASS|候选方案分叉结果：A规范化commonpath预计15/15且约25行但未覆盖blocked glob；B Path.resolve+relative_to+blocked glob预计15/15且约50行；独立测试审查发现S10身份断言需修正并建议3类对抗测试；运行时隔离分支均为只读评审，主会话实测B为22/22|合并方案：规范化路径祖先边界、blocked glob、AUTO拒绝优先、API排除BYPASS(来源:OpenAI Codex标杆+Climber原生适配)|回归：旧116→116 新15 对抗7/7|副作用：[有：相对路径改为基于sandbox workdir；API提交BYPASS由业务400收紧为schema 422；外部symlink路径被拒绝]|记忆新增：最佳实践4 反模式5 开源设计1|距交叉验证还剩2轮|下轮重点：安全-真实认证、管理授权与sandbox fail-closed|状态：[人工确认]

## Initial Configuration

- Climber version: evolution baseline `v0.4.0`, Git HEAD `6b6b1ef8e2aedf862eb29b754320124b9825a0b0`.
- Available model in this execution session: `monkeycode-ai/gpt-5.6-sol`; project model routing remains configuration-driven.
- Connected platform tools used in this round: filesystem read/search/patch, terminal, task forks, skills, documentation/web research, todo tracking, and human question gate.
- Default permission boundary: Climber `DEFAULT`; internal BYPASS remains unavailable through the public configuration API.
- Primary domain: full-stack Agent platform engineering.
- Verified upstream: `openai/codex@00a7b888b23715989db19b74f6cb623ca46be620`.

## Baseline

- Fifteen named scenarios were encoded in `tests/test_evolution_round4_security.py`.
- Initial result: `5 passed, 10 failed in 7.06s`.
- Path boundary failures: sibling-prefix escape, symlink escape, blocked sibling over-match, and two executor-level escape cases.
- Permission failures: AUTO ignored explicit DENY and denied-tools patterns; the API accepted BYPASS and used a broad string schema.

## Candidate Evidence

- Candidate A adapted Codex canonical roots through `realpath/commonpath`.
  Static estimate: `15/15`, approximately 25 changed lines. It did not handle
  the existing `/home/*/.ssh` blocked glob contract.
- Candidate B used Climber-native `Path.resolve(strict=False)`, ancestry
  checks, parent-aware blocked glob matching, typed safe API modes, and deny
  precedence in AUTO. Static estimate: `15/15`, approximately 50 changed lines.
- Independent test review accepted 14 scenarios and corrected S10 from object
  identity to an external value/type contract. It also proposed dangling
  symlink, blocked glob, and invalid JSON type adversarial coverage.
- Candidate B was selected because it covered the existing Climber blocked
  glob configuration and had the stronger boundary contract.

## Implementation And Adaptation

- `SecuritySandbox.validate_file_access()` now resolves paths relative to the
  configured workdir, resolves symlinks, checks path ancestry by components,
  and evaluates blocked glob patterns against the path and its parents.
- `PermissionConfig.evaluate()` now evaluates `denied_tools` and explicit DENY
  rules before AUTO's allow/ask decision.
- `PermissionConfigUpdate.mode` exposes only DEFAULT, ACCEPT_EDITS, PLAN, and
  AUTO. Internal BYPASS remains available only to trusted in-process callers.
- The Codex mechanism was adapted as a root-normalization principle. No Codex
  sandbox source or platform-specific ACL implementation was copied.

## Verification

- New and adversarial suite: `22 passed in 12.94s`.
- Scoped old plus new regression: `138 passed in 66.98s`.
- The scoped total contains 116 existing cases and 22 round-4 cases.
- Ruff, Python compilation, and `git diff --check` passed.
- Security read-only re-review increased the score from 76 to 86.

## Security Stop Gate

Security remains below the required score of 90. Ordinary cognition, memory,
reasoning, collaboration, tool creation, and MCP evolution are paused.

Remaining blockers:

1. HTTP and WebSocket authentication still map callers to a fixed local identity.
2. Permission configuration lacks a trusted administrator authorization boundary.
3. Agent Engine can degrade to `sandbox=None` after sandbox initialization failure.
4. Command execution lacks strong OS-level process, filesystem, and network isolation.
5. File validation and file opening remain separate operations with a TOCTOU window.

## Cost And Evidence Limits

- Local verification wall time recorded: 7.06s RED baseline, 12.94s focused
  GREEN/adversarial, and 66.98s scoped regression.
- Model token and currency telemetry is unavailable in the current task tool
  interface; no fabricated token or cost claim is recorded.
- Candidate forks were independent read-only task contexts. They did not
  modify isolated Git worktrees, so the comparison is labeled static until
  Climber's runtime worktree fork channel supports writable isolation.
