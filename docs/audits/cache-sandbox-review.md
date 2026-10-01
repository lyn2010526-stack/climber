# Climber 缓存机制与脚本前置校验/沙箱现状调研报告

> 生成时间：2026-10-01 | 生成方式：全仓库只读调研（explore agent），未修改任何代码。
> 对应设计文档痛点：`docs/DESIGN.md` 第 ③ 条"缓存机制不完善、脚本无前置测试、底层隐性bug大量留存，长期使用隐患极高"，以及 1.4 节"三级权限安全体系"要求的"沙箱前置校验、脚本预测试、缓存容错、隐患拦截"。

## 一、结论概览

1. **缓存层**：仅有一个正式的 Redis 缓存封装（`app/storage/cache.py`），已支持 TTL，但**实际业务代码中零调用**，`@cached` 装饰器未被任何函数使用；另有 3 处内存字典当作"缓存"使用（`ModelRegistry._models`、`ToolPrioritizer._stats/_description_cache`、`PersistentMemory._cache`），**均无 TTL、无大小上限、无清理机制**，存在长期运行内存无限增长风险。
2. **脚本/代码执行沙箱**：已有三套独立实现（`app/core/sandbox.py`、`app/workflow/code_sandbox.py` + `safe_code.py`、`app/tools/native_tools.py`），具备 `resource.setrlimit` 资源限制、AST 静态校验、黑名单过滤、超时控制，但**三套实现彼此不复用、校验规则不一致**，且 `app/tools/builtins.py` 中仍有未经校验的 `read_file`/`write_file` 旧实现与经过校验的版本并存。
3. **脚本预测试/dry-run**：`task_worker.py` 的 factory 执行链路中**没有任何预测试或 dry-run 机制**，`_check_objective` 只校验目标文本是否清晰，不涉及工具调用的沙箱预跑。
4. **权限分级**：三级权限（`read_only/partial/full`）**是真实的后端强制执行**，不是前端展示层面的标签，在 `app/core/engine/validation.py` 的 `_check_permission_rules` 中对每次工具调用做 DENY/ASK/ALLOW 判定，命中 DENY 后续审批无法绕过。

## 二、缓存现状详细排查

### 2.1 缓存层清单

| 缓存实现 | 文件位置 | 缓存内容 | TTL | 失效/清理机制 | 大小上限 | 实际调用方 |
|---|---|---|---|---|---|---|
| Redis 封装 `Cache` 类 | `app/storage/cache.py` | 通用 key-value，任意可 JSON 序列化对象 | 支持，`set(ttl=300)` 默认 300s | 有 `delete()`/`expire()` API，但**无人调用** | Redis 自身 maxmemory 策略（未在代码中配置） | 仅 `app/main.py`（启动时 ping 检测）、`doctor.py`（健康检查）。**没有任何业务逻辑调用 `Cache.get/set`** |
| `@cached` 装饰器 | `app/storage/cache.py:106` | 函数级缓存，key 由参数 md5 拼接 | 支持，默认 300s | 依赖 Redis TTL 自然过期，无主动失效 | 无 | **全仓库搜索为 0 次使用**，纯死代码 |
| `ModelRegistry._models` | `app/models/registry.py:55` | provider:model_id → ModelAdapter 实例，含 API key 相关的多 key 后缀变体 | 无 | 无清理方法，仅在进程生命周期内持续追加 | 无上限 | 每次 `register_keys()` 调用都新增条目，key 轮换场景下条目只增不减 |
| `ToolPrioritizer._stats` / `_description_cache` | `app/core/tool_prioritizer.py:50-51` | 工具调用统计（defaultdict）与工具描述文本 | 无 | 无 | 无上限 | 每次 `rank_tools()` 调用都可能新增 key，长会话下随工具种类增长可控，但无防护 |
| `PersistentMemory._cache` | `app/skills/memory_manager.py:33` | Agent 记忆条目列表（list，非 dict） | 无 | 仅有手动 `clear()` 方法，无自动触发 | 无上限，`store()` 无限 `append` | `app/skills/builtins.py` 中记忆相关工具直接调用；**这是最值得关注的一处**——长时间运行的 agent 会话会让这个 list 无限增长，`recall()` 虽然用 `limit` 截断返回值但不截断底层存储 |

### 2.2 一致性问题证据

