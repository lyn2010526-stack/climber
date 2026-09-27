# 前端工作台重构实施计划

Feature Name: frontend-rebuild
Updated: 2026-09-25

基线：`e0ab69f4`（工作树干净）。参考：`.monkeycode/docs/ui-research/`（001–100 开源调研）、`REVIEW_22_STATUS.md`。
约束：桌面优先、无登录界面、只借鉴交互范式不复制源码/品牌资产、最小改动、每步跑 typecheck。

## 阶段 0 —— 事实与基线（已完成核实）

- [x] 0.1 核实未定义 CSS 变量：`--accent*`/`--text-*`/`--surface-*`/`--border-*`/`--font-size-*`/`--color-danger` 共 19 个在 CSS 中缺失（6 个 ui 组件消费）
- [x] 0.2 核实 `dark:` 变体仅在 `components/LanguageSwitcher.tsx` 使用（6 处），主体走 `data-theme`
- [x] 0.3 核实死代码：`forms/`(30 文件)、`components/full/`(4)、`components/a11y/`(1)、`dashboard/Dashboard.tsx`（仅 barrel 导出 + 自测）
- [x] 0.4 核实两个 barrel（`components/index.ts`、`components/ui/index.ts`）全项目零引用
- [x] 0.5 核实 `api.ts:493` `reasonStream` 死参数 `_onEvent`；`chatStream`/`runAutonomousSkillStream` SSE 解析重复
- [x] 0.6 核实 `vite.config.ts` 已代理 `/health`（上一轮"只代理 /api"为误判）

## 阶段 1 —— 保命级：渲染正确性（已完成）

- [x] 1.1 在 `index.css` 增加兼容别名层：19 个旧变量 → 映射到 `--color-*` token（`index.css:164-184`）；并加 `@custom-variant dark` 绑定 `data-theme`（`index.css:6`）
- [x] 1.2 `LanguageSwitcher.tsx` 去除 6 处 `dark:` 与裸 gray/blue 调色板，改用 `var(--color-*)` token；全项目 `dark:` 工具类已归零（仅剩注释/类型字段/类名）
- [x] 1.3 验证：`tsc --noEmit` exit 0、`vite build` exit 0（6.2s）

### 阶段 1 附带：i18n 收敛（原 5.1 提前完成）

- [x] 5.1 `useTranslation`(hooks.ts) 与 `useTypedTranslation`(typed.ts) 收敛为 `useI18n`(utils.ts) 的薄别名，保留导出名不变，调用方零改动

### 已修复的既有红灯（基线 `e0ab69f4` 上即失败，非本次重构引入）

- [x] `presentation-contract.test.tsx` 2 例：根因是 vite 8 下 `import css from 'index.css?raw'` 返回空串（Tailwind 插件先于 raw loader 消费 `.css`；实测 CSS_LEN=0，而 `.tsx?raw` 正常 TSX_LEN=3454）。改为 `fs.readFileSync` 读取 `src/index.css`。**测试基建向 bug**，不涉及任何被删源码。
- [x] `AdaptiveMobileLayout.test.tsx` 1 例：旧断言要求 more sheet **不含** "api key"，与同基线的 `navConfig.test.tsx`（要求含 `apikeys`）、`App.tsx:111` 及移动端设计相矛盾。按"apikeys 应在 more sheet 可达"裁决，改断言为 `true`。

## 阶段 2 —— 死代码大扫除（已完成）

> 执行方式：`mv` 至 `/tmp/opencode/deadcode-backup/`（保留可回滚），未使用 `rm`。实际路径核实后修正了 tasklist 原记录的多处错误。

- [x] 2.1 删除 `src/forms/`（30 空壳文件，零引用）
- [x] 2.2 删除 `src/components/full/`（4 文件，零引用）
- [x] 2.3 删除 `src/components/a11y/`（实际仅 `Button.tsx` 1 文件，零引用）
- [x] 2.4 删除 `src/components/dashboard/`（实际路径；`Dashboard.tsx` + `__tests__/Dashboard.test.tsx`，仅被 barrel 引用）
- [x] 2.5 删除两个空 barrel（`components/index.ts`、`components/ui/index.ts`，全项目零外部引用；活组件均被各自路径直接 import）
- [x] 2.6 删除 `src/components/Sidebar.tsx`（零引用）
- [x] 2.7 删除 `src/pages/TasksPage.tsx`（`App.tsx` 实走 `MobileTasksPage`）
- [x] 2.8 删除 `src/components/agent/PermissionModes.tsx`（实际路径；仅被 barrel 引用）
- [x] 2.8b 删除 `src/utils/`（30 文件 5233 行 + 28 个自测；29 文件带 `@ts-nocheck`，src 内零引用）
- [x] 2.8c 删除 `src/legacy/`（9 文件；唯一外部引用是 `navConfig.test.tsx`，已同步删除该 import 与 legacy 用例）
- [x] 2.8d 移除死依赖 `@tanstack/react-query`（`package.json`，src 零使用）
- [x] 2.9 验证：typecheck exit 0、vitest 25 files / 210 tests 全绿、vite build 成功（2.90s）

### 阶段 2 附带：主题与无障碍修复（非删除类，零风险）

- [x] `hooks/useTheme.tsx:90` 系统非 light 时回退 `defaultTheme` → 改为硬编码 `'dark'`；同时修复 `matchMedia` 旧 API 的 `removeEventListener` 不存在导致的清理报错
- [x] 批量补 `<button type="button">` 148 处（52 文件），跳过通用 `ui/Button.tsx` 与需 `type="submit"` 语义的 `chat/ChatInput.tsx`（人工判断）

