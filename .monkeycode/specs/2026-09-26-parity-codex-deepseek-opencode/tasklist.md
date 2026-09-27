# 竞品对标实施状态（T1–T8 并发交付）

Feature Name: parity-codex-deepseek-opencode
Updated: 2026-09-26

色板基准：`.monkeycode/specs/2026-09-26-parity-codex-deepseek-opencode/benchmark.md`
唯一 token 源：`frontend-react/src/index.css`（Tailwind v4 `@theme` + `[data-theme="light"]` + `.high-contrast`）
约束：仅借鉴交互范式、语义角色与实测色值；不复制竞品源码、品牌资产、营销文案与 emoji；不改业务页面结构与真实数据流；颜色/间距/圆角/阴影/字号统一走 CSS token；保留工作树并行改动，不 commit、不 push、不回滚。

## 主色变更

| 阶段 | 变更前 | 变更后（深色 / 浅色） |
| --- | --- | --- |
| 主色 `--color-accent` | `#71809A` / `#475569` | `#5BC8D8` / `#1F7A8C` |
| 深色 page | — | `#20222E` |
| 深色 surface-1..4 | — | `#262938` / `#2A2D3E` / `#31354A` / `#3A3F57` |
| 浅色 page / surface-1..4 | — | `#F4F5F7` / `#FFFFFF` / `#ECEFF4` / `#E2E6EE` / `#D5DBE6` |

## 任务状态

- [x] **T1 共享色板基线** — 前置任务，先于 T2–T8 完成
  - 文件：`src/index.css`、`src/lib/parityPalette.ts`、`src/lib/__tests__/designTokens.test.ts`
  - 内容：深浅主题、accent、surface、文本、语义、syntax、diff token 全部落为声明值；provenance 记录竞品来源；designTokens 增补 syntax/diff 与 provenance 契约
  - 依赖关系：T2–T8 的唯一色值来源，色值改动必须先落 T1
- [x] **T2 品牌与应用图标** — 独立文件边界
  - 文件：`src/components/brand/ClimberMark.tsx`、`public/favicon.svg`、`public/icons.svg`、`public/icon-*.png`（72–512 共 12 尺寸）、`index.html`、`public/manifest.json`、`android/app/src/main/res/mipmap-*`
  - 内容：`CLIMBER_MARK` 作为几何唯一事实源；PNG 生成脚本从该常量读取坐标；PWA 背景 `#20222E`、主题色 `#5BC8D8`
  - 遗留处置：峰顶重复描边导致 PNG 鬼影已修复，192 parity guard 像素差异 `205 → 0`
- [x] **T3 语义图标体系** — 独立文件边界
  - 文件：`src/lib/icons.ts`、`src/components/ui/StatusIcon.tsx`、`src/lib/__tests__/designTokens.test.ts`
  - 内容：`StatusTone` 扩展为 8 态（error/success/warning/info/loading/queued/approval/unknown）；新增 `queued`=`Hourglass`、`approval`=`ShieldQuestion`；`TONE_GLYPH`/`TONE_TEXT`/`iconSize()`/`statusIconFor(null)` 统一
  - 范围收敛：未加入无 UI 消费点的 `task`/`tool`/`terminal`/`diff` 死导出
- [x] **T4 基础控件** — 独立文件边界
  - 文件：`Button`、`Badge`、`Input`、`Field`、`Label`、`Switch`、`Tabs`、`Progress`、`Skeleton`、`Helper`、`Card`、`PageHeader`
  - 内容：统一 accent 三态、surface、focus、disabled、loading、selected 与语义状态
- [x] **T5 叠加层与空态** — 独立文件边界
  - 文件：`Modal`、`Dropdown`、`EmptyState`、`ThemeToggle`
  - 内容：遮罩层级 token 化，移除 `Modal.tsx:165` 的 `backdrop-blur-sm` 字面类
- [x] **T6 图表** — 独立文件边界
  - 文件：`src/components/ui/Chart.tsx`、`src/components/ui/__tests__/chart-palette.test.tsx`
  - 内容：序列色/wash/grid/axis/tooltip/legend 全部走 token；6–8 色 palette；双主题对比度与 luminance band 断言
  - 关键结论：recharts 的 `Pie` 几何依赖真实 SVG 布局测量，jsdom 下扇区恒为空几何。饼图标签契约改为在 `pieLabel` 决策处做源码级断言，扇区描边由 token 源码断言覆盖。禁止为此重新导出 `pieLabel`（会触发 `only-export-components` 警告）
- [x] **T7 工具调用、审批、diff、tracing** — 独立文件边界
  - 文件：`src/components/agent/**`、`src/components/code/DiffPanel.tsx`、`src/components/tracing/**`
  - 内容：工具卡片使用 8 态 `StatusIcon`、syntax token、等宽工具名与状态 rail；diff 走 `--color-diff-*`；审批状态覆盖 pending/approving/denying/approved/denied/expired/error/unreported
  - 约束：未知状态独立表达为 `unknown`/"未上报"，禁止映射到成功或禁用
- [x] **T8 终端重构** — 独立文件边界
  - 文件：`src/components/terminal/TerminalPanel.tsx`、`src/components/terminal/__tests__/terminalPanel.test.tsx`
  - 内容：xterm canvas 主题不解析 `var()`，改用 `getComputedStyle(document.documentElement).getPropertyValue(...)` 解析 token，主题切换时重新应用
  - 治理：已从 style governance 例外白名单移除

## 验证结果

| 门禁 | 命令 | 结果 |
| --- | --- | --- |
| 类型检查 | `npm run typecheck` | 0 |
| Lint | `npm run lint` | 0 errors / 45 warnings（均为既有 `only-export-components` 类） |
| 构建 | `npm run build` | 0 |
| i18n | `npm run i18n:check` | 0（legacy drift 为既有告警） |
| 空白检查 | `git diff --check` | 0 |
| 目标测试套件 | `npx vitest run src/lib/__tests__ src/components/ui/__tests__ src/components/brand src/components/terminal src/components/agent src/components/code src/components/tracing` | 24 文件 / 333 测试全通过 |

## 治理例外白名单

style governance 当前仅剩两处，均为有说明的非样式例外：

- `src/styles/rtl.css`
- `src/lib/parityPalette.ts`（故意以 hex 记录 provenance，不参与 UI 样式）

## 尚未完成

- 深色/浅色主题 × 375 / 390 / 768 / 1024 / 1440 宽度的视觉验收
- 导航、资源卡、工具活动中的页面级零散图标迁移
- 全量 Vitest 与历史失败用例的单独定位
- Playwright/Axe 视觉回归（既有环境问题：Agent CRUD `429`、Settings 页面加载超时、Vite error overlay）
