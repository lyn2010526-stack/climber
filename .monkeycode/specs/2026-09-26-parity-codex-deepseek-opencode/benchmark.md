# 竞品对标：Codex / DeepSeek / OpenCode

本文件是本次 UI 对标的唯一事实来源。8 个子任务全部引用这里的色值、角色与门禁规则，禁止各自发挥。

## 1. 实测竞品色板

三家色值取自公开主题文件（OpenCode 官方 `theme.json` 规范、Codex CLI 实际界面取色、社区按 Codex 界面逐色对齐的复刻主题、DeepSeek 主题清单）。

### Codex CLI

| 角色 | Hex |
| --- | --- |
| Background | `#20222E` |
| Panel / status line | `#262938` |
| Message bubble | `#2A2D3E` |
| Border | `#34374A` |
| Text | `#C9CCD6` |
| Bright text / heading | `#E9EBF0` |
| Accent（链接、内联代码） | `#5BC8D8` |
| Keyword / success | `#7EC97E` |
| Error | `#E07A72` |
| Warning / dirty git | `#D9B26A` |
| Strings | `#8FB8E8` |
| Numbers | `#82A8E0` |
| Muted | `#8A8FA3` |

### OpenCode（官方主题 token 规范）

| 角色 | Hex |
| --- | --- |
| background | `#2E3440` |
| backgroundPanel / backgroundElement | `#3B4252` |
| border / borderSubtle | `#434C5E` |
| borderActive / textMuted | `#4C566A` |
| text | `#D8DEE9` |
| textMuted 浅色侧 | `#E5E9F0` |
| background 浅色侧 | `#ECEFF4` |
| accent | `#8FBCBB` |
| primary | `#88C0D0` |
| secondary | `#81A1C1` |
| primary 浅色侧 | `#5E81AC` |
| error | `#BF616A` |
| warning | `#D08770` |
| success | `#A3BE8C` |
| 语法辅助 | `#EBCB8B`、`#B48EAD` |

OpenCode 官方把主题 token 拆成这些语义角色，Climber 直接沿用这套**角色命名**（不含 Nord 品牌名）：
`primary` / `secondary` / `accent` / `error` / `warning` / `success` / `info` / `text` / `textMuted` / `background` / `backgroundPanel` / `backgroundElement` / `border` / `borderActive` / `borderSubtle` / `diffAdded` / `diffRemoved` / `diffContext` / `diffHunkHeader` / `diffAddedBg` / `diffRemovedBg` / `markdownHeading` / `markdownLink` / `markdownCode` / `syntaxComment` / `syntaxKeyword` / `syntaxFunction` / `syntaxString` / `syntaxNumber` / `syntaxType` / `syntaxVariable` / `syntaxOperator` / `syntaxPunctuation`。

### DeepSeek

DeepSeek 主题可配置，公开可选主题为 `dark`（默认）、`light`、`nord`、`dracula`、`monokai`、`one-dark`、`tokyo-night`，并支持 `DEEPSEEKCODE_THEME_COLORS` 做局部覆盖。

结论：DeepSeek 的可对标部分是**主题角色可覆盖机制**与**单一焦点输入区**，色值取 `nord`（与 OpenCode 同源）。Climber 已有的深浅双主题 + 单一 token 源正是这套机制，`--accent` 三态（hover / active / subtle）对应 DeepSeek 的局部覆盖能力，无需改造。

## 2. Climber 目标色板

以 Codex 为底（它最贴近我们的 Agent 工作台场景），把 OpenCode 的角色粒度补进来。主色从当前中性 slate 切到 Codex 的 teal 系，这是本次唯一一次主色变更。

### 深色（默认）

| Token | Hex | 来源 |
| --- | --- | --- |
| `--color-bg-page` | `#20222E` | Codex background |
| `--color-bg-surface-1` | `#262938` | Codex panel |
| `--color-bg-surface-2` | `#2A2D3E` | Codex message bubble |
| `--color-bg-surface-3` | `#31354A` | Codex bubble 提亮 |
| `--color-bg-surface-4` | `#3A3F57` | Codex border 提亮 |
| `--color-text-primary` | `#E9EBF0` | Codex bright text |
| `--color-text-secondary` | `#C9CCD6` | Codex text |
| `--color-text-muted` | `#8A8FA3` | Codex muted |
| `--color-text-disabled` | `#6C7182` | muted 压暗 |
| `--color-accent` | `#5BC8D8` | Codex accent |
| `--color-accent-hover` | `#79D6E3` | accent 提亮 |
| `--color-accent-active` | `#3FA9BA` | accent 压暗 |
| `--color-accent-foreground` | `#8FDCEC` | accent 底上的文字图标 |
| `--color-success` | `#7EC97E` | Codex success |
| `--color-warning` | `#D9B26A` | Codex warning |
| `--color-error` | `#E07A72` | Codex error |
| `--color-info` | `#8FB8E8` | Codex strings |
| `--color-unknown` | `#8A8FA3` | Codex muted，独立语义 |
| `--color-border-subtle` | `rgba(233, 235, 240, 0.08)` | 比 Codex border 更弱，只做分隔 |
| `--color-border-default` | `#34374A` | Codex border |
| `--color-border-strong` | `#4A4F66` | Codex border 提亮 |
| `--color-border-accent` | `#5BC8D8` | accent |