- `app/storage/cache.py` 的 `Cache.delete()` 存在但无调用方，说明即使未来接入 Redis 缓存，也没有写操作后清理缓存键的配套逻辑——典型的"只建了缓存写入接口，没建失效接口"的半成品状态。
- `ModelRegistry.register_keys()`（第146-177行）每次注册都在 `_models` 字典里新增 `cache_key`，没有对应的注销/替换逻辑；如果同一个 provider+model 的 key 被多次轮换注册，旧的 adapter 实例会一直驻留在字典里得不到释放。

### 2.3 监控与大小限制现状

- 唯一有主动内存监控的是 `app/core/memory_guardian.py`，但它监控的是**进程整体 RSS**，触发阈值后只会调用 `gc.collect()` 和注册的 relief 回调，**目前没有任何模块向 `MemoryGuardian.register_relief()` 注册缓存驱逐回调**（搜索 `register_relief` 全仓库只有 guardian 自身定义，无调用方）。也就是说"内存爆了就触发缓存清理"这个闭环目前是断的。
- 没有任何缓存命中率统计。

## 三、代码执行/脚本前置测试现状排查

### 3.1 三套并行的执行/沙箱实现

**(a) `app/core/sandbox.py` — `SandboxExecutor`（主路径，DI 注册为 `SandboxExecutor`，供 `run_command`/`stream_command` 工具使用）**
- 命令白名单 + 正则黑名单双重过滤（`allowed_commands`、`blocked_patterns`）
- `_restrict_resources()` 用 `resource.setrlimit` 限制 `RLIMIT_AS`（内存）、`RLIMIT_CPU`、`RLIMIT_NOFILE`、`RLIMIT_NPROC`，随 `preexec_fn` 注入子进程
- 临时工作目录隔离（`tempfile.mkdtemp`），敏感路径硬编码拦截（`/etc/shadow` 等）
- 超时用 `asyncio.wait_for` 包装，超时后 `proc.kill()`
- 相对完善，**唯一缺口**是没有执行前的语法/静态检查（纯 shell 层面的命令过滤，不检查脚本内容本身的逻辑风险）

**(b) `app/workflow/safe_code.py` + `app/workflow/code_sandbox.py` — 工作流代码节点专用**
- `safe_code.py` 做**真正的 AST 静态校验**：白名单 AST 节点类型、禁止访问 `_` 开头属性、禁止危险 import（仅放行 `json/math/datetime/re/collections/itertools/statistics/string`）、拒绝巨大指数幂运算防 DoS
- `code_sandbox.py` 用子进程隔离执行，`resource.setrlimit` 限制内存/CPU/文件数/文件大小（`RLIMIT_FSIZE=0` 禁止写文件），用 `python -I`（isolated mode）启动子解释器防止读取用户站点配置
- 这是仓库里**质量最高**的沙箱实现，但**只服务于 `app/workflow/engine.py` 的工作流代码节点**，agent 工具调用链路（`task_worker.py`/`agent_engine.py`）完全不会走到这里

**(c) `app/tools/native_tools.py` — "native_mode" 下的无限制系统访问工具**
- 命令白名单（`allowed_binaries`）+ 危险 shell 模式黑名单（分号/管道/反引号等）
- 路径访问用前缀黑名单（`_BLOCKED_PREFIXES`）+ 允许根（`_ALLOWED_FILE_ROOTS`）双重判断
- **没有 `resource.setrlimit`，没有超时之外的资源限制**，`native_run` 只用 `asyncio.wait_for` 控制超时，内存/进程数不受限
- 设计定位本身比 (a)(b) 宽松，依赖 `native_mode=True` 门槛，但一旦开启，资源限制明显弱于 `core/sandbox.py`

**此外** `app/tools/builtins.py` 里还有第四套未经任何路径校验的 `read_file`/`write_file`（第159-176行），直接 `open()` 任意路径，**没有调用 `_validate_file_path` 之类的函数**，与同文件里受 DI 注入、经过 `SandboxExecutor` 校验的 `run_command` 形成鲜明反差——典型的"同一文件里新旧实现并存，安全基线不一致"的隐患来源。

### 3.2 高风险执行方式统计

`subprocess`/`Popen` 出现在以下文件：
- `app/core/sandbox.py`（✅ 有 `resource.setrlimit`）
- `app/workflow/code_sandbox.py`（✅ 有 `resource.setrlimit` + `python -I`）
- `app/tools/native_tools.py`（⚠️ 仅超时，无内存/进程限制）
- `app/tools/builtins.py`（`container_exec` 直接 `subprocess.run`，⚠️ 仅超时限制，依赖外部 Docker）
- `app/core/engine/runtime_capsule.py`、`app/core/security_sandbox.py`、`app/headless/workspace.py`、`app/simulation/experiments.py`——未逐一深入，建议后续按同样方法排查

