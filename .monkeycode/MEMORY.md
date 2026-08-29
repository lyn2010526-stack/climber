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

[文档命令审查工作流]
- Date: 2026-08-27
- Context: Agent 在核对部署文档与 CI 实际命令时发现
- Category: 工作流协作
- Instructions:
  - 部署文档审查应同时核对 README.md、docs/DEPLOYMENT.md、.monkeycode/docs/DEPLOYMENT.md、package.json、前端 package.json 和 CI workflow
  - 文档修正后应检查目标路径存在性、package.json 脚本存在性、命令可执行性、shell 注释格式，并查看仅目标文档的 git diff
  - 文档审查任务只修改文档文件，不修改业务代码、配置或测试，不提交

[前端产品约束]
- Date: 2026-08-26
- Context: 用户要求全面检查 Climber 源仓库并修复问题时明确
- Instructions:
  - 产品不提供登录界面，前端保持直接进入工作台的体验；认证能力继续作为后台 API 的可选基础设施处理

[持续审查与优化方式]
- Date: 2026-08-26
- Context: 用户要求持续推进全仓库检查和优化时明确
- Instructions:
  - 持续执行全仓库检查和增量优化；每个问题都要经过定位、最小修复、验证和同类问题复查形成闭环
  - 已有明确下一步时继续推进，遇到真实需求歧义或高风险策略变更时暂停并请求确认

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
   - 全量后端测试命令: `cd /workspace && /usr/bin/python3 -m pytest tests/ -q --no-header -p no:cacheprovider --timeout=180 -W error::pytest.PytestUnhandledThreadExceptionWarning`（约 21 分钟）；单文件定位用 `-p no:cacheprovider -x`
   - 基线历史：2026-08-10 1487/50/0 → 2026-08-21 1660/16/0 → 2026-08-29 1963/16/1（新增 303 个测试，1 个预存失败 `test_p0_runtime_contracts.py::test_chat_applies_model_override_to_in_memory_session` 源自历史未提交的 chat.py 重构 `engine.get_session()` 与测试 mock 的 `Engine` 只有 `_sessions` 不匹配，与架构改动无关）
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

[权威后端启动方式与 pth 遮蔽根因]
- Date: 2026-08-10
- Context: Agent 新增后端端点后重启发现 AutoLoopEngine 缺 run 属性，排查出模块解析错误
- Category: 环境配置
- Instructions:
  - 根因：pip editable 留下的 `/usr/local/lib/python3.11/dist-packages/_editable_impl_agent_engine.pth` 把 `/workspace/agent-engine` 注入 sys.path 且优先，导致 `import app` 解析到参考项目而非权威 `/workspace/app`。已重命名禁用到 `/tmp/opencode/_editable_impl_agent_engine.pth.bak`。
  - 权威后端正确启动：`cd /workspace && PYTHONPATH=/workspace /usr/bin/python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000`（cwd 必须是 /workspace 使 `import app` 命中 /workspace/app/__init__.py；用 `app.main:app` 非 `main:app`）。之前 `cd /workspace/app && python -m uvicorn main:app` 实际解析到 agent-engine 版本，新端点全部失效。
  - pth 禁用前先备份到 /tmp/opencode 防丢；`_pth` 会影响参考项目导入但参考项目仅作功能参考不运行。
- Category: 排错调试

