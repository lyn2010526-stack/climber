# 前端视觉与交互改造方案

> 目标：为 `frontend-react`（React + Vite + Tailwind v4）定义视觉质感与交互反馈的改造方案。仅设计，不改源码。
> 参考对标：Open WebUI、LibreChat、assistant-ui、CopilotKit、LangGraph/AutoGen Studio、shadcn AI Chat。仅借鉴交互范式与信息架构，不复制源码、图标、品牌资产。
> 基线：`e0ab69f4`，工作树干净，`tsc --noEmit` 与 `vite build` 均 exit 0。

---

## 第一部分 当前 UI 结构梳理

### 1.1 应用壳与布局层级

应用壳在 `src/App.tsx` 收敛为两条分支：桌面与移动端。

```
app-shell (h-screen, overflow-hidden)
├── desktop
│   ├── aside (侧栏, --desktop-sidebar-width 240px / collapsed 64px)
│   │   ├── header (--header-height 52px, ClimberMark + 折叠按钮)
│   │   └── nav (ALL_NAV_ITEMS 25 项, main/manage/config 三组)
│   └── main
│       ├── desktop-context-bar (52px, 命令面板入口)
│       └── PageTransition > renderPage()
│           └── chat 页 = WorkspaceLayout
└── mobile
    └── AdaptiveMobileLayout
        ├── mobile-context-bar (56px, ClimberMark + 当前页标题)
        ├── mobile-content (PageTransition > renderPage)
        └── mobile-bottom-nav (5 列: dashboard/chat/factory/tasks/more)
            └── mobile-sheet-layer > mobile-nav-sheet (more 项)
```

关键真实类名与常量：

| 关注点 | 位置 | 值/类名 |
|---|---|---|
| 桌面侧栏宽 | `index.css:151-153` | `--desktop-sidebar-width: 240px`，`--sidebar-collapsed-width: 64px` |
| 顶栏高 | `index.css:154` | `--header-height: 52px` |
| 页容器宽 | `index.css:65,156,613` | `--content-max: 1120px`，`--content-max-width: 896px`，`.page-container { width: min(100%, var(--content-max)) }` |
| 桌面 shell | `App.tsx:148` | `.app-shell flex h-screen overflow-hidden` |
| 移动 shell | `index.css:671` | `.mobile-workspace-shell { position: fixed; inset: 0 }` |

### 1.2 工作台布局（chat 页）

`src/components/workspace/WorkspaceLayout.tsx` 是核心工作台，三栏由 `react-resizable-panels` 的 `Group/Panel/Separator` 驱动。

```
WorkspaceLayout (section flex-col)
├── ControlBar (--workspace-control-bar, 52px, 横向滚动)
└── flex row
    ├── SessionSidebar (--session-sidebar-width: 240px)
    └── Group (horizontal)
        ├── Panel minSize=40 → ChatPage
        └── Separator (w-1) → Panel (RIGHT_PANEL_WIDTH 360px / min 280 / max 460)
            └── RightPanel
```

- 右栏显隐：`showRightPanel = rightPanelOpen && isWideDesktop && !focusMode`（`WorkspaceLayout.tsx:20`）。
- 专注模式：`focusMode` 时只保留 `ControlBar + ChatPage`，`Escape` 退出，输入焦点内不拦截（`WorkspaceLayout.tsx:22-33`）。
- 面板分隔条样式：`Separator className="w-1 bg-[var(--color-border-subtle)] ... hover:bg-[var(--color-border-accent)] focus-visible:bg-[var(--color-accent)]"`（`WorkspaceLayout.tsx:63`）。

### 1.3 设计 token 体系（已存在，`index.css`）

```
@theme {
  /* 表面层次 */
  --color-bg-page / -surface-1..4
  /* 文本层次 */
  --color-text-primary / secondary / muted / disabled / inverse
  /* 强调色（克制的石板蓝，无发光） */
  --color-accent #475569, -hover #3B4A5C, -subtle rgba(71,85,105,.10),
  --color-accent-text #FFF, -foreground #94A3B8
  /* 语义色 */
  --color-success/warning/error/info + 各自 -subtle
  /* 边框 */
  --color-border-subtle/default/strong/accent
  /* 玻璃面 */
  --color-glass-bg/border/highlight
  /* 圆角 */ --radius-sm 6 / md 8 / lg 12 / xl 16
  /* 控件高 */ --control-height 44px
  /* 阴影 */ --shadow-xs..xl, --shadow-panel, --shadow-elevated
  /* 动效 */ --ease-spring/out/in-out, --transition-instant..slower
  /* 聚焦环 */ --focus-ring: 0 0 0 2px bg-page, 0 0 0 4px accent
  /* 字号/间距/图标 完整刻度 */
  /* z-index 系统 */ --z-base..tooltip
}
```

