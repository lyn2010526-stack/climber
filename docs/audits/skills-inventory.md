# Climber Skill 体系盘点报告

> 生成时间：2026-10-01 | 生成方式：全仓库只读调研（explore agent），未修改任何代码。
> 对应设计文档痛点：`docs/DESIGN.md` 第 ⑥ 条"内置提示词体系混乱 / 内置Skill无文档、无调用规范、无准入校验"。

## 一、Skill 定义的四个互不联通的位置

项目中实际存在 **四套相互独立、互不调用** 的 Skill 体系，这是最核心的结构性问题：

### 1. 数据库表 `Skill`（用户可增删改查，当前为空）
- 位置：`app/storage/models_platform.py:111`（不在 `app/storage/database.py`）
- 字段：`name/description/category/prompt_template/tools(JSON)/is_enabled/use_count` + 三层 scope 字段 `scope/scope_id/is_force_delivery/is_orphan/is_deleted/active_version_id/admin_description/admin_tags`
- 这些 scope/orphan/version 字段**全部未被任何 API 代码读写**，是预留但未接线的"僵尸字段"
- 无任何 seed 脚本或 migration 写入初始数据，数据库中默认**零条** skill 记录

### 2. 文件系统 YAML/JSON 定义（`skills/*/.skill.json`，共 5 个，**完全未被后端代码读取**）
- 路径：`skills/calculator/`、`skills/code-review/`、`skills/file-organizer/`、`skills/summarizer/`、`skills/web-search/`
- 已确认：全仓库 `grep -rn "\.skill\.json"` 除这 5 个文件自身外**零匹配**，没有任何 Python/TS 代码加载、解析或展示它们
- `skills_router.py` 的 `_skill_dict()` 拼出的 `"path": f"skills/{category}/{name}.yaml"` 是**伪造路径**：数据库里的 skill 实际没有对应文件，文件名后缀也错写成了 `.yaml` 而实际是 `.json`
- 结论：这 5 个文件是**完全孤立的死文件**

### 3. 内置 Agent 能力 Skill（`app/skills/` 包，19 条，有真实 Python handler）
- 核心文件：`app/skills/registry.py`（`SkillRegistry`/`SkillInfo`）、`app/skills/definitions.py`（声明 19 个 `SkillInfo`）、`app/skills/builtins.py`（1014 行，19 个异步 handler）
- 通过 `register_builtin_skills()` 在 `app/main.py:76-78` 启动时注册进内存单例 `skill_registry`，并经 DI 容器注册
- **注册后基本无人消费**：唯一下游是 `SkillComposer` → `SkillComposerExecutorAdapter` → 挂到 `UnifiedExecutor` 的 `"skill"` 类型适配器（`app/main.py:104`），但全仓库搜索未发现任何业务代码以 `type="skill"` 调用 `UnifiedExecutor.execute()`（`misc.py` 里 `type=data.get("type", "skill")` 是插件市场默认值字段，命名巧合与此无关）
- 没有 REST API、没有前端入口能触发这 19 个内置 skill 的真实执行；只在单元测试 `tests/test_builtin_skill_registration.py` 中验证"注册成功"，生产链路是断的

### 4. Factory 模式硬编码字典（`app/api/v1/skills_router.py`，真正被前端调用的那一套）
- `_FACTORY_TOOLS`（6 条，`skills_router.py:25-32`）：`code_executor / web_search / file_manager / data_analyzer / task_planner / code_reviewer`
- `_FACTORY_PROMPTS`（5 条，`skills_router.py:34-40`）：`senior-engineer / code-reviewer / architect / research-analyst / data-scientist`，一行英文 prompt 字符串，**100% 硬编码**，无文件来源、无版本号
- 前端 `FactoryModePage.tsx` 的 `SKILLS`（第41-48行）与 `PROMPTS`（第50-56行）**手动复制**了这两个字典的 key 和展示名，没有任何接口在运行时同步
- `task_worker.py` 里还有**第三份重复定义** `_FACTORY_SKILL_TOOLS`（第646-653行），内容与 `_FACTORY_TOOLS` 几乎一致但物理上是**独立复制的字典**，一处改动另一处不会同步

路由挂载链路：`app/api/v1/__init__.py` 的 `_include_extension_routes()` 手动摘取 `skills_router.py` 里 `/skills/autonomous` 开头的路由 + 单独摘取一条 PATCH 路由；标准 CRUD（list/create/enable/disable/delete）实际由**另一个文件** `app/api/v1/routes/skills.py` 承担（经 `generic.py` 整体挂载），二者有**重复定义**的 `list_skills`、`create_skill`、`enable_skill` 等函数名，一个用旧版 `current_user_id(request)`，一个用新版 `CurrentPrincipal` 依赖注入，是新旧并存未清理代码。

## 二、内置 Skill 清单统计

