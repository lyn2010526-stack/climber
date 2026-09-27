# 设计系统与图标重设计实施计划

Feature Name: design-system-and-icon-redesign
Updated: 2026-09-26

基线：`frontend-react` 当前工作树（Tailwind v4 `@theme`、Radix、CVA、lucide-react、Inter Variable、JetBrains Mono）。
范围：仅设计系统层与图标层，不改业务页面结构、不改真实数据流、不复制竞品源码与品牌资产。

视觉方向：Slate Operator（冷 slate 蓝灰 + 中性深色工作台）。主色 `#71809A`。
参考语言：Codex（执行与审批）、OpenCode（终端工作台）、DeepSeek（干净对话与模型标签）、Hermes 类 Agent 工作台（工具、任务、日志关系）。
唯一 token 源：`frontend-react/src/index.css` 的 `@theme` + `[data-theme="light"]`。
唯一图标源：`frontend-react/src/lib/icons.ts` 与 `frontend-react/src/components/brand/ClimberMark.tsx`。

## 阶段 0 —— 事实与约束（已完成核实）

- [x] 0.1 核实 token 唯一源：Tailwind v4 `@theme` 位于 `src/index.css:24-212`，浅色主题覆盖在 `[data-theme="light"]`（`src/index.css:245-286`）
- [x] 0.2 核实已存在浅色映射：主色 `--color-accent` 浅色为 `#475569`，深色为 `#79879B`，符合冷 slate 蓝灰方向，无需引入第二套主题体系
- [x] 0.3 核实组件库：Radix（Dialog/Dropdown/Popover/Select/Switch/Tabs/Tooltip/ScrollArea）+ CVA + lucide-react + sonner + vaul，无第二套 UI 库需要治理
- [x] 0.4 核实品牌图标唯一实现：`src/components/brand/ClimberMark.tsx`（polyline 攀登折线 + rect 峰顶），消费点 `App.tsx:171` 与 `AdaptiveMobileLayout.tsx:193`
- [x] 0.5 核实语义图标唯一源：`src/lib/icons.ts` 已定义 `iconSizes` 四级阶梯与 `icons` 语义映射，已包含 `StatusTone`（error/success/loading）
- [x] 0.6 核实 Agent 身份已收敛为单色 slate（`src/components/agents/agentVisualIdentity.ts:20` `AGENT_IDENTITY_PALETTE`）
- [x] 0.7 核实 token 契约测试入口：`src/components/ui/__tests__/presentation-contract.test.tsx:21` 与 `control-foundation.test.tsx:122` 通过 `readFileSync(src/index.css)` 校验 token
- [x] 0.8 核实工作树含 181 个文件的并行重构改动，本规格不执行回滚与清理

## 阶段 1 —— 视觉基线与方向

- [x] 1.1 记录 Codex 界面语言：任务执行状态、代码变更审查、审批确认、后台运行反馈、队列与评审入口
- [x] 1.2 记录 OpenCode 界面语言：终端工作台密度、等宽字体、窄侧栏、命令入口、分栏面板、低装饰
- [x] 1.3 记录 DeepSeek 界面语言：干净对话区、单一输入焦点、少量高辨识度主色、模型与推理模式标签
- [x] 1.4 记录 Hermes 类 Agent 工作台语言：Agent/工具/任务/日志关系、工具调用、审批、失败、重试、未上报状态
- [x] 1.5 融合为 Slate Operator 原则：深色优先、中性 surface、单一 slate 主色、边框承担结构、阴影只表达层级、无渐变无玻璃光晕、无营销文案、无 emoji
- [x] 1.6 判定可借鉴范围：仅交互范式与信息架构，禁止复制竞品源码、图标、品牌资产与营销文案

## 阶段 2 —— 主色与色彩体系

