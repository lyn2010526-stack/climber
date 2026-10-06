# E2B 深挖（云端隔离沙箱基础设施）

> 核验日期：2026-10-01（同日补充核验：仓库重组结构、SDK/runtime 源码入口、许可证）。结论仅来自本会话已核验的 E2B 公开仓库信息与源码结论，以及仓库内文档（`docs/references/opensource-eval-42-50.md` #45、`docs/references/open-source-projects.md` #45、`docs/audits/cache-sandbox-review.md`、`docs/integration/OPEN_SOURCE_INTEGRATION.md`、`docs/OPEN_SOURCE_COMPARISON.md`）。仍未核验项逐条标注。

## 仓库状态/许可证

- 地址：`https://github.com/e2b-dev/E2B`，本次核验确认可访问。
- 定位：官方 README 定位为云端隔离沙箱基础设施。
- 仓库重组（本次已核验）：主仓库已重组为纯 SDK monorepo，`packages/` 下 7 包——`cli`、`js-sdk`、`python-sdk`、`code-interpreter-js`、`code-interpreter-python`、`desktop-js`、`desktop-python`；基础设施（orchestrator、envd 等）迁至独立仓库 `https://github.com/e2b-dev/runtime`。
- 许可证：双仓库均 Apache-2.0（本次已核验）。
- 托管闭源侧：E2B Cloud 控制面、dashboard 私有仓库、orchestrator-ee 均闭源（本次已核验其存在与闭源属性）。

## 源码入口与调用链（含 URL）

- 主仓库入口：`https://github.com/e2b-dev/E2B`（SDK monorepo）。
- SDK 侧源码（本次已核验）：
  - `https://github.com/e2b-dev/E2B/tree/main/packages` — 7 包目录（cli/js-sdk/python-sdk/code-interpreter-js/code-interpreter-python/desktop-js/desktop-python）。
  - `https://github.com/e2b-dev/E2B/blob/main/packages/js-sdk/src/sandbox/index.ts` — JS SDK `Sandbox` 类。
  - `https://github.com/e2b-dev/E2B/blob/main/packages/python-sdk/e2b/sandbox_sync/main.py` — Python SDK 同步 `Sandbox` 实现。
- 基础设施侧源码（e2b-dev/runtime，本次已核验）：
  - `https://github.com/e2b-dev/runtime` — 基础设施仓库入口。
  - `https://github.com/e2b-dev/runtime/blob/main/packages/envd/main.go` — envd 守护进程入口，沙箱内服务端口 49983。
  - `https://github.com/e2b-dev/runtime/blob/main/packages/envd/internal/services/filesystem/service.go` — envd 文件服务。
  - `https://github.com/e2b-dev/runtime/tree/main/orchestrator/pkg/sandbox/fc/` — Firecracker 微 VM 驱动。
  - `https://github.com/e2b-dev/runtime/tree/main/pkg/network/` — 网络槽位 + nftables egress。
  - `https://github.com/e2b-dev/runtime/tree/main/pkg/tcpfirewall/` — SNI 域名防火墙。
- 调用链（本次源码级核验）：SDK `Sandbox` 类（js-sdk `sandbox/index.ts` / python-sdk `sandbox_sync/main.py`；沙箱寿命上限 Hobby 1h / Pro 24h 写死在 SDK 侧）→ orchestrator 经 Firecracker 驱动（`orchestrator/pkg/sandbox/fc/`）拉起微 VM → 网络槽位分配与 nftables egress（`pkg/network/`）+ SNI 域名防火墙（`pkg/tcpfirewall/`）控制出站 → 沙箱内 envd（`packages/envd/main.go`，端口 49983）承载命令执行、文件服务（`internal/services/filesystem/service.go`）等 SDK 能力。

## 核心机制拆解

本次已确认的机制概念（README 层面 + 本次源码级核验）：

1. **硬件级隔离**：沙箱为 Firecracker 微 VM（`orchestrator/pkg/sandbox/fc/`），硬件级隔离与 Climber 进程级 RLIMIT 隔离存在能力层级差异。
2. **envd 沙箱内服务**：入口 `packages/envd/main.go`，端口 49983；命令执行与文件服务（`internal/services/filesystem/service.go`）是 SDK 能力的服务端承载。
3. **网络边界**：网络槽位 + nftables egress（`pkg/network/`）、SNI 域名防火墙（`pkg/tcpfirewall/`）实现出站控制。
4. **沙箱寿命**：上限 Hobby 1h / Pro 24h，写死在 SDK 侧。
5. **多语言 SDK**：JS 与 Python SDK 均以 `Sandbox` 类为入口；CLI、Code Interpreter、Desktop 为 `packages/` 下并列能力包。
6. **开闭源边界**：SDK 与 runtime 双仓库开源（均 Apache-2.0）；控制面、dashboard、orchestrator-ee 闭源托管。

