# 前端现状核验报告（2026-09-26）

本报告记录对 `frontend-react/src` 的逐项代码核验结果，用于纠正此前基于旧报告的判断。
所有结论均通过引用图扫描与全量测试验证得出。

## 核验方法

- 引用判定使用**精确导入路径匹配**（`from './X'` / `from '../X'` / `from '../../X'`），
  而非后缀模糊匹配。后者会把 `ui/Card` 误判为根级 `Card` 的引用。
- 每个候选文件在删除前先确认：无业务引用、无测试引用、无 barrel 间接引用。
- 基线：25 个测试文件 / 210 个用例全绿，`typecheck` 通过，`lint` 0 errors。

## 一、此前判断有误的项目

### 1. 侧栏导航并未缺失

此前结论「侧栏只使用 `CORE_NAV_ITEMS_BASE` 的 8 项，25 项导航未展示」与代码不符。

- `src/App.tsx:75` 实际使用的是 `ALL_NAV_ITEMS_BASE`（25 项）。
- `src/App.tsx:209-247` 已按 `main` / `manage` / `config` 三组渲染。
- 分组标题、`aria-current="page"`、折叠态 `title`、`CORE_NAV_ITEMS_BASE`（8 项）
  仅供移动端 `AdaptiveMobileLayout.tsx:41` 使用。

结论：导航改造已完成，无需改动。

### 2. `forms/`、`components/full/`、`components/dashboard/`、`components/a11y/` 已不存在

这些目录属于更早一轮的模板清理，备份仍在 `/tmp/opencode/deadcode-backup/`。
其中 `src/components/a11y/Button.tsx` 等文件已随上一轮删除。

### 3. 通知 ToastProvider 未挂载 —— 属于选型问题而非缺陷

`src/components/ui/Toast.tsx` 的 `ToastProvider` 确实未在 `main.tsx` 挂载，
但真正在用的是 `sonner` 方案：`App.tsx:283` 挂载 `IOsToaster`。

原判断遗漏的关键事实：`sonner` 的 `toast()` 在业务代码中零调用点，
即当前**没有任何业务路径能弹出通知**。这是能力缺口，而非挂载遗漏。

### 4. `ChatInput.tsx` 等 6 个 chat 组件确为死代码（判断成立）

但 `chat/index.ts` barrel 自身零导入，导出的 10 个组件中有 6 个完全无引用。

## 二、本轮新发现的问题

### 1. 模板重复组件（`components/` 根级 vs `components/ui/`）

`components/` 根级存在 5 个与 `components/ui/` 同名的模板组件，业务代码全部
只使用 `ui/` 版本，根级版本零引用：

| 根级文件 | 行数 | 实际使用方 |
|---|---|---|
| `components/Badge.tsx` | 94 | 仅契约测试自身 |
| `components/Card.tsx` | 94 | 无 |
| `components/Dropdown.tsx` | 94 | 无 |
| `components/Progress.tsx` | 94 | 无 |
| `components/Skeleton.tsx` | 94 | 无 |

`ui/` 版本功能完整：例如 `ui/Card.tsx`(79 行) 导出 7 个成员，
`ui/Dropdown.tsx`(197 行)、`ui/Progress.tsx`(147 行)。

另有 `components/Alert.tsx`、`components/Notification.tsx` 各 94 行，同样零引用。

### 2. 三套并存的 Toast 实现（共 391 行，仅 1 套在用）

| 文件 | 行数 | 状态 |
|---|---|---|
| `components/ios/IOSToast.tsx` | 62 | **唯一使用**（`App.tsx:283`） |
| `components/ui/Toast.tsx` | 235 | 零引用，仅作契约测试 `?raw` 样本 |
| `components/Toast.tsx` | 94 | 零引用 |

### 3. 契约测试的 toast 样本指向死代码

`src/components/ui/__tests__/presentation-contract.test.tsx:16` 通过
`../Toast.tsx?raw` 读取 `ui/Toast.tsx` 作为「不得含旧紫色/装饰青色」的守门样本，
导致一个 235 行的死文件无法删除。已改指向 `../../ios/IOSToast.tsx?raw`。

