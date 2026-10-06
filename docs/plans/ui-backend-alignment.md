# 锚定 UI 与后端契约对齐

核查日期：2026-10-02。基于当前工作区行号，前端并行代理后续编辑可能移动行号。先读完 `active-plan.md`、`frontend-anchored-ui.md`、`ui-source-evidence.md`、`backend-source-evidence.md`。本轮手工修改限于 `app/**`、对应 tests 和本文；保留既有改动，无提交、删除、前端修改、网络请求或安全扫描。

## 行级证据表

路径相对 `/workspace/climber`。源码核对、离线实测和待办分别记录；下表“通过”仅指明确列出的测试范围。

| 要求（frontend-anchored-ui.md） | 前端事实 / 行级证据 | 后端事实 / 行级证据 | 实际验证 | 剩余 |
| --- | --- | --- | --- | --- |
| 技能分类、即时开关，49-53 | `frontend-react/src/components/workspace/AnchoredLeftNav.tsx:363` 调用开关；`src/api.ts:695-698` POST enable/disable | `app/api/v1/routes/skills.py:105-120,146-168,186-204` 主体过滤、持久化 `is_enabled`；`app/api/v1/__init__.py:71-75` 仅扩展 PATCH 路由 | `tests/core/test_ui_backend_alignment.py:test_skill_switch_persists_for_owner_and_requires_write` 真实 ASGI/SQLite：关后读回、其他主体 404、只读 403、重新启用 | 引擎 `app/core/agent_engine.py:477-487` 构造工具只读 session.tools；数据库技能开关与内置 SkillRegistry 执行策略接线待实现，不能以保存成功宣称执行中即时禁用 |
| 三配置档全局 UI / 工具权限 / 提示词策略，54-57、126 | `src/store/anchored.ts:90-100,129-159,303-306` minimal/standard/full 为 localStorage UI 偏好；左栏 `AnchoredLeftNav.tsx:416` 本地切换 | `app/api/v1/settings.py:18-82` 仅自主模式/MCP/notifications；`app/api/v1/permissions.py:61-146` 管理员全局权限配置，未定义三配置档映射 | 本轮源码核对；既有 permission chain 离线回归通过 | 三档权限与提示词具体映射未定义，需形成账户级策略并受既有权限上限约束。保留本地 UI 偏好与后端策略的独立作用域；当前无三档后端保存契约 |
| 三泳道、阻塞原因、拖拽迁移，92-96 | `src/components/anchored/TaskTracePanel.tsx:15-19,33-43,57-83` 账户任务 5 秒轮询；retrying 明示未映射；`store/anchored.ts:310-328` 本地规划泳道 | `app/api/v1/routes/tasks.py:64-145` submit/list/get/cancel/pause/resume/retry/rollback；`app/core/task_worker.py:374-450` 账户过滤。本轮列表增加 error/interruption_reason/起止时间 | 任务 owner/workflow 测试 17 项与 12 subtests；新增失败结果列表读回测试通过 | 会话关联字段/筛选、拖拽的状态机转换契约待实现。running→completed 应由执行器确认完成证据；任意拖拽写状态的接口尚未定义。前端需展示新增阻塞字段 |
| Token 六指标、最近十轮分色、重置，97-100 | `src/components/workspace/AnchoredInfoPanel.tsx:121-177,291-309` 拉 usage + records；`store/anchored.ts:179-200` 本地计算；缺数据 null | `app/api/v1/cost.py:96-112` 账户累计费用/token/calls；`routes/misc.py:670-686` 账户记录按时间倒序，可 session_id 过滤；`storage/models_cost.py:22-45` 每模型调用记录，无缓存 token 列 | 源码核对；本轮未运行计量专用测试 | 缓存命中率/缓存节省来源、未知费用与真实零费用区分、round/turn 聚合、重置基准与分页待实现。前端 slice(-10) 对倒序记录取旧记录、记录粒度为调用、今天真实零被 `|| null` 转空值，交前端代理处理 |
| 子任务树、失败高亮、真实耗时，101-104 | `AnchoredChatColumn.tsx:71-96` 通过工具名匹配扁平节点；`AnchoredInfoPanel.tsx:186-214` children/耗时 UI；TaskTracePanel 展示会话 trace | `app/core/collaboration/progress.py:200-333` node_id/parent_id/task_name/status/elapsed_ms；`group_ws_hub.py:210-230` 树/进度/最近事件快照。本轮挂载 `GET /groups/{group_id}/snapshot` 于 `routes/groups.py:30-42`，先验证 owner | 现有 WS/progress 28 项回归通过；新增群组快照真实 SQLite owner 与其他主体 404 通过 | sequential/hierarchical/base 生命周期接入仍见 active-plan.md:105；前端需消费真实树/parent_id/elapsed_ms，群组与当前会话关联待定义。树与事件为进程内数据，跨重启持久恢复待实现 |
| 文件预览、增删改标记、路径、多标签，105-108 | `AnchoredChatColumn.tsx:85-93` 仅成功文件工具结果；`store/anchored.ts:360-390,489-508` 结果行转换；`components/anchored/ArtifactPreview.tsx` 受控预览 | `app/core/engine/tool_exec.py:233-240,310-344` TOOL_CALL id/name/arguments + TOOL_RESULT id/tool_name/result/error；`app/tools/builtins.py:169-194,316-349` 文件读取/写入/编辑返回文本，edit 含 unified diff | 本轮源码核对；文件工具实际执行未验证 | 独立 artifact 内容/下载/版本 API、结构化 diff 与实际变更标识待实现；write_file 回执文本不等于完整文件内容，PLAN mode preview 不等于实际改动。UI 路径 fallback 与准确预览需前端调整 |
| SOUL/记忆/项目规则保存即时生效、上下文总线，109-112 | `AnchoredInfoPanel.tsx:227-281,329` saveRule 本地状态且提示未接后端；`store/anchored.ts:392-395` 本地修改 | 新增 `app/api/v1/ui_rules.py:11-35` GET/PUT；`app/core/ui_rules.py:25-82` Document 持久化、主体隔离、CAS revision、下一次模型迭代刷新；`engine/runner.py:169-174` 每迭代加载。API aggregation 已挂载 | 新增三 kind 保存读回/主体隔离/409 stale/403 scope/422 unknown+超长测试；`test_engine_facade_wiring.py:test_saved_ui_rules_reach_next_model_iteration` 真实引擎 + scripted 模型看到规则更新 | 前端 GET/PUT 接线待实现。当前 scope=user，project 文档是该用户的项目规范文本；多项目共享、项目成员权限、上下文总线通知与资产版本历史待实现。生效精确定义为下一次模型迭代，已发出的模型请求保持原输入 |
| 审批栈、成功才销毁、主体权限，83-85、124 | `AnchoredChatColumn.tsx:98-122` requiresApproval/toolCallId；`AnchoredPopupStack.tsx:33-50,135-143` POST 完成销毁、失败留栈、参数/确认 disabled | `tool_exec.py:267-273,310-322` requires_approval/tool_call_id/timeout_seconds；`permissions.py:41-58` scope write / 无 pending 404。本轮 resolve_permission 传 owner_id；`agent_engine.py:733-751` 匹配会话主体后决议 | 新增相同 tool_call_id 对其他主体无法决议的离线单测；permission chain 回归通过 | 参数配置与输入确认后端提交契约、审批列表/断线恢复与超时通知待实现；本轮新审批校验为引擎单测，真实 pending 审批 HTTP + 模型执行闭环待验证 |
| 规划展开任务看板，118 | `store/anchored.ts:330-341` expandForNewTask 本地登记；任务执行与本地规划记录分离 | `task_worker.py:908-949` factory_start/planning/plan 事件 | 任务快照/历史测试通过；factory 规划专用验收待执行 | 当前前端只轮询账户任务，需接 task events 的 planning/plan；会话发起任务关联待接 |
| 调用工具状态、失败展开，119-120 | `AnchoredChatColumn.tsx:41-69` 状态映射；useChat 保存工具终态（ui-source-evidence.md:61） | `tool_exec.py:233-240,310-344` 调用与结果；`engine/runner.py:169` thinking | 既有 WS/permission/engine 离线回归通过，前端回归由另一代理负责 | tool result 结构化终态/耗时及错误重试策略需统一；保留 result/error 事实 |
| 拆子任务与编辑文件自动展开，121-122 | `AnchoredChatColumn.tsx:71-96` 工具名启发式触发 | 树规范事件见 progress.py:280-323；文件事件见 tool_exec.py:233-240 | 本轮只核对真实字段，未宣称 UI/真实文件端到端通过 | 前端需用结构化树/文件变更事实替换名匹配触发；正式 producer 接线待完善 |
| 结束五秒自动折叠，123 | `AnchoredChatColumn.tsx:34-39` streaming 停止调用 noteTurnEnd；`store/anchored.ts:416-437` 五秒计时 | `engine/runner.py:116-125` DONE(status/metrics/tokens_used)；任务 SSE 本轮先快照、普通生命周期 task_update 后终态关闭 | 新增完成任务 SSE 单帧退出、心跳连续两次继续订阅、失败终态退出/清理测试通过 | 前端当前以 streaming 停止触发折叠，错误/网络断线/等待审批与实际完成需分开；仅真实终态触发折叠，失败卡与审批留存规则需对齐 |
| 斜杠命令，125 | `AnchoredComposer.tsx` 斜杠入口，尚需逐命令核对 | `app/api/v1/routes/chat_commands.py` 已有命令路由 | 本轮未执行命令端到端测试 | 逐条命令参数、scope、副作用与响应接线待验收 |
| 异常原因+重试，127 | TaskTracePanel.tsx:38-44,59；PopupStack.tsx:46-49,136 错误留存 | task_worker 失败持久化/error；本轮重试返回 failed 保持 failed，`task_worker.py:585-599` | 新增 scripted retry failed 返回、DB/status/event/list 一致通过 | 全局错误重试应绑定原任务/原调用及权限；运行请求失败时规则加载明确传播 ERROR，未做静默成功 |
| 任务事件快照/重连事实（支撑118-123） | 当前 TaskTracePanel:33-43 使用 5 秒轮询；独立 SSE 尚未接 | `tasks.py:147-185` events + snapshot；`task_worker.py:156-210,618-622` 有界历史、epoch/sequence/timestamp、普通进度入历史。本轮保留 TaskResponse 起止时间 | owner/其他主体 404、重启历史清空保留 DB 状态、100 事件上限、序号递增、心跳/终态/清理通过 | 历史 process_recent_100、epoch 全进程、sequence 全局单调；每个客户端需要快照为权威，实时队列补充。跨 worker/pubsub、持久事件游标、慢订阅者队列上限待实现 |

