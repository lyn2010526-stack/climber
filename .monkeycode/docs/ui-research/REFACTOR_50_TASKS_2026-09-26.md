# 全面前端重构：50 项任务与验收账本

日期：2026-09-26。范围：Climber `frontend-react` 全部可达页面及共享组件，桌面优先、移动兼容，保留无登录界面的产品约束。本次仅编制此文档；后续任务涉及的代码修改由主代理安排。

## 计数与证据规则

**当前真实计数（2026-09-26 补证据轮，见文末第 7 节）**：

| 范围 | 任务数 | 已完成 | 进行中 | 未开始 |
| --- | ---: | ---: | ---: | ---: |
| 01–20 研究与基础 | 20 | 11 | 9 | 0 |
| 21–50 实现与验收 | 30 | 9 | 15 | 6 |
| **合计** | **50** | **20** | **24** | **6** |

- 已完成的 20 项：01、02、03、07、08、15、16、17、18、19、20、21、23、25、27、28、31、33、34、35。其中 8 项（21、23、25、27、28、33、34、35）仍待浏览器验收，3 项（21、31、35）仍待后端联调，9 项（01、02、03、15–20）无待办。
- 未开始的 6 项：22、24、26、46、48、50，全部落在实现与验收段。
- 三态定义、逐条证据与待办清单以文末第 7 节为唯一来源。

**编制期计数（历史快照，保留不删）**：

| 范围 | 任务数 | 待办 | 进行中 | 待验收 | 已完成 |
| --- | ---: | ---: | ---: | ---: | ---: |
| 01–20 研究与基础 | 20 | 11 | 1 | 6 | 2 |
| 21–50 实现与验收 | 30 | 22 | 2 | 6 | 0 |
| 合计 | 50 | 33 | 3 | 12 | 2 |

- 编制期实际完成数为 **2/50**，均为本账本中的资料/现状核验任务；实现与验收完成数为 **0/30**。该结论已过期，当前为 20/50。
- 本轮主会话实际派发 **7 个独立子代理任务**：侧栏、命令与搜索、共享控件、右面板修复、本文账本、浏览器检查、手机浮层修复。50 是规划任务数量，分批实施。
- 待办：尚无满足本任务标准的交付证据。进行中：已有部分研究，或用户明确告知正在修复。待验收：代码/测试已落盘，独立验证尚缺。已完成：本项全部标准及证据齐备。
- 历史审计报告的测试通过数属于历史快照。本次未运行 typecheck、lint、build、Vitest、Playwright，未进行浏览器交互验收。
- 代码核验基于读取时的工作树，存在并行改动；实现任务升级为已完成时，应记录代码快照、命令、时间、退出码、用例数、日志位置和验收者。失败、跳过与未执行单列。
- 全面重构完成须以第 50 项验收为门槛。既有 RightPanel 分组与 SSE 修复分别计入局部任务。

## 已读依据与现状校正

### 本批集成验证补充

- 右侧面板翻译现已使用 `right_panel.xxx`；新增真实中英文 i18n 渲染测试，移除无数据依据的沙箱成功声明。
- 侧栏键盘目标增加数组边界判断；命令面板及搜索浮层移到桌面/手机共用层，补四项手机回归测试。
- 最终完整集成校验：typecheck、34 文件/280 测试、lint（31 warnings / 0 errors）、build 均通过；日志 `/tmp/terminal_term_1790411534274_80.log`。`git diff --check` 通过。
- 浏览器环境补齐后，1440×900 与 390×844、明暗主题四组 DOM smoke 通过，覆盖挂载、水平溢出、命令面板键盘操作与焦点恢复；日志 `/tmp/terminal_term_1790411404133_79.log`。此验证范围为 DOM 和交互，视觉审美验收仍待完成。
- 后端未启动，API 返回 502；端到端业务联调仍待执行。首次桌面冷加载超过原 2.5 秒等待阈值，改为最长 30 秒条件等待后通过。
- 本节覆盖上方编制时“未运行验证”及下方右面板修复中的历史描述。各任务含全站或视觉验收条件时仍保留待验收状态。

文档路径相对项目根目录，代码路径下文默认相对 `frontend-react/src/`。

| 依据 | 本次核验范围与结论 |
| --- | --- |
| `.monkeycode/docs/ui-research/FRONTEND_AUDIT_2026-09-26.md` | 已读全部 266 行；历史第三轮记录 29 文件/247 用例、lint 31 warnings，均未在本次重跑。末尾“仍待处理”需按当前代码更新理解。 |
| `.monkeycode/docs/ui-research/REFERENCE_INDEX.md` | 已读全部 139 行；100 个编号，确认 47、歧义 40、重复 4、未确认 9；索引记录外部运行验证 0 项，不能转换为 100 个独立源码研究成果。 |
| `.monkeycode/docs/ui-research/RIGHT_PANEL_SPEC_2026-09-26.md` | 已读全部 133 行；常驻摘要、四分组、七子分区与状态原语已有规范。 |
| `lib/icons.ts`、`components/ui/{Button,Badge,Input}.tsx`、`index.css` | 五种共享状态图标、尺寸映射、控件密度、焦点与减弱动态规则已有实现；基础测试文件已读取。统一图标入口目前仅覆盖共享控件状态。 |
| `components/workspace/SessionSidebar.tsx` | 已有语义列表、状态文字、方向键/Home/End、独立删除按钮、删除后焦点恢复；仍以 `sessions.map` 平铺，创建/检查点等文案仍有硬编码。 |
| `components/workspace/{CommandPalette,GlobalSearch}.tsx` | 命令面板已有分组、视觉顺序键盘导航、焦点恢复，匹配仍为 `includes`；搜索已有 300ms 防抖、过期结果隔离、失败重试、预览展开。相关测试已落盘。 |
| `components/workspace/rightPanel/RunSummary.tsx`、`sections/ExecutionSection.tsx`、`PanelState.tsx` | 读取时仍有 `right_panel:...` 调用、固定 `project_only` 沙箱文案、缺失数值回落 0、无会话参数的集群/链路请求。用户已告知翻译及真实性修复进行中。 |
| `i18n/config.ts` | 当前仅注册 `translation` namespace，右侧面板冒号式调用需用真实 i18n 配置验证；mock 翻译函数的组件测试不能证明运行时文案正确。 |
| `api.ts` | 定向核验到 `SSEIdleTimeoutError`、`idleTimedOut`、`releaseLock`、`normalizeChatEvent`；已有 `__tests__/api.sse.test.ts`。 |
| `navigation/navConfig.ts`、`pages/*.tsx`、`package.json` | 核验 25 项完整导航、8 项移动适配集合及现存页面文件；确认可用验证脚本。其余业务页仅作覆盖清单，完整行为仍待逐页检查。 |

本地真实参考根目录为 `/tmp/opencode/ref-repos`，当前可见 18 个仓库目录。本次完整读取 `assistant-ui_assistant-ui/packages/ui/src/components/react/assistant-ui/elements/thread-list.tsx`，核验其会话标题、时间、未读与当前选择呈现；仅读取 `open-webui_open-webui/src/lib/components/layout/Sidebar.svelte` 前 120 行，核验会话分页、文件夹、置顶及搜索的依赖入口。其余目录存在性已确认，源码研究待任务 03–08 补齐。未安装或运行外部 Agent，未复制源码、图标及品牌资产；上游 hover 操作等模式须经过 Climber 可访问性适配。

## 研究与基础：01–20

### 01. [已完成] 建立审计差异基线
范围：上述三份既有文档与本批核心代码。核验：已记录侧栏、命令面板、搜索和右侧面板的现状，区分历史测试结论与本次只读证据。
验收标准：本文件保留文档路径、读取范围、至少五项现状校正及未执行验证说明；上述依据表已满足。完成仅限本项基线整理。

### 02. [已完成] 校正参考索引的证据口径
范围：`REFERENCE_INDEX.md` 与本地参考目录。核验：已记录 100 编号的四类状态、外部运行验证 0 项、本地 18 个目录及两份源码的实际读取范围。
验收标准：编号、独立项目身份、源码阅读与运行验证分别说明；歧义/候选保留原限定，局部阅读范围明确。证据见前文。

### 03. [进行中] 固定实际采用参考的版本与许可
范围：`/tmp/opencode/ref-repos` 中拟采用的仓库。核验：目录清单和两处源码已读，版本与许可台账待补。
验收标准：每个采用对象记录 owner/repo、HEAD SHA、源码路径/符号、LICENSE 路径、读取范围、采用/舍弃理由；同谱系去重，缺失许可明确阻断资产复制。

