# 用户指令记忆

本文件记录了用户的指令、偏好和教导，用于在未来的交互中提供参考。

## 格式

### 用户指令条目
用户指令条目应遵循以下格式：

[用户指令摘要]
- Date: [YYYY-MM-DD]
- Context: [提及的场景或时间]
- Instructions:
  - [用户教导或指示的内容，逐行描述]

### 项目知识条目
Agent 在任务执行过程中发现的条目应遵循以下格式：

[项目知识摘要]
- Date: [YYYY-MM-DD]
- Context: Agent 在执行 [具体描述] 任务时发现
- Category: [运维部署|构建方法|测试方法|排错调试|工作流协作|环境配置]
- Instructions:
  - [具体的知识点，逐行描述]

## 去重策略
- 添加新条目前，检查是否存在相似或相同的指令
- 若发现重复，跳过新条目或与已有条目合并
- 合并时，更新上下文或日期信息
- 这有助于避免冗余条目，保持记忆文件整洁

## 条目

[前端项目 UI 重构]
- Date: 2026-08-04
- Context: 对 agent-engine/frontend-react 项目进行 UI 重构
- Category: 环境配置
- Instructions:
  - 项目使用 Vite + React + TypeScript + Tailwind CSS v4
  - 构建命令: `cd /workspace/agent-engine/frontend-react && npm run build`
  - tsconfig.app.json 需要关闭 noUnusedLocals/noUnusedParameters（ boilerplate 代码有未使用变量）
  - verbatimModuleSyntax 设为 false，isolatedModules 设为 true
  - exactOptionalPropertyTypes 设为 false，noPropertyAccessFromIndexSignature 设为 false
  - hooks/useTheme.tsx 和 useTheme.ts 存在命名冲突，需要区分导入
  - 测试文件在 src/utils/__tests__ 下有语法错误，已在 tsconfig exclude 中排除

[复杂任务并行执行与证据验收]
- Date: 2026-08-04
- Context: 用户要求推进跨前端、后端、测试、调研和质量审计的长期开发任务
- Instructions:
  - 复杂任务优先按互不重叠的文件域并行启动多个子任务，主线程持续监督、整合和复验
  - 子任务必须写明任务目标、写入范围、验收命令和剩余风险
  - 子任务完成声明仅作为候选结果，主线程必须通过构建、测试、接口或页面实测形成证据闭环
  - 持续推进已有明确下一步，遇到真实需求歧义或破坏性操作时再请求确认

[frontend-react 测试与依赖环境要点]
- Date: 2026-08-05
- Context: Agent 在修复 src/hooks/__tests__ 下的失败 hook 测试时发现
- Category: 环境配置
- Instructions:
  - 单文件测试命令: `cd /workspace/agent-engine/frontend-react && NODE_OPTIONS="--max-old-space-size=4096" npx vitest run <file>`
  - 真实 useChat 位于 src/useChat.ts，不在 src/hooks/ 目录，其接口为 { messages, isStreaming, error, sendMessage, stopStreaming, clear }
  - vite.config.ts 已补上 `@` alias（指向 ./src），此前缺失会导致 `@/` 导入无法解析；大量模板 hook（useActions/useSessions 等）依赖 `@/`，测试时必须 mock 对应模块
  - 已安装 @tanstack/react-query 依赖（src/hooks 下资源 CRUD 模板 hook 依赖它，测试运行时可 vi.mock 拦截避免 QueryClient Provider 报错）
  - vitest v4 的 vi.mock 工厂不能引用顶层变量（静态 import 使工厂先于 const 初始化执行，报 TDZ），需用 vi.hoisted() 定义共享变量；vi.mock 无法 mock 不存在的裸模块，vite transform 阶段会先解析失败

