# Climber 安全沙箱完整方案与渐进式迁移路径

## 一、当前状态分析（证据驱动）

### 1.1 现有三套沙箱实现

| 文件 | 用途 | 问题 |
|------|------|------|
| `app/core/security_sandbox.py` | 权限系统 + 命令黑名单 + 审计 | 正则可绕过，无编码检测 |
| `app/core/sandbox.py` | 子进程执行 + 资源限制 | 使用 `create_subprocess_shell`，shell 注入风险 |
| `app/tools/mcp_plugins/sandbox_runtime.py` | MCP 插件沙箱 | 独立实现，`TimeoutOut` 拼写错误 |

### 1.2 已确认的安全缺口（5 个 P0）

| # | 缺口 | 攻击向量 | 当前状态 |
|---|------|---------|---------|
| G1 | 编码绕过 | `base64("cm0gLXJmIC8=")` 解码后执行 | ❌ 无检测 |
| G2 | 路径遍历 | `../../../etc/passwd` | ⚠️ 部分（`abspath` 但不 `resolve`） |
| G3 | Shell 注入 | `; rm -rf /` 通过 `subprocess_shell` | ❌ `shell=True` 路径 |
| G4 | 网络无限制 | Agent 发起任意 HTTP 请求 | ❌ 仅环境变量删除代理 |
| G5 | 资源无限制 | fork bomb / 内存耗尽 | ⚠️ 仅 `sandbox.py` 有 |

### 1.3 架构债务

- 三套实现重叠但互不感知：`SecuritySandbox`、`SandboxExecutor`、`SandboxRuntime`
- `ExecutionMode` 枚举重复定义两次
- 审计系统内存存储为主，数据库持久化异步且无错误处理
- 权限系统未接入工具执行管道

---

## 二、目标架构：三级安全管道

```
┌───────────────────────────────────────────────────────────────┐
│                    SafetyPipeline (统一入口)                    │
│                                                               │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │ L1: Static Analysis (零资源开销，执行前拦截)              │  │
│  │  • 命令黑名单正则（含编码解码：base64/hex/url）           │  │
│  │  • 路径白名单 + Path.resolve() 遍历检测                   │  │
│  │  • JSON Schema 参数校验                                  │  │
│  │  • 风险评分 → 决定是否需要 L2/L3                          │  │
│  └─────────────────────────────────────────────────────────┘  │
│                          ↓ PASS                               │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │ L2: Process Isolation (轻量隔离，默认层)                  │  │
│  │  • subprocess.exec (非 shell) + resource limits          │  │
│  │  • 超时控制 + 输出截断 + cgroup v2 (可选)                │  │
│  │  • 网络隔离：unshare(CLONE_NEWNET) 或环境变量清除        │  │
│  │  • seccomp-bpf 系统调用过滤 (Linux)                      │  │
│  └─────────────────────────────────────────────────────────┘  │
│                          ↓ HIGH RISK                          │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │ L3: Container Isolation (强隔离，高风险操作)              │  │
│  │  • Docker/Podman 容器，每次执行一个新容器                 │  │
│  │  • 只读文件系统 (除工作目录)                              │  │
│  │  • 网络隔离 + 资源配额 (CPU/内存/PID)                    │  │
│  │  • seccomp profile + AppArmor                            │  │
│  └─────────────────────────────────────────────────────────┘  │
│                                                               │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │ Audit Trail: 全链路审计日志 (同步写入数据库)              │  │
│  └─────────────────────────────────────────────────────────┘  │
└───────────────────────────────────────────────────────────────┘
```

---

## 三、渐进式迁移路径（4 个 Phase）

### Phase 1: 统一 L1 静态分析 + 修复 P0 缺口（1-2 天）

**目标**：消灭 5 个 P0 安全缺口，统一静态分析入口

- [ ] 创建 `app/core/safety_pipeline.py`：统一 `SafetyPipeline` + `SafetyResult`
- [ ] 实现 `StaticAnalyzer`：
  - 编码解码检测（base64、hex、url-encoding）
  - 路径遍历检测（`Path.resolve()` + 白名单前缀匹配）
  - 命令黑名单正则（扩展现有 HAZARD_COMMANDS）
  - JSON Schema 参数校验