### 04. [待办] 研究会话组织与长列表模式
范围：assistant-ui、Open WebUI、LobeHub、LibreChat 的会话列表源码。核验：前两者局部证据见前文，四者比较尚缺。
验收标准：形成标题、时间分组、运行状态、检索、删除确认、长列表六维对照；至少三处真实源码证据映射到任务 21–22，明确后端支持边界。

### 05. [待办] 研究流式消息与输入交互
范围：assistant-ui、vercel_ai、Chainlit 的 composer/message/stream 实现。核验：目录存在，相关源码本次未读。
验收标准：产出发送、停止、失败重试、IME、滚动跟随、部分内容六项状态契约，逐项提供来源符号与 Climber 对应组件，供任务 31–33 使用。

### 06. [待办] 研究执行过程与工具披露层级
范围：Dify、Flowise、AutoGen 的运行详情及工具调用 UI。核验：已有右侧面板规范，新增比较待做。
验收标准：以真实前端源码比较运行/步骤/工具三级结构，明确默认展开项、错误优先级及无数据呈现；将结论映射到右侧面板和任务 34、37–38。

### 07. [待办] 研究代码变更与权限确认模式
范围：OpenHands、Cline、SWE-agent 的 Diff、审批或轨迹界面。核验：仓库目录存在；各仓库具体 UI 范围待定位。
验收标准：至少两处可定位实现支持变更摘要、文件导航、危险操作确认和取消路径；仅有轨迹/文档的对象显式标注证据层级，映射任务 29、35、43。

### 08. [待办] 研究管理页与诊断信息密度
范围：LobeHub、LibreChat、Dify 中设置、模型、资源列表或运行统计页。
验收标准：提供列表密度、详情编辑、凭据选择、异常反馈四类源码对照，每类明确一项采用决策及一项适配限制，映射任务 36、40–43。

### 09. [待办] 建立全部路由与用户旅程矩阵
范围：`App.tsx`、`navigation/navConfig.ts`、实际页面映射。核验：25 项完整导航已存在，`Page` 类型还包含额外标识。
验收标准：25 项逐一列出入口、组件、主操作、接口、加载/空/失败态及验收任务号；额外路由单列可达性，含刷新、返回和未知 hash 行为，保持无登录界面。

### 10. [待办] 定义桌面布局与信息优先级
范围：`App.tsx`、工作区布局、控制栏、左右面板。
验收标准：给出 1440×900、1280×720、1024×768 的宽度/最小尺寸/独立滚动约束；写明聚焦模式、折叠及调整尺寸规则，主输入与关键操作始终可达。

### 11. [待办] 冻结视觉令牌与语义映射
范围：`index.css`、共享 UI、图表与代码高亮。核验：accent、状态色、尺寸和字体规则已有实现，完整视觉基准待验收。
验收标准：列出亮/暗两套背景层级、文字、边框、accent、成功/警告/失败、字号、间距、圆角和阴影；每类给出实际使用组件及允许例外，避免业务状态与品牌色混淆。

### 12. [待办] 定义统一异步及权限状态契约
范围：`rightPanel/PanelState.tsx`、列表页、弹窗、权限确认。核验：右侧面板已有三态原语，全站接入尚待核验。
验收标准：加载、空数据、请求失败、权限待确认各有文案、操作、ARIA 和恢复路径；另定义未知/未上报数据，过期响应及重复提交处理规则。

### 13. [待办] 核对运行状态与接口字段来源
范围：`store/workspace`、`api.ts`、`useChat.ts`、对应后端路由，只读核对。
验收标准：逐项标出 session/run/task ID、状态、工具数、错误数、Token、模型上限、沙箱、DAG、trace 的字段来源和缺省语义；无接口能力的操作明确禁用原因，提供缺失/零值/失败样例。

### 14. [待办] 冻结可访问性与国际化验收矩阵
范围：共享控件、弹窗、导航、七份 locale。核验：Input 密码按钮仍为英文常量，侧栏部分文案硬编码。
验收标准：矩阵涵盖键盘、焦点归还、可访问名称、状态播报、对比度、减弱动态、长翻译和 IME；中文/英文逐页运行验证，七语言关键键和插值参数静态检查。

### 15. [待验收] 验收共享状态图标词汇
范围：`lib/icons.ts` 及 Button/Input 引用。核验：loading/error/success/showPassword/hidePassword 五项与 xs/sm/md/lg 尺寸已落盘。
验收标准：五项映射与 CSS 尺寸一致，装饰图标对读屏隐藏，交互图标由按钮提供名称；现有导入与控件测试通过。业务图标迁移范围按任务 11 明确。

### 16. [待验收] 验收控件密度、焦点与动态基础
范围：`index.css`。核验：四档 control-height、两档 gap、icon 尺寸、全局 focus-visible 与 reduced-motion 规则存在。
验收标准：四档高度对应 32/36/40/44px，旧 44px 触达规则保留；亮暗主题焦点可见，减弱动态时动画/过渡有效关闭，实际计算样式与基础测试一致。

### 17. [待验收] 验收 Button 行为与视觉契约
范围：`components/ui/Button.tsx`。核验：已有 variant/size、loading、aria-busy、ref 和样式覆盖实现。
验收标准：全部 variant/size 渲染正确，loading/disabled 阻止重复操作，submit 与普通按钮按调用方语义工作，ref/className/自定义图标保持；键盘焦点和双主题状态图通过。

### 18. [待验收] 验收 Badge 状态表达
范围：`components/ui/Badge.tsx`。核验：已有尺寸、语义色、icon/ref 转发，部分语义边框仍为 RGBA 字面量。
验收标准：所有 variant 在亮暗主题文字可读，状态附文案，icon/ref/className 保持；固定边框色纳入令牌或记录经验证的例外，组件测试通过。

### 19. [待验收] 验收 Input 描述、错误与密码操作
范围：`components/ui/Input.tsx`。核验：稳定 ID、aria-describedby 合并、error/hint 优先级、密码显示及禁用逻辑已实现。
验收标准：ref、原生属性、调用方描述均保留；错误关联唯一，loading 可编辑，状态图标无重叠；密码切换支持键盘及禁用，名称本地化缺口在任务 45 结清。

### 20. [待验收] 验收基础控件回归集
范围：`components/ui/__tests__/control-foundation.test.tsx` 及 presentation contract。核验：已读测试，覆盖尺寸、禁用、转发、ID、描述、密码、CSS 契约。
验收标准：主代理在当前快照执行并记录实际展开用例数；新增改动回归通过，断言覆盖用户行为；DOM/字符串断言与浏览器视觉验证分别登记。

## 实现与验收：21–50

### 21. [待验收] 验收会话侧栏本批交互重构
范围：`SessionSidebar.tsx`、既有 SessionSidebar 测试与 accessibility 测试。核验：语义列表、状态文字、44px 删除入口、键盘移动、删除后焦点恢复已实现。
验收标准：方向键/Home/End 仅移动焦点，Enter 激活；删除失败保留数据，成功后焦点有去处；加载与空态区分，创建入口可达，检查点展开关联正确，身份变化测试通过。

### 22. [待办] 补齐会话分组、过滤与真实上下文摘要
范围：`SessionSidebar.tsx` 与会话数据层。核验：当前平铺列表、无列表过滤，fallback 会话含固定 Token limit。
验收标准：按真实时间分组并可过滤标题，运行状态与未知上下文区分；无时间数据归入明确分组；0/1/200 会话可操作；删除有确认或已实现的可撤销机制，失败保留列表与选择。

### 23. [待验收] 验收命令面板本批交互
范围：`CommandPalette.tsx` 及对应测试。核验：Radix Dialog、分组视觉顺序、上下键、Enter、IME 保护与焦点恢复已实现。
验收标准：选中顺序等于呈现顺序，边界及无结果可处理；Enter 单次执行，Tab 留在弹窗，Escape 关闭归还焦点，重开清空查询；对应测试与浏览器键盘检查通过。

### 24. [待办] 增加可解释的命令匹配排序
范围：命令过滤逻辑及导航元数据。核验：当前使用 `includes`，空查询取前八项。
验收标准：明确完整名称、前缀、关键词、模糊匹配的优先级及稳定同分规则；全部 25 项可搜索；中英文、空白、拼写偏差与无命中有确定测试，空查询推荐规则写明。

### 25. [待验收] 验收全局搜索本批重构
范围：`GlobalSearch.tsx` 及对应测试。核验：防抖、trim、数组/envelope 检查、过期结果隔离、过滤、预览、重试已实现。
验收标准：少于两字符与关闭态零请求；300ms 防抖、旧响应/旧错误隔离、畸形响应提示、当前查询重试均通过；键盘展开结果、焦点锁定/恢复与结果类型过滤可用。

