# 前端组件级源码证据与落地

日期：2026-10-02。研究仅请求 `api.github.com` 仓库元信息/tree 与 `raw.githubusercontent.com` 源码，另读取已下载的 cc-haha。未访问演示网站，未复制上游源码、图标或品牌资产。位置与尺寸依据 `frontend-anchored-ui.md`，用户给出的产品描述仅作为研究目标。

## 仓库核实

请求形态：`GET /repos/{owner}/{repo}`，从响应的 `full_name/default_branch` 继续请求 `GET /repos/{full_name}/git/trees/{default_branch}?recursive=1`，再按精确路径读取 raw。所有成功 tree 的 `truncated=false`。首次部分请求 403，增加查询标识后重试，以下是最终结果。HTTP 404 表示当前公开访问无法取得仓库，无法据此判断仓库从未存在或是否私有。

| 用户指定仓库 | 核实结果 / 默认分支 | tree SHA |
| --- | --- | --- |
| All-Hands-AI/OpenHands | API 重定向至 OpenHands/OpenHands / main | 2414d6ee5e31bede2e78211f72b58e9949575a75 |
| WorkDSH/WorkDSH | 两次 API 404，未读源码 | 无 |
| opencove/opencove | 两次 API 404，未读源码 | 无 |
| bytedance/deer-flow | main | 63e399f2bdf6ad1269724c10cfc98bb40c7550d3 |
| EKKOLearnAI/ekko-studio | main | ef9409601855557633edf07c08512b9dadb7a03f |
| CopilotKit/CopilotKit | main | f835ce816112541654ded07162c2cc8ddf4f3f2c |
| web3dev1337/agent-workspace | 两次 API 404，未读源码 | 无 |
| Tencent/WeKnora | main | bccb4b151bae403508da77fbb174efc79dc47c1a |
| AgentGUI-Team/AgentGUI | 两次 API 404，未读源码 | 无 |
| milisp/codexia | master，首次 tree 403，重试成功 | 7e3cffee3534e2e242df8c20193c944ffc3cb7dd |
| mastra-ai/mastra-ui | 两次 API 404，未读源码 | 无 |
| dyad-app/dyad-web | 两次 API 404，未读源码 | 无 |
| arkon-dev/agent-control-room | 首次 403，重试 404，未读源码 | 无 |
| json-render/json-render | 首次 403，重试 404，未读源码 | 无 |
| saadnvd1/agent-os | 首次 403，重试 404，未读源码 | 无 |
| NousResearch/hermes-control-room | 首次 fetch failed，curl 与重试 API 均 404，未读源码 | 无 |
| NanmiCoder/cc-haha | main，本地 HEAD 与 API tree 同 SHA | 6d8071be8e739d32bf218b1942bec2cece12beb3 |

## 已读文件与组件对照

远程研究逐文件读取前 100 行；表中结论仅针对已读范围，不宣称完成整个文件或仓库审查。临时原始输出在 `/tmp/terminal_term_1790927876848_77.log` 与 `/tmp/terminal_term_1790928017330_78.log`。

