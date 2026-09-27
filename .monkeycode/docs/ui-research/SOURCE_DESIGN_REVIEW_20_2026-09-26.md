# 源码设计审查 20：成熟 Agent UI 对照与验收清单

- 日期：2026-09-26
- 范围：Climber `frontend-react` 当前工作树，以及 `/tmp/opencode/ref-repos` 中四个成熟 Agent 项目的实际 UI 源码
- 工作方式：只读源码；本文件是本轮唯一写入文件；未提交任何改动
- 证据规则：参考结论只采用 LICENSE、Git 元数据和具体 UI 源文件。README、截图、品牌资产不作为 UI 证据。参考项目只用于交互范式对照，不复制源码、图标、文案或品牌表达。

## 1. 参考仓库证据台账

| 项目 | 上游身份 | HEAD SHA | 许可证证据 | 实际 UI 路径与源码事实 | 对 Climber 的设计启示 | 许可/资产边界 |
| --- | --- | --- | --- | --- | --- | --- |
| OpenHands | `All-Hands-AI/OpenHands` | `47a10808d78561546a02555d0d2c7fa96fa96300` | `/tmp/opencode/ref-repos/All-Hands-AI_OpenHands/LICENSE`，MIT，文件第 1–21 行 | `src/components/features/conversation/conversation-main/chat-interface-wrapper.tsx` 第 17–69 行：主线程 `min-w-0`、全高、独立 overview 列；`src/components/features/chat/chat-status-indicator.tsx` 第 15–47 行：状态以紧凑胶囊、状态点和状态文案呈现 | 工作区主内容应允许主线程收缩，辅助信息采用可显示/隐藏的独立列；运行状态需要同时具备图形和文字 | MIT 要求保留许可证与版权声明；仅吸收布局和状态层级，不使用其 SVG、名称或视觉资产 |
| Cline | `cline/cline` | `29896ec7fa8e2dd98805b56c2dae987d59fc9baa` | `/tmp/opencode/ref-repos/cline_cline/LICENSE`，Apache 2.0，文件第 1–201 行；VS Code 子路径另有同许可证文件 | `apps/vscode/webview-ui/src/components/chat/ChatView.tsx` 第 378–433 行：聊天区 `flex-1 overflow-hidden`，底部依次放 `AutoApproveBar`、`ActionButtons`、排队提示和输入区；第 350–371 行：主动发送后恢复滚动吸附 | 输入区上方应保留权限/自动化控制、操作按钮和排队状态；流式输出应区分用户主动发送与任务切换 | Apache 2.0 允许衍生与分发但要求许可证、修改声明和 NOTICE 处理；不复制组件实现或 Cline 专有文案 |
| Dify | `langgenius/dify` | `3960b5710292c584102b918b982481c252b3be6f` | `/tmp/opencode/ref-repos/langgenius_dify/LICENSE` 第 1–22 行：修改版 Apache 2.0，含多租户、Logo/版权和外观专利附加条款 | `web/app/components/workflow/run/index.tsx` 第 103–184 行：运行详情以 Result/Detail/Tracing 三标签组织；加载占满面板，内容区独立滚动；第 47–90 行按 URL 获取结果和 trace | 右侧运行信息应按结果、详情、追踪分层；加载、运行中、结果和追踪应占据稳定面板空间，且请求跟随当前运行上下文 | 前端标识与版权不可按普通 Apache 逻辑处理；外观专利和附加条款是采用阻断点。仅取信息架构事实，不取 Dify 品牌或视觉外观 |
| Chainlit | `Chainlit/chainlit` | `190ea74239d9e84b26e7c91bc2882dd038942564` | `/tmp/opencode/ref-repos/Chainlit_chainlit/LICENSE` 第 1–203 行：Apache 2.0 | `frontend/src/components/chat/MessageComposer/SubmitButton.tsx` 第 23–71 行：加载且已有首轮交互时切换 Stop；否则显示禁用态 Send；两者均有 tooltip 与翻译键 | 发送/停止是同一输入位的互斥状态，按钮名称、tooltip、禁用态和可恢复动作必须同步 | Apache 2.0 的许可证与修改声明要求适用于衍生分发；只采用状态契约，不复制图标或组件代码 |

参考仓库的上游 URL 均由 Git remote 读取。四个仓库均已在本地存在并成功解析 HEAD；本轮没有安装、运行或复制任何外部 Agent。