## 本轮可用契约

全部路径带 `/api/v1`。以下接口已由代码提供，前端另代理需完成消费接线。

| 接口 | 输入 / 输出 | 权限与失败 |
| --- | --- | --- |
| GET `/ui/rules` | 三条 `{id,kind,title,content,revision,scope:"user"}`；未保存 content 空、revision null | read；当前主体，API 无可提交 owner 字段 |
| PUT `/ui/rules/{soul\|memory\|project}` | `{content,revision}`；首次 revision=null；返回已提交的 content/revision 及 effective=next_iteration | write；内容最多32000字符；未知 kind/字段/超长422；旧revision409；DB失败向上传播 |
| GET `/tasks/{task_id}/snapshot` | `{type:"snapshot",task_id,protocol_version:1,epoch,sequence,timestamp,data:持久任务状态,events,history_scope:"process_recent_100"}` | read；owner/admin 可见，其他主体404；events 最多100条，仅进程内 |
| GET `/tasks/{task_id}/events` | `data: JSON`；首帧同snapshot，后续 `{type,data,task_id,protocol_version,epoch,sequence,timestamp}`；空闲心跳 `: keep-alive` | read及owner检查；completed/failed/cancelled 终态退出；paused 留订阅；退出取消订阅。无持久 Last-Event-ID 恢复声明 |
| GET `/groups/{group_id}/snapshot` | group_id/generated_at/protocol_version/connected_clients/recent_events/task_tree/progress/history_scope=process_recent | read + group owner；其他主体404；树/进度仅当前进程 |
| POST `/permissions/resolve` | tool_call_id / allow、allow_session、allow_always、deny | write；本轮限制 pending session.user_id 等于调用主体；无匹配404 |