### 4. iOS 工具类族全员零引用（24 个 CSS 类）

`index.css` 中 `.ios-list-group` / `.ios-card` / `.ios-navbar` / `.ios-switch` /
`.ios-segmented` / `.ios-title-1` 等 24 个类及其全部规则，`.tsx` 中零引用。
`.ios-skeleton` 已随组件删除而成为孤儿。

注意：`.safe-area-top` / `.safe-area-bottom` **仍在使用**
（`AdaptiveMobileLayout.tsx:56,66`、`MobileChatInterface.tsx:267`），已保留。

### 5. `App.tsx` 的 Toaster 主题硬编码

`App.tsx:283` 传入 `theme="dark"`，与项目主题系统冲突。
toast 样式实际全走 CSS var（会自动跟随主题），`theme` 属性只影响 sonner 自身的
明暗分支。已改为 `theme="system"`。

### 6. Agent 删除无二次确认、菜单含禁用按钮

- `AgentsPage.tsx` 的 `deleteAgent` 直接调用 API，无确认、无错误处理。
- 卡片菜单含 2 个 `disabled` 的占位按钮（Copy Config / Edit Settings），
  仅靠 `title` 提示 Coming soon。
- 触发按钮在 `md` 断点下用 `md:opacity-0 md:group-hover:opacity-100` 隐藏，
  触屏设备无 hover 态，菜单入口不可见。

### 7. `ErrorBoundary` 绕过 i18n 且含 emoji

`components/ErrorBoundary.tsx` 硬编码英文文案（Something went wrong /
An unexpected error occurred / Try Again），装饰符为 emoji `⚠`，
颜色硬编码 `text-red-400`（未走 `--color-error` token）。

### 8. `fallbackLng` 为英文

`i18n/config.ts:37` 为 `fallbackLng: 'en'`，缺失 key 回退英文。
语言列表含 7 种语言但 `zh-CN` 排在第 2 位。

## 三、本轮已完成的改动

| 改动 | 规模 |
|---|---|
| 删除零引用 `.tsx` 死代码 | 14 个文件，1473 行 |
| 删除孤儿 `ios-*` CSS | 24 个类，约 222 行 |
| `IOsToaster` 跟随主题 | `App.tsx` + `IOSToast.tsx` |
| Agent 删除确认对话框 | 复用 `ui/Modal` 的 `ConfirmDialog`（`variant="danger"`） |
| 删除操作错误处理 | `deleteAgent` 返回 `boolean`，失败保留对话框 |
| 移除 2 个 disabled 占位按钮 | 同上 |
| 菜单入口触屏/键盘可达 | 去掉 `md:opacity-0`，按钮尺寸改为 44px 触达区 |
| `ErrorBoundary` 接入 i18n + 去 emoji + token 化 | 新增 `error_boundary` 段，7 语言 |
| `agents` 段 i18n 更新 | 新增 `delete_confirm_title` / `delete_failed`，移除 `coming_soon_title`，7 语言 |
| `LanguageSwitcher` 去国旗 | 7 个 emoji → lucide `Languages` 图标，`showFlag` → `showIcon` |
| `fallbackLng` 改中文 | `en` → `zh-CN` |

## 四、验证结果

| 项目 | 清理前 | 清理后 |
|---|---|---|
| typecheck | 通过 | 通过 |
| 测试 | 25 文件 / 210 用例全绿 | 25 文件 / 210 用例全绿 |
| lint errors | 0 | 0 |
| lint warnings | 123 | 78 |
| `?raw` 契约样本 | 含 1 个死文件 | 全部指向存活实现 |

## 五、第二轮：模板复制根因与 AG-UI 适配

### 1. warning 居高不下的根因：`ui/` 下 7 份 110 行模板副本