- [x] 2.1 确定唯一主色 `--color-accent` 深色为 `#71809A`、浅色为 `#475569`，作为全局交互主色
- [x] 2.2 推导主色六角色：`accent`（填充，3:1）、`accent-hover`、`accent-active`、`accent-subtle`（选中底）、`accent-foreground`（文字与图标，4.5:1）、`accent-text`（主色填充上的文字）
- [x] 2.3 推导文本五级：primary `#F1F3F6`、secondary `#D0D5DE`、muted `#A6AFBC`、disabled `#727B88`、inverse，用于标题、正文、辅助、禁用、浅色填充文字
- [x] 2.4 推导语义色与浅底：success `#69C593`、warning `#E4B35E`、error `#F18D87`、info `#87B1E4`、`unknown` 复用 muted 体系独立语义
- [x] 2.5 推导边框四级：subtle、default、strong、accent，其中 subtle 低于 3:1 用于分隔，default 与以上用于控件边界
- [x] 2.6 推导 surface 五级：`bg-page`、surface-1、surface-2、surface-3、surface-4，表达 page/panel/hover/elevated/pressed
- [x] 2.7 固化「未上报」独立语义：使用 muted 背景与 muted 文字，标签文案为 "Not reported"，禁止映射到 success 或 disabled

## 阶段 3 —— 字号、间距、圆角、阴影调性

- [x] 3.1 固化字体职责：Inter Variable 用于界面文字，JetBrains Mono 用于代码、路径、任务 ID、日志
- [x] 3.2 固化字号阶梯：2xs `0.6875rem`、xs `0.75rem`、sm `0.875rem`、base `1rem`、lg `1.125rem`、xl `1.25rem`、2xl `1.5rem`
- [x] 3.3 固化字重边界：400 正文、500 控件与标签、600 标题与状态、700 仅关键页面标题
- [x] 3.4 固化 4px 间距网格：space-1 `0.25rem` 到 space-12 `3rem`，工具栏 8px、列表项 12–16px、页面区块 24–32px
- [x] 3.5 固化轻圆角：xs 4px、sm 6px、md 8px、lg 12px、xl 16px、pill 999px，胶囊仅用于状态与筛选
- [x] 3.6 固化阴影用途：xs/sm 用于面板，md/lg 用于弹层，xl 用于对话框，阴影仅使用黑色透明度，禁止彩色光晕
- [x] 3.7 固化焦点与动效统一值：`--focus-ring`、offset `2px`、transition 100/150/200/300/500ms 配 `ease-out` 与 `ease-spring`

## 阶段 4 —— 统一设计 token 实施

- [x] 4.1 以 `src/index.css` `@theme` 为唯一源，将颜色、字号、间距、圆角、阴影、动效、焦点、z-index 按区块重新分组并补齐注释边界
- [x] 4.2 补齐缺失状态 token：`--color-accent-active`、`--color-accent-subtle` 双主题、border-accent 双主题、`--color-unknown` 配色位
- [x] 4.3 补齐 `--text-2xs` 与 `--radius-xs`、`--radius-pill`、图标尺度的注释与值
- [x] 4.4 保留 `:root` 旧变量别名层（`src/index.css:219-240`）跟随主题自动切换
- [x] 4.5 保留 `[data-theme="light"]` 作为浅色唯一覆盖点，与深色默认值构成 1:1 映射
- [x] 4.6 记录必须继续使用 `var(--color-*)` 的证据，页面与组件不写颜色字面值
- [x] 4.7 编写 token 结构契约测试：深色与浅色 1:1 映射、必需 token 存在、状态 token 完整（`src/lib/__tests__/designTokens.test.ts`，9 项通过）

## 阶段 5 —— 组件主题桥接