规则复用既有 documents 表与确定性 owner/kind UUID 主键，采用 `anchored-ui-rules` collection，未新增迁移或 schema。当前数据库必须已有 documents 表。规则作为 user-role 上下文读取，保持 system policy 与工具权限原有权威；模型请求只使用标准 role/content 字段。刷新放在最近 user 消息之前，保留 assistant tool_call 与 tool_result 的相邻协议。保存返回成功发生在事务 commit 后，内容 hash 用作 CAS 修订标识；多项目作用域与完整版本历史分别属于待办。

事件快照非原子跨数据库/内存事务：订阅先建立，然后读取快照，DB状态为权威；events 是最近进程内事实。消费方应按 epoch/sequence 去重并保留订阅期间补充事件；epoch 变化后重新获取快照。进程重启后 DB 状态仍可读，events 可为空，未构造恢复过往子任务的假事件。

## 离线验证

身份与模型/执行器是明确标注的 scripted doubles；HTTP 使用 httpx ASGITransport，存储使用私有 SQLite。没有对在线模型、真实服务器、浏览器或生产数据做验收。使用 `--noconftest` 避开共享数据库清理，未修改阈值或忽略失败断言。

```bash
python3 -m pytest --noconftest -o addopts='' tests/core/test_ui_backend_alignment.py tests/core/test_task_owner_workflow_contract.py tests/core/test_engine_facade_wiring.py tests/core/test_engine_metacognition_wiring.py tests/core/test_ws_protocol_progress.py tests/core/test_permission_security_chain.py tests/core/test_prompt_optimizer_runner.py -q -p no:cacheprovider

ruff check --select E,F,I app/core/ui_rules.py app/api/v1/ui_rules.py tests/core/test_ui_backend_alignment.py

git diff --check -- app tests docs/plans/ui-backend-alignment.md
```