## 2. 当前 Climber 源码事实

### 2.1 信息架构与协作位置

- `frontend-react/src/navigation/navConfig.ts` 第 10–14、32–59 行将导航分为“工作 / 资源 / 管理运维”，主组包含对话、工厂、任务、推理、工作流、定时、终端，并把集群和团队标记为 secondary。
- `frontend-react/src/App.tsx` 第 159–261 行仍由 `App` 内联渲染桌面侧栏；`frontend-react/src/layout/SidebarNavigation.tsx` 已提供同一导航职责的独立实现，但当前 `App.tsx` 搜索结果未显示其实际挂载。导航重构存在实现与集成边界。
- `frontend-react/src/components/workspace/WorkspaceLayout.tsx` 第 50–70 行的桌面工作区是 `SessionSidebar -> ChatPage -> RightPanel`；右面板仅在宽桌面、打开且非 focus mode 时出现。协作控制台实际位于 `pages/ClusterPage.tsx`，由 `CollaborationConsole` 渲染。
- `frontend-react/src/components/workspace/RightPanel.tsx` 第 63–169 行实现常驻 `RunSummary` 加四组 progressive disclosure：overview、execution、changes、activity；组内最多三层执行分区。

### 2.2 空间预算

- 全局 `frontend-react/src/index.css` 第 159–165 行定义桌面侧栏 `240px`、收起侧栏 `64px`、会话侧栏 `240px`、顶部高度 `52px`、内容最大宽度 `896px`。
- `WorkspaceLayout.tsx` 第 11–14、57–68 行定义右面板默认 `360px`、最小 `280px`、最大 `460px`；主聊天面板最小比例为 `40`，拖拽分隔条为 `4px`。
- `ChatInterface.tsx` 第 151–155 行输入框自动增长上限为 `200px`；消息区滚动跟随由 `scrollRef` 和 `followOutput` 控制。`ChatPage.tsx` 第 22–39 行错误提示固定在底部 `24px`，需与输入区和小屏安全区共同验收。
- 参考对照中，OpenHands 明确使用主线程 `min-w-0` 和独立 overview 列，Dify 将运行内容放入可滚动固定面板，Cline 将底部 composer 控制层固定在聊天布局尾部。这些是空间约束事实，具体像素不应照搬。

### 2.3 颜色、图标和文案

- `index.css` 第 8–165 行有五级深色表面、文字层级、slate accent、成功/警告/错误/信息色、边框、阴影、字号、间距、图标尺寸及 44px 控件基线；第 196–229 行提供浅色主题覆盖。
- `lib/icons.ts` 仅集中共享控件语义图标：loading、error、success、密码显示/隐藏、关闭、子菜单、空态和主题切换，并定义 `12/14/16/20px` 尺寸。业务图标仍分散在各组件中。
- `RightPanel.tsx` 第 95–109、138–145 行使用组图标、11px 分区图标、accent-subtle 选中态；`RunSummary.tsx` 第 6–26 行将 idle/running/paused/completed/error 映射到图标和语义色。
- `ControlBar.tsx` 第 163–171 行仍有硬编码“专注模式”“切换专注模式”；`SessionSidebar.tsx` 第 114–116、152、166 行仍有硬编码会话创建和失败文案；这些是国际化和状态文案验收点。

### 2.4 状态与数据真实性

- `PanelState.tsx` 第 17–47 行提供取消旧请求写入、loading/error/reload 生命周期；第 50–109 行提供可读屏的 loading、empty、error 和 retry 状态。
- `ExecutionSection.tsx` 第 21–31、82–95 行仍通过 `api.getClusterStatus()` 和 `api.listTraces()` 读取数据，未在函数参数层看到当前会话 ID；运行上下文关联需要 P0 验收。
- `ControlBar.tsx` 第 29–32 行在 token limit 缺失时回落为 `0`，第 130–151 行仍可能按该值渲染 `0%`；未知上限需要明确为 unknown 状态，不能表达成确定比例。
- `ChatInterface.tsx` 第 134–155 行已具备空白禁发、流式中防重复、IME 保护、Shift+Enter 换行和 200px 输入增长；第 83–93 行权限处理当前仅移除本地请求，实际批准/拒绝接口路径仍需业务联调验证。

## 3. P0 验收清单

