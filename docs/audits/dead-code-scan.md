# Climber 后端死代码扫描报告

> 生成时间：2026-10-01 | 生成方式：全仓库只读调研（explore agent），未修改任何代码。
> 对应设计文档痛点：`docs/DESIGN.md` 第 ⑤ 条"后端乱融合开源功能，大量开源模块强行堆砌、不兼容、无调用链路、无测试、形成大规模死代码"。

## 一、路由挂载核查

### 1.1 `app/api/v1/routes/*.py`（二级 router 文件）
全部 11 个路由模块（agents / arcbench / chat_commands / crews / groups / integrations / misc / reasoning / research / skills / tasks / websocket / workflows）均能在 `app/api/v1/generic.py` 或 `app/api/v1/__init__.py` 中找到 `include_router` 调用，**没有孤儿路由文件**。

### 1.2 关键发现：`_include_extension_routes` 造成的"影子死代码"
`app/api/v1/__init__.py` 中存在一个按路径前缀"摘取"路由的特殊机制：

```python
_include_extension_routes(cost_router.router, ("/cost/usage",))
_include_extension_routes(scheduler_router.router, ("/scheduler/tasks",))
_include_extension_routes(mcp_router.router, ("/mcp/servers", "/mcp/categories"))
_include_extension_routes(skills_router_module.router, ("/skills/autonomous",))
```

它只把源 router 中匹配指定前缀的 route 对象摘出来挂载，**同一文件里其余端点虽然写了完整实现，但从未被挂载到 app 上，请求永远 404**。逐一核实如下：

| 源文件 | 定义的端点 | 实际被挂载 | 未挂载（死代码） |
|---|---|---|---|
| `app/api/v1/cost.py`（110行） | `/cost/records`, `/cost/budget`, `/cost/quota`, `/cost/usage` | 仅 `/cost/usage` | `/cost/records`、`/cost/budget`、`/cost/quota` 三个 handler，**且与 `routes/misc.py` 中真正生效的同名端点几乎逐行重复**（差异仅在于 `cost.py` 用硬编码 `DEFAULT_USER`，`misc.py` 用 `current_user_id(request)`，前者是明显的旧版本遗留） |
| `app/api/v1/scheduler.py`（128行） | `/scheduler`, `/scheduler/tasks`(CRUD) | 仅 `/scheduler/tasks` 系列 | `/scheduler` 的 GET/POST（list_scheduled / create_scheduled），且与 `routes/misc.py` 中已生效的 `/scheduler` 实现**代码几乎完全相同（复制粘贴）** |
| `app/api/v1/mcp.py`（172行） | `/mcp`, `/mcp/{id}/start|stop`, `/mcp/{id}`(DELETE), `/mcp/servers`, `/mcp/categories`, `/mcp/servers/{id}/install` | 仅 `/mcp/servers`、`/mcp/categories` | `/mcp` 的 GET/POST、`/mcp/{id}/start`、`/mcp/{id}/stop`、`/mcp/{id}`(DELETE)、`/mcp/servers/{id}/install`，且前五个与 `routes/misc.py` 中生效版本重复 |
| `app/api/v1/skills_router.py`（314行） | `/skills`(GET/POST), `/skills/{id}/enable|disable`, `/skills/{id}`(DELETE/PATCH), `/skills/autonomous/run` | 仅 `/skills/autonomous/run` + `/skills/{id}`(PATCH) | `/skills`(GET/POST)、`/skills/{id}/enable`、`/skills/{id}/disable`、`/skills/{id}`(DELETE) 共 5 个 handler，**且与 `routes/skills.py` 中真正生效的版本重复** |

这 4 个文件呈现同一种模式：疑似早期单体实现，后被拆分重构到 `routes/*.py` 并改写了部分接口（如改为按 `user_id` 隔离数据），但旧文件没有删除，只通过前缀摘取保留了一两个"还没迁移"的端点，其余全部沦为死代码，且与新实现并存会造成后续维护者误读（文件体积占比：4 个文件共 724 行代码中，约 500+ 行是未挂载的死代码）。

### 1.3 `app/core/` 顶层模块引用核查
逐一 grep 全仓库（app + tests）对 `app/core/*.py` 的 import 引用：

