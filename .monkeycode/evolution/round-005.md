# Agent Evolution Round 5

## Required Record

【第5轮】版本v0.5.0|检查点CP-20260822T070000Z-R5|综合分64.9(+0.3)|七维分：认知57 工具66 记忆46 推理56 协作68 安全88 开源73|端到端100%|本轮研究标杆：OpenAI Codex-explicit approval policy and writable capability boundary|核心问题Top3：sandbox初始化失败时副作用工具放行；debug recovery绕过统一验证与审批；工具名称可伪装成只读能力|候选方案分叉结果：首版名称集合方案聚焦26/26但独立终审44/100并发现debug直调注册表及大量别名遗漏；正向能力声明方案聚焦29/29但终审87/100并发现ASK与MCP同名绕过；终版显式安全元数据+拒绝传播方案聚焦31/31且终审88/100；本轮无可写隔离A/B分支，候选证据标记为串行证伪|合并方案：sandbox故障默认拒绝、受信纯/读取工具显式声明、debug retry复用验证并保留审批拒绝(来源:OpenAI Codex标杆+Climber原生适配)|回归：旧181→181 新31 对抗10/10|副作用：[有：未声明工具在sandbox故障时被拒绝；读取工具保留宿主可读范围；策略拒绝不再触发自动恢复]|记忆新增：最佳实践3 反模式4 开源设计1|距交叉验证还剩1轮|下轮重点：安全-读取机密性边界与native symlink防护|状态：[人工确认]

## Initial Configuration

- Git HEAD: `6b6b1ef8e2aedf862eb29b754320124b9825a0b0`.
- Initial tracked diff SHA-256: `a84d764b047edbbb1558b5a9a07916d3fbf6f6724afa956d4e2f45df3c137799`.
- Approved scope: fail closed when the security sandbox cannot initialize.
- Preserved compatibility: explicitly trusted pure and read-only tools remain available.
- Excluded scope: authentication, administrator authorization, MCP registration changes, new high-risk tools, sandbox expansion, and OS/container isolation.
- Verified upstream remains `openai/codex@00a7b888b23715989db19b74f6cb623ca46be620`.

## Threat Boundary

- Asset: host files, command execution, external side effects, and approval integrity.
- Trust boundary: model-selected tool calls and debug-loop generated retry calls.
- Abuse cases: sandbox initialization exception, dynamic tool registration, MCP name collision, retry tool switching, and ASK decision bypass.
- Required invariant: a failed policy layer cannot increase tool authority.

## TDD Evidence

- Initial reproduction: `write_file` and `run_command` were allowed with `sandbox=None`.
- Expanded RED: `6 failed, 20 passed`; native command, streaming command, container command, native write, and download aliases were all allowed.
- First GREEN: `26 passed`; explicit aliases were denied.
- Independent review invalidated the name-list design because debug recovery called `ToolRegistry.execute()` directly and registered tools exceeded the hand-maintained aliases.
- Positive capability RED introduced an unsupported registration contract and failed all 28 fixture setups.
- Positive capability GREEN: `29 passed`; unclassified dynamic tools defaulted to deny and sandbox policy rejection skipped recovery.
- Final adversarial RED reproduced MCP `read_file` name inheritance and ASK retry behavior.
- Final GREEN: `31 passed in 15.08s`.

## Implementation

- `ToolDefinition.sandbox_safe_when_unavailable` defaults to `False` and is propagated through local registration and decorators.
- MCP registration retains the safe default and cannot inherit a capability from its name.
- Selected built-in pure and read-only tools explicitly opt into degraded operation.
- `AgentEngine._validate_tool_call()` denies every unclassified tool when `sandbox=None`.
- Debug retry calls `_validate_tool_call()` before registry execution.
- ASK results return a permission denial to the recovery loop and execute zero tools.
- Initial sandbox and permission denial results skip automatic recovery.
- Recovery output carrying a policy denial cannot overwrite the original failed tool result.

## Verification

- Focused Agent Engine suite: `31 passed in 15.08s`.
- Final scoped regression: `212 passed in 107.50s`.
- Scoped total: 181 existing cases and 31 focused cases.
- Ruff, Python compilation, and `git diff --check` passed.
- An earlier regression command referenced absent `tests/test_tools.py`; it ran zero tests and was discarded. The corrected command used existing `test_unified_tools.py` and `test_tool_runtime.py`.
- Final read-only security review closed the debug ASK and MCP name-collision findings.

## Residual Risks And Side Effects

- Security score is `88/100`, below the mandatory 90-point gate.
- Explicitly trusted read tools remain available when sandbox initialization fails; built-in `read_file` can access any host-readable path.
- `native_read_file` uses an `abspath`-based internal check and can mis-handle workspace symlinks.
- `native_list_dir` lacks the canonical path boundary used by `SecuritySandbox`.
- Policy rejection propagation still uses string prefixes rather than a structured result type.
- Pure analysis tools without an explicit capability declaration lose availability during sandbox failure. This is a safe degradation.
- Fixed local identity, administrator authorization, OS isolation, and file-open TOCTOU remain unresolved from round 4.

## Candidate Evidence Limit

- Independent task reviewers provided static candidate and security analysis.
- No writable isolated worktree candidate was available in this round.
- The three implementations were sequential RED/GREEN refinements in the shared worktree, so they are recorded as serial falsification rather than independent A/B execution.

## Cost

- Recorded test wall time: focused RED 13.07s, intermediate GREEN runs 12.44s to 15.61s, final focused 15.08s, final scoped regression 107.50s.
- Model token and currency telemetry is unavailable; no estimated value is presented as measured cost.