- [x] 5.1 核实 Radix 各部件样式入口均通过 `className`/`data-state` 消费全局 token，禁用分量级色彩定义
- [x] 5.2 核实 CVA 变体定义与全局 token 对齐，Button/Badge/Input/Tabs/Modal/Panel 的变体名保持稳定
- [x] 5.3 核实第三方视觉输入（xterm、Monaco、recharts、MonacEditor、xyflow）已通过既有 token 或自有主题配置接入
- [x] 5.4 记录禁止项：新增页面级硬编码颜色、圆角、阴影、间距，或引入第二套 CSS 变量命名体系
- [x] 5.5 编写 component-variant 契约测试：`shared-controls.test.tsx` 断言 `icons` 全部语义名在 `components/ui` 内被真实消费（7 项通过）

## 阶段 6 —— 组件语义状态规范

- [x] 6.1 规范 Button 状态矩阵：primary/secondary/ghost/danger/quiet 变体 × hover/active/focus-visible/selected/disabled/loading
- [x] 6.2 规范 Badge 状态矩阵：neutral、selected、success、warning、error、info、unknown，unknown 与 disabled 视觉可区分
- [x] 6.3 规范 Tag/Chip/Badge 语义边界：Tag 分类属性、Chip 可交互筛选、Badge 数量与状态提醒
- [x] 6.4 规范 Tabs 状态：默认、hover、`aria-selected`、焦点、禁用；视觉选中态用 accent-subtle + accent-foreground
- [x] 6.5 规范 Input/Field 状态：默认、hover、focus-visible、invalid、disabled、placeholder 用 muted

- [x] 6.6 规范 Panel/Modal 状态：default、elevated、overlay、backdrop；禁止使用渐变或光晕
- [x] 6.7 规范状态与 ARIA 对应：`aria-selected` 同步视觉选中、`aria-busy` 同步 loading、`aria-disabled` 同步禁用
- [x] 6.8 编写组件状态覆盖测试：`shared-controls`、`control-foundation`、`control-restraint`、`presentation-contract`、`accessibility-polish` 共 59 项通过
- [x] 6.9 状态色对齐：`rightPanel/statusTone.ts` 新增 `unknown` 色调，后端未声明的状态改用 `--color-unknown` 而非借用 idle

## 阶段 7 —— 图标系统重设计

- [x] 7.1 定义图标设计语言：单一 24×24 网格、2px 描边、圆头圆角、`currentColor` 继承、无渐变无填充装饰
- [x] 7.2 固化图标尺寸阶梯：`iconSizes` 仅保留 xs 12、sm 14、md 16、lg 20 四级，与 `--icon-*` token 对齐
- [x] 7.3 重设计 `ClimberMark` 品牌图标：改为等宽线宽、`currentColor` 默认、保留 24 视窗与折线加峰顶语义
- [x] 7.4 扩展 `src/lib/icons.ts` 语义映射：新增 `warning`、`info`、`unknown`（`CircleDashed`，与 loading/failure 可区分）
- [x] 7.5 扩展 `StatusTone` 为 error/success/warning/info/loading/unknown 六态，`statusIcon` 改为 `Record` 全覆盖，新增 `src/components/ui/StatusIcon.tsx` 作为唯一 tone→glyph 渲染入口
- [ ] 7.6 收拢页面内零散图标用法：导航、资源卡、状态点、工具活动统一引用 `lib/icons.ts` 语义名（属页面级改造，本轮按“先不写页面”约束保留为待办）
- [x] 7.7 保留 lucide-react 为图标来源，Climber 自绘图标仅限品牌标记与产品特有符号
- [x] 7.8 编写图标契约测试：四级尺寸阶梯、六态映射、unknown 与 loading/error 可区分、无 tone 时不渲染图标（`designTokens.test.ts`）
- [x] 7.9 `EmptyState` 新增 `warning` 与 `unreported` 图标选项，承接共享 StatusIcon，避免出现无消费者的图标导出

## 阶段 8 —— 样式治理与验证