| 仓库 | 确切路径（已读范围） | 源码可确认的结构 | Climber 落地 |
| --- | --- | --- | --- |
| OpenHands/OpenHands | `src/routes/root-layout.tsx` 1-100 | sidebar/provider/query 分层，错误边界输出错误原因 | 保留既有三栏骨架，面板请求错误显式显示 |
| OpenHands/OpenHands | `src/types/agent-server/core/events/acp-tool-call-event.ts` 1-100 | tool_call_id 对应 started/terminal 状态，completed/failed 分离 | `useChat.ts` 保留工具终态，done 仅完成回合 |
| OpenHands/OpenHands | `src/stores/conversation-panel-preferences-store.ts` 1-100；`src/components/features/conversation-panel/conversation-layouts-menu.tsx` 1-100 | 布局偏好与配置档类型分层 | 保留 anchored UI 偏好 store 与业务契约边界 |
| OpenHands/OpenHands | `src/components/conversation-events/chat/event-content-helpers/get-acp-tool-call-content.ts` 1-100；`src/stores/error-message-store.ts` | 按工具类型归一化，payload 显示防御处理；错误 store | 错误输出保留并内嵌展开 |
| bytedance/deer-flow | `frontend/src/app/workspace/layout.tsx` 1-57；`frontend/src/app/(auth)/layout.tsx`；`frontend/src/app/artifacts/view/layout.tsx` | workspace 与 artifact route/provider 边界 | 不引入上游登录流程与布局 |
| bytedance/deer-flow | `frontend/src/components/workspace/messages/tool-call-details.tsx` 1-100 | 内嵌 details，aria-controls，input/result 分离，错误结果标签 | 工具结果默认折叠，失败展开且支持再次折叠 |
| bytedance/deer-flow | `frontend/src/components/workspace/artifacts/context.tsx` 1-100；`frontend/src/components/workspace/artifacts/artifact-viewer.tsx` 1-100 | 路由域持久化、selected artifact、内容读取/预览边界 | 会话切换重置旧预览，只显示真实成功文件工具输出 |
| EKKOLearnAI/ekko-studio | `packages/client/src/components/layout/AppSidebar.vue` 1-100；`packages/client/src/components/hermes/chat/ToolChangeCard.vue` 1-100 | sidebar 模块与选中文件受控展示 | 保持 Climber 固定左栏顺序和右侧预览位置 |
| EKKOLearnAI/ekko-studio | `packages/client/src/components/hermes/chat/ToolRunCard.vue` 1-32；`packages/client/src/composables/useToolTraceVisibility.ts` 1-35 | runId 聚合工具、trace 可见性偏好 | 工具卡按 id 更新，trace 内嵌既有任务树卡片 |
| EKKOLearnAI/ekko-studio | `packages/client/src/components/hermes/skills/PendingWriteApprovals.vue` 1-100；`packages/client/src/components/layout/GlobalPendingActions.vue` 1-100 | pendingActions、submitting、generation 与订阅清理字段 | 审批按钮提交期间禁用，面板请求用生命周期标记阻止陈旧写入 |
| CopilotKit/CopilotKit | `examples/showcases/a2a-travel/components/hitl/BudgetApprovalCard.tsx` 1-100 | approve/reject 回调与 isApproved/isRejected 展示分离 | 真实权限 POST 完成后才销毁审批 |
| CopilotKit/CopilotKit | `examples/showcases/scene-creator/src/components/ArtifactPanel.tsx` 1-100；`examples/canvas/langgraph-python/src/app/layout.tsx` | artifact 独立面板，通过输入上下文发起编辑；示例布局 | 保持右侧文件卡，明确缺少独立产物下载契约 |
| Tencent/WeKnora | `frontend/src/views/chat/components/ToolApprovalCard.vue` 1-100 | resolved/submitting 驱动审批按钮、参数区与超时提示 | 审批错误留在输入栈，支持重新提交 |
| Tencent/WeKnora | `frontend/src/views/chat/components/ChatArtifactsPanel.vue` 1-100；`frontend/src/api/artifacts.ts` 1-100 | artifact preview 与列表切换、session/message/index 标识与 API 边界 | 本次只对接已有文件输出，标注独立 artifact API 未接入 |
| Tencent/WeKnora | `frontend/src/utils/traceAxis.ts` 1-84；`frontend/src/utils/kbPermission.ts`；`frontend/src/views/integrations/IntegrationLandingLayout.vue` | trace 时间轴采用真实 duration，权限工具与布局独立 | trace 展示服务端 duration_ms/spans，缺少耗时显示未上报 |
| milisp/codexia | `src/components/layout/AppLayout.tsx` 1-100；`src/bindings/ApplyPatchApprovalParams.ts` 1-22 | 可调整右栏与布局 store，审批类型化 binding | 保留锚定尺寸，右栏折叠宽度改为 0，标题栏提供展开操作 |
| NanmiCoder/cc-haha | `desktop/src/components/agentTeams/AgentTeamsWorkbench.tsx` 1-100；`desktop/src/api/traces.ts` 1-44 | workbench 模型与组件分离，trace API 独立 | 子任务按 id upsert，trace 请求限定当前 session |
| 本地 cc-haha | `desktop/src/components/chat/PermissionDialog.tsx` 1-200；`desktop/src/components/chat/ToolCallBlock.tsx` 1-200 | session/requestId 绑定审批；工具 input/result、pending/error/展开状态分离 | requires_approval 贯穿 SSE 到输入栈；错误结果独立于回合结束 |
| 本地 cc-haha | `desktop/src/components/activity/SessionActivityPanel.tsx` 1-120；`desktop/src/stores/taskStore.ts` 1-78；`desktop/src/stores/workflowStore.ts` 1-120 | activity section 分类，任务 API 镜像，session epoch 与 snapshot 权威边界 | 账户任务标明范围，trace 会话过滤，轮询卸载清理 |

## 本地契约核对

- `app/core/engine/tool_exec.py` 245-344：审批来自 tool_call 事件，其 `requires_approval` 与 `tool_call_id` 是事实来源；等待权限决议后继续执行。
- `app/api/v1/permissions.py` 1-146：POST `/permissions/resolve` 接受 tool_call_id 与 allow/deny；无待审批项返回 404。前端成功响应后销毁，错误保留并允许重试。
- `app/api/v1/routes/tasks.py` 1-192：任务 GET 列表与 task_id/progress/total_steps/status 契约；列表缺少会话筛选字段。当前 UI 标明账户范围，5 秒轮询快照。
- `app/api/v1/routes/misc.py` 270-319、850-874：trace 列表按用户隔离，含 session_id/name/status/duration_ms/error/spans。前端按当前 session_id 过滤。
- `frontend-react/src/api.ts` 30-64、950-999；`src/types/chatEvents.ts`；`src/useChat.ts`：复用既有 API 客户端，补齐审批字段；同步 toolCallsMap 终态，防止后续 tool_call 恢复旧运行态。

## 实施边界