- 主题切换走 `data-theme`，`@custom-variant dark (&:where([data-theme="dark"], [data-theme="dark"] *))`（`index.css:6`）；light 覆盖在 `[data-theme="light"]`（`index.css:187-207`）。
- 兼容层：`:root` 中为 19 个旧的无前缀变量（`--text-primary`、`--surface-bg`、`--accent` 等）建立别名映射到规范 token（`index.css:164-184`）。
- 全局聚焦环：`:focus-visible { box-shadow: 0 0 0 2px var(--color-bg-page), 0 0 0 4px var(--color-accent) }`（`index.css:796-800`）。

### 1.4 已定义的组件类

`.sidebar`、`.nav-menu`、`.card`、`.icon-button`、`.workspace-control-bar`、`.session-sidebar`、`.chat-container`、`.mobile-bottom-nav`、`.mobile-sheet-layer`、`.mobile-nav-sheet`、`.mobile-more-grid`、`.modal-overlay`、`.modal-content`、`.streaming-cursor`、`.code-block`、`.settings-layout`、`.settings-sidebar`、`.view-tab`、`.page-container`、`.page-scroll`。

### 1.5 关键交互组件

| 组件 | 路径 | 现状要点 |
|---|---|---|
| ChatInterface | `components/agent/ChatInterface.tsx` | 消息列表、StreamingCursor、空态、建议、编辑（行内/模态）、反馈 |
| ToolCallVisualization | `components/agent/ToolCallVisualization.tsx` | 工具调用展开/收起、running 态 |
| ThinkingIndicator / ThinkingDetails | `components/agent/`、`components/chat/` | 推理过程展示 |
| FloatingPermissionDialog | `components/agent/FloatingPermissionDialog.tsx` | 权限请求浮动确认 |
| SessionSidebar | `components/workspace/SessionSidebar.tsx` | 新建会话、Agent/模型选择、checkpoints |
| ControlBar | `components/workspace/ControlBar.tsx` | 右栏 tab、Token 进度、权限模式、自主度、专家/专注 |
| RightPanel | `components/workspace/RightPanel.tsx` | 右栏内容容器 |
| ReasoningPanel | `components/workspace/ReasoningPanel.tsx` | 推理模式/候选/覆盖率/trace |
| CommandPalette / GlobalSearch | `components/workspace/` | 命令面板与全局搜索 |
| AdaptiveMobileLayout | `components/layout/AdaptiveMobileLayout.tsx` | 底栏 4 主项 + more sheet |

### 1.6 现状已具备的良好基础

- token 体系完整，且已处理 light/dark 与旧变量兼容。
- 动效已收敛为 `fadeIn/scaleIn/slideUp/slideInRight/messageEnter/pageSlideIn/cursorBlink`，并有 `prefers-reduced-motion` 处理。
- 焦点环全局统一，`aria-*` 在移动底栏、右栏 tab、ControlBar 图标按钮上已有使用。
- 移动端安全区、触控目标（44px）、滚动性能优化已落地。

---

## 第二部分 五维差距清单

格式：**现状 → 对标做法 → 建议**。每条均落到真实文件/类名。

### 维度一：视觉质感