- **零引用（高置信度死代码）**：
  - `app/core/mcp_controller.py`（34行，定义 `McpController` / `McpStatus`，无任何地方 import）
  - `app/core/prompt_manager.py`（30行，定义 `PromptManager`，无任何地方 import）
  - `app/core/session_manager.py`（37行，定义 `SessionInfo` / 会话管理类，无任何地方 import）
  - `app/core/scheduler.py`（126行，定义 `TaskScheduler`/`ScheduledTask`）——虽然被 `app/main.py` 实例化并注册进 DI 容器、放入 watchdog 循环，但其 `add_task`/`get_due_tasks`/`register_handler` 等核心方法在全仓库**无任何调用方**，`run_pending()` 每 30 秒跑一次空任务列表；真正的业务调度功能已被 `app/api/v1/scheduler.py` + `routes/misc.py`（基于数据库 `Workflow.schedule` 字段）取代。

- **其余顶层模块**（core_memory / error_analyzer / file_index / group_collaboration / memory_reflection 等）经核实均有 1 处以上的懒加载 import（多为函数内部 `from app.core.xxx import yyy` 形式），**不属于死代码**，属于正常的延迟导入模式。

### 1.4 模型适配器（`app/models/*_adapter.py`）
`app/models/registry.py` 的 `PROVIDERS` 字典注册了全部 5 个适配器（openai / anthropic / google / ollama / stepfun），`app/models/` 目录下不存在额外的、未注册的适配器文件。**这部分无死代码**。

## 二、重复/冗余实现

### 2.1 Task/Queue/Scheduler 三套并行实现
仓库中存在 **3 套相互独立、未整合的任务调度/执行引擎**：

1. `app/core/scheduler.py` 的 `TaskScheduler`（cron 任务，依赖 `croniter` 包）——已确认为死代码，见上。
2. `app/core/task_worker.py` 的 `TaskManager`（异步任务队列，被 `routes/tasks.py`、`skills_router.py` 实际使用）——在用。
3. `app/core/auto_loop.py` 的 `AutoLoopEngine`（自治循环任务，被 `main.py` 启动并常驻 watchdog）——在用。

后两者（TaskManager / AutoLoopEngine）职责有重叠（都管理长任务生命周期、状态、恢复），但各自被不同上游代码路径依赖，暂不能判定为死代码，但建议人工评估是否可合并，属于架构层面的"开源功能乱融合"证据之一。

### 2.2 Permission/Auth 并非简单重复
核查了 4 处权限相关实现（`auth.py`、`auth_manager.py`、`permission_rules.py`、`collaboration/roles.py`），**职责分层清晰、互不重叠**（分别对应：提取 request 中 user_id / JWT token+scope 校验 / 工具调用权限规则 / multi-agent 角色能力），不属于冗余实现，予以排除。

### 2.3 `/cost`、`/scheduler`、`/mcp`、`/skills` 四组路由的"新旧并存"
详见 1.2，本质上是同一问题的 4 个实例：重构后旧文件未清理，属于最典型的"大量开源模块强行堆砌、无调用链路"死代码模式。

## 三、TODO/FIXME/XXX 与注释代码块

- 全仓库 `grep -rn "TODO\|FIXME\|XXX" app/` **命中 0 次**，说明该类标记未被使用（可能项目规范禁止，或遗留代码已被清理过一轮）。
- 大块注释代码（连续注释掉的 `def`/`class`/`import`）扫描同样**未发现**。

## 四、依赖包核查（粗查）

`requirements.txt` 中 `croniter>=6.0` 仅被 `app/core/scheduler.py` 引用，而该文件已被判定为死代码；若清理该文件，此依赖包可一并移除。其余包（chromadb、playwright、mcp、psutil 等）均有多处引用，未发现明显冗余依赖，未做穷举式逐包分析。

## 五、结论与清理建议

### 高置信度死代码（无引用、无路由挂载、无测试覆盖，可安全删除）