- [x] 8.1 核实 `src/index.css` 为唯一 token 源，`@theme` 与 `[data-theme="light"]` 构成深浅双主题 1:1 映射
- [x] 8.2 记录硬编码治理规则：页面与组件禁止写颜色、圆角、阴影、间距字面值，统一读 `var(--color-*)` 与 `--space-*`、`--radius-*`、`--shadow-*`
- [x] 8.3 记录允许例外：SVG 图表、Monaco、xterm、recharts、xyflow 等第三方内部样式
- [x] 8.4 核实既有 token 契约测试入口：`presentation-contract.test.tsx` 与 `control-foundation.test.tsx` 已用 `readFileSync(src/index.css)` 校验
- [x] 8.5 执行验证：`npm run typecheck` 退出码 0；`npm run lint` 0 errors / 47 warnings（均为既有告警）；`npm run i18n:check` 全语言完整；`git diff --check` 退出码 0
- [x] 8.6 编写治理门禁测试 `src/lib/__tests__/styleGovernance.test.ts`（5 项通过）：扫描生产代码，拦截未声明 token 引用、Tailwind 调色板工具类、hex/rgb 字面值、token 命名空间外的 CSS 变量；白名单仅 `terminal/TerminalPanel.tsx`（xterm 自带主题）与 `styles/rtl.css`（var 兜底值）
- [x] 8.6.1 门禁首次运行即暴露 5 处失效 token（`--color-bg-secondary`、`--color-bg-primary`、`--color-text-error`、`--color-bg-deep`、`--color-error-hover`），已改写为规范 token；`IOSToast` 的圆角/字号/内边距/阴影改读 `var(--radius-lg)`、`var(--text-sm)`、`var(--space-3) var(--space-4)`、`var(--shadow-lg)`
- [x] 8.7 执行 `npm run build`：退出码 0，`✓ built in 4.00s`，最大产物 `index-DwEmiNmT.js` 472.97 kB（gzip 148.88 kB）

## 阶段 9 —— 收尾

- [x] 9.1 同步本规格进度并记录真实命令、退出码与测试数量（见下方「验证记录」）
- [x] 9.2 记录后续页面级重构的 token 消费约束（见下方「页面级改造约束」）
- [x] 9.3 确认品牌图标与语义图标在深色、浅色主题下的渲染一致性：两者均只用 `currentColor`，颜色由消费方 token 决定，故主题切换无需改图标本身；`ClimberMark.test.tsx` 与 `designTokens.test.ts` 共同锁定该契约

## 验证记录

| 命令 | 结果 |
| --- | --- |
| `npx vitest run src/lib/__tests__ src/components/brand/__tests__/ClimberMark.test.tsx src/components/ui/__tests__` | 9 文件 / 102 测试通过 |
| `npm run typecheck` | 退出码 0 |
| `npm run lint` | 0 errors / 47 warnings（既有告警） |
| `npm run build` | 退出码 0 |
| `npm run i18n:check` | 全语言翻译完整 |
| `git diff --check` | 退出码 0 |

## 页面级改造约束

后续任何页面或组件改动必须满足 `src/lib/__tests__/styleGovernance.test.ts` 的四条规则：

1. 颜色一律 `var(--color-*)`；新增语义色先在 `src/index.css` 的 `@theme` 与 `[data-theme="light"]` 同时落位。
2. 间距用 `--space-*`，圆角用 `--radius-*`，阴影用 `--shadow-*`，字号用 `--text-*`。
3. 禁止 Tailwind 调色板工具类（`bg-blue-600`、`text-gray-400` 等），它们绕过 token 层。
4. 禁止在 token 命名空间之外新增 CSS 变量；组件私有变量只允许用 Tailwind 任意属性 `[--name:value]` 在自身作用域声明。

唯一白名单是第三方自带主题：`terminal/TerminalPanel.tsx`（xterm 终端配色）与 `styles/rtl.css`（`var()` 兜底值）。新增例外必须先在本规格登记原因。

## 遗留项

- 7.6 页面内零散图标用法收拢：属页面级改造，按本轮「先不写页面」约束保留待办。
- 全量 Vitest 仍有既有失败（协作标题、阅读宽度、集群成员、RightPanel 持久化），与本规格无关，需单独处理。