| # | 现状 | 对标做法 | 建议 |
|---|---|---|---|
| V1 | 强调色 `#475569` 偏灰，`-foreground #94A3B8` 在深色下对比度低，激活态辨识弱 | Open WebUI/LibreChat 用一个明确品牌色承担「主操作 + 激活 + 链接」，并在深色下提高亮度 | 保留 slate 基调，提升 `--color-accent-foreground` 在暗色的亮度；激活态统一用 `accent-subtle` 背景 + `accent-foreground` 文字，禁止再用纯 `accent` 填充小块图标 |
| V2 | 深层表面 `surface-1..4` 色差小（#121318→#292c34），层次靠边框撑 | shadcn AI Chat 用 1-2 级表面 + 明确阴影区分层级 | 收敛为 3 级表面：page / surface-1（卡片）/ surface-2（内嵌），surface-3/4 仅用于 hover 与输入底；卡片一律 `surface-1 + border-subtle + shadow-panel` |
| V3 | 阴影偏重（`--shadow-lg` 为 `0 12px 28px -6px rgb(0 0 0/.5)`），深色下易糊 | assistant-ui 深色下几乎不用大阴影，靠表面差与 1px 边框 | 深色下把 `--shadow-lg/xl/elevated` 降一档；浮层（modal/sheet/dropdown）才用 `shadow-xl` |
| V4 | 圆角混用：`rounded-lg/xl/2xl/3xl` 与 `--radius-*` 并存，`ChatInterface.tsx:311,331` 用 `rounded-2xl` 超出 token 体系 | 对标产品统一圆角刻度（输入/卡片/浮层三级） | 统一：卡片 `radius-lg(12)`、输入与按钮 `radius-md(8)`、浮层 `radius-xl(16)`；清除组件内散落的 `rounded-2xl/3xl` 字面量 |
| V5 | `ChatInterface.tsx:149,194` 用 `from-violet-500 to-blue-500` 品牌渐变做头像，与克制的 slate 体系冲突 | 对标产品头像用中性面 + 语义色点 | 头像改为 `surface-2 + border-subtle`，用图标本身区分角色；移除紫色渐变 |
| V6 | `MessageContent` 头像尺寸 36px 与消息字号 14px 比例偏大 | LibreChat 头像 28-32px | 头像统一 32px，与 `--icon-lg` 对齐 |
| V7 | `index.css` 代码块背景 `#0D1117`（GitHub Dark）与页面 `#0d0e11` 几乎同色 | 对标产品代码块用比页面更亮或更暗的独立层 | 代码块背景改为 `--color-code-bg` 且与页面至少差 1 级明度，或加 1px 边框 + `surface-2` 底 |

### 维度二：布局与信息架构

| # | 现状 | 对标做法 | 建议 |
|---|---|---|---|
| L1 | `chat-container > div:first-child > div` 用 nth-child 结构选择器硬控宽度（`index.css:578-604`），脆弱 | 对标产品用语义容器类显式控制 | 用语义类（如 `.chat-empty`、`.chat-column`）替换所有 `:first-child` 结构选择器 |
| L2 | 消息列宽 `max-w-[85%]`（`ChatInterface.tsx:148,193,215,224`）与阶段 4.1 的 `max-w-4xl` 外框并存，双层约束 | 对标产品消息列固定内容宽（如 768px），头像列 + 内容列 | 统一为 `max-w-3xl(768px)` 内容列 + 用户气泡 `max-w-[80%]`，移除 85% 散落值 |
| L3 | ControlBar 单行横向滚动，25 项导航在侧栏长列表，无分组折叠 | CopilotKit/LibreChat 侧栏分组可折叠，ControlBar 只放高频项 | 侧栏三组可折叠并记忆状态；ControlBar 溢出项收进「更多」下拉，避免横向滚动发现性差 |
| L4 | 右栏固定 360px 且 tab 切换即开合（`ControlBar.tsx:109`），与专注模式叠加逻辑复杂 | 对标产品右栏为可切换面板，默认关闭 | 右栏默认关闭；用图标按钮显式开合，去掉「点同一 tab 才关闭」的隐式行为 |
| L5 | 空态文案硬编码中文（`ChatInterface.tsx:56-59`），与阶段 5 已收敛的 i18n 体系不一致 | 对标产品空态文案全部走 i18n | 空态标题/描述/建议全部键化，补 7 locale |
| L6 | 移动端 more sheet 为 2 列网格（`index.css:758-765`），项目多时需长滚动 | 对标产品移动导航分组 + 搜索 | more sheet 加分组标题；项数多时提供搜索框 |
| L7 | Token 进度条（`ControlBar.tsx:140`）用 `w-20 h-1` 极细，状态色用 `bg-blue-500/bg-amber-500` 字面量，未接语义 token | 对标产品用量指示接语义色 + tooltip | 改用 `--color-info`/`--color-warning`，并加 `title`/`aria-label` 展示 used/limit |

### 维度三：交互反馈