### 浅色

| Token | Hex | 来源 |
| --- | --- | --- |
| `--color-bg-page` | `#F4F5F7` | Nord 浅色底 |
| `--color-bg-surface-1` | `#FFFFFF` | OpenCode light text |
| `--color-bg-surface-2` | `#ECEFF4` | Nord nord6 |
| `--color-bg-surface-3` | `#E2E6EE` | Nord nord6 压深 |
| `--color-bg-surface-4` | `#D5DBE6` | Nord nord5 |
| `--color-text-primary` | `#2E3440` | Nord nord0 |
| `--color-text-secondary` | `#3B4252` | Nord nord1 |
| `--color-text-muted` | `#4C566A` | Nord nord3 |
| `--color-text-disabled` | `#7B8496` | nord3 提亮 |
| `--color-accent` | `#1F7A8C` | Codex accent 压到浅底 4.6:1 |
| `--color-accent-hover` | `#18606E` | accent 压暗 |
| `--color-accent-active` | `#134B57` | accent 最深 |
| `--color-accent-foreground` | `#12545F` | 浅底上的 accent 文字 |
| `--color-accent-text` | `#FFFFFF` | accent 填充上的文字 |
| `--color-success` | `#3F7A4E` | Codex success 压深 |
| `--color-warning` | `#8A6520` | Codex warning 压深 |
| `--color-error` | `#B3453D` | Codex error 压深 |
| `--color-info` | `#3F6E9E` | Codex strings 压深 |
| `--color-unknown` | `#6B7484` | 独立语义 |
| `--color-border-default` | `#D5DBE6` | Nord nord5 |
| `--color-border-strong` | `#AEB7C6` | nord5 压深 |
| `--color-border-accent` | `#1F7A8C` | accent |

### 语法与 diff（新增，取自 OpenCode 角色表 + Codex 实测）

| Token | 深色 | 用途 |
| --- | --- | --- |
| `--color-syntax-comment` | `#6C7182` | 注释 |
| `--color-syntax-keyword` | `#7EC97E` | 关键字 |
| `--color-syntax-function` | `#5BC8D8` | 函数名 |
| `--color-syntax-string` | `#8FB8E8` | 字符串 |
| `--color-syntax-number` | `#82A8E0` | 数字 |
| `--color-syntax-type` | `#B48EAD` | 类型 |
| `--color-syntax-operator` | `#C9CCD6` | 运算符 |
| `--color-diff-added` | `#7EC97E` | 新增行 |
| `--color-diff-removed` | `#E07A72` | 删除行 |
| `--color-diff-hunk` | `#5BC8D8` | hunk 头 |
| `--color-diff-added-bg` | `rgba(126, 201, 126, 0.12)` | 新增底 |
| `--color-diff-removed-bg` | `rgba(224, 122, 114, 0.12)` | 删除底 |

## 3. 门禁规则

`src/lib/__tests__/styleGovernance.test.ts` 是自动门禁，8 个子任务共同遵守：

1. 颜色一律 `var(--color-*)`。
2. 间距 `--space-*`、圆角 `--radius-*`、阴影 `--shadow-*`、字号 `--text-*`。
3. 禁止 Tailwind 调色板工具类。
4. 禁止 token 命名空间外的新 CSS 变量。
5. 白名单只有 `terminal/TerminalPanel.tsx`（xterm 自带主题）与 `styles/rtl.css`（`var()` 兜底值）。

## 4. 子任务边界

| 子任务 | 负责文件 | 禁止触碰 |
| --- | --- | --- |
| T1 共享基线 | `src/index.css`、`src/lib/parityPalette.ts`、`src/lib/__tests__/*` | 任何组件与页面 |
| T2 品牌图标 | `src/components/brand/**`、`public/favicon.svg`、`public/icons.svg` | `src/index.css`、`src/lib/icons.ts` |
| T3 图标体系 | `src/lib/icons.ts`、`src/components/ui/StatusIcon.tsx` | `src/index.css`、品牌图标、页面 |
| T4 基础控件 | `src/components/ui/Button.tsx`、`Badge.tsx`、`Input.tsx`、`Field.tsx`、`Label.tsx`、`Switch.tsx`、`Tabs.tsx`、`Progress.tsx`、`Skeleton.tsx`、`Helper.tsx`、`Card.tsx`、`PageHeader.tsx` | 页面、图表、diff、工具调用、终端 |
| T5 叠加层 | `src/components/ui/Modal.tsx`、`Dropdown.tsx`、`EmptyState.tsx`、`ThemeToggle.tsx` | 页面、图表、diff、工具调用 |
| T6 图表 | `src/components/ui/Chart.tsx` 及图表相关 | 其他所有 |
| T7 工具与 diff | `src/components/agent/**`、`src/components/code/DiffPanel.tsx`、`src/components/tracing/**` | 页面、`src/components/ui/**` |
| T8 终端 | `src/components/terminal/TerminalPanel.tsx` | 其他所有 |

## 5. 并行执行约束

- T1 必须最先完成，其余 7 个任务在其产出的 token 落地后才能开工。
- T2 到 T8 之间文件互斥，可完全并行。
- 任一子任务都不得改动真实 API、数据流、业务逻辑或后端。
- 任一子任务都不得 commit 或 push。