没有发现裸露的 `eval()`/`exec()` 用于执行用户指令（`app/tools/builtins.py` 的 `_safe_eval_math` 和 `app/workflow/safe_code.py` 的 `safe_eval` 都是带 AST 校验的受限版本，属于正确做法）。

### 3.3 factory 执行链路中的"预测试"缺口

`task_worker.py` 的 `handle_factory_run`（第696-847行）流程是：目标校验 → 调用 LLM 生成计划 → 按步骤顺序调用 `agent_handler` 真实执行，**没有任何环节对计划中即将调用的工具参数做静态校验或 dry-run**。唯一的"安全阀"是运行期的权限评估（`_check_permission_rules`），这是**执行时拦截**而非**执行前预测试**。`_check_objective`（第510-534行）只负责判断目标文本是否清晰，不涉及工具调用安全性。

## 四、安全权限分级现状

### 4.1 三级权限是真实后端强制，不是展示层标签

证据链：`app/api/v1/routes/reasoning.py` 的三档（`read_only/partial/full`）直接映射到 `app/core/permission_rules.py` 的 `PermissionMode`（`PLAN/DEFAULT/AUTO`），`PermissionConfig.evaluate()` 在 `app/core/engine/validation.py:144` 被**每次工具调用前**真实调用，返回 `DENY` 时在同文件147行直接拒绝执行（`return False, ...`），不经过模型或前端二次确认即可拦截。`read_only`（PLAN 模式）在 `evaluate()` 里是硬编码只放行 `_PLAN_READ_TOOLS` 白名单，其余一律 DENY（第193-197行）——这是真实的写操作/命令执行拦截，不是前端标签。

此外还有一套"legacy permission overlay"（`app/core/security_sandbox.py` 的 `PermissionOverlay`），在 `_check_permission_overlay` 中并行生效，两套权限系统**同时存在**，增加了维护和审计复杂度，建议后续评估是否收敛为一套。

### 4.2 `_SIDE_EFFECT_TOOLS` 安全契约（本轮已修复部分）

`task_worker.py:498-507` 定义了 `_SIDE_EFFECT_TOOLS` 冻结集合（`write_file/edit_file/append_file/file_delete/run_command/http_request/web_search/fetch/post_message`），`_step_has_side_effects()` 用于在 `handle_factory_run` 第780行判定当前步骤是否可重试——命中副作用工具的步骤不会被任务级重试覆盖，避免重复写入/重复发送。这是一个很好的参考模式：用一个集中维护的工具名单 + 判定函数，在关键执行路径前做"契约检查"。下节的沙箱前置校验建议复用同样的代码风格（集中黑名单 + 独立判定函数 + 调用处仅一行判断）。

## 五、设计建议（可落地）

### 5.1 缓存层改进

| 建议 | 对应文件 | 改动规模 | 优先级 |
|---|---|---|---|
| 给 `PersistentMemory._cache` 加硬上限（如 `maxlen=2000`，用 `collections.deque` 替换 `list`），超限时 FIFO 丢弃最旧条目 | `app/skills/memory_manager.py` | 小 | **高**（唯一会随 agent 长会话无限增长的内存结构） |
| 给 `ModelRegistry._models` 增加 `unregister_key()` 方法，key 轮换时清理旧 adapter；字典加软上限告警（超过如 200 条时打 warning 日志） | `app/models/registry.py` | 小 | 中 |
| 给 `ToolPrioritizer._stats`/`_description_cache` 增加 LRU 上限（如 500），防止工具种类爆炸式增长场景下内存泄漏 | `app/core/tool_prioritizer.py` | 小 | 低 |
| 把 `app/storage/cache.py` 的 `Cache.delete()` 真正接入业务：写操作成功后清理对应读缓存 key，建立"写后失效"约定 | `app/storage/cache.py` + `app/tools/builtins.py` | 中 | 中 |
| 给 `MemoryGuardian` 的 hard threshold 回调注册一个"缓存驱逐"relief，打通"内存告警→主动清缓存"闭环 | `app/core/memory_guardian.py` + `app/main.py` | 小 | 中 |
| 删除或标注 `@cached` 装饰器为"暂未启用"，避免后来者误以为它在生效 | `app/storage/cache.py` | 小 | 低 |

### 5.2 脚本/代码执行前置校验方案