### 26. [待办] 统一应用导航与搜索结果去向
范围：`App.tsx`、navConfig、命令面板、GlobalSearch。核验：已有完整分组导航；搜索目前 Enter 展开预览。
验收标准：完成任务 09 的全部入口核对，路由高亮/标题一致；有详情页的结果定位真实对象，无详情页明确标为预览；切页保留有效会话，失效对象有反馈，移动端可访问其余功能的入口明确。

### 27. [待验收] 验收右侧面板四分组架构
范围：`RightPanel.tsx`、`groupModel.ts`、ControlBar 与对应测试。核验：既有分组实现及规范已落盘。
验收标准：常驻摘要跨分区保留，四组/七分区与共享元数据一致；关闭和折叠不挂载相应请求内容；无会话回落/禁用正确，外部跳转展开目标，全部折叠/展开与七值存储兼容通过。

### 28. [进行中] 修复右侧面板真实翻译解析
范围：RightPanel、ControlBar、RunSummary、各 section、locale 与 i18n 配置。核验：用户报告正在修复；读取时仍使用未注册的 `right_panel:` namespace。
验收标准：统一到实际资源组织方式；用生产 i18n 初始化验证中英全部分区文案、状态、错误与插值；七语言 key 齐备；页面无原始 key，测试包含真实翻译资源且排除仅回显 key 的伪通过。

### 29. [进行中] 修复运行摘要及面板数据真实性
范围：RunSummary、Config/Execution/Changes/Activity sections、store。核验：用户报告正在修复；读取时沙箱固定 project_only，Token/耗时缺省回落 0，DAG/trace 请求未传会话。
验收标准：指标逐项满足任务 13 来源契约；未知上限不显示确定占比，未知沙箱明确未上报；全局数据显式标注范围，会话数据按真实标识关联；切换会话无串数；固定样例、零值、缺失值分别测试。

### 30. [待验收] 验收右侧异步生命周期与恢复
范围：`PanelState.tsx` 与各 section。核验：已有 loading/error/reload、卸载结果隔离；当前测试含基本空态。
验收标准：每个请求分区覆盖成功/空/失败/重试，快速切会话和折叠后旧响应不覆盖新数据；重新加载期间不误呈旧范围结果，ARIA 状态正确；补足行为测试后由主代理执行。

### 31. [待验收] 验收 SSE 修复及 UI 收尾
范围：`api.ts`、`types/chatEvents.ts`、`useChat.ts` 与 SSE/事件测试。核验：空闲超时错误、reader 释放、规范化适配已有实现。
验收标准：event 行/data.type、分块 UTF-8、无尾空行、未知事件、空 body、持续活跃、卡流、用户取消均有测试；超时 UI 显示可恢复错误，结束只收尾一次，保留部分输出；AG-UI 完整生命周期支持范围单独声明。

### 32. [待办] 重构工作区消息输入与发送控制
范围：`ChatPage.tsx`、实际 composer、`useChat.ts`、模型选择。核验：既有聊天调用链存在，本次完整交互未验收。
验收标准：空白禁发、IME 回车不误发、Shift+Enter 换行、发送中防重复；停止与失败重试可达，输入增长不遮挡主操作；支持的附件具上传/失败反馈，不支持能力有明确说明。

### 33. [待办] 重构消息阅读、Markdown 与滚动
范围：`components/chat/{MessageContent,MarkdownRenderer,ThinkingDetails}.tsx` 及消息列表。
验收标准：长文/表格/代码局部滚动，复制成功失败有反馈，TOC 定位正确；流式更新保留选区与手动上滚位置，可一键回最新；未知消息有降级展示，补直接行为测试。

### 34. [待办] 统一工具调用与推理过程呈现
范围：`components/agent/ToolCallVisualization.tsx`、协作 ToolCallCard、ThinkingIndicator、ReasoningPanel。
验收标准：按真实调用 ID 对齐开始/结果/错误；运行/成功/失败/取消明确，参数和结果渐进展开，大结果可截断展开；工具专项测试覆盖并发、乱序和失败，推理仅展示后端提供内容。

### 35. [待办] 重构权限待确认与危险操作反馈
范围：FloatingPermissionDialog、PermissionModeToggle、删除确认及 Toast 调用路径。
验收标准：待确认显示真实动作、范围、风险和批准/拒绝；重复点击只提交一次，失败保留上下文；焦点锁定/恢复可用；关键成功失败触发真实通知，已失效审批不能继续执行。

### 36. [待办] 完成智能体管理页统一重构
范围：`AgentsPage.tsx`、列表、编辑表单和确认对话框。核验：审计记录删除确认与菜单可达性修复，全面页面验收待做。
验收标准：检索、创建、编辑、删除主路径使用真实 API；必填/服务端错误就地反馈，失败保留输入；0/1/多项及长名称布局通过，键盘与双主题验收覆盖全部主操作。

### 37. [待办] 完成工作流列表与编辑器重构
范围：WorkflowsPage、WorkflowEditor、WorkflowNodes、PropertiesPanel。
验收标准：创建/打开/编辑/保存/执行形成真实闭环；选中节点与属性同步，校验错误定位节点，保存失败保留草稿；画布缩放、窄侧栏和键盘操作通过，运行结果可追溯任务。

### 38. [待办] 完成集群、团队与工厂工作台重构
范围：ClusterPage、FactoryModePage、`crews` 实际入口、collaboration/group 组件。
验收标准：团队配置、启动、停止与阶段进度绑定真实 run/task；计划、成员和产物分区明确，失败可定位；无 Agent/模型时提供可达配置入口，断线显示实际状态，禁用操作均解释原因。

### 39. [待办] 完成任务、历史与调度页面重构
范围：TaskMonitorPage、TaskHistoryPage、SchedulerPage。
验收标准：状态过滤、详情、提交/取消和调度保存匹配实际端点；禁用幻影 pause/resume 行为；时区、空结果、失败重试明确，切换过滤防串数据，历史详情可定位对应运行。

### 40. [待办] 完成模型、凭据与设置页重构
范围：ApiKeysPage、AuthApiKeysPage、SettingsPage、ModelConfig/ModelSelector。
验收标准：模型发现按所有者与 provider 关联凭据，界面不回显密钥；切换身份清空不适用选择，发现失败阻止提交无效配置；保存失败保留编辑态，无登录流程，成功后聊天实际采用选择配置。

### 41. [待办] 完成技能、插件与 MCP 管理重构
范围：SkillsPage、PluginsPage、PluginPage、MCPPage。
验收标准：可用/已配置/运行失败状态有真实来源；详情、配置保存、启停或调用严格对齐已有 API；缺失能力提供明确说明，列表/详情统一四态，搜索、长描述和错误反馈均有行为测试。

### 42. [待办] 完成概览、诊断与观测页面重构
范围：DashboardPage、DoctorPage、StatsPage、TracesPage、EvalPage、CostPage、ReasoningPage、ReasoningHistoryPage。
验收标准：逐页列出主指标来源、单位、时间范围及主操作；未知与零值区分，加载/失败/空态完整；图表有文本摘要，链路/评估/推理可定位详情，八页逐项签验，不能仅以共享组件替换结项。

### 43. [待办] 完成终端、文件变更与通知入口重构
范围：TerminalPage、DiffPanel、文件分区、NotificationsPage。
验收标准：终端连接/断开/失败可见且隐藏后资源正确处置；Diff 与文件展示真实项目和路径，空变更有说明；通知列表及已读操作匹配接口，长内容可读，三类入口分别具备行为验证证据。

### 44. [待办] 将统一状态原语接入全部业务页
范围：任务 09 路由矩阵及任务 12 状态契约。
验收标准：每页登记加载/空/失败/权限待确认四态的适用性与截图或测试；失败重试保留筛选，空态动作可达；不适用状态写明原因，所有适用项均有实际组件与覆盖。

### 45. [待办] 结清全站国际化与动态文案
范围：七份 locale、Input、SessionSidebar、控制栏、全部可达页面。
验收标准：静态及动态 key 枚举无缺失、插值一致；中文/英文真实运行无原始 key 和非预期混用，长德文等不遮挡控件；日期/数值随 locale，权限/错误/密码名称均可翻译。

### 46. [待办] 完成双主题视觉与品牌回归
范围：任务 11 令牌及全部页面、弹窗、代码与图表。
验收标准：1440×900 亮暗截图覆盖各路由和主状态；普通文字对比度至少 4.5:1，大字及关键非文本边界至少 3:1；accent 使用一致，硬编码色逐项解释或迁移，截图差异经人工确认。