- `_FACTORY_PROMPTS` 硬编码 5 条：`senior-engineer`、`code-reviewer`、`architect`、`research-analyst`、`data-scientist`
- `_FACTORY_TOOLS` 硬编码 6 条：`code_executor`、`web_search`、`file_manager`、`data_analyzer`、`task_planner`、`code_reviewer`
- `app/skills/definitions.py` 的 `BUILTIN_SKILLS`（有 handler，无生产调用链路）19 条：`recursive_research`、`task_decomposition`、`self_evolving`、`memory_manager`、`frontend_engineer`、`backend_engineer`、`database_architect`、`devops_engineer`、`git_master`、`code_reviewer`、`security_auditor`、`tdd_engineer`、`systematic_debugger`、`data_analyst`、`tech_researcher`、`doc_generator`、`rag_organizer`、`incident_analyzer`、`dependency_auditor`
- `skills/*/.skill.json` 死文件 5 条：`calculator`、`code-review`、`file-organizer`、`summarizer`、`web-search`

**命名冲突证据**：`code_reviewer`（下划线，BUILTIN_SKILLS 和 _FACTORY_TOOLS）、`code-reviewer`（连字符，Factory Prompt key）、`code-review`（连字符无 er，死文件名）—— 三种同义不同形的 key 分散在四套体系中，无统一命名规范或别名映射表。

## 三、逐项核查结果

| 检查项 | 结果 |
|---|---|
| prompt_template 来源 | 数据库 Skill 表：用户自由文本（无约束）；Factory：Python 文件硬编码；BUILTIN_SKILLS：Python 文件硬编码（`system_prompt`）；.skill.json：JSON 硬编码但无代码读取 |
| 版本号/过期标记 | 仅数据库 `Skill` 表有 `active_version_id`（未使用）；`SkillVersion`/`SkillTestCase`/`SkillTestResult` 三张表（`models_skills.py`）+ `SkillVersionManager`/`SkillTester` 已实现，但**无任何 API 路由暴露**，完全是死代码。`.skill.json` 有 `"version": "1.0.0"` 字段但无代码读取。BUILTIN_SKILLS 和 Factory 字典**均无版本号字段** |
| 调用前准入校验 | Factory 模式下 `task_worker.py` 的 `_parse_factory_plan()` 对 LLM 生成计划里的工具名做了白名单过滤（`allowed_tools = {...}`，第660-676行），这是唯一一处工具白名单校验；但用户在 `/skills` POST 里自由填写的 `tools: list[str]` **无任何校验**（`SkillCreateRequest` 只校验字段名，不校验内容是否在全局 `ToolRegistry` 中真实存在） |
| 文档 | 全仓库零 Skill 使用文档，与设计文档记录的痛点完全吻合 |
| 重名/冲突 | 存在（见上文）；另有 `_FACTORY_TOOLS` 与 `_FACTORY_SKILL_TOOLS` 内容几乎相同的独立重复定义 |
| 权限/鉴权 | `routes/skills.py` 按 `user_id` 隔离，但**没有角色/权限分级**（任何登录用户都可创建/删除自己的 skill，无管理员审核） |

## 四、现状结论

1. **四套 Skill 体系互不联通**：数据库表（空、字段多未接线）、5 个死文件（零引用）、19 条内置能力（注册了但无执行入口）、Factory 硬编码字典（唯一真正被前端调用）。
2. **新旧路由文件并存**：`skills_router.py`（旧）与 `routes/skills.py`（新）功能重复，维护成本高、易改错文件。
3. **零文档**，设计文档"无文档"痛点完全属实。
4. **工具白名单校验只覆盖 Factory 执行计划一个环节**，数据库自定义 Skill 的 `tools` 字段不校验是否为系统真实工具。
5. **版本管理基础设施已搭好但完全没接线**：三张表 + 两个管理类写好了，无 API 暴露，白写。

## 五、改进建议（按优先级排序）

1. **【最高】统一 Skill 数据源，砍掉死代码**：删除或改造 `skills/*/.skill.json`；合并 `skills_router.py` 与 `routes/skills.py` 为一个文件。
2. **【高】补齐工具白名单校验**：`SkillCreateRequest` 增加校验器，核对 `tools` 字段是否在全局 `tool_registry` 中存在；`update_skill`（PATCH）同步补校验。
3. **【高】合并重复的 Factory 工具映射字典**：`skills_router.py:_FACTORY_TOOLS` 与 `task_worker.py:_FACTORY_SKILL_TOOLS` 抽成共享常量模块（如 `app/skills/factory_catalog.py`）。
4. **【中】补齐 Skill 文档**：新增 `docs/SKILLS.md`，说明四套体系各自用途、调用链路，标注"已接线可用" vs "预留未接线"；对 19 条 `BUILTIN_SKILLS` 逐条补充"谁在调用它"，否则标记为实验性/未启用。
5. **【中】统一命名规范**：Skill key 统一用 `snake_case`，修正 `code-reviewer` → `code_reviewer`、死文件名 `code-review` 等同义不同形问题。