`components/ui/` 存在 `Nav.tsx` / `List.tsx` / `Header.tsx` / `Form.tsx` /
`Error.tsx` / `Details.tsx` / `Box.tsx`，每个恰好 110 行、内容为同一份模板，
全部零引用。每个文件产生 9 个 `no-unused-vars` warning，合计 63 个 ——
占清理前 78 个 warning 的 81%。

另有第三份 `ErrorBoundary`：`components/ui/ErrorBoundary.tsx`(115 行) 零引用，
实际使用的是 `components/ErrorBoundary.tsx`(54 行，已 i18n 化)。

三份同源文件已全部删除，warning 从 78 降至 31。

### 2. AG-UI 事件适配层

新增 `src/types/chatEvents.ts`：

- `ChatStreamEvent` 为判别联合，覆盖 `text` / `thinking` / `tool_call` /
  `tool_result` / `done` / `error` / `unknown` 七种情形。
- `normalizeChatEvent()` 同时接受两种事件名来源：**优先 `data.type`（AG-UI 形态）**，
  其次 `event:` 行（当前后端形态）。这让后端切换到 AG-UI 规范时前端零改动。
- `unknown` 分支保留原始帧，调用方记录告警而不中断流。

改造点：

| 文件 | 改动 |
|---|---|
| `api.ts` `readSSEStream` | 新增**空闲超时**（120s，每收数据块重置，长时生成不误杀）；`finally` 中释放 reader lock；补发无尾空行的末帧 |
| `api.ts` `chatStream` | 回调签名改为 `ChatStreamEvent`；空 body 从静默返回改为发出 `error` 事件 |
| `api.ts` `runAutonomousSkillStream` | 复用同一解析器；`data: any` → `unknown`；补空 body 错误收尾 |
| `useChat.ts` | 整段 if-else 链改为 `switch (event.type)`，消除 `(event: any)` |

新增 12 个单元测试 `src/types/__tests__/chatEvents.test.ts`，覆盖两种事件名来源、
字符串负载、备用字段名、缺省值、错误消息多来源、未识别事件。

### 3. i18n 覆盖度：以代码引用为基准的真实缺口

先前以 `en.json` 为基准做集合比对，方向错了 —— `en.json` 本身也缺 key。
改为**提取代码中全部 `t('...')` 与 `labelKey: '...'` 字面量**（176 个），
再对 7 份语言文件逐个核对，暴露真实缺口：

- `home.*` 7 个 key（`DashboardPage.tsx:39,67,68,78,79,90,91` 正在引用）
  在**全部 7 种语言中都不存在** —— 仪表盘此前直接显示原始 key 字符串。
- `navigation.factory`（`navConfig.ts:39`）仅 `zh-CN` 有，其余 6 种显示原始 key。
- `chat.*` 8 个 key 在 ja/ko/es/fr/de 缺失。
- `workflows.member_agent_id`（`ClusterPage.tsx:498`）在 ja/ko 缺失。

已全部补齐。现状：7 种语言各 435 key，代码引用的 176 个 key **零缺失**。

### 4. 其他修复

| 改动 | 说明 |
|---|---|
| `MobileChatPage.tsx:48` | `bg-red-500/10` / `text-red-400` → `--color-error` token |
| `ChatPage.tsx` | 重试按钮从 `window.location.reload()` 改为 `useChat` 的 `refresh()`；硬编码中文接入 i18n |
| `common.retry` | 确认 7 语言均已存在，无需新增 |

## 六、最终验证

| 项目 | 初始 | 第一轮后 | 第二轮后 | 第三轮后 |
|---|---|---|---|---|
| typecheck | 通过 | 通过 | 通过 | 通过 |
| 测试 | 25 文件 / 210 | 25 文件 / 210 | 26 文件 / 222 | 29 文件 / 247 |
| lint errors | 0 | 0 | 0 | 0 |
| lint warnings | 123 | 78 | 31 | 31 |
| build | 成功 | 成功 | 成功 | 成功 |
| i18n 覆盖 | 未知 | 未知 | 176/176 key × 7 语言 | +right_panel 11 组 × 7 语言 |
| 删除代码量 | — | 1695 行 | +2965 行 | RightPanel 507 → 205 行（拆 6 文件） |