- 首轮优先契约：24 passed / 12 subtests passed。
- 接引擎后回归发现1项失败：私有fixture缺 documents 表；新增 Document fixture。
- 联合收集发现4项失败，原始错误 `(sqlite3.OperationalError) no such table: checkpoints`，checkpoint 模块已提前导入旧 async_session；fixture 显式 patch checkpoint.async_session，保留真实存储验证。
- 修复后七文件联合回归：76 passed / 12 subtests passed（10.66秒）；含新增9条契约测试及引擎模型请求规则更新测试。
- 新增文件 E/F/I 检查通过；限定路径 diff --check 通过。全仓回归、真实生产执行、前端接线、视觉验收仍待执行。

## 明确待办

- [x] 规则账户级保存/读回/CAS/权限/下一次迭代刷新及测试。
- [x] 普通任务生命周期进入 SSE 历史、初始权威快照、心跳持续连接、终态清理及测试。
- [x] 任务列表错误/阻塞原因/起止时间字段保留。
- [x] 重试 failed 结果保持失败；审批按 owner 决议。
- [x] 群组树/进度快照 owner-gated HTTP 入口及测试。
- [ ] 前端消费新规则/任务/群组快照契约，真实交互与自动显隐验收（另代理）。
- [ ] 技能开关与执行工具/提示词即时策略联动，含运行中切换。
- [ ] 三配置档账户策略、工具上限与提示词映射定义/持久化/执行接线。
- [ ] 任务会话关联/筛选与有证据的泳道状态机迁移。
- [ ] Token六指标统一快照、缓存真实计量、turn粒度十轮趋势、用户重置基准。
- [ ] 子任务 TaskTree/ProgressTracker 生产生命周期接线、会话/group映射、持久树恢复。
- [ ] 独立文件产物/结构化diff/版本/下载契约；PLAN与实际变更区分。
- [ ] 项目级规则scope、项目成员权限、上下文总线通知与版本历史。
- [ ] 审批待处理快照、参数/确认提交协议、超时同步。
- [ ] 所有斜杠命令逐条离线验收与错误重试副作用规则。
- [ ] 事件跨worker/持久日志/游标恢复、有界订阅队列、原子快照边界。