| # | 现状 | 对标做法 | 建议 |
|---|---|---|---|
| I1 | `ChatInterface.tsx:331` 发送按钮 `shadow-[#5E6AD2]/20` 硬编码紫色阴影，hover 增强，与 slate 体系冲突 | 对标产品主按钮用品牌色实底 + 无彩色阴影 | 发送按钮改 `bg-accent hover:bg-accent-hover`，移除彩色阴影 |
| I2 | 停止生成用 `<Square>`，但无 `aria-label` | 对标产品发送/停止按钮有明确 aria-label 与状态 | 发送/停止按钮加 `aria-label`，loading 时切换为停止并 `aria-busy` |
| I3 | 消息操作（复制/反馈/编辑）仅 hover 出现，键盘不可达 | assistant-ui 操作条 `focus-within` 可见 | `MessageActions` 容器加 `group-focus-within:opacity-100`，确保 Tab 可达 |
| I4 | 反馈 `submitFeedback` 失败仅 `console.error`（`ChatInterface.tsx:87`），用户无感知 | 对标产品用 toast 反馈成功/失败 | 接入统一 toast；成功后按钮置为已选态并禁用重复提交 |
| I5 | 工具调用 running 态用 `animate-pulse`，无进度语义 | CopilotKit 工具调用显示步骤与耗时 | ToolCallCard 增加「运行中」语义标签 + 已耗时，成功后展示耗时与可折叠结果 |
| I6 | 会话创建失败 `setCreateError`（`SessionSidebar.tsx:143`）为纯文本，无重试入口 | 对标产品错误态给重试按钮 | 错误态统一为「内联错误条 + 重试按钮」组件 |
| I7 | 权限请求批准/拒绝无 pending 反馈（`ChatInterface.tsx:69-79` 直接移除） | 对标产品批准后按钮进入 pending 再消失 | 批准/拒绝加 pending 与失败回滚 |
| I8 | 编辑消息保存即 `onSend`（`ChatInterface.tsx:114`），无确认与撤销 | 对标产品编辑后重发有明确提示 | 保存后展示「已重新发送」提示，并提供撤销入口 |
| I9 | `⌘K` 命令面板提示存在（`ChatInterface.tsx:317-322`），但未见全局快捷键注册 | 对标产品 ⌘K 全局可用 | 在应用壳层注册全局 ⌘K/Ctrl+K，避免仅输入框内提示 |

### 维度四：空态与加载态

| # | 现状 | 对标做法 | 建议 |
|---|---|---|---|
| E1 | 聊天空态为固定三条建议（`ChatInterface.tsx:59`），无角色区分 | 对标产品空态按场景给建议并支持点击填充 | 建议项可点击填入输入框；根据当前 Agent 能力动态生成 |
| E2 | 工具调用 loading 用 2 个 `animate-pulse` 块，无骨架结构 | 对标产品骨架屏还原真实行高 | 骨架按工具卡真实高度（图标 + 标题 + 一行）绘制 |
| E3 | `ReasoningPanel` 空态仅「暂无工具调用」两行文字 | 对标产品空态含图标 + 说明 + 引导操作 | 空态统一为 `EmptyState` 组件：图标 + 标题 + 说明 + 可选操作 |
| E4 | 页面级 `Suspense fallback={<PageFallback />}`（`App.tsx:151`）具体内容未统一 | 对标产品页面级骨架 | `PageFallback` 按页面类型给骨架（列表/表单/图表） |
| E5 | 会话列表无加载/空/错误三态区分 | 对标产品列表三态明确 | SessionSidebar 列表补 loading（骨架行）、empty（引导新建）、error（重试） |
| E6 | 流式输出仅光标 `animate-pulse`（`ChatInterface.tsx:15`），无「已停止」态 | 对标产品流式结束有明确收尾 | 流式结束移除光标并展示完成态；中断时展示「已停止」标签 |

### 维度五：动效