### 47. [待办] 完成键盘与响应式兼容验收
范围：桌面全站与移动适配入口。
验收标准：1440×900、1280×720、1024×768、390×844 下关键操作可达；仅代码/表格等允许局部横滚；200% 缩放、纯键盘、读屏名称、焦点返回和 reduced-motion 覆盖导航/弹窗/工作区，触屏关键入口至少 44px。

### 48. [待办] 完成长列表与流式性能回归
范围：会话、消息、工具调用、搜索和图表。
验收标准：本地固定 200 会话、1000 消息与连续事件样例，记录浏览器/机器/基线；筛选和切会话测量 10 次，p95 交互反馈不超过 200ms；连续开关面板无累计监听器/请求增长，滚动位置稳定。仅本地功能性能验证。

### 49. [待办] 执行当前快照全量自动验证
范围：package.json 现有 typecheck/lint/build/test/i18n 脚本及 Playwright。
验收标准：主代理按受管理后台任务规则串行执行 typecheck、lint、build、受限 worker 的全量 Vitest、翻译检查及既有 E2E；记录命令/退出码/实际计数/失败与跳过；新增错误零容忍，历史 warnings 逐项登记，不套用旧审计数字。

### 50. [待办] 主代理完成跨模块验收与交付结项
范围：全部 49 项成果、任务 09 路由矩阵与真实运行链路。
验收标准：前置任务全部满足各自标准；主代理在同一代码快照串行验证配置模型→建会话→发送/停止→工具/权限→产物/错误恢复，以及全部导航主操作；真实后端与 mock 证据分别列出。需要用户模型凭据的链路缺凭据时标阻塞。汇总残余问题、截图、日志与验收者；满足全量门槛后才标全面重构完成。

## 执行顺序与状态维护

- 优先收敛任务 28–29，随后验收本批 15–21、23、25、27、30–31，防止翻译和状态真实性问题被局部测试掩盖。
- 任务 03–14 为后续改造提供证据与契约；业务实现按 22–43 的相关依赖推进，44–48 逐页补齐横向质量，49–50 串行结项。
- 每次验收同时更新任务状态、证据与顶部计数；拆分执行步骤保留原 50 个顶级编号。新增阻塞写入对应任务，避免用增加任务数代替真实完成数。
- 本次只写入此文档，保留其他代理工作树；未提交、未启动服务、未改动实现文件。后续全量验收责任归主代理。

## 状态同步（2026-09-26 逐条核验）

本节由一次独立的文档同步核验写入，判定以 `frontend-react/src` 的实际文件与实际命令执行为准，不采信任何既有文档的状态自述。上方编制期的计数与状态标签保持原样，作为历史快照保留；本节取代其作为当前状态来源。

### 1. 本次核验取得的可复现证据

| 编号 | 命令 / 核验方式 | 结果 | 时间 | 证据位置 |
| --- | --- | --- | --- | --- |
| V1 | `npm run typecheck`（tsc -b） | 通过，退出码 0 | 2026-09-26 11:46:38 | `/tmp/terminal_term_1790423198464_190.log` |
| V2 | `npm run lint`（oxlint） | 通过，退出码 0；25 warnings / 0 errors / 217 files | 2026-09-26 11:48:13 | `/tmp/terminal_term_1790423293928_191.log` |
| V3 | `npx vitest run --reporter=dot`（全量） | 通过，退出码 0；55 文件 / 509 用例 / 239.56s | 2026-09-26 11:49:27 起 | `/tmp/terminal_term_1790423363667_193.log` |
| V4 | `python3 scripts/check-translations.py` | 通过，退出码 0；6 语言 328 键 100% | 2026-09-26 11:44–11:56 | 命令输出（覆盖 `public/locales`，见 D2） |
| V5 | 构建产物检查 | `dist/` 产物时间 2026-09-26 10:36，早于当前快照；当前快照无构建证据 | 2026-09-26 11:44–11:56 | `frontend-react/dist` mtime |
| V6 | Playwright E2E | 本轮未执行；`e2e/*.spec.ts` 自 2026-09-23 基线提交起未改动 | 2026-09-26 11:44–11:56 | `git status --porcelain frontend-react/e2e` |
| V7 | 参考仓库许可与 SHA 复核 | 5 个仓库 LICENSE 均存在，SHA 与文档记录逐位一致 | 2026-09-26 11:44–11:56 | `/tmp/opencode/ref-repos/*` |
| V8 | 硬编码用户可见中文扫描 | 25 个源文件共 635 行（已剔除注释与测试文件） | 2026-09-26 11:44–11:56 | `grep -rnP '[\x{4e00}-\x{9fa5}]' src/pages src/components src/layout` |
| V9 | 右侧面板翻译解析核验 | 冒号式 `right_panel:` 调用 0 处；点式调用 113 处；7 份 locale 各 512 键，缺失 0、多余 0 | 2026-09-26 11:44–11:56 | `src/locales/*.json`、`src/i18n/config.ts` |
| V10 | 沙箱与令牌上限真实性 | `project_only` 字面量 0 处；令牌块在 limit 缺失时不渲染 | 2026-09-26 11:44–11:56 | `src/components/workspace/ControlBar.tsx:34,107` |
| V11 | 面板会话关联 | `ExecutionSection` 仍以无参 `getClusterStatus()` / `listTraces()` 取数 | 2026-09-26 11:44–11:56 | `src/components/workspace/rightPanel/sections/ExecutionSection.tsx:34,81` |
| V12 | 会话列表能力 | 侧栏无时间分组、无标题过滤、无删除确认 | 2026-09-26 11:44–11:56 | `src/components/workspace/SessionSidebar.tsx` |
| V13 | 命令匹配算法 | 仍为三处 `includes` 匹配，无评分排序 | 2026-09-26 11:44–11:56 | `src/components/workspace/CommandPalette.tsx:35-39` |
| V14 | 搜索结果去向 | Enter 仅展开预览，无结果类型导航 | 2026-09-26 11:44–11:56 | `src/components/workspace/GlobalSearch.tsx:157-158` |
| V15 | 状态原语接入面 | 仅 9 个页面引用 `useAsyncData` / `EmptyState` 等原语 | 2026-09-26 11:44–11:56 | `src/pages/*.tsx` |
| V16 | 视觉与性能产物 | 无验收截图，无性能测试文件 | 2026-09-26 11:44–11:56 | `find frontend-react -name '*screenshot*'` |
| V17 | 页面测试覆盖 | TerminalPage / WorkflowsPage / NotificationsPage / DoctorPage / EvalPage / CostPage 无任何测试文件 | 2026-09-26 11:44–11:56 | `src/pages/__tests__/` |
| V18 | 密码可访问名称本地化 | `showPasswordLabel` / `hidePasswordLabel` 仍回落英文常量，全站无调用点传入翻译值 | 2026-09-26 11:44–11:56 | `src/components/ui/Input.tsx:20` |
| V19 | 控制栏文案本地化 | 仍硬编码“保存快照”“专注模式”“专家模式” | 2026-09-26 11:44–11:56 | `src/components/workspace/ControlBar.tsx:89,158,190` |
| V20 | 附件能力 | 聊天输入区无任何附件上传入口 | 2026-09-26 11:44–11:56 | `src/components/agent/ChatInterface.tsx`、`src/pages/ChatPage.tsx` |

### 2. 真实三态计数

| 范围 | 任务数 | 已完成 | 进行中 | 未开始 |
| --- | ---: | ---: | ---: | ---: |
| 01–20 研究与基础 | 20 | 9 | 9 | 2 |
| 21–50 实现与验收 | 30 | 9 | 15 | 6 |
| **合计** | **50** | **18** | **24** | **8** |

三态定义（本次统一口径）：

- **已完成**：源码改动已落盘，且存在对应的测试或验收证据，且该证据在当前快照上通过。
- **进行中**：源码已改但缺少验证证据，或已有部分证据但任务自身的验收标准未整体满足。
- **未开始**：该任务的交付物在 `frontend-react/src` 中不存在。

已完成的 18 项中，**待浏览器验收 20 项、待后端联调 9 项**（任务 10、21、35、38、39、43 两类都待）。另有 6 项待当前快照构建复跑、3 项待翻译检查目录修正。

### 3. 逐条状态与证据

状态格式：`[已完成]` / `[进行中]` / `[未开始]`；标注项为仍需补齐的验收类别。

#### 研究与基础 01–20