- 代码只修改 `frontend-react/**`；本文件是用户指定的文档输出例外。所有手工编辑使用 apply_patch；无 commit/push，无覆盖或回退其他人的改动。
- 任务/trace 位于右栏已有任务看板/子 Agent 卡片，产物仍位于文件预览卡。右栏五卡顺序保持固定，审批仍在中栏输入框上方。
- 新任务卡使用 64px token，trace 内容上限使用 240px token。右栏折叠 0px，左/中/右默认及范围保留 240(180-360)/600 min/320(240-480)。
- 尚未接入：任务会话筛选、任务泳道拖拽迁移、独立 artifact 下载/版本管理、规则后端保存、参数配置/确认提交契约。界面明确显示边界，参数/确认的提交按钮禁用。
- 当前刷新采用 5 秒快照轮询；没有宣称已实现 SSE/WS 实时订阅或完整 trace 瀑布图。
- `components/anchored/TaskTracePanel.tsx` 独立负责账户任务/会话 trace 快照、请求生命周期与重试；`ArtifactPreview.tsx` 独立负责受控文件选择、变更标记、路径与关闭操作，由既有五卡面板组合。

## 验证

测试使用模拟 API 确认组件契约；真实后端端到端验证与浏览器视觉验收尚待执行。阈值、测试排除项与 TypeScript 严格度保持原样。

所有命令在 `frontend-react` 目录运行，构建与测试使用受管理后台终端、两核 CPU 配额与 600 秒超时。

| 检查 | 实际结果 |
| --- | --- |
| `npm run typecheck` | 通过 |
| `npm test -- src/components/anchored/AnchoredComponents.test.tsx src/useChat.smooth.test.ts src/types/__tests__/chatEvents.test.ts --maxWorkers=2` | 3 文件 / 34 测试通过，含 10 条 anchored 组件测试 |
| `npm run build` | 通过；入口 chunk 约 561 kB，触发原有 500 kB 告警阈值 |
| `npm run lint` | 退出码 0；56 warnings / 0 errors，含 Fast Refresh 混合导出与其他文件的未使用符号等警告 |
| `npm test -- --maxWorkers=2` | 101 文件：86 通过 / 15 失败；982 测试：894 通过 / 88 失败；退出码 1 |
| `git diff --check` | 通过 |
| 本地预览 | Vite 5173 已启动；平台连接探针返回前端 HTML，未包含 mcai-preview-error；当前后端 8000 尚未启动 |

全量测试日志：`/tmp/terminal_term_1790928935156_81.log`。首次从 `/workspace` 使用 `npm --prefix ... exec -- vitest --root ...` 导致源码扫描测试读取 `/workspace/src/index.css` 并 ENOENT；已在正确目录重跑，上表采用重跑结果。最后增加的会话错误清理回归在针对性验证中通过，全量结果对应增加此条测试之前的版本。

### 尚待处理的全量失败

15 个失败文件如下，完整逐条错误和 DOM 输出保留在全量日志。本次未确认全部失败的引入来源，保留失败状态，不调整断言或排除测试。

- `src/__tests__/App.mobile.test.tsx`
- `src/layout/SidebarNavigation.test.tsx`
- `src/components/agent/ChatInterface.hierarchy.test.tsx`
- `src/components/agent/ChatInterface.task03.test.tsx`
- `src/components/agent/readingWidth.task05.test.tsx`
- `src/components/collaboration/collaborationLayout.test.tsx`
- `src/components/tracing/TraceViewer.test.tsx`
- `src/pages/__tests__/FactoryModePage.review2.test.tsx`
- `src/pages/__tests__/FactoryModePage.test.tsx`
- `src/pages/__tests__/PluginAndOperationsPages.taskB.test.tsx`
- `src/pages/__tests__/ResourceCatalogRows.task5.test.tsx`
- `src/pages/__tests__/SchedulerPage.test.tsx`
- `src/pages/__tests__/reportedDataStates.test.tsx`
- `src/pages/__tests__/reportedValues.test.tsx`
- `src/components/workspace/rightPanel/__tests__/RightPanel.persistence.test.tsx`

已核查的原始错误例子：协作页 `Unable to find role="heading" and name "Task"`；工厂配置 `Unable to find an element with the text: /Read 1 active agents and 1 provider credential configurations/`；旧 RightPanel 持久化测试寻找 `role="tab"`，实际 DOM 采用分组 heading。它们分别涉及页面呈现/组件契约，无法仅凭这轮日志归因于本次组件抽离。

流式生命周期测试通过时仍输出一条 React `act(...)` warning。构建 chunk 大小告警保留，未提高阈值。最终代码（含错误清理与结果区 token 统一）的 typecheck / 34 tests / build / lint 串行验证退出码 0，日志 `/tmp/terminal_term_1790929295349_84.log`；移除未使用高度常量后 lint 从 57 降至 56 条警告。

预览地址：`https://5173-1822695f51232c6b.monkeycode-ai.online`，后台终端 `term_1790929204180_83`。此次仅确认服务器启动与平台 HTTP 连接；任务/trace/审批的真实 API 操作需后端服务支持。
