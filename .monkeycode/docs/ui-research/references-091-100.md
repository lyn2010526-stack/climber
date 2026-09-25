# UI 参考研究 091-100

核验日期：2026-09-25。范围：Climber 的交互范式资料研究；本次仅新增本文件。

## 核验口径

- 每项均执行了真实联网查询，随后实际打开作者仓库 README、源码、官方文档或许可证。下列查询词是执行记录，来源 URL 是实际读取地址。
- 身份状态：确认 = 原名与主体有明确对应；歧义 = 泛称或多个近名项目，列出的实现均为候选；重复 = 同一实现被多个条目再次引用；未确认 = 本轮未建立原名到具体开源实现的可靠对应。检索未确认不等于项目不存在。
- 产品层级：L0 执行基础设施/CLI；L1 嵌入式面板/浏览器扩展；L2 IDE/桌面工作台；L3 系统托盘/移动伴随界面。层级描述职责，不代表优劣。
- 证据层级：E1 = 原作者 README/官方产品文档；E2 = 实读开发文档或源码；E3 = 本地运行验证。本次达到 E1/E2，未安装、运行或接入第三方 agent，未进行 E3 验证。
- 各来源默认分支会变化，本文是本次读取快照，未固定 commit。README 的功能声明与本文的 Climber 设计建议分开列出；截图和视频未做视觉分析。
- 许可证只记录实际读到的文本及适用对象；公开仓库、商业服务和开源实现分别判断。仅借鉴交互范式，不复制代码、图标或品牌资产。
- Climber 约束取自已读 `.monkeycode/MEMORY.md`：桌面优先、移动兼容、无登录流程。本次保留全部已有文档与并行改动。

## 覆盖总览

| 编号 | 原名 | 身份状态 | 核验对象或候选 | 产品层级 | 证据层级 |
| --- | --- | --- | --- | --- | --- |
| 91 | MixLabPro Earth | 确认 | MixLabPro/Earth | L1 浏览器扩展 | E1 |
| 92 | Agent Browser(Vercel) | 确认 | vercel-labs/agent-browser | L0 CLI + L1 Web Dashboard | E1 |
| 93 | Page Agent UI(Alibaba) | 确认 | alibaba/page-agent 的 UI/Core 分层 | L1 页内面板 | E2 |
| 94 | Browser Use Extension | 歧义 | Nanobrowser；Browser Use 官方库/CLI 作边界对照 | L1 候选扩展、L0 官方执行层 | E1 |
| 95 | Claude Code GUI(JetBrains插件) | 歧义 | 优先候选 CC GUI；另有 Swttch | L2 IDE 插件/WebView | E1 |
| 96 | Cursor UI开源实现 | 歧义 | Void，独立开源替代候选 | L2 IDE 工作台 | E2 |
| 97 | Windsurf开源复刻版UI | 未确认 | 官方 Windsurf 文档仅作产品对照；Void 候选与 96 重复 | L2 商业产品参考 | E1 |
| 98 | Desktop AI Agent UI | 歧义 | UI-TARS Desktop | L2 桌面 GUI Agent | E1 |
| 99 | System Tray Agent UI | 歧义 | sprklai/agenttray；mjtpena/AgentTray 为专有对照 | L3 托盘通知 | E1 |
| 100 | Mobile Agent UI | 歧义 | slopus/happy 移动/Web 客户端 | L3 伴随客户端 | E1 |

统计：10/10 有独立查询及一手资料读取；3 项确认、6 项歧义、1 项未确认。原名级重复 0 项；97 的替代候选 Void 与 96 重复，候选只计一个实现。

## 91. MixLabPro Earth

- 身份状态：确认。指定仓库为 `MixLabPro/Earth`；README 自称 AGIUI 的 Earth 浏览器插件，并链接 AGIUI 发布地址。PC/Mac 产品 Solis 是另外一个链接对象，本次未读取其实现。
- 实际查询：`MixLabPro Earth github`。
- 读过 URL [91R]：https://github.com/MixLabPro/Earth ，阅读 README 的主要特色、Combo 数据示例、版本记录。
- 读过 URL [91L]：https://raw.githubusercontent.com/MixLabPro/Earth/main/LICENSE 。
- 层级：L1 浏览器扩展工作台；E1 README，包括内嵌配置示例。
- 证据：[91R] 声明支持 Chrome/Edge、多模型、网页读取与自定义工作流。Combo 示例把 `interfaces` 分成 `showInChat`、`contextMenus`、`home`，通过 `nextId` 串联提示步骤；版本记录写有右键总结、选中内容交互、导入导出和可折叠调试窗口。
- 边界：这些是仓库文档描述；历史模型名称及集成可用性未做当日运行验证。Chrome/Edge 支持来自说明正文，不能从构建命令推断其他浏览器完整受支持。
- Climber 可借鉴点（建议）：让同一个工作流模板从聊天快捷入口、对象上下文菜单和模板页启动；执行时统一进入任务详情与步骤调试面板。
- 许可证：[91L] 实读 MIT，版权行标为 2023 AGIUI。记录适用于该仓库代码，不扩展到外部模型服务。