[根 frontend-react 为权威前端，iOS 动效依赖已接入]
- Date: 2026-08-09
- Context: Agent 在推进前端 iOS 化时发现
- Category: 环境配置
- Instructions:
  - 权威前端位于 `/workspace/frontend-react`（agent-engine/frontend-react 是旧副本），前端测试命令: `cd /workspace/frontend-react && NODE_OPTIONS="--max-old-space-size=4096" npx vitest run --maxWorkers=2 --reporter=dot`（vitest v4 不支持 --timeout CLI 参数）
  - token 体系已收敛：src/index.css 是唯一生效入口（@theme + data-theme + iOS 动效类），src/styles/tokens.css 与 base.css 是未被引用的死代码，勿再新增变量到它们
  - 已安装 framer-motion ^13 / vaul ^1.1.2 / sonner ^2.0.7，Toaster 已挂载到 main.tsx；消息动效在 ChatInterface，底部 sheet 在 MobileBottomNav 用 Drawer
  - vite 配置的 test.allowedHosts 无需配置；tsc 检查命令: `npx tsc --noEmit -p tsconfig.json`

[后端全量测试与关键修复]
- Date: 2026-08-09
- Context: Agent 在执行后端全量回归修复时发现
- Category: 排错调试
- Instructions:
  - 全量后端测试命令: `cd /workspace && timeout 2400 /usr/bin/python3 -m pytest tests/ -q --no-header -p no:cacheprovider --timeout=180`（约 18 分钟，当前基线 1487 passed / 50 skipped / 0 failed）；单文件定位用 `-p no:cacheprovider -x`
  - 用后台终端跑全量（background_terminal_create），中途无输出属正常（tail 管道到结束才输出）
  - app/core/sandbox.py 用 shlex.split 而非 str.split 解析命令（引号参数会被拆坏）；已导入 shlex
  - app/core/web_content_cleaner.py 的噪音过滤不能按行长度 <20 武断删除（会误删短标题）；靠噪音模式判定
  - app/core/auto_loop.py 的 start() 设计为非阻塞（供测试），run() 为常驻（供 watchdog register，保持 healthy），main.py 注册的是 run
  - app/tools/browser_tools.py 导航后要 wait_for_function 等 body 文本非空再提取，wait_until=domcontentloaded 可能过早
  - app/config.py 的 app_secret_key 持久化到 data/.secret_key（优先级 env APP_SECRET_KEY > 文件 > ephemeral），已在 .gitignore 排除
  - 全量测试时单独跑通过的测试可能报 OSError（如 context_manager 系列），是 ChromaDB/vector_memory 残留状态或资源问题，非代码 bug，重跑即可

[运行时 API 三修复与 git 收口]
- Date: 2026-08-10
- Context: Agent 修复预览页 500 并收口工作区时发现
- Category: 排错调试
- Instructions:
  - app/api/v1/generic.py 的 MODEL_ALIASES 是模块级变量（app/models/registry.py），不能写成 ModelRegistry.MODEL_ALIASES 类属性引用，否则 /api/v1/models 返回 500
  - doctor 的 workspace 检查路径要用 config.BASE_DIR（/workspace），不能自行 Path.parent 叠三层（会指到 /workspace/app）；缺失目录应 mkdir 自动创建而非要求预存在
  - FastAPI 静态路由（/export-all）必须定义在泛化路由（/{template_id}）之前，否则被吞导致 404；同 method 才冲突
  - 冒烟测试全部无参 GET 路由：/usr/bin/python3 /tmp/opencode/smoke_routes.py；页面实测用 /tmp/opencode/verify_final.py
  - git 收口完成：node_modules/__pycache__/data//logs/ 已 git rm --cached 解除跟踪（磁盘保留），agent-engine/climber-repo/climber_legacy_conflict 嵌套仓库 gitlink 指针已移除，.gitignore 已扩充覆盖
  - 后端 uvicorn 用 timeout 7200（此前 3600 到期导致服务退出），后台 term 526/527 常驻
  - 全量回归基线（3 修复后）：1487 passed / 50 skipped / 0 failed，约 13 分钟

