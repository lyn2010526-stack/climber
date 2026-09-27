# Cluster/Group 协作 UI 研究与实现依据

日期：2026-09-26

## 研究口径

本轮只采用仓库已有的开源 Agent UI 研究记录中标注为源码级的证据，不复制源码、图标或品牌资产。证据索引记录了 8 个源码级条目；本轮选择与协作工作区最接近的 `assistant-ui`、LangChain `agent-chat-ui`、`prompt-kit` 和 `Open Multi-Agent Canvas` 作为交互参照。

证据位置：

- `ui-research/REFERENCE_INDEX.md`：源码级条目的分级、项目身份和对应报告定位。
- `ui-research/references-001-020.md`：`prompt-kit` 的源码级输入组件证据，支持输入保留、明确提交动作和可重试的输入边界。
- `ui-research/references-041-050.md`：LangChain `agent-chat-ui` 的 `Stream.tsx` 源码证据，支持把运行状态与消息 transcript 分离展示。
- `ui-research/references-041-050.md`：Open Multi-Agent Canvas 的源码/README 记录，支持把协作上下文放在工作区旁侧，减少主任务区域的状态混杂。
- `ui-research/references-001-020.md`：`assistant-ui` 的项目级交互记录，支持消息列表、输入区和状态反馈保持清晰职责边界。

## 应用到 Climber

1. 主工作区展示后端任务状态、进度、错误、结果和取消动作；提交表单放在协作侧栏，避免出现两个任务入口。
2. 成员列表、添加/移除错误与任务提交错误保持在各自区域；接口失败不转换为空列表或空消息。
3. 群组讨论以 transcript API 为唯一消息正文来源。WebSocket 广播只触发 transcript 重读，页面不渲染只有 ID 的空消息。
4. 消息发送等待后端 ack 成功后清空输入；ack 错误、连接错误和发送异常保留草稿，用户可以重试。
5. 任务状态仅接受任务 API 实际使用的 `pending`、`running`、`completed`、`failed`、`cancelled`。缺失或未知状态显示显式未上报，未知状态不进入轮询和取消流程。
6. 交互只保留后端已有能力：创建群组、成员 CRUD、任务提交/轮询/取消、讨论消息读取/发送。页面不提供暂停、自动完成或未由接口支持的高级配置。

## 后端字段依据

- `app/api/v1/routes/groups.py`：群组列表返回 `id`、`name`、`description`、`topic`、`status`、成员信息；成员新增使用 `agent_id` 和 `role`；成员移除使用 `member_id`；讨论读取返回 `{ "messages": [...] }`。
- `app/storage/models_groups.py`：成员字段包含 `id`、可空 `agent_id`、`role`；消息字段包含 `id`、`sender_name`、`content`、`created_at`。
- `app/api/v1/routes/tasks.py`：任务提交返回 `task_id` 和 `status`；任务读取返回 `objective`、`status`、`progress`、`total_steps`、`result`、`error`；取消接口返回 `cancelled`。
- `app/api/v1/routes/websocket.py` 与 `app/core/group_ws_hub.py`：群组 WebSocket 对消息发送返回 ack，广播消息事件只携带持久化消息的确认信息，正文仍由讨论 transcript 接口读取。

## 本轮约束

本轮修改集中在 Cluster/Group 协作页面、协作组件、GroupRoom、相关测试和本文件。全局 store、后端接口和其他页面保持原状。