## 92. Agent Browser(Vercel)

- 身份状态：确认。作者组织为 `vercel-labs`，项目实际名为 `agent-browser`。
- 实际查询：`Agent Browser Vercel github`。
- 读过 URL [92R]：https://github.com/vercel-labs/agent-browser ，阅读 CLI 定位、Usage with AI Agents、Observability Dashboard、AI Chat。
- 读过 URL [92L]：https://raw.githubusercontent.com/vercel-labs/agent-browser/main/LICENSE 。
- 层级：L0 浏览器自动化 CLI，附带 L1 本地 Web Dashboard；E1。
- 证据：[92R] 主体是 Rust CLI；交互示例使用快照元素引用进行点击/填充。Dashboard 章节明确列出实时视口、带耗时及可展开详情的命令/结果流、浏览器 console 和会话创建；另有需要配置 Vercel AI Gateway 的可选聊天面板。
- 边界：应分别标记执行 CLI、可观察性 Dashboard 和可选聊天依赖。将整个项目标成完整浏览器产品会扩大其定位；只登记 CLI 又会遗漏已存在的 UI。
- Climber 可借鉴点（建议）：任务详情采用“执行证据视口 + 按时间排序的动作结果流”；每步显示目标、耗时、结果和错误，聊天作为发起入口保留。
- 许可证：[92L] 实读 Apache-2.0，版权行标为 Vercel Inc.；外部 Gateway 服务单独评估。

## 93. Page Agent UI(Alibaba)

- 身份状态：确认。对应 `alibaba/page-agent`；UI 是该项目内部独立包，而 Page Agent 是包含 Core 和面板的入口。
- 实际查询：`Page Agent UI Alibaba github`。
- 读过 URL [93R]：https://github.com/alibaba/page-agent 。
- 读过 URL [93D]：https://github.com/alibaba/page-agent/blob/main/AGENTS.md ，阅读 Project Overview、Module Boundaries、DOM Pipeline。
- 读过 URL [93S]：https://github.com/alibaba/page-agent/blob/main/packages/core/src/PageAgentCore.ts ，定点阅读状态 getter、事件派发和 `stop()`/`execute()` 附近代码。
- 读过 URL [93L]：https://raw.githubusercontent.com/alibaba/page-agent/main/LICENSE 。
- 层级：L1 页内 GUI Agent/可嵌入面板；E2。
- 证据：[93R] 描述文本化 DOM 操作、页内 JavaScript 和可选跨页扩展。[93D] 明确 Core 无 UI，`packages/ui` 经 `PanelAgentAdapter` 解耦，PageController 负责 DOM 和可选视觉反馈。[93S] 可见 `statuschange`、`historychange`、`activity` 三类事件；`stop()` 发出 abort 并等待当前运行收束。
- 边界：页内控制、跨标签扩展与外部 MCP 是不同集成面。UI/Core 的架构文档作为研究材料读取，未执行其中的开发命令。
- Climber 可借鉴点（建议）：分开持久步骤历史、任务状态与短暂活动提示；将停止操作显示为“停止请求中”，待执行器确认后再展示最终状态，避免按钮与真实任务脱节。
- 许可证：[93L] 实读 MIT，包含 SimonLuvRamen 与 Alibaba Group Holding Limited 的版权声明。

## 94. Browser Use Extension