P0 表示影响核心工作流、数据可信度、协作入口或整体布局的阻断项。每项需要在当前工作树重新执行验证并记录命令、时间、尺寸、结果和证据位置。

### P0-IA-01 信息架构与入口一致性

- [ ] `App.tsx` 的实际桌面导航与 `SidebarNavigation.tsx` 的分组、顺序、secondary 语义一致。
- [ ] 25 个导航项逐一可达，当前页高亮、hash 刷新、未知 hash 回退、返回行为和移动入口均一致。
- [ ] 工作区路径固定为会话侧栏、聊天主区、右侧运行信息；集群/团队协作路径可从主导航进入并能返回当前会话。
- [ ] 右面板四组与 ControlBar 四个快捷入口共享同一 `TAB_TO_GROUP` 语义；关闭、折叠和 focus mode 不丢失当前分区。

### P0-SPACE-01 空间预算与核心操作可达

- [ ] 在 1440x900、1280x720、1024x768 验证 `240/64px` 桌面侧栏、`240px` 会话侧栏、右面板 `280–460px` 边界下聊天输入和发送/停止始终可见。
- [ ] 主聊天区、会话列表、右面板分别独立滚动；任何组合下均无水平溢出，长标题、长工具结果和长翻译不会挤压发送区。
- [ ] focus mode 隐藏右侧信息后，Escape 从中性焦点退出；输入框聚焦时 Escape 保留编辑器语义。
- [ ] 右面板关闭或小于 wide desktop 时，状态和协作入口仍有可达替代路径。

### P0-STATE-01 状态与数据真实性

- [ ] 运行摘要的 session、status、token、耗时、sandbox、DAG、trace、tool call 均能追溯到真实 API 字段；缺失、零值、未知和失败分别呈现。
- [ ] `ExecutionSection` 的 DAG/trace 请求按当前 session/run 关联；快速切换会话时旧响应不能覆盖新会话。
- [ ] token limit 未上报时显示未知上限或不可计算状态，不显示伪造的 `0%` 确定比例。
- [ ] 运行中的暂停、停止、完成、错误、取消和权限待确认均有文字、图标、可访问状态和恢复动作。
- [ ] SSE 卡流、用户取消、部分输出、未知事件、错误重试和结束收尾各自可验证，UI 不丢失已经收到的内容。

### P0-COLLAB-01 协作位置和权限路径

- [ ] 协作入口在信息架构中与 cluster/crews 的现有路由保持一致，协作控制台不会被“工作”组的弱化 secondary 样式误认为不可用。
- [ ] 协作任务、参与者、工具调用、审批和失败信息在协作页与右侧 Activity/Execution 之间有明确归属，避免同一事件出现两个互相矛盾的状态。
- [ ] 权限待确认展示真实动作、作用范围、风险、批准、拒绝、失败和过期；重复点击只产生一次提交，焦点关闭后回到触发点。
- [ ] 协作上下文切换后，session、group、task 和 trace 标识不串用；无后端能力的操作明确禁用并说明原因。

### P0-UX-01 核心发送闭环

- [ ] 空白消息不可发送；IME 输入不误发；Shift+Enter 换行；发送中发送按钮变为停止按钮；停止后保留部分输出。
- [ ] 错误提示与重试按钮避开 composer，重试只针对当前请求，不创建重复 session 或重复消息。
- [ ] 输入框、停止、权限审批、右面板折叠、会话删除在键盘和读屏路径中均可完成。

## 4. P1 验收清单

P1 表示完成质量、跨页面一致性和维护成本。P0 稳定后逐项关闭。

### P1-IA-02 导航与检索

- [ ] 命令面板对完整名称、前缀、关键词、中文、英文、空格、拼写偏差和无命中提供稳定排序。
- [ ] 全局搜索的结果类型、预览、详情去向和无详情页提示一致；搜索结果不会把协作对象误导向普通资源页。
- [ ] 会话列表按真实时间分组，支持 0/1/200 条规模；删除失败保留数据，成功后焦点有明确去处。

### P1-SPACE-02 密度与响应式

- [ ] 共享按钮、输入、Badge、状态徽标在 32/36/40/44px 密度下保持对齐；触控操作保留 44px 目标。
- [ ] 移动端 390x844 验证底部导航、composer、命令面板、搜索和错误提示的安全区、焦点和滚动。
- [ ] 右面板所有分组支持空态、失败、重试、折叠和卸载；分区内容不因隐藏分组而继续发请求。