- **01 建立审计差异基线** `[已完成]` ｜ 依据：本文件依据表 + V1–V20 全量核验 ｜ 缺口：无
- **02 校正参考索引的证据口径** `[已完成]` ｜ 依据：`REFERENCE_INDEX.md` 100 编号、外部运行验证 0 项 ｜ 缺口：无
- **03 固定实际采用参考的版本与许可** `[已完成]` ｜ 依据：`SOURCE_DESIGN_REVIEW_20_2026-09-26.md:10-17`、`ROUND10_TASK_G_LICENSE_SHA_2026-09-26.md`；V7 复核 5 仓库 LICENSE 与 SHA 逐位一致 ｜ 缺口：无
- **04 会话组织与长列表模式** `[进行中]` ｜ 证据：`ROUND9_REFERENCE_AGENT_ACCEPTANCE_2026-09-26.md` 会话身份行（assistant-ui thread-list 源码事实）｜ 缺口：四项目六维对照未成文；无后端支持边界说明
- **05 流式消息与输入交互** `[进行中]` ｜ 证据：同文件 Composer states 行（Cline ChatTextArea、Chainlit SubmitButton 源码事实）｜ 缺口：发送/停止/失败重试/IME/滚动跟随/部分内容六项状态契约未成文
- **06 执行过程与工具披露层级** `[进行中]` ｜ 证据：`RIGHT_PANEL_SPEC_2026-09-26.md` §3/§5、`SOURCE_DESIGN_REVIEW_20_2026-09-26.md:14`（Dify 运行详情三标签）｜ 缺口：三级结构横向比较、默认展开项与错误优先级未落文
- **07 代码变更与权限确认模式** `[未开始]` ｜ 证据：无 ｜ 缺口：OpenHands / Cline / SWE-agent 的 Diff、审批或轨迹界面源码事实未采集
- **08 管理页与诊断信息密度** `[未开始]` ｜ 证据：无 ｜ 缺口：列表密度、详情编辑、凭据选择、异常反馈四类源码对照未采集
- **09 路由与用户旅程矩阵** `[进行中]` ｜ 证据：`src/navigation/navConfig.ts`（工作树已改）、`src/navigation/navConfig.test.tsx`（V3 通过）｜ 缺口：25 项入口/组件/主操作/接口/三态矩阵未成文；额外路由与未知 hash 行为未登记
- **10 桌面布局与信息优先级** `[进行中]` ｜ 证据：`src/components/workspace/__tests__/WorkspaceLayout.geometry.task01.test.tsx`（V3 通过）、`ROUND10_TASK_A_DOM_2026-09-26.md`（1440/1280/1024/768/390 无水平溢出）｜ 缺口：待浏览器验收（宽度实测）、待后端联调；折叠与调整尺寸规则未成文
- **11 视觉令牌与语义映射** `[进行中]` ｜ 证据：`src/index.css`（工作树已改）、`src/components/ui/__tests__/presentation-contract.test.tsx`（V3 通过）｜ 缺口：亮暗两套令牌清单与实际使用组件、允许例外未逐项登记
- **12 统一异步及权限状态契约** `[进行中]` ｜ 证据：`src/components/workspace/rightPanel/PanelState.tsx`、`RIGHT_PANEL_SPEC_2026-09-26.md` §5/§8 ｜ 缺口：全站四态契约、未知与未上报语义、过期响应与重复提交规则未成文
- **13 核对运行状态与接口字段来源** `[进行中]` ｜ 证据：`src/components/workspace/rightPanel/__tests__/InspectorData.test.tsx` 7 用例（V3 通过）、V10、V11 ｜ 缺口：逐项字段来源与缺省语义表未成文；DAG/trace 仍无会话关联（V11）
- **14 冻结可访问性与国际化验收矩阵** `[进行中]` ｜ 证据：`src/a11y-styles.css`、`src/index.css:821,1198`（focus-visible、reduced-motion）｜ 缺口：验收矩阵未成文；V18、V19 两处本地化缺口仍在
- **15 共享状态图标词汇** `[已完成]` ｜ 证据：`src/lib/icons.ts`（新建）、`src/components/ui/__tests__/control-foundation.test.tsx`（V3 通过）｜ 缺口：无
- **16 控件密度、焦点与动态基础** `[已完成]` ｜ 证据：`src/index.css:74-81,821,1198`、`src/components/ui/__tests__/control-restraint.test.tsx` 21 用例（V3 通过）｜ 缺口：无
- **17 Button 行为与视觉契约** `[已完成]` ｜ 证据：`src/components/ui/Button.tsx`、`src/components/ui/__tests__/shared-controls.test.tsx`（V3 通过）｜ 缺口：无
- **18 Badge 状态表达** `[已完成]` ｜ 证据：`src/components/ui/Badge.tsx`、rgba 字面量 0 处、`src/components/ui/__tests__/shared-controls.test.tsx`（V3 通过）｜ 缺口：无
- **19 Input 描述、错误与密码操作** `[已完成]` ｜ 证据：`src/components/ui/Input.tsx`、`src/components/ui/__tests__/control-foundation.test.tsx`（V3 通过）｜ 缺口：密码可访问名称本地化按本任务定义结清于任务 45，V18 仍开放
- **20 基础控件回归集** `[已完成]` ｜ 证据：`control-foundation` 8 + `presentation-contract` 7 + `shared-controls` 7 + `control-restraint` 21 = 43 用例，全部计入 V3 通过集 ｜ 缺口：无

#### 实现与验收 21–50