累计删除约 4660 行死代码与模板残留。

第三轮新增 1 条 lint warning（`rightPanel/PanelState.tsx` 的
`react/only-export-components`），同时消掉 1 条（`RightPanel.tsx` 原有
`no-explicit-any`），总数持平于 31。

## 六之一、右侧面板两层模型（第三轮）

原 7 个平级 Tab 改为「常驻运行摘要 + 4 个分组折叠区」，完整规范见
`RIGHT_PANEL_SPEC_2026-09-26.md`。

| 变更 | 说明 |
|---|---|
| `RightPanel.tsx` | 重写为组装器，507 行 → 205 行 |
| `rightPanel/RunSummary.tsx` | 新增常驻摘要：状态、模型、Token 进度、工具/错误/技能计数 |
| `rightPanel/groupModel.ts` | 新增分组元数据，被 `RightPanel` 与 `ControlBar` 共享 |
| `rightPanel/PanelState.tsx` | 新增 `useAsyncData` + `PanelLoading/PanelEmpty/PanelError` |
| `rightPanel/sections/*` | 4 个文件承载 7 个分区，失败态带重试 |
| `ControlBar.tsx` | 7 个 Tab 图标 → 4 个分组入口，无会话时 `changes` 回落到 files、`activity` 禁用 |
| 存储层 | `rightPanelTab` 七值不变，深链与外部调用无需改动 |

## 六之二、SSE 空闲超时修复（第三轮）

`readSSEStream` 的注释声明超时抛 `SSEIdleTimeoutError`，实现却只
`reader.cancel()`。`cancel()` 只会让挂起的 `reader.read()` 以 `done` 收尾，
函数正常返回——超时表现为「流安静地结束」，用户看不到任何错误。

修复：

1. 新增导出的 `SSEIdleTimeoutError`，带 `idleTimeoutMs` 字段供上层展示阈值。
2. 计时器回调先置 `idleTimedOut` 标记再取消 reader。
3. 读循环结束后显式 `throw`，因此不会被 `finally` 吞掉。
4. `reader.read()` 因取消而 reject 时，把错误改写为 `SSEIdleTimeoutError`，
   避免上报成不明原因的 stream error。
5. `chatStream` 增加可选 `options.idleTimeoutMs`，让阈值可按端点调整，
   同时让测试可用毫秒级阈值。

`src/__tests__/api.sse.test.ts` 覆盖 5 个用例：AG-UI 形态解析、`event:`
行形态解析、卡流必须报错、窗口内持续有数据时不误杀、错误对象字段。
两个调用点（`chatStream`、`runAutonomousSkillStream`）的 catch 本就把
异常转成 `error` 事件，因此无需改动即可让超时对用户可见。

## 七、仍待处理

1. **会话侧边栏信息架构**：`SessionSidebar` 仍按线性列表展示会话，
   缺少分组、运行状态、上下文用量与快速切换，重构规范待落盘。
2. **空/加载/错误/权限待确认四态统一**：右侧面板已收敛到 `PanelState`
   原语，其余页面（设置页、列表页、移动端）尚未接入同一套。
3. **命令面板与全局搜索升级**：`CommandPalette` / `GlobalSearch` 仍是
   基础实现，缺分组、模糊匹配权重与快捷键导航。
4. **品牌 accent 重定义**：主题色、状态色与代码高亮的层次需要一次
   亮/暗双主题视觉回归。
5. **专项测试缺口**：`ToolCallVisualization`、Markdown TOC 仍缺直接测试。
6. **后端 AG-UI 对齐**：前端适配器已同时兼容两种事件名来源，
   后端 `/workspace/climber/app` 若切换到 `data.type` 形态，前端无需改动；
   若要启用，则需覆盖 run 生命周期、state、step、snapshot 等事件类型。

已在本轮结清的项：硬编码彩色工具类清零、Toast 体系收敛到 `sonner`、
`ChatInterface` 改为纯展示组件、剩余 lint warning 逐个清理。