### P1-COLOR-ICON-01 颜色与图标词汇

- [ ] 亮/暗主题逐页验证文本、边框、accent、成功/警告/错误/信息对比度；业务状态色不被品牌 accent 替代。
- [ ] 共享控件语义图标继续从 `lib/icons.ts` 取用；业务图标建立独立迁移清单，避免把外部 Agent 图标当作设计资产。
- [ ] 装饰图标 `aria-hidden`，交互图标有可访问名称；loading、error、success、unknown 各有文字备援。
- [ ] 减弱动态模式下关闭旋转、脉冲和面板过渡，同时保留状态变化的文字反馈。

### P1-COPY-01 文案与国际化

- [ ] 侧栏、ControlBar、SessionSidebar、RightPanel、权限弹窗和错误提示不含硬编码用户可见文案。
- [ ] 七个 locale 的关键键、插值参数和长文案均可渲染；英文、中文和长语言不会破坏 11px/12px 密集布局。
- [ ] “unknown”“未上报”“暂无会话”“加载失败”“重试”“已停止”等状态文案能区分数据缺失、空数据和请求失败。

### P1-STATE-02 细节呈现

- [ ] 工具调用按真实调用 ID 对齐开始、结果、错误、取消；并发和乱序事件仍能正确归并。
- [ ] 推理内容只展示后端提供的内容；长参数和结果默认截断并提供展开，代码、表格和 Markdown 有局部滚动。
- [ ] DAG、trace、diff、files、tool calls 的默认展开规则、更新时间和来源范围可见。

### P1-COLLAB-02 协作可读性

- [ ] 协作列表显示参与者、角色、当前任务、状态、更新时间和失败原因；空团队与无权限状态有独立文案。
- [ ] 协作消息、任务进度、审批和工具调用有稳定时间线顺序；状态颜色与普通 session 状态保持同一语义。
- [ ] 协作入口在桌面和移动端均有明确位置；移动端不依赖右面板才能完成关键审批或查看任务结果。

## 5. 已验证与未验证边界

### 本轮已验证

- [x] 四个成熟 Agent 仓库的上游 URL、HEAD SHA、LICENSE 路径和许可证文本已读取。
- [x] 四个仓库的实际 UI 文件已定位并读取：OpenHands 对话布局/状态、Cline 聊天底部控制、Dify 运行详情标签、Chainlit 发送/停止按钮。
- [x] Climber 当前导航分组、App 内联导航、工作区三栏布局、右面板四组架构、颜色令牌、共享图标入口、核心聊天输入状态已读取。
- [x] 当前工作树基准提交为 `c0ab630a6b202cca57e69e167f9ca884f28580bb`；工作树存在大量并行改动，本文件不覆盖或回退这些改动。
- [x] 本文件是本轮唯一写入目标；未写源代码、未写参考仓库、未提交。

### 本轮未验证

- [ ] 未运行 `typecheck`、`lint`、`build`、Vitest、Playwright 或浏览器视觉回归；源码证据不能替代运行时验收。
- [ ] 未启动后端，未验证 API 真实返回字段、session/run 关联、权限审批副作用、SSE 实际流和协作后端状态。
- [ ] 未验证四个参考项目的运行时视觉结果、全部 UI 路由、所有许可证依赖和第三方资产清单；本轮只核验指定源码路径及仓库根许可证。
- [ ] 未完成 `App.tsx` 内联导航与 `SidebarNavigation.tsx` 的集成一致性验收。
- [ ] 未完成 1440x900、1280x720、1024x768、390x844 的真实布局、对比度、键盘、读屏、IME、减弱动态和长翻译验收。
- [ ] 未核验协作页与右侧面板的事件去重、上下文关联和移动端审批闭环。

## 6. 后续验收顺序

1. 先关闭 P0-IA-01、P0-SPACE-01 和 P0-STATE-01，建立可复现的桌面基线。
2. 在后端可用后验证 P0-COLLAB-01 与 P0-UX-01，重点记录 session/run/group/task/trace 标识。
3. 再执行 P1 的颜色、图标、文案、状态细节和移动端矩阵。
4. 每次关闭条目记录源码快照、命令、时间、退出码、用例数、日志位置和验收者；等待其他任务完成后重新核对本文件“已验证/未验证”两节。