- 身份状态：歧义。该原名缺少作者及唯一仓库。Nanobrowser 是已核实的扩展 UI 候选；Browser Use 官方执行库/CLI 单列作名称边界对照。
- 实际查询：`Browser Use Extension github`；补查 `nanobrowser nanobrowser github browser use extension`。
- 读过 URL [94R]：https://github.com/nanobrowser/nanobrowser ，阅读 Key Features、Browser Support、License。
- 读过 URL [94B]：https://github.com/browser-use/browser-use ，阅读 Which Browser Use do I need、CLI/Python Library、Related Repositories。
- 读过 URL [94H]：https://github.com/browser-use/browser-harness ，与 [94B] 的官方关联仓库链接交叉核对；本次仅用于确认关联主体，不据此描述具体扩展 UI。
- 读过 URL [94L]：https://raw.githubusercontent.com/nanobrowser/nanobrowser/master/LICENSE 。
- 层级：候选 Nanobrowser 为 L1 扩展侧栏；Browser Use 库/CLI 属 L0；E1。
- 证据：[94R] 明确聊天侧栏、实时任务状态、历史对话、后续追问、Planner/Navigator 多 agent 分工及按 agent 配置模型。[94B] 明确区分托管 Cloud、CLI 和 Python Library。两组一手材料支持分别登记主体，本轮尚未建立原名与某个官方扩展 UI 的唯一对应。
- Climber 可借鉴点（建议）：执行侧栏展示当前阶段和承担该步骤的 agent；任务结束后允许基于结果继续追问；模型选择下沉到进阶配置，保持任务入口简洁。
- 许可证：[94L] 实读候选 Nanobrowser 的 Apache-2.0。Browser Use 的 README 另有库 MIT 声明，本次未单独读取其 LICENSE，故不为该对照库作独立许可证核验结论。
- 读取修正：`https://raw.githubusercontent.com/nanobrowser/nanobrowser/main/LICENSE` 返回 404；从仓库 LICENSE 链接确认实际分支为 `master`，换用 [94L] raw 读取成功。失败地址只作审计记录。

## 95. Claude Code GUI(JetBrains插件)

- 身份状态：歧义，优先候选是 CC GUI。其 README 明确写有旧名 Claude Code GUI；另一个独立项目 Swttch 旧名 Claude Code with GUI，也符合宽泛描述，应保留作者限定。
- 实际查询：`Claude Code GUI JetBrains plugin github`；补查 `"jetbrains-cc-gui" "Originally"`。
- 读过 URL [95R]：https://raw.githubusercontent.com/zhukunpenglinyutong/jetbrains-cc-gui/main/README.md ，完整读取；亦打开其仓库主页 https://github.com/zhukunpenglinyutong/jetbrains-cc-gui 。
- 读过 URL [95A]：https://github.com/Swttch/swttch ，阅读改名声明及 Highlights。
- 读过 URL [95L]：https://raw.githubusercontent.com/zhukunpenglinyutong/jetbrains-cc-gui/main/LICENSE 。
- 读过 URL [95AL]：https://raw.githubusercontent.com/Swttch/swttch/main/LICENSE 。
- 层级：L2 IDE 插件/WebView，背后接入编码 CLI；E1。作者项目与 Anthropic 官方 CLI、JetBrains 商业 IDE 分别登记。
- 证据：[95R] 描述多引擎、`@file`、图片上下文、会话 rewind、DIFF、权限控制、历史搜索/收藏/导出。[95A] 明确自己是启动 Claude Code CLI 的 wrapper，并描述 IDE 与浏览器双环境 UI。两者是独立作者实现。
- Climber 可借鉴点（建议）：把上下文附件、权限确认、产物差异与会话历史放在同一任务工作区；多引擎差异用能力标记体现，执行状态共用一套展示协议。
- 许可证：[95L] 实读 CC GUI 的 MIT；[95AL] 实读 Swttch 的 GNU AGPL 第 3 版。两个项目的许可证分别记录；本次保持交互研究范围。

## 96. Cursor UI开源实现