沙箱生命周期与资源边界是借鉴方向；CPU/内存级资源配额细节仍未核验。

## Climber 映射（引用本仓文件路径）

| Climber 模块 | 对应关系 |
| --- | --- |
| `app/core/sandbox.py` | `SandboxExecutor` 主路径（DI 注册，供 `run_command`/`stream_command` 工具使用）：命令白名单 + 正则黑名单双重过滤、`_restrict_resources()` 用 `resource.setrlimit` 限 RLIMIT_AS/RLIMIT_CPU/RLIMIT_NOFILE/RLIMIT_NPROC（随 `preexec_fn` 注入子进程）、`tempfile.mkdtemp` 临时工作目录隔离、敏感路径硬编码拦截（`/etc/shadow` 等）、`asyncio.wait_for` 超时后 `proc.kill()`；**仍是进程级隔离，保留与 E2B 硬件级隔离（Firecracker 微 VM）的能力层级差异**；唯一缺口是无执行前语法/静态检查 |
| `app/workflow/code_sandbox.py` + `app/workflow/safe_code.py` | 仓库内质量最高的沙箱实现（AST 白名单静态校验、禁止危险 import、`python -I` 隔离模式、`RLIMIT_FSIZE=0`），但仅服务工作流代码节点，agent 工具链不会走到 |
| `app/tools/native_tools.py` | native_mode 工具：仅 `asyncio.wait_for` 超时控制，无 `resource.setrlimit`，内存/进程数不受限 |
| `app/tools/builtins.py` | `container_exec` 直接 `subprocess.run`，仅超时限制，依赖外部 Docker |
| `app/core/engine/validation.py` | 三级权限（read_only/partial/full）后端强制执行，`_check_permission_rules` 每次工具调用 DENY/ASK/ALLOW 判定 |

## 可借鉴/不采用结论

- **可借鉴**：沙箱生命周期和资源边界两个概念，对应 `docs/references/opensource-eval-42-50.md` 借鉴优先级第 2 类"阶段性架构参考"。
- **能力差异标注（保留现状）**：`app/core/sandbox.py` 仍是进程级 RLIMIT 隔离，与 E2B 硬件级隔离（Firecracker 微 VM）的能力层级差异必须持续标注，不以"已有沙箱"掩盖隔离层级差距（见 `docs/references/open-source-projects.md` #45 与已落地对照表）。
- **不采用**：引入 E2B 依赖或云端服务。`docs/audits/cache-sandbox-review.md` 5.3 明确当前环境约束为容器内运行、无 Docker-in-Docker，沙箱改进走"统一收口而非推倒重来"轻量路线（共享 `app/core/resource_limits.py` 常量、setrlimit 补齐、mkdtemp 统一、出站白名单），重量级方案与投入产出比结论相悖。
- **历史集成设想（未实施）**：`docs/integration/OPEN_SOURCE_INTEGRATION.md` 曾列出"Sandboxed Python: E2B/Docker 隔离执行"与"增强 `sandbox.py` 支持 E2B 远程执行"，`docs/OPEN_SOURCE_COMPARISON.md` 列表提及"E2B 代码沙箱"；均为设想条目，本次无实施证据。
- 阶段定位（见 `docs/references/open-source-projects.md` #45）：🔧 部分。

## 证据等级

| 记录内容 | 等级 |
| --- | --- |
| 仓库地址、可访问、README 定位（云端隔离沙箱）、JS/Python SDK、命令执行、Code Interpreter、Desktop 能力 | 已核验（前次会话公开页面确认，记录于 `docs/references/opensource-eval-42-50.md`、`docs/references/open-source-projects.md`） |
| 主仓库重组为纯 SDK monorepo（`packages/` 7 包）、基础设施迁至 e2b-dev/runtime、双仓库均 Apache-2.0 | 已核验（本次会话公开仓库核验） |
| SDK `Sandbox` 类（js-sdk/python-sdk）、envd `main.go` 端口 49983、文件服务 `service.go`、Firecracker 驱动、网络槽位 + nftables、SNI 防火墙、寿命上限 Hobby 1h/Pro 24h 写死 SDK | 已核验（本次会话源码核验） |
| 托管闭源侧（E2B Cloud 控制面、dashboard 私有仓库、orchestrator-ee） | 已核验（本次会话公开仓库核验） |
| Climber `app/core/sandbox.py`、`app/workflow/code_sandbox.py`、`app/workflow/safe_code.py`、`app/tools/native_tools.py`、`app/tools/builtins.py`、`app/core/engine/validation.py` 现状 | 已核验（本仓只读调研，记录于 `docs/audits/cache-sandbox-review.md`） |
| 维护强度 | 未核验 |
| CPU/内存级资源配额细节 | 未核验（寿命上限与网络边界已核验，配额机制细节本次未记录） |
| 历史集成设想是否已实施 | 未核验（文档仅列为设想） |