- **21 会话侧栏本批交互重构** `[已完成]` ｜ 证据：`src/components/workspace/__tests__/SessionSidebar.test.tsx`、`.accessibility.test.tsx`、`.hierarchy.test.tsx`（V3 通过）；`ROUND10_TASK_C_SESSION_IA_2026-09-26.md` 记录最终信息架构顺序 ｜ 缺口：待浏览器验收、待后端联调（创建与检查点需真实 API 数据）
- **22 会话分组、过滤与真实上下文摘要** `[未开始]` ｜ 证据：V12（`SessionSidebar.tsx` 内无 group / filter / confirm 结构）｜ 缺口：时间分组、标题过滤、未知上下文区分、删除确认或可撤销机制全部未实现
- **23 命令面板本批交互** `[已完成]` ｜ 证据：`src/components/workspace/__tests__/CommandPalette.test.tsx`、`ROUND10_TASK_D_KEYBOARD_BOUNDARIES_2026-09-26.md:93-114` ｜ 缺口：待浏览器验收（真实按键序列与焦点归还）
- **24 可解释的命令匹配排序** `[未开始]` ｜ 证据：V13（`CommandPalette.tsx:35-39` 仍为 `includes`）｜ 缺口：优先级规则、同分稳定性、25 项可搜索性、中英文与拼写偏差用例全部未实现
- **25 全局搜索本批重构** `[已完成]` ｜ 证据：`src/components/workspace/__tests__/GlobalSearch.test.tsx`、`ROUND10_TASK_D_KEYBOARD_BOUNDARIES_2026-09-26.md:127-148` ｜ 缺口：待浏览器验收
- **26 统一应用导航与搜索结果去向** `[未开始]` ｜ 证据：V14（`GlobalSearch.tsx:157-158` Enter 仅展开预览）｜ 缺口：有详情页结果定位、无详情页标记、切页保留会话、失效对象反馈全部未实现
- **27 右侧面板四分组架构** `[已完成]` ｜ 证据：`src/components/workspace/rightPanel/groupModel.ts`、`src/components/workspace/__tests__/RightPanel.test.tsx`、`ControlBar.test.tsx`（V3 通过）、`ROUND10_TASK_B_INSPECTOR_CONTROLBAR_2026-09-26.md:83-194` 单一入口结论 ｜ 缺口：待浏览器验收（窄屏抽屉与分组切换）
- **28 右侧面板真实翻译解析** `[已完成]` ｜ 证据：V9（0 处冒号调用、7 语言 512 键齐备）、`src/components/workspace/rightPanel/__tests__/RightPanel.i18n.test.tsx` 引入生产 `i18n/config` 并断言中英真实文案（V3 通过）｜ 缺口：待浏览器验收
- **29 运行摘要及面板数据真实性** `[进行中]` ｜ 证据：`InspectorData.test.tsx` 7 用例（V3 通过）、V10（沙箱固定文案与令牌 0% 已消除）｜ 缺口：V11 未解——DAG/trace 请求仍无会话参数，任务标准“会话数据按真实标识关联”未满足；待后端联调
- **30 右侧面板异步生命周期与恢复** `[进行中]` ｜ 证据：`PanelState.tsx` 取消旧请求写入、`InspectorData.test.tsx` 覆盖失败/重试/缺失/无名步骤 ｜ 缺口：ConfigSection 与 ChangesSection 无对应成功/空/失败/重试用例；快速切会话与折叠卸载后的旧响应隔离未逐分区验证；待后端联调
- **31 SSE 修复及 UI 收尾** `[已完成]` ｜ 证据：`src/__tests__/api.sse.test.ts` 5 用例（AG-UI 与 event 行两种形态、卡流报错、窗口内持续活跃、阈值透传）、`src/types/__tests__/chatEvents.test.ts` 13 用例（分块/未知事件/空载荷/错误归一）、`src/useChat.test.ts`（V3 通过）｜ 缺口：待后端联调（真实流与用户取消的服务端副作用）
- **32 工作区消息输入与发送控制** `[进行中]` ｜ 证据：`src/components/agent/ChatInterface.tsx`、`src/useChat.ts`（工作树已改）、`ChatInterface.task03.test.tsx`、`ChatInterface.hierarchy.test.tsx`、`src/pages/__tests__/ChatPage.test.tsx`（V3 通过）｜ 缺口：V20——附件上传与失败反馈不存在，“不支持能力有明确说明”亦未落地；待浏览器验收
- **33 消息阅读、Markdown 与滚动** `[已完成]` ｜ 证据：`src/components/chat/__tests__/MarkdownRenderer.states.task03.test.tsx`（表格溢出、代码控件、不安全链接）、`MarkdownRenderer.toc.test.tsx`、`ChatInterface.task03.test.tsx`（V3 通过）｜ 缺口：待浏览器验收
- **34 工具调用与推理过程呈现统一** `[已完成]` ｜ 证据：`src/components/agent/toolCallStatus.ts` 与 `ToolDisclosure.tsx`（新建共享状态词汇）、`ToolCallVisualization.tsx:59-140` 已改用该词汇、`src/components/agent/ToolDisclosure.task02.test.tsx` 17 用例（V3 通过）｜ 缺口：待浏览器验收
- **35 权限待确认与危险操作反馈** `[已完成]` ｜ 证据：`src/components/agent/FloatingPermissionDialog.tsx`（高危二次确认、重复提交锁、失败保留上下文、role=alert、最小化态）、`ToolApproval.task04.test.tsx` 7 用例、`ToolDisclosure.task02.test.tsx:127-163`（V3 通过）｜ 缺口：待浏览器验收、待后端联调（审批接口副作用）；V19 显示的硬编码中文名未本地化
- **36 智能体管理页统一重构** `[进行中]` ｜ 证据：`src/pages/__tests__/AgentsPage.test.tsx`、`ResourceLists.task10.test.tsx`（V3 通过）｜ 缺口：0/1/多项与长名称布局、键盘与双主题覆盖全部主操作未验证；待浏览器验收
- **37 工作流列表与编辑器重构** `[进行中]` ｜ 证据：`src/pages/WorkflowsPage.tsx` 与 `components/workflow/*`（工作树已改，WorkflowsPage 已引用状态原语，V15）｜ 缺口：V17——WorkflowsPage 无任何测试文件，闭环、校验定位、画布与窄侧栏均无证据；待浏览器验收
- **38 集群、团队与工厂工作台重构** `[进行中]` ｜ 证据：`ClusterPage.members.test.tsx`、`collaborationLayout.test.tsx`、`FactoryModePage.test.tsx` 与 `.review2.test.tsx`、移动端三页测试（V3 通过）｜ 缺口：`ClusterPage.tsx` 仍有 23 行硬编码中文（V8）；断线与禁用原因说明未验证；待浏览器验收、待后端联调
- **39 任务、历史与调度页面重构** `[进行中]` ｜ 证据：`src/pages/__tests__/Task14.logs.test.tsx` 6 用例（过滤、失败重试、切选后过期响应隔离、取消后同契约刷新）、`SchedulerPage.test.tsx` 6 用例（V3 通过）｜ 缺口：时区与空结果表达、TaskMonitorPage 提交/取消的真实端点匹配未验证；待浏览器验收、待后端联调
- **40 模型、凭据与设置页重构** `[进行中]` ｜ 证据：`AuthApiKeysPage.test.tsx`、`SettingsPage.credentials.test.tsx`、`SettingsPage.api-contract.test.ts`、`src/components/chat/ModelSelector.test.tsx`（V3 通过）｜ 缺口：`SettingsPage.tsx` 仍有 68 行硬编码中文（V8）；切换身份清空选择与成功后聊天实际采用未验证；待浏览器验收
- **41 技能、插件与 MCP 管理重构** `[进行中]` ｜ 证据：`ResourceCatalogRows.task5.test.tsx`（MCP 7 + Plugins 用例）、`ResourceLists.task10.test.tsx`、`PluginAndOperationsPages.taskB.test.tsx`（V3 通过）｜ 缺口：`PluginPage` 与 `PluginsPage` 重复调用面未合并（`ROUND8_TASK04` 记录）；长描述与错误反馈未逐项验证；待浏览器验收
- **42 概览、诊断与观测页面重构** `[进行中]` ｜ 证据：`PluginAndOperationsPages.taskB.test.tsx`（Dashboard、Stats）、`Task14.logs.test.tsx`（Traces、Reasoning、ReasoningHistory）｜ 缺口：V17——DoctorPage / EvalPage / CostPage 无任何测试文件，八页逐项签验未完成；待浏览器验收
- **43 终端、文件变更与通知入口重构** `[进行中]` ｜ 证据：`src/components/terminal/TerminalPanel.tsx`、`src/components/code/DiffPanel.tsx`、`src/pages/NotificationsPage.tsx`（工作树已改；`ROUND8_TASK03` 记录 xterm 卸载清理与 trace 过期隔离）｜ 缺口：V17——TerminalPage 与 NotificationsPage 无测试文件，DiffPanel 无测试文件；待浏览器验收、待后端联调
- **44 统一状态原语接入全部业务页** `[进行中]` ｜ 证据：V15（Agents、ApiKeys、Factory、MCPPage、PluginPage、PluginsPage、SchedulerPage、SkillsPage、WorkflowsPage 共 9 页已引用）｜ 缺口：其余约 16 页未接入；每页四态适用性与覆盖登记未成文
- **45 全站国际化与动态文案** `[进行中]` ｜ 证据：V9（7 语言键齐备）、V4（检查脚本退出码 0）｜ 缺口：V8（635 行硬编码中文，FactoryModePage 69、SettingsPage 68、ReasoningPanel 40 居前）；V18（密码名称英文回落）；V19（控制栏三处硬编码）；D2（翻译检查指向错误目录）；待浏览器验收
- **46 双主题视觉与品牌回归** `[未开始]` ｜ 证据：V16（无任何验收截图）｜ 缺口：亮暗截图、对比度实测、硬编码色逐项解释全部缺失
- **47 键盘与响应式兼容验收** `[进行中]` ｜ 证据：`WorkspaceLayout.geometry.task01.test.tsx`、`AdaptiveMobileLayout.viewport.test.tsx`、`.pages.test.tsx`、`src/__tests__/App.mobile.test.tsx`、`src/pages/mobile/__tests__/` 四页测试（V3 通过）；`ROUND10_TASK_E_MOBILE_SAFE_AREA_2026-09-26.md` 记录安全区与缺页回落补丁；`ROUND10_TASK_A` 记录五宽度无水平溢出 ｜ 缺口：V6——纯键盘、读屏名称、200% 缩放、44px 触屏目标无浏览器实测；待浏览器验收
- **48 长列表与流式性能回归** `[未开始]` ｜ 证据：V16（无性能测试文件，无基线记录）｜ 缺口：200 会话 / 1000 消息样例、p95 测量、监听器与请求增长观测全部缺失
- **49 当前快照全量自动验证** `[进行中]` ｜ 证据：V1（typecheck 通过）、V2（lint 通过）、V3（Vitest 55 文件 509 用例通过）、V4（i18n 脚本退出码 0）｜ 缺口：D3（当前快照无构建证据，产物为 10:36 旧快照）、V6（Playwright E2E 未执行）、D2（翻译检查对象错误）
- **50 主代理跨模块验收与交付结项** `[未开始]` ｜ 证据：无 ｜ 缺口：前置 46、48 未开始，49 缺构建与 E2E；配置模型→建会话→发送/停止→工具/权限→产物/错误恢复的串行联调与真实后端证据缺失

### 4. 本次核验发现的具体缺口（按可执行性排序）