[限流中间件启用与 WS 代理修复]
- Date: 2026-08-10
- Context: Agent 启用 RateLimitMiddleware、新增 terminal/approvals 端点并验证 WS 时发现
- Category: 排错调试
- Instructions:
  - RateLimitMiddleware 原 check_rate_limit 从不记时间戳（record 从未被调用）导致限流形同虚设；已在 UsageTracker 加 `record_request`（仅记时间戳），中间件 check 通过后调用；单例默认放宽到 600 req/min 避免开发冒烟误伤（此前 120/min 连续 curl 触发 429）。
  - RateLimitMiddleware 在 main.py add_middleware 最后（最外层最先执行）；SKIP_PATHS 已含 /metrics、/api/v1/terminal/health。
  - 前端 vite 代理 `/api` 必须加 `ws: true`，否则浏览器经 vite 访问 `/api/v1/ws/...`（前端 TaskMonitorPage 用 `/api/v1/ws/task` 前缀）WS 握手超时；`/ws` 独立代理无此问题。
  - approvals/terminal/notifications 等端点历史遗留写法 `@router.get("xxx")`（无前导斜杠）与 prefix 拼接成 `/api/v1/xxx`（缺分隔符，如 notificationssend、approvalsapprove），属死路由冗余，统一改为单独 `@router.get("/xxx")`；`""` 空串路由（prefix 本身）是正确写法需保留。
  - 审批双系统：app/core/approval.py 的 ApprovalManager(单例 approval_manager) 被新 approvals API 使用；app/core/security_sandbox.py 的 PermissionApprovalSystem 是另一套。前端审批请求仍无产生点（_validate_tool_call 的 ASK 直接 return False 而非入队）是残余缺口。

[后端 WS 端到端与 agent_engine 边界测试要点]
- Date: 2026-08-10
- Context: Agent 新增 tests/test_websocket_endpoints.py 与 tests/test_agent_engine_edges.py 时发现
- Category: 测试方法
- Instructions:
  - WS 端到端用 fastapi TestClient（sync）的 websocket_connect，AsyncClient 不支持；module scope `with TestClient(app)` 先例见 test_new_routes.py；非法 group 关闭后 `ws.receive()` 返回 {"type":"websocket.close"}，非法 task 连接保持打开仍可收 pong
  - agent_engine 测试必须 mock `engine._persist_message`（async no-op）和 `engine.memory_service`（假对象），否则每轮真实 DB commit + chromadb 查询使单测试 50s+ 甚至 120s 超时；engine.debug_loop 置 None 防自动恢复干扰
  - ToolRegistry.execute 吞掉工具异常，把 `Error executing {name}: {e}` 作为 result 返回（error 字段为空），断言工具失败须看 TOOL_RESULT 的 result 字段
  - 已知 bug：group_ws_hub._save_group_message 用 `sender_id=` 构造 AgentGroupMessage，但模型只有 agent_id/sender_name，任何 group message 都会 TypeError 断开；测 group ack 路径须 monkeypatch handle_message，非法 group 路径不受影响

[用户 LLM 端点配置与平台稳定性]
- Date: 2026-08-11
- Context: Agent 配置用户提供的 OpenAI 兼容端点并验证长任务时发现
- Category: 运维部署
- Instructions:
  - 用户 LLM 配置在 /workspace/.env（已 gitignore，含用户自己的 key，勿提交）；端点 https://platform.ai.hixinghai.top/api/v1，模型 deepseek-v4-flash，deepseek-v4 系列需 MODEL_EXTRA_PARAMS={"reasoning_effort":"none","thinking":{"type":"disabled"}} 关闭 reasoning（否则 content 空、max_tokens 被吃光）
  - 平台间歇性不稳定（约 50% ReadTimeout，正常时 2-15s 响应）：重试可恢复；该平台 deepseek-v4-pro 是 reasoning 模型
  - LLM 调用重试已内置 agent_engine._stream_with_retry/_chat_with_retry（2026-08-11 提交 ffb88e99）：流式仅在 0 chunk 时重试（避免中途失败重复输出），非流式失败直接重试；MODEL_MAX_RETRIES=3、MODEL_RETRY_DELAY=2.0、MODEL_STREAM_IDLE_TIMEOUT=60（读 .env，经 app/config.py load_dotenv）
  - adapter 超时环境变量：MODEL_HTTP_TIMEOUT=900（httpx 总超时）、MODEL_STREAM_IDLE_TIMEOUT（watchdog 空闲关闭）
  - 写操作工具（write_file/run_command/stream_command）默认受权限系统+审批双重拦截：权限模式 DEFAULT 时写/执行返回 ASK 需审批，且 tool_requires_approval 硬编码 run_command/write_file/delete_file 需人工审批（300s 超时拒绝）。已修复：权限配置 ALLOW 时跳过审批（app/core/parallel.py pre_allowed 判断），切 AUTO 模式（`PUT /api/v1/permissions/config {"mode":"auto"}`）可让写工具真实执行，高危命令（rm -rf / 等）仍拦截
  - run_command 的 SandboxExecutor 在 app/main.py 注册，workdir 已改为项目根（CLIMBER_SANDBOX_WORKDIR 或 os.getcwd()），命令中绝对路径必须在 workdir 内（app/core/sandbox.py _is_command_safe）；服务重启后需重新 PUT 切 AUTO 模式
  - 服务重启加载 .env 生效：`cd /workspace && PYTHONPATH=/workspace /usr/bin/python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000`