| 建议 | 对应文件/函数位置 | 改动规模 | 优先级 |
|---|---|---|---|
| 把 `app/tools/builtins.py` 中裸露的 `read_file`/`write_file`（第159-176行）改为调用 `app/tools/native_tools.py` 已有的 `_validate_file_path()`，消除同一文件内双重安全基线 | `app/tools/builtins.py` 第159-176行 | 小 | **高**（最容易被忽视的真实漏洞点：两个同名能力，一个有路径校验一个没有） |
| 在 `SandboxExecutor.execute()` 入口增加轻量"预检"钩子：对 `python`/`node` 等解释型命令，执行前先对脚本文件内容跑一次 `ast.parse()`（复用 `safe_code.py` 现成的 `validate_code_ast`），语法错误或命中危险 AST 节点直接拒绝 | `app/core/sandbox.py`，新增 `_precheck_script()`，在 `execute()` 的 `is_safe` 判断之后、`create_subprocess_exec` 之前调用 | 中 | 中 |
| 仿照 `_SIDE_EFFECT_TOOLS` + `_step_has_side_effects()` 模式，在 `handle_factory_run` 计划生成后增加 `_precheck_plan_tools()`：遍历 plan 里每一步引用的 tools，交叉比对 `_SIDE_EFFECT_TOOLS` 与当前会话权限等级，`read_only` 会话的计划中出现副作用工具则在计划阶段标记为 `blocked`，而不是等执行时才被逐步拦截 | `app/core/task_worker.py`，新增函数紧邻 `_step_has_side_effects`（507行后） | 小 | **高**（最贴合"脚本预测试"诉求、且改动量最小——把运行时拦截提前到计划阶段做批量预检，复用已有常量和风格） |
| `native_run` 参照 `core/sandbox.py` 补齐 `resource.setrlimit`（内存、进程数），当前只有超时控制 | `app/tools/native_tools.py` 第65-70行 | 小 | 中 |
| `container_exec` 的 `subprocess.run` 增加命令内容的危险模式黑名单校验（复用 `SandboxConfig.blocked_patterns`），当前完全没有过滤 | `app/tools/builtins.py` 第525-547行 | 小 | 中 |

### 5.3 沙箱隔离建议（轻量方案，不依赖额外基础设施）

当前环境约束：容器内运行、无 Docker-in-Docker、优先 Python 标准库方案。已有 `resource.setrlimit` 基础，建议统一收口而非推倒重来：

1. **统一资源限制配置入口**（小改动，高优先级）：`SandboxConfig` 和 `code_sandbox.py` 的模块级常量（`_MAX_MEMORY_BYTES` 等）是两份独立定义的限制值，建议提取共享的 `app/core/resource_limits.py` 存放默认值常量，避免漂移。
2. **文件描述符与进程数限制补齐到 `native_tools.py`**（已在5.2提出）。
3. **工作目录隔离统一用 `tempfile.mkdtemp` 模式**：`native_run` 支持 `cwd` 参数但默认不强制隔离，建议默认也用临时目录，调用方显式传 `cwd` 时才例外放行，且仍需经过路径校验。
4. **网络隔离**（标准库层面可行）：`SandboxConfig.enable_network` 只是环境变量透传/剥离，不是真正的网络命名空间隔离（容器内无 root 权限做不到 `unshare -n`）。现实可行的补充是对命令行中出现的 `curl`/`wget`/`nc` 等网络工具的目标地址做域名/IP 白名单校验。
5. **不建议**：引入 Docker-in-Docker、gVisor、Firecracker 等重量级方案，与"容器内 Agent 系统"的环境约束冲突，且当前组合已能覆盖大多数内部风险场景（防御目标是"脚本跑飞/误操作"而非"恶意攻击者逃逸"，重方案投入产出比低）。

## 六、落地顺序建议

1. **高优先级**（预计 1-2 天）：
   - `app/tools/builtins.py` 的 `read_file`/`write_file` 接入路径校验（5.2第1条）
   - `app/skills/memory_manager.py` 的 `_cache` 加硬上限（5.1第1条）
   - `handle_factory_run` 增加计划阶段的批量工具预检（5.2第3条）
2. **中优先级**（预计 3-5 天）：
   - `native_tools.py` 补齐 `resource.setrlimit`（5.2第4条）
   - `container_exec` 增加命令黑名单（5.2第5条）
   - `ModelRegistry` key 清理与缓存驱逐闭环（5.1第2、5条）
   - 资源限制配置统一收口（5.3第1条）
3. **低优先级**（可延后）：
   - `ToolPrioritizer` LRU 上限（5.1第3条）
   - 死代码 `@cached` 清理标注（5.1第6条）
   - 网络出站白名单增强（5.3第4条）
</content>