| # | 现状 | 对标做法 | 建议 |
|---|---|---|---|
| M1 | 全局过渡 `transition: all 280ms`（`index.css:217-222`）作用于 `.card`/`.sidebar`，`all` 易引发意外动画 | 对标产品只过渡具体属性 | 收窄为 `background-color/border-color/box-shadow/color/opacity` |
| M2 | 消息进入 `messageEnter` 8px 位移（`index.css:315`），历史消息重渲染会重复动画 | 对标产品只对新消息播放 | 仅对追加的最后一条消息播放进入动画 |
| M3 | 主题切换无过渡或全量过渡，切换时闪烁 | 对标产品主题切换 150-200ms 颜色过渡 | 在 `html` 上对 `background-color/color` 加 200ms 过渡，切换瞬间给 `data-theme-transition` 临时类 |
| M4 | 移动 sheet 无进入/退场动画（`AdaptiveMobileLayout.tsx:66` 直接条件渲染） | 对标产品 sheet 有遮罩淡入 + 面板上滑 | sheet 挂载时 `fadeIn` 遮罩、面板 `slideUp`；退场用状态延迟卸载 |
| M5 | `pageSlideIn` 页面切换动画（`index.css:786-788`）方向单一 | 对标产品按导航层级决定方向 | 前进/后退区分左右滑入 |
| M6 | `prefers-reduced-motion` 已有处理，但新增动效需继承 | 对标产品统一降级为无位移 | 所有新增位移/缩放动效统一在 reduced-motion 下降为 opacity |

---

## 第三部分 改造清单（P0/P1/P2）

### P0 —— 一致性硬伤与体系冲突（先做）

| 编号 | 文件 | 改动点 |
|---|---|---|
| P0-1 | `components/agent/ChatInterface.tsx:149,194` | 移除 `from-violet-500 to-blue-500` 头像渐变，改 `bg-[var(--color-bg-surface-2)] border border-[var(--color-border-subtle)]`，图标色 `text-[var(--color-text-secondary)]` |
| P0-2 | `components/agent/ChatInterface.tsx:331` | 发送按钮去掉 `shadow-[#5E6AD2]/20 hover:shadow-[#5E6AD2]/30`，改 `bg-[var(--color-accent)] hover:bg-[var(--color-accent-hover)]` |
| P0-3 | `components/agent/ChatInterface.tsx:311` | 输入框去掉 `focus:border-[#5E6AD2]/40`，改 `focus:border-[var(--color-border-accent)] focus:bg-[var(--color-bg-surface-2)]`；`rounded-2xl` → `rounded-[var(--radius-lg)]` |
| P0-4 | `index.css:217-222` | `.sidebar/.nav-menu/.card/.tool-call-card` 的 `transition: all 280ms` 收窄到具体属性 |
| P0-5 | `index.css:578-604` | 用语义类替换 `.chat-container > div:first-child ...` 结构选择器（需同步 `ChatInterface` 空态容器加类） |
| P0-6 | `components/agent/ChatInterface.tsx:56-59` | 空态文案与建议键化，补 7 locale |
| P0-7 | `components/workspace/ControlBar.tsx:140-146` | Token 进度色改 `var(--color-info)`/`var(--color-warning)`，加 `title` 展示 used/limit |
| P0-8 | `components/agent/ChatInterface.tsx:15` + 停止按钮 | 发送/停止按钮补 `aria-label` 与 `aria-busy`；流式结束移除光标并展示完成/停止态 |
| P0-9 | 全局 | 清除组件内残留的 `rounded-2xl/3xl`、`#5E6AD2`、`from-violet-500` 等字面量，统一走 token |

### P1 —— 体验与信息架构

| 编号 | 文件 | 改动点 |
|---|---|---|
| P1-1 | `App.tsx` 侧栏 nav | 三组（main/manage/config）可折叠 + 状态持久化到 localStorage |
| P1-2 | `components/workspace/ControlBar.tsx` | 溢出项收进「更多」下拉，替代横向滚动；右栏开合改显式按钮，移除「点同 tab 关闭」隐式逻辑 |
| P1-3 | `components/agent/ChatInterface.tsx:148,193,215,224` | 消息列统一 `max-w-3xl mx-auto` + 用户气泡 `max-w-[80%]` |
| P1-4 | `components/chat/MessageContent.tsx` / `MessageActions` | 操作条 `group-focus-within:opacity-100`；反馈失败接 toast，成功后置已选态 |
| P1-5 | `components/agent/ToolCallVisualization.tsx` | running 态加语义标签与已耗时；成功展示耗时与可折叠结果 |
| P1-6 | `components/workspace/SessionSidebar.tsx:143,157` | 创建/删除错误改内联错误条 + 重试按钮；列表补 loading/empty/error 三态 |
| P1-7 | `components/agent/FloatingPermissionDialog.tsx` | 批准/拒绝加 pending 与失败回滚 |
| P1-8 | `components/agent/ChatInterface.tsx:114` | 编辑保存后展示「已重新发送」提示 + 撤销入口 |
| P1-9 | `components/workspace/EmptyState.tsx` | 统一空态组件（图标 + 标题 + 说明 + 可选操作），替换 ReasoningPanel 等散落空态 |
| P1-10 | `components/agent/ChatInterface.tsx:317-322` + `App.tsx` | ⌘K/Ctrl+K 提升为应用壳全局快捷键 |
| P1-11 | `components/layout/AdaptiveMobileLayout.tsx:66` | more sheet 加分组标题；项多时加搜索 |
| P1-12 | `App.tsx:151` `PageFallback` | 按页面类型给骨架（列表/表单/图表） |