- [ ] 修复 `sandbox.py`：`create_subprocess_shell` → `create_subprocess_exec`
- [ ] 修复 `sandbox_runtime.py`：`TimeoutOut` → `TimeoutError`
- [ ] 添加测试：编码绕过、路径遍历、shell 注入

**验证**：`pytest tests/test_safety_pipeline.py` 全部通过

### Phase 2: 强化 L2 进程隔离 + 接入执行管道（2-3 天）

**目标**：所有工具执行通过 SafetyPipeline，L2 默认启用

- [ ] 重构 `SandboxExecutor`：
  - `subprocess_exec` + 参数列表（非 shell 字符串）
  - `preexec_fn` 资源限制（CPU/内存/文件描述符/PID）
  - 可选 `unshare(CLONE_NEWNET)` 网络隔离
- [ ] 接入 `ToolExecutionPipeline`：所有工具调用前经过 L1 → L2
- [ ] 安全审计：每次执行记录到数据库（同步，不丢日志）
- [ ] 添加资源限制测试：超时、输出截断、内存限制

**验证**：`pytest tests/test_safety_pipeline.py tests/test_tool_pipeline.py`

### Phase 3: 实现 L3 容器隔离 + 配置化（2-3 天）

**目标**：高风险操作默认走 L3，用户可配置

- [ ] 实现 `DockerSandbox`：
  - Docker SDK 集成
  - 只读文件系统 + 工作目录挂载
  - 网络隔离 + 资源配额
  - seccomp profile
- [ ] `SandboxConfig` 增加 `use_docker`、`docker_image` 配置
- [ ] Agent 级别沙箱策略：`agent.sandbox_level` 字段
- [ ] 健康检查：Docker 不可用时自动降级 L2

**验证**：`pytest tests/test_safety_pipeline.py -k docker`

### Phase 4: 清理冗余 + 文档 + 监控（1-2 天）

**目标**：删除旧实现，完善可观测性

- [ ] 删除 `sandbox_runtime.py`（功能并入 `sandbox.py`）
- [ ] 统一 `security_sandbox.py` 中的权限系统接入新管道
- [ ] `ExecutionMode` 枚举去重
- [ ] 前端安全事件面板：审计日志可视化
- [ ] 安全文档：`docs/SECURITY.md`

---

## 四、关键设计决策

| 决策 | 选择 | 原因 |
|------|------|------|
| 统一入口 | `SafetyPipeline` 单例 | 避免三套实现各自为政 |
| 编码检测 | base64 + hex + url | 覆盖常见绕过方式 |
| 进程创建 | `exec` 非 `shell` | 消除 shell 注入 |
| 路径检测 | `Path.resolve()` 后前缀匹配 | 彻底防止遍历 |
| 审计写入 | 同步 + 内存缓冲 | 不丢安全事件 |
| L3 降级 | Docker 不可用 → L2 | 可用性优先 |
| 配置粒度 | Agent 级别 | 不同 Agent 不同安全策略 |

---

## 五、风险评估

| 风险 | 概率 | 影响 | 缓解 |
|------|------|------|------|
| `exec` 模式破坏现有工具调用 | 中 | 高 | 分阶段迁移，兼容层 |
| Docker 不可用 | 高 | 低 | 自动降级 L2 |
| 资源限制过严导致正常任务失败 | 中 | 中 | 可配置限制值 |
| 编码检测误报 | 低 | 中 | 白名单 + 可配置 |

---

## 六、与 LongCat-2.0 路线图对齐

| LongCat 建议 | 本方案对应 |
|-------------|-----------|
| eBPF 实时监控 | Phase 2 可选扩展 |
| 隐私风险评分引擎 | Phase 1 风险评分 |
| 动态安全级别切换 | Phase 3 Agent 级别策略 |
| 分层解耦 + 动态编排 | 三级管道设计 |
| 量化模型 + TEE | 超出沙箱范围，后续 Phase |