- 身份状态：歧义。原名描述一类实现；选取 Void 为独立开源替代候选，Cursor 产品身份与 Void 作者身份分列。尚未核实“Cursor 官方 UI 源码”这一对应关系。
- 实际查询：`Cursor UI open source Void github`；补查 `voideditor void github`。首轮包含同名终端项目，补查后将候选限定为 `voideditor/void`。
- 读过 URL [96R]：https://github.com/voideditor/void 。
- 读过 URL [96D]：https://raw.githubusercontent.com/voideditor/void/main/VOID_CODEBASE_GUIDE.md ，阅读进程分层、Apply、DiffZone、Approval State；亦打开同文件 GitHub 页面。
- 读过 URL [96L]：https://raw.githubusercontent.com/voideditor/void/main/LICENSE.txt 。
- 层级：L2 VS Code 派生 IDE 工作台；E2 开发文档。
- 证据：[96D] 描述 React/browser 与 electron-main 通道、统一 `editCodeService`、Fast/Slow Apply、流式 DiffZone 及派生审核状态。[96R] 当次页面明确标为 deprecated；仓库归档提示给出 2026-06-02。
- 边界：适合做结构研究与交互参考；评估为可持续依赖时需单独检查维护接续情况。Cursor 的品牌、商业服务和官方代码开放状态未由 Void 许可证覆盖。
- Climber 可借鉴点（建议）：Agent 修改产物时显示差异区域和审核状态，关联产生修改的步骤；流式内容、待审核变更与已确认结果分别呈现。
- 许可证：[96L] 实读 Apache-2.0，版权行标为 Glass Devtools, Inc.；本次未逐项审计继承依赖与第三方声明，结论限定到已读文件。

## 97. Windsurf开源复刻版UI

- 身份状态：未确认。本轮查询没有建立该原名到唯一、可核验开源 UI 复刻仓库的对应。候选重复：将 Void 当作同类替代会与 96 重复，保留为交叉参考。
- 实际查询：`Windsurf open source UI clone github`；`"Windsurf" "open source" "clone" "UI" github`；`site:docs.windsurf.com windsurf cascade checkpoints`。
- 读过 URL [97D]：https://docs.windsurf.com/de/windsurf/terminal ，读取官方德文 Terminal 文档；[96R]/[96D] 是已读取的开源替代候选资料。
- 层级：L2 商业 IDE 的官方产品文档对照，E1；目标“开源复刻实现”证据仍缺。
- 证据：[97D] 描述终端选区送入 Cascade、终端上下文引用、四级自动执行设置及 Teams/Enterprise 管理上限。它能证明官方交互设计，不能承担“已找到开源复刻源码”的证据职责。检索出现的账号工具、CLI 控制工具和网站克隆工作流均未采纳为 UI 复刻。
- Climber 可借鉴点（建议）：任务输入支持引用明确的日志片段；执行卡片持续显示当前授权范围，策略限制附近给出需要用户确认的原因。保留 Climber 既有无登录流程约束。
- 许可证：目标复刻仓库及许可证未确认；官方文档阅读仅支持交互研究。Void 候选许可证见 96，不能转移到 Windsurf 产品。

## 98. Desktop AI Agent UI

- 身份状态：歧义。原名为桌面 Agent UI 泛称；候选选取 ByteDance 的 UI-TARS Desktop。
- 实际查询：`Desktop AI Agent UI github UI TARS`。查询出现 fork 后回到 README 标示的上游 `bytedance/UI-TARS-desktop` 读取。
- 读过 URL [98R]：https://github.com/bytedance/UI-TARS-desktop ，阅读 Introduction 与 UI-TARS Desktop Features。
- 读过 URL [98D]：https://github.com/bytedance/UI-TARS-desktop/blob/main/docs/quick-start.md 。
- 读过 URL [98L]：https://raw.githubusercontent.com/bytedance/UI-TARS-desktop/main/LICENSE 。
- 层级：L2 原生桌面 GUI Agent；同仓 Agent TARS 另有 CLI/Web UI；E1。
- 证据：[98R] 明确区分上述两条产品线，UI-TARS Desktop 描述截图、鼠标键盘操作和实时状态。[98D] 要求 macOS 辅助功能/屏幕录制权限，注明单显示器限制，并公告 Remote Operator 服务的停用日期为 2025-08-20。该日期早于本次核验日期；本次未连接服务验证实际停用状态。
- 边界：README 的远程操作展示不能直接推定官方远程服务仍可用；模型、桌面程序、算力提供方是三种对象。本次没有运行桌面应用验证限制。
- Climber 可借鉴点（建议）：运行前展示操作目标、权限缺项和环境前置检查；运行中把截图证据与动作步骤配对，停止入口持续可见。
- 许可证：[98L] 实读仓库 Apache-2.0；模型权重和外部算力服务条款不在本次核验范围。

## 99. System Tray Agent UI