### P2 —— 打磨与动效

| 编号 | 文件 | 改动点 |
|---|---|---|
| P2-1 | `index.css` 消息动画 | `messageEnter` 只对追加的最后一条播放 |
| P2-2 | `index.css` / 主题切换 | `html` 加 200ms 颜色过渡 + 切换临时类，消除闪烁 |
| P2-3 | `index.css:740-747` | `.mobile-nav-sheet` 挂载 `slideUp` + 遮罩 `fadeIn`，退场延迟卸载 |
| P2-4 | `index.css:786-788` | `pageSlideIn` 按导航层级区分左右方向 |
| P2-5 | `index.css` 阴影 | 深色下 `--shadow-lg/xl/elevated` 降一档 |
| P2-6 | `index.css:803-809` `.code-block` | 背景与页面差 1 级明度或加边框 |
| P2-7 | `components/agent/ChatInterface.tsx` 空态建议 | 建议项可点击填入输入框；按 Agent 能力动态生成 |
| P2-8 | 全局 | 所有新增位移/缩放动效在 `prefers-reduced-motion` 下降为 opacity |

---

## 第四部分 具体样式与交互建议

### 4.1 配色层次

**表面（深色）**

| 层级 | Token | 用途 |
|---|---|---|
| L0 页面底 | `--color-bg-page` #0d0e11 | app-shell |
| L1 卡片/侧栏 | `--color-bg-surface-1` #121318 | card、session-sidebar、topbar |
| L2 内嵌/输入底 | `--color-bg-surface-2` #181a20 | 输入框底、内嵌块、hover 底 |
| L3 浮层 | `--color-bg-surface-3` #202229 | dropdown、popover |
| L4 浮层 hover | `--color-bg-surface-4` #292c34 | 浮层内 hover |

规则：卡片 = L1 + `border-subtle` + `shadow-panel`；浮层 = L3 + `border-default` + `shadow-lg`。L4 仅用于 hover，不作为静态背景。

**强调与语义**

- 主操作：`bg-accent` + `text-accent-text`，hover `bg-accent-hover`，禁止彩色阴影。
- 激活态（导航/tab）：`bg-accent-subtle` + `text-accent-foreground`，左侧或底部 2px `bg-accent` 指示条。
- 语义色仅用于状态：`success`（成功/已完成）、`warning`（用量告警/需注意）、`error`（失败）、`info`（中性信息/进度）。禁止用语义色做装饰。

**文本层次**

| Token | 用途 | 对比要求 |
|---|---|---|
| `text-primary` | 正文、标题 | 对 surface-1 ≥ 7:1 |
| `text-secondary` | 次要说明、标签 | ≥ 4.5:1 |
| `text-muted` | 元信息、时间、占位 | ≥ 3:1 |
| `text-disabled` | 禁用 | 仅禁用态 |

检查点：`--color-accent-foreground` #94A3B8 在 `surface-1` 上约 5.2:1，可作激活文字；若作正文需提升到 `text-secondary`。

### 4.2 间距与布局

- 间距只用 token：4 / 8 / 12 / 16 / 24 / 32（`--space-1..8`）。禁止 `p-[10px]` 类散值。
- 页面容器：`.page-container { width: min(100%, var(--content-max)); margin-inline: auto; padding: var(--page-gutter) }`，`--page-gutter: clamp(16px, 3vw, 32px)`。
- 消息列：内容区 `max-w-3xl(768px) mx-auto`；头像 32px；头像与内容间距 12px；消息间垂直间距 16px。
- 侧栏项：高 44px（`--control-height`），内边距 `8px 12px`，图标 16px，图标与文字间距 12px。
- 顶栏/ControlBar 高 52px（`--header-height`），横向内边距 12-20px。

