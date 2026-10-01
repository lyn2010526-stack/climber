# OpenSandbox 深挖（本地到 Kubernetes 的沙箱运行时）

> 核验日期：2026-10-01。结论仅来自本会话已确认的仓库内文档（`docs/references/opensource-eval-42-50.md` #46、`docs/references/open-source-projects.md` #46、`docs/audits/cache-sandbox-review.md`）。本次未读取 OpenSandbox 源码，超出下文记录范围的内容一律标注"未核验"。

## 仓库状态/许可证

- 真实地址：`https://github.com/opensandbox-group/OpenSandbox`，本次核验确认可访问。
- 仓库活动：持续有仓库活动（本次公开页面可确认）；维护强度未核实（不以 star、fork 推断维护质量）。
- 许可证：未核验（本次核验未记录其 LICENSE 信息）。

## 源码入口与调用链（含 URL）

- 已确认入口：`https://github.com/opensandbox-group/OpenSandbox`（官方仓库，README 为本次能力清单的依据）。
- README 层面确认的运行形态：Docker 本地启动、Kubernetes 部署，覆盖本地到 Kubernetes 的沙箱运行时。
- 内部源码入口与调用链：未核验（本次未克隆、未读取源码，模块划分、API 实现路径与调用关系均无证据）。

## 核心机制拆解

README 层面确认的能力概念（内部实现细节未核验）：

1. **统一生命周期 API**：沙箱创建、执行、销毁的统一接口契约。
2. **命令/文件/浏览器执行**：三类执行能力并列提供。
3. **网络出口策略**：对沙箱网络出站做策略控制。
4. **Credential Vault（凭据保险库）**：凭据与沙箱运行时隔离存放。
5. **本地到 Kubernetes 双形态**：本地 Docker 与 K8s 部署共用同一套生命周期契约。

上述五点的实现细节（生命周期 API 具体签名、出口策略实现方式、Vault 加密方案）未核验；本会话仅确认这些概念存在于 README 能力清单。

## Climber 映射（引用本仓文件路径）

| Climber 模块 | 对应关系 |
| --- | --- |
| `app/core/sandbox.py` | `SandboxExecutor` 子进程级隔离（`resource.setrlimit` 限 RLIMIT_AS/CPU/NOFILE/NPROC、`tempfile.mkdtemp` 工作目录隔离、白名单+正则黑名单、`asyncio.wait_for` 超时后 kill），对应 OpenSandbox 生命周期契约的本地对照 |
| `app/core/permission_rules.py` | 三级权限（read_only/partial/full → PLAN/DEFAULT/AUTO），与沙箱联动 |
| `app/core/engine/validation.py` | `_check_permission_rules` 每次工具调用做 DENY/ASK/ALLOW 判定，命中 DENY 不可绕过 |
| `app/core/resource_limits.py` | 资源限制常量收口位置（本次会话确认该文件存在于 `app/core/`，内部机制未核验） |
| `app/core/api_key_crypto.py` | 凭据隔离的本地承载候选（本次会话仅确认文件存在，内部机制未核验） |
| `SandboxConfig.enable_network` | 当前仅为环境变量透传/剥离，非真正网络命名空间隔离；网络出口策略是当前缺口（见 `docs/audits/cache-sandbox-review.md` 5.3 第 4 条） |

## 可借鉴/不采用结论

- **可借鉴（契约层面）**：统一生命周期 API、网络出口策略、Credential Vault 凭据隔离三个契约，对应 `docs/references/opensource-eval-42-50.md` 借鉴优先级第 2 类"阶段性架构参考"。
- **不采用**：直接引入 OpenSandbox 依赖或 Kubernetes 部署形态。Climber 当前环境约束为容器内运行、无 Docker-in-Docker，`docs/audits/cache-sandbox-review.md` 5.3 已明确沙箱改进走"统一收口而非推倒重来"路线（共享常量、setrlimit 补齐、mkdtemp 统一、出站白名单）。
- 阶段定位（见 `docs/references/open-source-projects.md` #46）：🔧 部分。

## 证据等级

| 记录内容 | 等级 |
| --- | --- |
| 仓库地址、可访问、持续有仓库活动、README 能力清单（Docker/K8s/生命周期 API/三类执行/出口策略/Vault） | 已核验（本会话公开页面确认，记录于 `docs/references/opensource-eval-42-50.md`、`docs/references/open-source-projects.md`） |
| Climber `app/core/sandbox.py`、`app/core/permission_rules.py`、`app/core/engine/validation.py`、`SandboxConfig.enable_network` 现状 | 已核验（本仓只读调研，记录于 `docs/audits/cache-sandbox-review.md`） |
| `app/core/resource_limits.py`、`app/core/api_key_crypto.py` | 存在已核验（本会话目录清点），内部机制未核验 |
| OpenSandbox 许可证、维护强度、内部源码调用链 | 未核验 |