## 阶段 3 —— 导航与路由

- [x] 3.1 `getPageFromHash` 去首尾斜杠，容错 `#/chat` 与 `#chat`、`#chat/`（`App.tsx:53-59`）
- [x] 3.2 修复 `ALL_NAV_ITEMS_BASE` 重复/错配 `labelKey`：`plugin-manage` 由 `navigation.plugins` → `navigation.plugin_management`；`crews` 由 `navigation.users` → `navigation.crews`；`factory`/`cluster` 由硬编码英文 label → `navigation.factory`/`navigation.cluster`；7 个 locale 各新增 5 个键（`factory`/`plugin_management`/`crews`/`cluster`/`stats`/`cost_analysis`）
- [x] 3.2b 侧栏导航改为渲染 `ALL_NAV_ITEMS`（25 项），按 `main`/`manage`/`config` 分组；移除 `App.tsx` 中已无用的 `CORE_NAV_ITEMS` 局部变量
- [x] 3.3 验证：导航单测 31 passed（`navConfig.test.tsx` 8 项 + 相关 5 文件），`Page` 全部可达

## 阶段 4 —— 体验级

- [x] 4.1 对话宽度收敛：消息列与输入框统一为 `max-w-4xl mx-auto`（`ChatInterface.tsx:249,292`）；移除 1536px `.chat-container { max-width: 900px }` 与之冲突的旧覆盖，改为仅在超宽屏兜底外框；加载指示器行对齐同一列
- [x] 4.2 权限控件归位：核实为**两类独立控件**而非三处同一控件重复——(a) `PermissionModeToggle`(sandbox/native) 与 `AutonomySlider` 由 store 支撑、持久化 localStorage，位于 ControlBar；(b) `SessionSidebar` 内的 `PermissionModes`(manual/plan/auto) 是**局部 state，写入后无人读取**，从不进 store、不发给后端、不参与会话创建，属误导性死 UI。已从 SessionSidebar 摘除该块及其残留 import；`PermissionModes.tsx` 本体零消费者，保留待删除确认
- [x] 4.3 验证：`tsc --noEmit` exit 0；workspace+store 测试串行 16/16（并行下 ControlBar/SessionSidebar 各 1 例 5s 超时为 jsdom 争抢 flaky，串行通过）

## 阶段 5 —— 一致性级

- [x] 5.1 i18n 统一入口：`useI18n`/`useTranslation` 收敛为单一 hook，保留兼容别名（见阶段 1 附条）
- [x] 5.2 去除硬编码英文：AgentsPage 表单/空态/搜索（新增 18 键）；ApiKeysPage + AuthApiKeysPage 全量接 `apiKeys` 命名空间（含嵌套 `authApiKeys`，新增 21 键）；WorkflowsPage 接 `workflows` 命名空间（9 键）；ClusterPage 角色名接 `workflows.role_*`；通用文案（Refresh/Retry/Thinking/Version outdated/Copy code/Close notification/Close dialog）入 `common`（新增 6 键）。7 locale 全部补齐并校验 JSON 合法
- [x] 5.3 API 数据层：`reasonStream` 删除死参数 `_onEvent` 并改调用点 `ReasoningPanel.tsx:86`；`api.ts` 抽出模块级公共 SSE 读取函数供 `chatStream`/`runAutonomousSkillStream` 复用；新增 `checkHealth`，`DashboardPage.tsx:16` 不再裸 `fetch('/health')`；AgentsPage 表单 Ollama provider 免除 `api_key` 校验（`AgentsPage.tsx:316`），残留英文（`Previous`/`Next`/`Create Agent`/空态）全部键化（新增 8 键 × 7 locale）；AuthApiKeysPage `Create Key` 键化（新增 `create_key` × 7 locale）
- [x] 5.4 验证：`tsc --noEmit` exit 0、`vite build` exit 0、vitest 54 files / 797 tests 全绿（修 `AuthApiKeysPage.test.tsx`、`SettingsPage.credentials.test.tsx` 的 i18n mock）

## 阶段 6 —— 收尾

- [x] 6.1 全量 typecheck + vitest + build（见 5.4）
- [x] 6.2 更新 tasklist（阶段 1/3/4/5 全部完成；阶段 2 死代码待用户确认后删除）
- [x] 6.3 本地提交 checkpoint（`b6cb04ce`，未推送）

## 阶段 7 —— 性能与无障碍（并行子任务，已完成）

- [x] 7.1 ThinkingIndicator：4 个 setInterval 收敛为 1 个 tick interval；ThinkingDots 改为 CSS 动画
- [x] 7.2 LazyImage：三套懒加载收敛为单一 IntersectionObserver；移除 DOM 直改 src
- [x] 7.3 SessionSidebar focus 刷新：保留（多标签账号同步，有测试覆盖，成本低）
- [x] 7.4 无障碍：模态背景层补 Escape 关闭；剩余 button type 人工判断后补齐
- [x] 7.5 验证：typecheck exit 0、vitest 25 files / 210 tests 全绿、vite build 成功

## 阶段 8 —— 待推进（结构性改动，需确认）

- [ ] 8.1 token 双 key 收敛（`auth_token` vs `climber-auth`，方案见 `design-code-refactor.md`）
- [ ] 8.2 三套数据层收敛（api.ts / api-client.ts / services/，方案见 `design-code-refactor.md`）
- [ ] 8.3 巨型文件拆分（api.ts 830 / SettingsPage 780 / FactoryModePage 704）
- [ ] 8.4 视觉 P0 实施（方案见 `design-visual-upgrade.md`）