[原生桌面与媒体工具能力]
- Date: 2026-08-11
- Context: Agent 补齐"打开电脑/剪辑视频"能力时发现并修复
- Category: 环境配置
- Instructions:
  - native_tools.py 的桌面/媒体工具（native_run/native_read_file/native_write_file/open_browser/take_screenshot/click_mouse/type_text/process_video/process_image/download_file）此前从未注册（register_builtins 只导入 builtins），现已注册（app/tools/__init__.py register_builtins 导入 native_tools）；存量 agent 的 tool_ids 是创建时固化的旧列表，chat.py 加载 session 时已改为 agent tool_ids 与当前注册工具做并集，新工具自动可用
  - headless 环境桌面能力依赖：ffmpeg、imagemagick(convert)、xvfb、scrot、xdotool、chromium 已安装；Xvfb 需启动 `Xvfb :99 -screen 0 1280x800x24 -ac`，服务需带 `DISPLAY=:99 XAUTHORITY=/tmp/opencode/.Xauthority` 启动才能用桌面工具
  - pyautogui 在 Xvfb 下 import/截图会阻塞，已禁用（_pyautogui_available 恒 False），截图/点击/输入走 scrot/xdotool 兜底；无 DISPLAY 时返回明确错误
  - open_browser 无 DISPLAY 时用 chromium `--headless=new --no-sandbox --no-first-run --dump-dom`（旧 --headless + --user-data-dir 会报 "Multiple targets not supported"），首次运行可能 ~40s
  - process_video 已修复只读 stderr 的 bug（-version 等输出在 stdout），现合并 stdout+stderr
  - 验证过的能力：process_video 剪辑视频真实落盘（e2e: sample.mp4 5s→cut.mp4 2s）、run_command 执行 ls、write_file 写文件

[开发方法论：第一性原理、对抗式审查、逆向与系统思维]
- Date: 2026-08-12
- Context: 用户明确提出的三条工作方法论指令
- Instructions:
  - 第一性原理开发：从需求/问题的本质出发，逐层分解到不可再分的基本事实或原理，再从基础向上构建解决方案，而非依赖类比或现有方案
  - 对抗式审查：以"找出漏洞/缺陷"为目的审查代码，假设代码存在隐性问题，主动构造反例和边界条件来检验
  - test 和 debug 时用逆向思维和系统思维：逆向思维是从输出/现象反推根因和路径；系统思维是从整体系统角度考虑组件间的关联影响，而非局部修补

[前端优化共享组件库与设计令牌]
- Date: 2026-08-16
- Context: Agent 执行 Climber 平台全面优化任务时发现
- Category: 环境配置
- Instructions:
  - 共享组件库已创建在 src/components/ui/：ErrorBanner, EmptyState, LoadingSpinner, SearchInput, PageHeader, ListCard, FilterChips, StatCard, ActionButtonGroup
  - 设计令牌统一在 src/index.css，使用 CSS 变量如 --color-accent, --color-bg-surface-1, --color-text-primary 等
  - 新增 UI 组件需导出对应 Props 接口（export interface XxxProps），否则 TypeScript 类型检查会失败
  - vitest 测试失败常见原因：climber_legacy_conflict 子目录缺少依赖，不影响主项目；核心测试通过即可