[批量修复盘点与并行子任务经验]
- Date: 2026-08-10
- Context: Agent 并行派发 5 个修复子任务后主线程整合复验时发现
- Category: 排错调试
- Instructions:
  - 盘点经验：前端问题用 `npx tsc -b --noEmit`（tsconfig.json 是 solution 聚合文件 files:[]，`-p tsconfig.json` 是假象）；后端用 curl 冒烟 + 路由顺序扫描脚本（静态路由须在泛化路由前）
  - 后端已修复：settings/prompt_templates 双重 prefix 404（router 自带 prefix 与 __init__.py include prefix 叠加，去掉 router 内部 prefix）；reasoning /modes//history 被 /{trace_id} 吞（移到泛化路由前）；WebSocket 403（websocket 参数必须标 WebSocket 类型不能 Any）；CORS env 不生效（list 字段需 validation_alias + Annotated[list, NoDecode] 防 JSON 解码）；缺 ollama_base_url 字段；FRONTEND_DIR 自动探测 frontend/frontend-react
  - 前端已修复：ChatInterface whileTap undefined 导致 TS2375 阻塞 build；ChatPage alert→sonner toast；FloatingPermissionDialog 改 vaul Drawer；移动端新增 MobileSessionDrawer（vaul 会话列表/新建/切换，权威数据源是 useSessions() 而非 workspace store 的本地 sessions）
  - 后端补齐前端 3 个缺失 API：/tasks/{id}/cancel、/eval/datasets/seed-builtin、/eval/datasets/{id}/run（都在 generic.py 内新增，注意前端契约：均无 body、返回结构对齐现有端点）
  - 死代码处理用归档到 /tmp/opencode/dead_code_archive/ 而非删除（遵守 no-delete 规则）：前端 styles/ + 6 个文件/组件，后端 10 个未挂载 router（agents/eval/models/search/stats/tools/traces/plugins/users/websocket，均与 generic.py 重复且无任何引用）；前端 UI 组件（Alert/Dialog/Select 等）虽字面 0 引用但有子组件/泛型引用，必须全名核验勿误删
  - 路由验证：OpenAPI paths 数（TestClient /openapi.json）是权威口径，app.routes 数不包含 include 的子 router；WebSocket 路由不出现在 OpenAPI paths 属正常

[ruff 静态检查规则选型经验]
- Date: 2026-08-10
- Context: Agent 对标领先项目用 ruff 全规则集（默认 1427 错误）清洗 app/ 与 tests/ 时发现
- Category: 构建方法
- Instructions:
  - 项目此前无 lint 配置，`/usr/local/bin/ruff` 可用；清洗命令：`ruff check app/ --no-cache --output-format=concise`（全清）与 `ruff check tests/ --no-cache`
  - 规则选型：pyproject.toml 定义 select E/W/F/I/S/B/UP/RET/C4/RUF；ignore BLE001(防御性宽 except)、B008(FastAPI Depends)、E402(延迟导入)、E501(格式化器管行长)、E712(SQLAlchemy 布尔列需 ==True/False)、RUF012(类级只读常量)、S105/107/108/603/607(沙箱设计误报)、ASYNC109/220/221/230/240/251(建议类)、DTZ007(解析用户日期无时区)、RUF001/002/003(中文全角标点在中文注释/文档/字符串正常)
  - per-file-ignores：tests/* = S101/S105/S106/S311；**/__init__.py = F401(公共 API 重导出)
  - UP042(str,Enum→StrEnum) 迁移安全前提：枚举值均小写等于成员名且无 str() 依赖 name 的代码；迁移后必须全量回归
  - 沙箱 eval/exec(有 AST 白名单+受限 builtins) 加 `# noqa: S307/S102` 保留设计意图，勿盲改；S311/S324 用于抖动/采样/缓存键等非加密场景加 noqa
  - DTZ004/005/006 修复统一模式：`datetime.fromtimestamp(ts, UTC)` 或 `now(UTC)`，DB 时间戳保持 naive 用 `.replace(tzinfo=None)` 防 aware/naive 混合 bug；file_index mtime 比较是真实时区 bug（原 fromtimestamp 用本地时区与 DB naive UTC 比较错位）
  - RUF006 fire-and-forget create_task 统一 `_spawn` helper：模块级 `_background_tasks: set[asyncio.Task]` + done_callback discard，防任务被 GC 回收
  - S306 tempfile.mktemp 改 `mkstemp`(fd 关闭后路径已占位，无 TOCTOU 竞态)
  - 教训：`for t_name, t_config in ...` 中 B007 报 t_config 未用时，只改未用的那个变量为 `_`，循环体内若引用了 `t_name` 必须保留原名，误改 `_` 会导致 F821 回归