### 4.3 圆角、阴影、边框

| 元素 | 圆角 | 阴影 | 边框 |
|---|---|---|---|
| 按钮/输入 | `--radius-md` 8px | 无 | `border-subtle`，hover `border-default` |
| 卡片 | `--radius-lg` 12px | `--shadow-panel` | `border-subtle` |
| 浮层（dropdown/modal/sheet） | `--radius-xl` 16px | `--shadow-lg`~`xl` | `border-default` |
| 头像/徽标 | `--radius-md` 8px | 无 | `border-subtle` |
| 代码块 | `--radius-lg` 12px | 无 | `--color-code-border` |

深色下阴影仅用于浮层；静态卡片靠边框与表面差区分。

### 4.4 交互状态

**hover**
- 可点区域：`background-color` 变 L2（`surface-2`），文字 `muted → secondary/primary`，150ms。
- 图标按钮：背景 `surface-2`，文字 `text-secondary`。
- 列表项：背景 `surface-2`，右侧操作图标淡入（`opacity 0 → 1`，150ms）。

**focus（键盘）**
- 统一使用全局 `:focus-visible`：`0 0 0 2px var(--color-bg-page), 0 0 0 4px var(--color-accent)`。
- 禁止 `outline: none` 且不补 ring。
- 浮层内首个可聚焦元素自动聚焦；`Escape` 关闭并焦点归位到触发元素。
- 面板分隔条：`focus-visible:bg-accent`，并支持方向键调整。

**active**
- 按钮按下：`transform: scale(0.98)`，100ms，`prefers-reduced-motion` 下取消缩放。
- 导航/tab：左侧或底部 2px `bg-accent` 指示条 + `bg-accent-subtle` 背景。

**disabled**
- `opacity: 0.4-0.5`，`cursor: not-allowed`，hover 背景不变，移出 tab 序列（`disabled` 或 `aria-disabled` + 阻止事件）。

**loading**
- 按钮内联 spinner（16px），保留原文字宽度避免跳动，`aria-busy="true"`。
- 流式：光标 2px `bg-accent` 闪烁；结束后移除光标，展示完成/停止态。

### 4.5 键盘可达性

| 场景 | 按键 | 行为 |
|---|---|---|
| 全局命令面板 | `⌘K` / `Ctrl+K` | 打开 `CommandPalette` |
| 全局搜索 | `⌘/` 或 `/`（非输入态） | 打开 `GlobalSearch` |
| 发送 | `Enter` | 发送 |
| 换行 | `Shift+Enter` | 输入换行 |
| 停止生成 | `Esc`（流式中） | 中断生成 |
| 专注模式 | `Esc` | 退出（输入焦点内不拦截，已在 `WorkspaceLayout.tsx:28` 实现） |
| 浮层 | `Escape` | 关闭并焦点归位 |
| 面板分隔条 | `←/→` | 调整宽度 |
| 侧栏导航 | `↑/↓` | 移动，`Enter` 进入 |
| 消息列表 | `Tab` | 操作按钮可见且可达（`group-focus-within`） |

补充要求：
- 所有图标按钮必须有 `aria-label`（当前 ControlBar 已具备，ChatInterface 发送/停止需补）。
- 动态内容（流式、工具调用、权限请求）使用 `aria-live="polite"`，错误用 `role="alert"`。
- 移动端触控目标不小于 44px（`--control-height`），已有 `.mobile-touch-target`。
- 跳转主内容链接（skip link）应指向 `#main-content`（移动端已有该 id，见 `AdaptiveMobileLayout.tsx:48`；桌面端需补）。

---

## 附录：落地顺序与验收

1. **P0 全部**：消除紫色字面量、结构选择器、transition all、i18n 硬编码、a11y 缺失。验收：全仓 `rg '#5E6AD2|from-violet|rounded-2xl|rounded-3xl'` 无命中；`tsc --noEmit` + `vitest` 全绿。
2. **P1 体验项**：折叠侧栏、ControlBar 溢出、消息列宽、三态、权限 pending、toast、⌘K 全局。
3. **P2 打磨**：动效方向与 reduced-motion、主题切换过渡、sheet 动画、阴影降档。

每阶段结束运行 `tsc --noEmit`、`vite build`、`vitest run`，并保持 7 locale JSON 合法。