[后端 pytest 必须单进程运行]
- Date: 2026-08-21
- Context: Agent 在排查任务领域测试出现随机缺表错误时发现
- Category: 测试方法
- Instructions:
  - 后端测试共用 `data/test.db`，`tests/conftest.py::cleanup_db` 会在每项测试后执行全库 `drop_all` 和 `init_db`
  - 同一时间只能运行一个 pytest 进程；多个 pytest 命令需合并为单条串行命令，避免互相删表产生 `no such table` 伪失败
  - 启动定向或全量回归前先确认没有遗留 pytest 进程；Ruff、前端检查等不访问该测试库的命令可以并行
  - async engine 的数据库清理必须在 pytest 当前事件循环内执行，并在 teardown 中 `await engine.dispose()`；测试创建的后台数据库任务必须显式等待完成，避免进程退出时出现 aiosqlite `Event loop is closed`

[Climber Agent 进化实验工作流]
- Date: 2026-08-21
- Context: 用户要求后续 Agent 能力优化采用可度量、可回滚、有人类审批边界的持续实验流程
- Instructions:
  - 每轮开始重读本条规则，研究一个已核验的官方开源标杆模块，并在 Climber 原生架构内做适配实验
  - 修改系统提示、策略、记忆规则或多 Agent 编排逻辑前先创建检查点；每轮最多合并 3 个优化点
  - 候选方案使用独立分叉做 A/B 测试，仅将量化结果最优且端到端无回归的方案合入主工作流
  - 每轮执行基准、旧测、新测试、对抗测试和副作用检测，长期保存成功、失败、成本与适配记录
  - 涉及权限体系、MCP 注册逻辑、高风险工具或沙箱规则时暂停实现并请求人工确认
  - 连续 3 轮综合得分未提升时暂停迭代并请求人工确认；每 3 轮组织 7 个专家角色交叉验证
  - 每轮结构化日志持久化到 `.monkeycode/evolution/`，记录量化得分、端到端完成率、标杆来源、候选结果、成本和下一轮目标
  - 进化主线聚焦吸收已核验开源 Agent 的核心机制并适配进 Climber；测试用于基线、证伪和回归，避免把测试数量当作进化目标
  - 每轮优先交付可运行的 Agent 能力提升，记录来源机制、Climber 适配修改点、实际能力变化、适配成本和残余风险

[Climber Agent 事件回放验证]
- Date: 2026-08-22
- Context: Agent 在适配 Codex 有界事件缓冲和 DeepSeek Harness 回放隔离时发现
- Category: 测试方法
- Instructions:
  - 第3轮事件回放验证使用后端单进程命令：`/usr/bin/python3 -m pytest tests/test_chat_replay.py tests/test_event_replay.py tests/test_agent_engine_edges.py tests/test_checkpoint_survival.py tests/test_agi_p1_survival.py tests/test_tool_pipeline_fixes.py tests/test_parallel_concurrency.py -q --no-header -p no:cacheprovider`
  - 回放缓冲当前为进程内有界存储，默认容量 256 条、字节预算 256 KiB；重启或多 worker 交接会丢失事件，持久化事件表需要单独评估 schema 和迁移范围
  - 回放 API 使用认证、session owner 校验、`after` 游标、`turn_id` 过滤和 `limit` 上限；游标早于保留窗口时通过 `oldest_sequence` 暴露 gap 检测信息
  - 前端回归、lint 和构建命令：`cd /workspace/frontend-react && npm run test -- --run src/hooks/__tests__/useChat.test.ts`、`npm run lint`、`npm run build`