- **D1 待浏览器验收覆盖面 20 项**：10、21、23、25、27、28、32、33、34、35、36、37、38、39、40、41、42、43、45、47。已有 jsdom 行为测试覆盖逻辑分支，纯键盘、读屏名称、200% 缩放、44px 触屏目标、对比度与长翻译无任何真实浏览器记录。
- **D2 翻译检查脚本指向错误目录**：`scripts/check-translations.py:12` 读取 `public/locales`（328 键），而 `src/i18n/config.ts` 运行时加载 `src/locales`（512 键）。V4 的“全部完整”结论只覆盖 328 键，另有 185 个运行时键不在检查范围，且 `public/locales` 存在 1 个运行时已无的过期键。
- **D3 当前快照缺构建与 E2E 证据**：`dist/` 产物生成于 2026-09-26 10:36，其后 `src/` 持续改动至 11:46；`e2e/*.spec.ts` 自基线提交未改动，V6 显示本轮未执行。
- **D4 六页零测试**：TerminalPage、WorkflowsPage、NotificationsPage、DoctorPage、EvalPage、CostPage（V17）。这直接阻塞 37、42、43 的逐项签验。
- **D5 三类文案缺口**：V19 控制栏三处硬编码、V18 密码可访问名称英文回落、V8 全站 635 行硬编码中文。三者共同阻塞 45。
- **D6 面板会话关联未修复**：V11 显示 `ExecutionSection` 的 DAG/trace 请求仍无会话参数，直接阻塞 29 的“会话数据按真实标识关联”与 30 的旧响应隔离验证。
- **D7 状态原语接入面 9/25 页**：V15。任务 44 需要逐页四态适用性登记与覆盖。
- **D8 参照 `SOURCE_DESIGN_REVIEW_20_2026-09-26.md` §5 的“本轮未验证”清单仍然成立**：该清单中的布局、对比度、键盘、读屏、IME、减弱动态、长翻译与协作闭环验收，本节核验后依旧没有新增证据。

### 5. 与编制期计数的差异说明

- 编制期为已完成 2、进行中 3、待验收 12、待办 33；本次核验为已完成 18、进行中 24、未开始 8。
- 差异主因：编制期后 7 个并行子代理与 Round 8/9/10 轮次落盘了源码与测试（共享控件词汇与回归集、会话侧栏三套测试、命令面板与全局搜索测试、右侧面板四分组与 i18n 测试、面板数据保真测试、工具披露与审批测试、Markdown 状态测试、协作与移动端测试），V3 证明这些测试在当前快照全部通过，故多项由“待验收/待办”升为“已完成”。
- 编制期的“实际完成数 2/50，实现与验收完成数 0/30”已过期。实现与验收段（21–50）现为已完成 9 项：21、23、25、27、28、31、33、34、35。
- 编制期引用的“34 文件 / 280 测试”“lint 31 warnings”均为历史快照；当前实测为 55 文件 / 509 用例、25 warnings / 0 errors（V2、V3）。

### 6. 状态维护规则（本次确立）

- 状态升级只接受可复现证据：命令、退出码、用例数、日志路径、时间，五项齐备才可写“已完成”。
- 单元测试通过不构成浏览器验收。涉及布局、对比度、按键、读屏、触屏的任务，在真实浏览器记录写入前一律保留“待浏览器验收”标注。
- 单元测试通过不构成后端联调。涉及真实 API 字段、会话关联、审批副作用、SSE 实际流的任务，在后端可用并记录响应前一律保留“待后端联调”标注。
- 本地代码与测试的变更不算结项。上方编制期计数与状态标签保留为历史快照，本节为当前唯一状态来源。
- 未新增阻塞项时，只更新本节；不得通过增加任务编号替代真实完成数。
- 本次同步只写入此文档，未修改 `frontend-react/src` 下任何文件，未提交，未删除既有文档。

## 状态同步第 7 节（2026-09-26 补证据轮）

本节由研究与文档执行者写入，专注补齐上一节列出的 8 项未开始任务的证据，并给出跨模块结项验收清单。详细证据见 `ROUND11_TASK_H_EIGHT_GAPS_2026-09-26.md`，验收做法调研见 `ROUND11_ACCEPTANCE_CHECKLIST_2026-09-26.md`。第 3 节的 V1–V20 命令级证据仍是当前唯一的命令级记录；本节未执行任何命令验证，判定基于源码读取与文件检索。

### 7.1 8 项未开始任务的真实三态

| 任务 | 上一节状态 | 本节真实三态 | 关键证据 |
| --- | --- | --- | --- |
| 07 代码变更与权限确认模式 | 未开始 | **已完成** | 4 仓库 8 处源码证据：OpenHands `conversation-confirmation-buttons.tsx:44-47,66-78,92-131`（提交去重 + 拒绝/确认双出口 + 键盘等价）、`risk-alert.tsx:20-33`、`danger-modal.tsx:9-12,26-37`、`diff-change-list.tsx:19-43`；Cline `DiffEditRow.tsx:26-30,52-80`、`AutoApproveMenuItem.tsx:34-56`、`AutoApproveBar.tsx:29-41`；LobeHub `ModelItem.tsx:84,204-228`。SWE-agent 全仓仅 4 个 HTML，无 React UI，证据层级降级为轨迹/文档级 |
| 08 管理页与诊断信息密度 | 未开始 | **已完成** | 四类各 2 处：列表密度 LibreChat `VirtualizedModelList.tsx:8-11,26-39` + OpenHands `diff-change-list.tsx:19-24`；详情编辑 LibreChat `Advanced.tsx:24,38-67` + LobeHub `CustomProviderDetail.tsx:19-30`；凭据选择 Dify `use-credential-panel-state.ts:11-66` + `popup-item.tsx:79-86,175-189`；异常反馈 LobeHub `CheckError.tsx:32-58` + Dify `popup-item.tsx:162-174`。每类含采用决策与适配限制 |
| 22 会话分组、过滤与上下文摘要 | 未开始 | **未开始** | `src/components/workspace/SessionSidebar.tsx:309-310` 仍为单一 `<ul>` + `sessions.map`；全文件 `group\|filter\|confirm\|undo` 仅命中 1 处（第 313 行 Tailwind `group` 类名）；时间格式化唯一一处在第 409 行且属检查点；删除走 `api.deleteSession`（187、199 行）无确认无撤销。store 层 `src/store/workspace.ts:60-62,94-99` 的 `tokenUsage` 可选与 `unknown` 状态已就绪，侧栏未读取 |
| 24 可解释的命令匹配排序 | 未开始 | **未开始** | `src/components/workspace/CommandPalette.tsx:36-40` 三处 `includes` 并列布尔；第 34 行空查询 `slice(0, 8)`，推荐规则未成文；`allItems` 来自 `ALL_NAV_ITEMS_BASE`（24-31 行），25 项可搜索性满足；无编辑距离与中文分词 |
| 26 统一应用导航与搜索结果去向 | 未开始 | **未开始** | `src/components/workspace/GlobalSearch.tsx:48-51` Props 无导航回调；157-162 行 Enter 分支只 `setExpanded` 切换；`RESULT_TYPES`（13 行）三类均无详情路由。前置任务 09 自身为进行中 |
| 46 双主题视觉与品牌回归 | 未开始 | **未开始** | `artifacts/ui-acceptance/` 仅 3 张单主题截图（实测 1440×1000 / 768×1024 / 375×812），全为 light，主内容空白或仅 Loading 骨架；无 `toHaveScreenshot`、无基线目录、无对比度实测、无硬编码色登记。可执行方案见 ROUND11 文件 §7.3 |
| 48 长列表与流式性能回归 | 未开始 | **未开始** | 无性能测试文件、无基线记录。`src/useChat.ts:100-171` 七个事件分支各执行一次全量 `setMessages(prev => prev.map(...))`，`throttle\|debounce\|batch\|requestAnimationFrame` 检索 0 命中；`src/components/agent/ChatInterface.tsx:357-361` 全量渲染，`MessageContent.tsx` 无 `memo`；`SessionSidebar.tsx:309-310` 无虚拟化；`@tanstack/react-virtual`（`package.json:34`）0 处使用。可执行方案见 ROUND11 文件 §8.2 |
| 50 主代理跨模块验收与交付结项 | 未开始 | **未开始** | 门槛未达成：46、48 未开始；49 缺当前快照构建（D3）与 E2E（D6）；22/24/26 未开始；串行联调链路无记录。补充：`e2e/02-agents.spec.ts` 与 `e2e/helpers.ts` 本轮工作树已修改（选择器适配 + 429 退避），尚未执行过一次；`scripts/acceptance-session-sync.cjs` 是现成的串行联调骨架但无执行记录 |

### 7.2 计数更新