| 文件 | 行数 | 判定依据 |
|---|---|---|
| `app/core/mcp_controller.py` | 34 | 全仓库零 import |
| `app/core/prompt_manager.py` | 30 | 全仓库零 import |
| `app/core/session_manager.py` | 37 | 全仓库零 import |
| `app/core/scheduler.py` | 126 | 核心方法零调用，功能已被 DB 驱动方案取代（仅保留一个空转的 30s 轮询） |
| `app/api/v1/cost.py` 中 `list_cost_records`/`get_budget`/`get_quota` 三个 handler | ~75（文件内约 3/4） | 未挂载，且与 `routes/misc.py` 生效版本重复，用的还是过时的 `DEFAULT_USER` 而非真实 user_id（潜在数据隔离 bug 来源） |
| `app/api/v1/scheduler.py` 中 `/scheduler`（非 tasks）两个 handler | ~35 | 未挂载，与 `routes/misc.py` 重复 |
| `app/api/v1/mcp.py` 中 `/mcp`、`/mcp/{id}/start`、`/mcp/{id}/stop`、`/mcp/{id}`(DELETE)、`/mcp/servers/{id}/install` | ~140（文件内约 5/6） | 未挂载，前 4 个与 `routes/misc.py` 重复 |
| `app/api/v1/skills_router.py` 中 `/skills`(GET/POST)、`/skills/{id}/enable`、`/skills/{id}/disable`、`/skills/{id}`(DELETE) | ~200（文件内约 2/3） | 未挂载，与 `routes/skills.py` 重复 |

### 需要人工确认的可疑文件（看起来孤立，但不能 100% 排除动态引用/间接依赖）

- `app/api/v1/cost.py`、`app/api/v1/scheduler.py`、`app/api/v1/mcp.py`、`app/api/v1/skills_router.py` 这 4 个文件**不建议整文件删除**，因为每个文件里都还有 1-2 个端点在真正生效（如 `skills_router.py` 的 `_factory_agent_payload` 被 `tests/test_factory_path_regressions.py` 直接 import 测试，且 `/skills/autonomous/run` 路由在用）。需要人工拆分：保留生效部分，删除未挂载部分，或者彻底重构合并进 `routes/*.py`。
- `app/core/task_worker.py`（TaskManager）与 `app/core/auto_loop.py`（AutoLoopEngine）：功能重叠但各自在用，是否合并需要人工评估业务语义差异，不属于死代码范畴但建议纳入架构梳理。
- `app/api/v1/routes/research.py`：仅被 `app/api/v1/__init__.py` 引用一次，路由本身已挂载（`/research`），功能未发现被前端或其他模块调用，建议人工确认该功能是否仍在产品路线图内，暂不列入死代码。

### 清理优先级与注意事项

1. **优先级 1（低风险，可直接清理）**：`app/core/mcp_controller.py`、`app/core/prompt_manager.py`、`app/core/session_manager.py` ——零引用，删除前跑一次 `pytest tests/` 全量测试确认无隐式依赖（如字符串反射 `getattr(module, name)`）即可。
2. **优先级 2（中风险，需先核实数据隔离 bug）**：`app/api/v1/cost.py` 整理。注意其中 `DEFAULT_USER` 硬编码的问题即使是死代码也建议先确认历史上是否被任何客户端直接请求过 `/cost/records`、`/cost/budget`、`/cost/quota` 这几个路径（它们返回 404，但如果前端曾经有代码指向这些路径会导致功能误判为"已修复"实际从未工作），建议在清理前检查 `frontend-react/src` 是否有调用。
3. **优先级 3（需要拆分重构而非直接删除）**：`app/api/v1/scheduler.py`、`app/api/v1/mcp.py`、`app/api/v1/skills_router.py`。删除前必须：
   - 跑全量测试套件（`tests/test_factory_path_regressions.py` 对这些文件有耦合）；
   - 确认 `_include_extension_routes` 摘取的那部分端点迁移到对应 `routes/*.py` 文件后行为一致；
   - 搜索 `frontend-react/src` 确认前端没有直接依赖这些文件里将被删除的 404 端点路径。
4. `app/core/scheduler.py` 删除后需同步：移除 `app/main.py` 中 `TaskScheduler` 的实例化、DI 注册、watchdog 注册代码（约 5 处），以及 `requirements.txt` 里的 `croniter` 依赖。
5. 建议补充集成测试：当前死代码之所以能长期存活，核心原因是**路由挂载层缺少"未使用 router 对象"的静态检查**，建议后续在 CI 中加入脚本校验：所有 `app/api/v1/*.py` 定义的 `@router` 装饰端点都必须能在最终 FastAPI app 的 `app.routes` 中找到，否则 CI 失败，防止此类死代码再次复发。
</content>