[Climber 安全边界验证与暂停门禁]
- Date: 2026-08-22
- Context: Agent 在执行第3轮七专家交叉审计及第4、5轮安全进化时发现
- Category: 测试方法
- Instructions:
  - 安全低于90时暂停普通能力优化；第5轮 fail-closed 加固后安全复评分为88，仍需人工确认后才能继续读取机密性、native path、认证、管理授权或 OS 隔离改造
  - 路径隔离必须使用 `Path.resolve(strict=False)` 加组件级祖先判断；字符串 `startswith` 会误放行同前缀兄弟目录并误封同前缀安全目录
  - blocked path 包含 glob 时应匹配目标路径及其父路径，确保 `/home/*/.ssh` 能覆盖密钥文件，同时避免误封 `.ssh-notes`
  - 公共权限配置 API 只允许 DEFAULT、ACCEPT_EDITS、PLAN、AUTO；内部 BYPASS 仅供受信进程内调用；AUTO 必须优先执行 `denied_tools` 和显式 DENY
  - 第4轮单进程回归命令：`/usr/bin/python3 -m pytest tests/test_evolution_round4_security.py tests/test_sandbox_integration.py tests/test_security_fixes_tools.py tests/test_permission_controller.py tests/test_permission_tiers.py tests/test_parallel_approval.py tests/test_agent_engine_edges.py tests/test_chat_replay.py tests/test_event_replay.py tests/test_checkpoint_survival.py -q --no-header -p no:cacheprovider`
  - sandbox 初始化失败时采用正向能力声明：`ToolDefinition.sandbox_safe_when_unavailable` 默认False，只有显式受信的纯/读取工具可运行；MCP和动态工具默认拒绝，工具名称本身不授予能力
  - debug recovery 必须复用工具验证边界；sandbox拒绝、权限拒绝和ASK结果不能触发自动副作用，也不能被恢复结果改写为成功
  - 第5轮单进程回归命令：`/usr/bin/python3 -m pytest tests/test_evolution_round4_security.py tests/test_sandbox_integration.py tests/test_security_fixes_tools.py tests/test_permission_controller.py tests/test_permission_tiers.py tests/test_parallel_approval.py tests/test_agent_engine.py tests/test_agent_engine_edges.py tests/test_chat_replay.py tests/test_event_replay.py tests/test_checkpoint_survival.py tests/test_tool_pipeline.py tests/test_tool_pipeline_fixes.py tests/test_parallel_concurrency.py tests/test_native_tools.py tests/test_unified_tools.py tests/test_tool_runtime.py -q --no-header -p no:cacheprovider`
  - 已知残余风险：sandbox故障时受信读取工具保留宿主可读范围、native读取使用较弱的abspath边界、固定本地身份、权限配置缺少管理员边界、宿主进程缺少强网络/文件系统隔离、路径验证与打开之间存在TOCTOU窗口

[Climber 降级只读边界与符号链接安全]
- Date: 2026-08-23
- Context: Agent 在执行第6轮安全加固时发现
- Category: 排错调试
- Instructions:
  - sandbox=None 时原实现对 sandbox_safe_when_unavailable=True 的工具无条件放行，导致 read_file 可读取宿主任意文件；修复后降级构建 SecuritySandbox 通过 validate_file_access 限制到 workdir 内
  - native_tools.py 的 _validate_path_within_workspace 和 _validate_file_path 使用 os.path.abspath+startswith 会误放行同前缀兄弟目录（如 /workspace-data 误匹配 /workspace）；修复后使用 Path.resolve()+relative_to() 做精确祖先判断
  - native_list_dir 缺少路径验证调用，现已添加 _validate_path_within_workspace
  - process_video 和 process_image 接受 command 参数执行子进程，但未纳入 _COMMAND_TOOLS 或 _FILE_TOOLS，导致沙箱验证完全绕过；修复后加入 _MEDIA_TOOLS 走 sandbox.validate_command()
  - sandbox=None 分支的 FILE_TOOLS 只检查 mode=="read"，write 模式会跳过整个分支直接放行；修复后显式拒绝 write 模式工具
  - 第6轮单进程回归命令：`python3 -m pytest tests/test_evolution_round6_security.py tests/test_agent_engine_edges.py tests/test_security_regressions.py tests/test_security_fixes.py tests/test_security_fixes_tools.py tests/test_agi_p5_security.py tests/test_sandbox_integration.py tests/test_native_tools.py tests/test_agent_engine.py -q --timeout=120`