- 身份状态：歧义。这是托盘交互泛称；优先开源候选为 `sprklai/agenttray`，另查到同名 `mjtpena/AgentTray`，其开放状态不同。
- 实际查询：`System Tray Agent UI github AgentTray`。社区搜索结果只作定位，随后读取两个作者仓库。
- 读过 URL [99R]：https://github.com/sprklai/agenttray 。
- 读过 URL [99A]：https://github.com/mjtpena/AgentTray 。
- 读过 URL [99L]：https://raw.githubusercontent.com/sprklai/agenttray/main/LICENSE 。
- 读过 URL [99AL]：https://raw.githubusercontent.com/mjtpena/AgentTray/main/LICENSE 。
- 层级：L3 托盘/通知伴随 UI；E1。托盘是状态入口，完整会话保留在原编码工具。
- 证据：[99R] 描述 hook 状态、缺少 hook 时进程扫描、通知及会话弹窗；状态为 needs-input/error/working/idle/offline，回到终端依赖可用 focus metadata。[99A] 描述配额、用量与成本 popup；README 虽使用 source-available 字样，同段明确源码尚未公开，仓库当前文件列表只有 README 和 LICENSE。
- Climber 可借鉴点（建议）：先在现有 Web 顶栏实现紧凑任务状态入口；优先提醒等待输入和失败，点击定位任务；颜色同时配文字/图标语义，减少完成通知噪声。原生托盘作为后续独立载体评估。
- 许可证：[99L] 实读 MIT；[99AL] 明确 proprietary/confidential 与 All rights reserved。后者只作公开产品说明参考，排除出可复用开源代码清单。

## 100. Mobile Agent UI

- 身份状态：歧义。原名可指手机上的 Agent 客户端，也可指操控手机界面的 Agent；本项选取前者的具体候选 Happy，后者未作实现归属判断。
- 实际查询：`Mobile Agent UI happy github mobile client`；补查 `"slopus/happy" mobile web client`。
- 读过 URL [100R]：https://raw.githubusercontent.com/slopus/happy/main/README.md ，完整读取；亦打开 https://github.com/slopus/happy 。
- 读过 URL [100L]：https://raw.githubusercontent.com/slopus/happy/main/LICENSE 。
- 层级：L3 移动/Web 伴随客户端，配套 CLI 和同步服务属于执行/传输层；E1。
- 证据：[100R] 明确 Happy App 为 Expo Web/移动客户端，另列 Happy CLI、远程控制 CLI 和 Happy Server；描述权限请求/错误推送、手机与桌面接续以及端到端加密。加密与隐私属于作者声明，本次未作实现审计。
- 边界：这些条目是 Happy 的 UI 与同步体系；Claude Code/Codex 本身以及各自服务使用条件单独处理。手机控制桌面编码会话与自动点击手机应用是不同任务。
- Climber 可借鉴点（建议）：保持桌面优先；移动兼容首先覆盖查看状态、阅读关键产物和处理待确认操作，沿用同一个 task/session 标识。会话跨端恢复、通知去重与过期批准提示作为后续需求，不增加登录流程。
- 许可证：[100L] 实读 MIT，版权行标为 Happy Coder Contributors；外部编码工具和托管服务另外核验。

## 三条优先建议

1. **P0：统一执行可观察性。** 综合 92、93、98 的资料，设计一套任务状态、步骤历史、短暂活动、证据预览与停止确认模型。先写清状态转换与空/错误/停止中展示，再评估界面改动。
2. **P1：让上下文与产物可审核。** 综合 91、95、96、97 的资料，让文件、网页或日志引用可追溯；变更差异关联产生它的步骤，权限说明与实际操作范围保持一致。Void 作为归档参考使用。
3. **P2：用伴随入口减少打断。** 综合 94、99、100 的资料，先做 Web 内待处理队列和移动兼容，聚焦等待输入、失败及关键结果；桌面壳、托盘、跨端同步分别评估，保持现有无登录流程边界。

## 读取与范围审计

- 唯一实际失败读取：94 的 Nanobrowser `main/LICENSE` raw 返回 404；随后从官方文件链接取得 `master` 路径，换 raw 一次成功。未把失败响应算作已读许可证。
- GitHub 部分页面含站点导航加载提示，但正文可读取；本次核验依据为实际返回的 README/文档/源码正文，许可证另读 raw。
- 本次确认的是具体来源及其内容；97 保持未确认，94/95/96/98/99/100 保持候选标注。没有把十条清单写成十个已证实开源产品。
- 仅新增 `references-091-100.md`；未修改应用、其他研究文档或记忆文件，未执行 commit/push、安装、构建或第三方 agent 运行。