| 范围 | 任务数 | 已完成 | 进行中 | 未开始 |
| --- | ---: | ---: | ---: | ---: |
| 01–20 研究与基础 | 20 | 11 | 9 | 0 |
| 21–50 实现与验收 | 30 | 9 | 15 | 6 |
| **合计** | **50** | **20** | **24** | **6** |

相对第 3 节的 18 / 24 / 8，变化为：07 与 08 由未开始升为已完成（研究类任务，其交付物是本目录的成文证据，现已写入带行号的源码事实）。实现与验收段（21–50）三态不变，仍为已完成 9 项（21、23、25、27、28、31、33、34、35）、进行中 15 项、未开始 6 项（22、24、26、46、48、50）。

研究段 01–20 现为已完成 11 / 进行中 9 / 未开始 0：第 3 节记录的 2 项未开始即 07、08，本次已补齐证据并升为已完成，故未开始归零。

**计数差异说明**：第 3 节为 18 / 24 / 8，本节为 20 / 24 / 6。已完成 +2、未开始 −2，进行中不变。总数 50 恒定。本节为当前唯一状态来源。

### 7.3 已完成任务的浏览器验收与后端联调待办标注

第 3 节记录：已完成 18 项中待浏览器验收 20 项、待后端联调 9 项（任务 10、21、35、38、39、43 两类都待）。该 20 项与 9 项是**全 50 项范围**的待办清单，其中包含状态为进行中的任务。本节按要求只对**已完成**的 18 项逐条标注，并纠正两类清单与已完成集合的交集。

已完成 18 项：01、02、03、15、16、17、18、19、20、21、23、25、27、28、31、33、34、35。

| 分类 | 数量 | 任务 |
| --- | ---: | --- |
| 两类待办都有（待浏览器验收 + 待后端联调） | 2 | 21、35 |
| 仅待浏览器验收 | 6 | 23、25、27、28、33、34 |
| 仅待后端联调 | 1 | 31 |
| 两类都无待办 | 9 | 01、02、03、15、16、17、18、19、20 |

合计 2 + 6 + 1 + 9 = 18。

**已完成的 20 项中仍待浏览器验收的任务（8 项，逐条待办）**：

| 任务 | 待浏览器验收的具体项 |
| --- | --- |
| 21 会话侧栏本批交互 | 方向键 / Home / End 的真实按键序列；删除成功后焦点归还有无去处；加载态与空态的视觉区分 |
| 23 命令面板本批交互 | ⌘K 打开、上下键越界、Enter 单次执行、Tab 留在弹窗、Escape 关闭并归还焦点、重开清空查询的真实按键序列 |
| 25 全局搜索本批重构 | 300ms 防抖的真实延迟、旧响应隔离、结果类型过滤、键盘展开结果后焦点仍锁定在输入 |
| 27 右面板四分组架构 | 窄屏抽屉形态的分组切换；关闭与折叠确实不挂载对应请求内容 |
| 28 右面板真实翻译解析 | 中英两语言在浏览器中渲染的七分区文案、状态与错误串；页面无原始 key |
| 33 消息阅读、Markdown 与滚动 | 长文 / 表格 / 代码的局部滚动；复制成功失败反馈；流式更新保留选区与手动上滚位置 |
| 34 工具调用与推理过程呈现统一 | 真实调用 ID 对齐的渲染；大结果截断展开；工具失败与取消的视觉区分 |
| 35 权限待确认与危险操作反馈 | 桌面与移动宽度的真实点击；焦点锁定与恢复；高危二次确认的呈现 |

**已完成的 20 项中仍待后端联调的任务（3 项，逐条待办）**：

| 任务 | 待后端联调的具体项 |
| --- | --- |
| 21 会话侧栏 | 创建会话、检查点展开需真实 API 数据；删除的真实副作用与失败路径 |
| 31 SSE 修复及 UI 收尾 | 真实 SSE 流与用户取消的服务端副作用；卡流错误与空闲超时的实际服务端表现 |
| 35 权限待确认 | 审批接口的真实副作用；已失效审批不能继续执行 |

**已完成且无待办的 9 项（01、02、03、15、16、17、18、19、20）**：其中 19 的密码可访问名称本地化按任务 19 的定义结清于任务 45，V18 仍开放，属任务 45 的待办，不重复计入 19。

**未完成任务的待办不进本表**：任务 10、38、39、43 虽同属第 3 节的「两类都待」，但其状态为进行中，已在第 3 节逐条记录。

**新增待办（由本节核验产生）**：

- **B-1 六页零测试仍阻塞 37、42、43**：`src/pages/__tests__/` 共 13 个测试文件，TerminalPage、WorkflowsPage、NotificationsPage、DoctorPage、EvalPage、CostPage 六项检索 0 命中。承接 D4，标为 37、42、43 的「待浏览器验收 + 待后端联调」前置。
- **B-2 E2E 选择器适配未验证**：`e2e/02-agents.spec.ts` 的 `article[aria-label]` → `li[aria-label]`、`[data-dropdown-trigger]` → `button[aria-label]` 两处改动在本轮未执行过。需在 G-5 门槛项中一次跑通，失败应视为选择器收敛待办（详见 ROUND11 验收清单 E-8）。
- **B-3 视觉基线需在 44 收敛后生成**：V15 显示状态原语仅 9/25 页接入，页面改造会使基线频繁失效。建议 44 的 16 页接入完成后再生成基线。
- **B-4 性能阈值 P-8 当前必然失败**：`renders < chunks / 4` 在 `useChat.ts:100-171` 的每片 setState 模式下无法通过。48 需按「先跑测量拿失败基线 → 改造 → 复测」推进，改造前先执行长列表交互延迟、泄漏观测、滚动稳定三项。
- **B-5 产物体积预算无先例**：6 个参考仓库均未发现 bundlesize / bundlewatch / size-limit 配置，46 与 48 的性能预算目前只覆盖运行时指标，产物体积需自建门槛（验收清单 P-13）。
- **B-6 D2 已由并行工作流消解**：`scripts/check-translations.py` 于 12:28:36 被重写，`LOCALES_DIR` 现指向 `src/locales`（第 22 行），旧 `public/locales` 降级为不影响退出码的漂移警告（第 24、132–136 行）。G-4 的脚本侧前置解除，仍需在当前快照重跑记录退出码与实际键数；V4 的「6 语言 328 键」不可沿用。
- **B-7 行号稳定性**：`SessionSidebar.tsx`（12:24:36）与 `index.css`（12:20:47）在核验期间被并行工作流改动，行号已按 12:29 工作树复核。后续复核应以符号名与检索式为主。ROUND11 文件 §10 的 W1–W14 给出可复现检索式。

### 7.4 结项验收清单摘要

完整清单见 `ROUND11_ACCEPTANCE_CHECKLIST_2026-09-26.md`，含 10 项门槛（G-1 至 G-10）、视觉 10 项（V-1 至 V-10）、性能 14 项（P-1 至 P-14）、a11y 8 项（A-1 至 A-8）、E2E 稳定性 8 项（E-1 至 E-8）与 7 条结项判定规则（R-1 至 R-7）。核心结论：

- 参考实现集中在 LibreChat，其把 a11y、性能基准、视觉回归各自拆为独立 Playwright config 的结构（不同 `testDir` / `retries` / `timeout` / `webServer`）是本项目最值得直接照搬的做法。
- `retries` 应按「结果是否确定性」分档：确定性检查（a11y、视觉、性能）统一 `retries: 0`，业务流才给重试。当前项目主配置 `retries: IS_CI ? 2 : 0`（`playwright.config.ts:12`）需为三个新 config 单独覆盖。
- 性能数字必须带 `host`（`logicalCpus`、前后 `loadAverage`、`cpuUtilizationPct`）与 `raw`（原始样本），缺任一字段的数字不作为基线。
- axe-core 检查 DOM 语义违规，纯键盘全流程、200% 缩放、读屏实际播报顺序、44px 触屏目标、对比度分档均需额外手段，不能由工具替代。
- 视觉基线只在声明的平台生成；本项目应采用「结构断言先行 + 像素比对由开关控制」的降级路径，避免在后端不可用时产出无判读价值的空基线。

### 7.5 本节状态维护规则

- 本节为当前状态来源，取代第 3 节。编制期（第 7–11 行表）与第 3 节作为历史快照保留。
- 三态定义沿用第 3 节。研究类任务（01–14）的交付物是本目录的成文证据，其「已完成」取决于证据是否已写入且带可验证行号；实现类任务（15–50）的「已完成」取决于 `frontend-react/src` 中的产物与当前快照的测试或验收证据。
- 本节只写入本文件与本目录两份新文档，未修改 `frontend-react/src` 下任何文件，未 commit、未 push、未删除既有文档。