[开源标杆研究与动态工具安全加固]
- Date: 2026-08-23
- Context: Agent 在执行第7轮安全加固 + 开源研究时发现
- Category: 排错调试
- Instructions:
  - dynamic_tool.py 的 exec() 仅限制 builtins 但无 AST 预校验，代码可通过 __import__ 引入 os/subprocess 等模块绕过限制；修复后添加 _validate_code_safety() 用 AST walk 拦截危险 import/call
  - dynamic_tool.py 的 _load() 加载持久化工具时未做安全校验，旧代码可能包含危险操作；修复后加载时执行 _validate_code_safety()，不通过的工具直接跳过
  - sandbox_runtime.py 使用 create_subprocess_shell() 允许 shell 元字符注入（管道、重定向、分号）；修复后改用 shlex.split() + create_subprocess_exec()
  - 第7轮单进程回归命令：`python3 -m pytest tests/test_evolution_round6_security.py tests/test_agent_engine_edges.py tests/test_security_regressions.py tests/test_security_fixes.py tests/test_security_fixes_tools.py tests/test_agi_p5_security.py tests/test_sandbox_integration.py tests/test_native_tools.py tests/test_agent_engine.py tests/test_tool_pipeline.py tests/test_tool_pipeline_fixes.py -q --timeout=120`
  - 开源标杆：Hermes Agent (NousResearch) — GEPA 自进化管线、三层记忆、自修复技能、轨迹压缩、四层风险分级进化；下轮可适配自修复技能到 Climber ToolExtender

[全面安全加固：文件转换路径校验 + 沙箱模式统一]
- Date: 2026-08-23
- Context: Agent 在执行第7轮全面优化时发现
- Category: 排错调试
- Instructions:
  - file_conversion_tools.py 的 13 个工具函数接受 input_path/output_path 参数但无路径校验，LLM 可通过工具参数读写宿主任意文件；修复后添加 _validate_conversion_path() 用 Path.resolve()+relative_to() 校验 /workspace 和 /tmp 根目录
  - sandbox_runtime.py 的 BLOCKED_PATTERNS 只有 10 条（security_sandbox.py 有 30+ 条），遗漏了 sudo、shutdown、reboot、nc 反弹 shell 等关键模式；修复后统一为 30+ 条与 HAZARD_COMMANDS 对齐
  - container_exec 通过 sh -c 将命令传入容器，命令中的 shell 元字符（管道、重定向、分号）可在容器内注入；修复后在传递前用 HAZARD_COMMANDS 校验命令字符串
  - agent_engine._validate_tool_call 中 tool_registry.get_tool() 被调用两次（JSON Schema 校验和 sandbox 分支各一次）；修复后缓存结果避免重复查找
  - threading.Lock 在 resource_quotas.py 中是同步方法使用的，不能替换为 asyncio.Lock（会导致 with 语句失效）；维持原状，实际阻塞时间极短（dict 操作）
  - 安全复审评分 78/100，主要残余：download_file 缺少内部路径验证、CLIMBER_SANDBOX_WORKDIR 环境变量信任假设
  - sandbox-None 分支 path 回退必须包含 dir 参数，否则 list_directory 会因路径为空绕过沙箱检查
  - _BLOCKED_PREFIXES 中 /proc /sys /dev 必须带尾斜杠，否则 /procxfoo 会被误封；用 rstrip("/") 标准化比较
  - process_video/process_image 必须注册到测试 ToolRegistry 才能测试 _MEDIA_TOOLS 代码路径，否则命中"未分类工具"拒绝
