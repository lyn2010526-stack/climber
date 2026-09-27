# Round 11：8 项未开始任务的证据补齐与真实三态判定

- 日期：2026-09-26
- 角色：研究与文档执行者，只读 `frontend-react/src` 与 `/tmp/opencode/ref-repos`
- 写入范围：本目录两份新文档 + `REFACTOR_50_TASKS_2026-09-26.md` 追加第 7 节
- 未修改 `frontend-react/src` 下任何产品源码；未 commit、未 push、未删除任何既有文档
- 证据规则：参考结论只采用具体 UI 源文件并给出绝对路径与行号。README、截图、营销页、许可证正文不作为 UI 证据。未找到证据的条目直接写「未找到证据」。

判定基准沿用账本第 3 节的三态定义：

- **已完成**：交付物在 `frontend-react/src` 中存在且在当前快照有对应测试或验收证据。
- **进行中**：源码已改但缺验证证据，或任务自身验收标准未整体满足。
- **未开始**：该任务的交付物在 `frontend-react/src` 中不存在。

研究类任务（07、08）的交付物是本目录的成文证据，故其三态取决于本文件是否已写入可验证证据，而非 Climber 侧是否已实现。

---

## 1. 汇总：8 项真实三态

| 任务 | 编制期标签 | 真实三态 | 判定依据摘要 |
| --- | --- | --- | --- |
| 07 代码变更与权限确认模式 | 待办 | **已完成** | 本文件 §2 给出 4 个仓库 8 处 `路径:行号` 证据，覆盖变更摘要、文件导航、危险操作确认、取消路径；SWE-agent 无 React UI 已显式降级标注 |
| 08 管理页与诊断信息密度 | 待办 | **已完成** | 本文件 §3 给出列表密度、详情编辑、凭据选择、异常反馈四类各 2 处证据，每类含采用决策与适配限制 |
| 22 会话分组/过滤/上下文摘要 | 待办 | **未开始** | `SessionSidebar.tsx:308-310` 仍是单一 `<ul>` + `sessions.map`；无分组、无过滤、无删除确认；`SessionSidebar.tsx:409` 的时间格式化只用于检查点 |
| 24 命令匹配排序 | 待办 | **未开始** | `CommandPalette.tsx:33-41` 仍为三处 `includes`，无评分、无同分规则、无模糊匹配 |
| 26 导航与搜索结果去向统一 | 待办 | **未开始** | `GlobalSearch.tsx:157-162` Enter 分支只切换 `expanded`，无 `onNavigate` 出口；组件 props 亦无导航回调 |
| 46 双主题视觉回归 | 待办 | **未开始** | 仓库仅有 3 张单主题、内容为空的截图（`artifacts/ui-acceptance/*.png`）；无 `toHaveScreenshot`、无基线目录、无对比度实测记录 |
| 48 长列表与流式性能回归 | 待办 | **未开始** | 无性能测试文件；`useChat.ts` 每个分片一次全量 `setMessages(prev => prev.map(...))`，无节流；`@tanstack/react-virtual` 声明为依赖但 0 处使用 |
| 50 跨模块验收结项 | 待办 | **未开始** | 门槛未达成：46、48 未开始，49 缺当前快照构建与 E2E 证据；串行联调链路无记录 |

真实计数由 18/24/8 变为 **20 / 24 / 6**。已完成 +2（07、08），未开始 −2（07、08 已升级），进行中不变，合计 50 恒定。

| 范围 | 已完成 | 进行中 | 未开始 |
| --- | ---: | ---: | ---: |
| 01–20 研究与基础 | 11 | 9 | 0 |
| 21–50 实现与验收 | 9 | 15 | 6 |
| **合计** | **20** | **24** | **6** |

剩余 6 项未开始全部落在实现与验收段：22、24、26、46、48、50。

---

## 2. 任务 07：代码变更与权限确认模式

范围为 OpenHands、Cline、SWE-agent 的 Diff、审批或轨迹界面。任务标准要求「至少两处可定位实现支持变更摘要、文件导航、危险操作确认和取消路径；仅有轨迹/文档的对象显式标注证据层级」。本次取得 8 处，全部为源码。

### 2.1 变更摘要与文件导航

**证据 1 — Cline：按文件分块 + 三态样式 + 流式跟随滚动**

`/tmp/opencode/ref-repos/cline_cline/apps/vscode/webview-ui/src/components/chat/DiffEditRow.tsx`

```
26: const ACTION_STYLES = {
27: 	Add: { icon: FilePlus, iconClass: "text-success", borderClass: "border-l-success" },
28: 	Delete: { icon: FileX, iconClass: "text-error", borderClass: "border-l-error" },
29: 	default: { icon: FileText, iconClass: "text-info", borderClass: "border-l-background" },
30: } as const
```

```
52: 	return (
53: 		<div className="space-y-4 rounded-xs">
54: 			{parsedFiles.map((file, index) => (
55: 				<FileBlock
56: 					file={file}
57: 					isStreaming={isStreaming}
58: 					key={`${file.path}-${index}`}
59: 					startLineNumber={startLineNumbers?.[index]}
60: 				/>
61: 			))}
62: 		</div>
63: 	)
```

```
66: const FileBlock = memo<{ file: Patch; isStreaming: boolean; startLineNumber?: number }>(
67: 	({ file, isStreaming, startLineNumber }) => {
68: 		const [isExpanded, setIsExpanded] = useState(true)
69: 		const scrollContainerRef = useRef<HTMLDivElement>(null)
70: 		const shouldFollowRef = useRef(true)
```

- 变更摘要：增/删/改三态各有独立图标与左侧边框色（26–30 行），不靠文案区分。
- 文件导航：每文件一个 `FileBlock`，各自持有展开态与独立滚动容器（66–70 行），`memo` 包裹使未变文件不重渲染。
- 流式：`isStreaming` 与 `shouldFollowRef` 组合，流式期间自动跟随到块底部，用户上滚后停止跟随。

**证据 2 — OpenHands：单开手风琴 + path/status 作为行身份**

`/tmp/opencode/ref-repos/All-Hands-AI_OpenHands/src/components/features/diff-viewer/diff-change-list.tsx`

```
19: /**
20:  * Single-open accordion of file diffs. Expanding one path collapses the
21:  * previously open one (same behavior as the Commits list).
22:  */
23: export function DiffChangeList({ changes, commit }: DiffChangeListProps) {
24:   const [expandedPath, setExpandedPath] = useState<string | null>(null);
25:
26:   return (
27:     <div data-testid="diff-change-list" className="w-full flex flex-col">
28:       {changes.map((change) => (
29:         <FileDiffViewer
30:           key={change.path}
31:           path={change.path}
32:           type={change.status}
33:           commit={commit}
34:           isExpanded={expandedPath === change.path}
35:           onToggle={() =>
36:             setExpandedPath((prev) =>
37:               prev === change.path ? null : change.path,
38:             )
39:           }
40:         />
41:       ))}
```

- 单一 `expandedPath` 状态（24 行）保证同一时刻只有一个文件展开，长 diff 列表不会同时撑开多个重块。
- `key={change.path}` + `type={change.status}`（30、32 行）使行身份来自真实路径与 git 状态。
- `commit` 参数（16 行注释）支持按 commit 切换 diff 源，而非只显示工作区。

### 2.2 危险操作确认与取消路径

**证据 3 — OpenHands：高危分级提示 + 拒绝/确认双出口 + 提交去重 + 键盘等价**

`/tmp/opencode/ref-repos/All-Hands-AI_OpenHands/src/components/shared/buttons/conversation-confirmation-buttons.tsx`

```
 44:       // Mark event as submitted to prevent duplicate submissions
 45:       if (awaitingAction.id) {
 46:         addSubmittedEventId(awaitingAction.id);
 47:       }
```

```
 66:     const handleCancelShortcut = (event: KeyboardEvent) => {
 67:       if (event.shiftKey && event.metaKey && event.key === "Backspace") {
 68:         event.preventDefault();
 69:         handleConfirmation(false);
 70:       }
 71:     };
 72:
 73:     const handleContinueShortcut = (event: KeyboardEvent) => {
 74:       if (event.metaKey && event.key === "Enter") {
 75:         event.preventDefault();
 76:         handleConfirmation(true);
 77:       }
 78:     };
```

```
 92:   // Only show if agent is waiting for confirmation and we haven't already submitted
 93:   if (
 94:     curAgentState !== AgentState.AWAITING_USER_CONFIRMATION ||
 95:     !awaitingAction ||
 96:     (awaitingAction.id !== undefined &&
 97:       submittedEventIds.includes(awaitingAction.id))
 98:   ) {
 99:     return null;
100:   }
```

```
102:   // Get security risk from the action (only ActionEvent has security_risk)
103:   const risk = isActionEvent(awaitingAction)
104:     ? awaitingAction.security_risk
105:     : SecurityRisk.UNKNOWN;
106:
107:   const isHighRisk = risk === SecurityRisk.HIGH;
108:
109:   return (
110:     <div className="flex flex-col gap-2 pt-4">
111:       {isHighRisk && (
112:         <RiskAlert
113:           content={t(I18nKey.CHAT_INTERFACE$HIGH_RISK_WARNING)}
114:           icon={<WarningIcon width={16} height={16} color="#fff" />}
115:           severity="high"
116:           title={t(I18nKey.COMMON$HIGH_RISK)}
117:         />
118:       )}
119:       <div className="flex justify-between items-center">
120:         <p className="text-sm font-normal text-contrast">
121:           {t(I18nKey.CHAT_INTERFACE$USER_ASK_CONFIRMATION)}
122:         </p>
123:         <div className="flex items-center gap-3">
124:           <ActionTooltip
125:             type="reject"
126:             onClick={() => handleConfirmation(false)}
127:           />
128:           <ActionTooltip
129:             type="confirm"
130:             onClick={() => handleConfirmation(true)}
131:           />
```

- 危险分级来自事件自身的 `security_risk` 字段（103–107 行），缺失回落 `UNKNOWN` 而非猜测为低危。
- 取消路径是一等出口：`type="reject"` 独立按钮（124–127 行）+ `⇧⌘⌫` 快捷键（66–71 行），与确认 `⌘↩`（73–78 行）同源同函数。
- 提交去重靠 `submittedEventIds` 集合（45–47、96–98 行），双击或键盘+点击只生效一次。
- 监听器在 effect cleanup 中移除（89 行 `removeEventListener`），面板关闭不留残留。

**证据 4 — OpenHands：高危横幅的独立组件与颜色/语义绑定**

`/tmp/opencode/ref-repos/All-Hands-AI_OpenHands/src/components/shared/risk-alert.tsx`

```
19:   // Currently, we are only supporting the high risk alert. If we use want to support other risk levels, we can add them here and use cva to create different variants of this component.
20:   if (severity === "high") {
21:     return (
22:       <div
23:         className={cn(
24:           "flex items-center gap-3.5 bg-[#4A0709] border border-[#FF0006] text-red-400 rounded-xl px-3.5 h-13 text-sm text-white",
25:           className,
26:         )}
27:       >
28:         {icon && <span className="">{icon}</span>}
29:         <span className="font-bold">{title}</span>
30:         <span className="font-normal">{content}</span>
31:       </div>
32:     );
33:   }
34:
35:   return null;
```

高危提示是独立语义组件，标题加粗、正文常规，两段文案分别来自 `title` 与 `content`（29–30 行）。非 high 等级显式返回 `null`（35 行），不渲染「未知风险」的伪中性样式。

**证据 5 — OpenHands：危险操作按钮样式由调用方指定**

`/tmp/opencode/ref-repos/All-Hands-AI_OpenHands/src/components/shared/modals/confirmation-modals/danger-modal.tsx`

```
 9:   buttons: {
10:     danger: { text: string; onClick: () => void };
11:     cancel: { text: string; onClick: () => void };
12:   };
...
26:       buttons={[
27:         {
28:           text: buttons.danger.text,
29:           onClick: buttons.danger.onClick,
30:           className: "bg-danger",
31:         },
32:         {
33:           text: buttons.cancel.text,
34:           onClick: buttons.cancel.onClick,
35:           className: "bg-interactive-selected",
36:         },
37:       ]}
```

Props 契约强制同时提供 `danger` 与 `cancel` 两个出口（9–12 行），类型层面无法只发危险动作。危险动作使用独立 `bg-danger` 语义类，取消使用中性 `bg-interactive-selected`（30、35 行）。

**证据 6 — LobeHub：删除确认 + 危险按钮属性 + 权限原因作为禁用说明**

`/tmp/opencode/ref-repos/lobehub_lobe-chat/src/features/Settings/provider/features/ModelList/ModelItem.tsx`

```
 84:     const { allowed: canManageProvider, reason } = usePermission('manage_provider_key');
```

```
204:           {source !== AiModelSourceEnum.Builtin && (
205:             <ActionIcon
206:               disabled={!canManageProvider}
207:               icon={TrashIcon}
208:               size={'small'}
209:               title={canManageProvider ? t('providerModels.item.delete.title') : reason}
210:               onClick={() => {
211:                 if (!canManageProvider) return;
212:                 confirmModal({
213:                   cancelText: t('cancel', { ns: 'common' }),
214:                   content: t('providerModels.item.delete.confirm', {
215:                     displayName: displayName || id,
216:                   }),
217:                   okButtonProps: {
218:                     danger: true,
219:                   },
220:                   okText: t('delete', { ns: 'common' }),
221:                   onOk: async () => {
222:                     await removeAiModel(id, activeAiProvider!);
223:                     toast.success(t('providerModels.item.delete.success'));
224:                   },
225:                   title: t('providerModels.item.delete.title'),
226:                 });
227:               }}
228:             />
229:           )}
```

- 权限 hook 同时返回 `allowed` 与 `reason`（84 行），禁用时把 `reason` 直接作为 `title`（209 行），禁用原因对用户可读，不做静默禁用。
- `onClick` 内二次守卫 `if (!canManageProvider) return;`（211 行），不依赖 `disabled` 单一防线。
- 确认框内容带目标对象的真实名称（214–216 行），危险属性落在 `okButtonProps.danger`（217–219 行），成功后 toast 反馈（223 行）。

**证据 7 — Cline：自动化批准的父子层级，子项启用时父项不重复展示**

`/tmp/opencode/ref-repos/cline_cline/apps/vscode/webview-ui/src/components/chat/auto-approve-menu/AutoApproveMenuItem.tsx`

```
34: 	const onChange = async (e: React.MouseEvent) => {
35: 		if (disabled) {
36: 			return
37: 		}
38: 		e.stopPropagation()
39: 		await onToggle(action, !checked)
40: 	}
...
52: 			{action.subAction && (
53: 				<SubOptionAnimateIn inert={!checked ? "" : undefined} show={checked}>
54: 					<AutoApproveMenuItem action={action.subAction} isChecked={isChecked} onToggle={onToggle} />
55: 				</SubOptionAnimateIn>
56: 			)}
```

```
13: const SubOptionAnimateIn = styled.div<{ show: boolean; inert?: string }>`
14:   position: relative;
15:   transform: ${(props) => (props.show ? "scaleY(1)" : "scaleY(0)")};
16:   transform-origin: top;
17:   padding-left: 24px;
18:   opacity: ${(props) => (props.show ? "1" : "0")};
19:   height: ${(props) => (props.show ? "auto" : "0")}; /* Manage height for layout */
```

`/tmp/opencode/ref-repos/cline_cline/apps/vscode/webview-ui/src/components/chat/auto-approve-menu/AutoApproveBar.tsx`

```
29: 		// Filter out parent actions if their subaction is also enabled (show only subaction)
30: 		const actionsToShow = enabledActions.filter((action) => {
31: 			if (!action?.shortName) {
32: 				return false
33: 			}
34:
35: 			// If this is a parent action and its subaction is enabled, skip it
36: 			if (action.subAction?.id && enabledActionsNames.includes(action.subAction.id)) {
37: 				return false
38: 			}
```

- 自动化是分级授权：父项勾选才展开子项（52–56 行），子项未勾选时父项不隐式放行子项。
- 摘要条在子项启用时不重复显示父项（29–41 行），避免用户误读「已批准 N 项」的真实粒度。
- 撤销路径是取消父项勾选，子项随之不可见（`show={checked}`），授权范围收窄立即生效。

### 2.3 证据层级降级标注：SWE-agent

`/tmp/opencode/ref-repos/SWE-agent_SWE-agent` 全仓仅 4 个 HTML 文件，均为文档覆盖页或测试夹具：

- `/tmp/opencode/ref-repos/SWE-agent_SWE-agent/sweagent/inspector/index.html` — 轨迹查看器（单文件）
- `/tmp/opencode/ref-repos/SWE-agent_SWE-agent/docs/overrides/main.html` — 文档主题覆盖
- `/tmp/opencode/ref-repos/SWE-agent_SWE-agent/tools/web_browser/test_console.html` — 测试夹具
- `/tmp/opencode/ref-repos/SWE-agent_SWE-agent/tests/test_data/data_sources/ctf/web/i_got_id_demo/index.html` — 漏洞数据集

**证据层级：仅轨迹/文档级。** 无 React/Vue/Svelte 组件、无审批状态机、无 diff 组件。按任务 07 的标准，SWE-agent 的可迁移结论为零，仅可作为「Agent 轨迹需要可回看」的存在性佐证。本任务范围内其余证据由 OpenHands 与 Cline 承担。

### 2.4 任务 07 映射

| Climber 落点 | 采用项 | 适配限制 |
| --- | --- | --- |
| 任务 35 `FloatingPermissionDialog` | OpenHands 事件级 `submittedEventIds` 去重（证据 3，45–47 行）；Cline 分级自动化而非单开关（证据 7） | Climber 无登录、无多租户，授权粒度不需要父子两层，只需「本会话 + 本工具类别」两级 |
| 任务 35 高危提示 | OpenHands `RiskAlert` 标题/正文双段（证据 4，29–30 行） | 上游用硬编码 hex（24 行），Climber 必须走 `--color-error-subtle` 令牌，否则阻塞任务 11 与 45 |
| 任务 43 `DiffPanel` | Cline 三态图标+边框色（证据 1，26–30 行）；OpenHands 单开手风琴（证据 2，24 行） | 上游 diff 来自 git 与 SEARCH/REPLACE 块解析；Climber 后端当前只提供结构化变更，需先确认 `DiffPanel` 的变更来源字段 |
| 任务 29 取消路径 | OpenHands reject 独立出口 + 快捷键等价（证据 3，124–131 行） | `⌘↩`/`⇧⌘⌫` 与浏览器保留键冲突，Climber 只能提供按钮出口 + `Escape` 关闭 |

---

## 3. 任务 08：管理页与诊断信息密度

任务标准要求「提供列表密度、详情编辑、凭据选择、异常反馈四类源码对照，每类明确一项采用决策及一项适配限制」。每类给出 2 处证据。

### 3.1 列表密度

**证据 1 — LibreChat：固定行高 + 窗口化 + 超扫参数全部显式**

`/tmp/opencode/ref-repos/danny-avila_LibreChat/client/src/components/Chat/Menus/Endpoints/components/VirtualizedModelList.tsx`

```
 8: /** Matches the rendered height of a `CustomMenuItem` row (px-2 py-1 around a py-1 body). */
 9: const ROW_HEIGHT = 36;
10: const MAX_LIST_HEIGHT = 320;
11: const OVERSCAN = 8;
```

```
26: /**
27:  * Windowed model list for endpoints with very large model sets (agents, mainly).
28:  *
29:  * Only the visible slice is mounted, so the per-row costs — Ariakit composite
30:  * registration, the active-item subscription, and ~12 DOM nodes each — stay
31:  * bounded no matter how many agents the user can see.
```

```
33:  * Ariakit's composite only knows about mounted rows, so arrow-keying to the edge
34:  * of the window would otherwise find no next item and let focus escape the nested
35:  * menu, closing it. `handleBoundaryNavigation` catches that case: it scrolls the
36:  * next index into the window, waits for the row to mount, then moves the composite
37:  * onto it. Navigation inside the window is left entirely to Ariakit, whose own
38:  * `scrollIntoView` drives the list's scroll position.
39:  */
```

密度契约三点齐全：行高常量与实际 CSS 行高对齐（8–9 行注释）、列表最大高度封顶（10 行）、超扫行数固定（11 行）。32–37 行记录了每行约 12 个 DOM 节点的成本模型，并显式处理窗口化与键盘边界的冲突（74 行起 `handleBoundaryNavigation`）。

**证据 2 — OpenHands：单开手风琴控制长列表的展开总量**

同 §2.1 证据 2，`diff-change-list.tsx:19-24`：单一 `expandedPath` 状态即长列表密度的直接手段——列表可平铺任意长度，同时展开的重块恒为 1。

**采用决策**：管理页列表采用「固定行高 + 单开展开 + 明确超扫参数」的组合。Climber 的 `SessionSidebar` 与 `PluginAndOperations` 类列表以 `ROW_HEIGHT` 对齐现有 36/40/44 三档控件高度常量，不引入窗口化。

**适配限制**：`SessionSidebar.tsx:309` 当前是原生 `<ul>`，窗口化会破坏 `role="list"` 语义与现有 `SessionSidebar.accessibility.test.tsx` 的方向键契约。`@tanstack/react-virtual` 已在 `package.json:34` 声明为依赖，选用时需为窗口外行补 `aria-setsize`/`aria-posinset`，否则读屏失去位置信息。

### 3.2 详情编辑

**证据 1 — LibreChat：防抖输入 + 未完成组件的显式自述**

`/tmp/opencode/ref-repos/danny-avila_LibreChat/client/src/components/Endpoints/Settings/Advanced.tsx`

```
24:   /* This is an unfinished component for future update */
25:   const localize = useLocalize();
...
38:   const [setChatGptLabel, chatGptLabelValue] = useDebouncedInput({
39:     setOption,
40:     optionKey: 'chatGptLabel',
41:     initialValue: chatGptLabel,
42:   });
...
63:   const [setPresP, presPValue] = useDebouncedInput({
64:     setOption,
65:     optionKey: 'presence_penalty',
66:     initialValue: presP,
67:   });
68:
69:   if (!conversation) {
70:     return null;
```

6 个字段全部走 `useDebouncedInput`（38–67 行），每个字段自带 `setOption` 通道，编辑态与保存态解耦。`unfinished component` 与 `return null`（24、69–70 行）是两处诚实信号：未完成与无数据各自显式表达，不渲染半成品表单。

**证据 2 — LobeHub：详情页骨架 + 配置/列表两段式**

`/tmp/opencode/ref-repos/lobehub_lobe-chat/src/features/Settings/provider/detail/default/CustomProviderDetail.tsx`

```
19:   const { data, isLoading } = useClientDataSWR(providerKeys.clientConfig(id), () =>
20:     aiProviderService.getAiProviderById(id),
21:   );
22:
23:   if (isLoading || !data || !data.id) return <SurfaceSkeleton header={false} variant={'form'} />;
24:
25:   return (
26:     // No block padding of its own — SettingContainer already insets the page.
27:     <Flexbox gap={24}>
28:       <ProviderConfig {...data} id={id} name={data.name || ''} />
29:       <ModelList id={id} />
30:     </Flexbox>
31:   );
```

单一 `isLoading` 守卫覆盖加载与数据缺失两种情况（23 行），骨架形态按表单而非卡片（`variant={'form'}`）。详情页结构固定为「凭据配置段 + 该凭据下的模型列表段」（28–29 行），`id` 同时传给两段，保证配置与列表的数据源一致。

**采用决策**：详情编辑采用「单一加载守卫 + 配置段与列表段共享同一 `id`」的结构。Climber `ModelConfig` 与 `PluginPage` 的详情表单按此拆分，加载与缺失共用一个守卫，编辑输入走防抖通道。

**适配限制**：`useDebouncedInput`（证据 1，38–67 行）依赖设置容器把「选项变更」即时下发到后端，Climber 的 `SettingsPage` 采用显式保存，两者不能混用；直接套用会绕过任务 40 的「保存失败保留编辑态」要求。

### 3.3 凭据选择

**证据 1 — Dify：9 值卡片变体 + 纯函数派生 + 破坏性变体集合**

`/tmp/opencode/ref-repos/langgenius_dify/web/app/components/header/account-setting/model-provider-page/provider-added-card/use-credential-panel-state.ts`

```
11: export type UsagePriority = 'credits' | 'apiKey' | 'apiKeyOnly'
12:
13: export type CardVariant =
14:   | 'credits-active'
15:   | 'credits-fallback'
16:   | 'credits-exhausted'
17:   | 'no-usage'
18:   | 'api-fallback'
19:   | 'api-active'
20:   | 'api-required-add'
21:   | 'api-required-configure'
22:   | 'api-unavailable'
...
35: const DESTRUCTIVE_VARIANTS = new Set<CardVariant>([
36:   'credits-exhausted',
37:   'no-usage',
38:   'api-unavailable',
39: ])
40:
41: export const isDestructiveVariant = (variant: CardVariant) => DESTRUCTIVE_VARIANTS.has(variant)
42:
43: function deriveVariant(
44:   priority: UsagePriority,
45:   isExhausted: boolean,
46:   hasCredential: boolean,
47:   authorized: boolean | undefined,
48:   credentialName: string | undefined,
49: ): CardVariant {
50:   if (priority === 'credits') {
51:     if (!isExhausted) return 'credits-active'
52:     if (hasCredential && authorized) return 'api-fallback'
53:     if (hasCredential && !authorized) return 'no-usage'
54:     return 'credits-exhausted'
55:   }
56:
57:   if (hasCredential && authorized) return 'api-active'
58:
59:   if (priority === 'apiKey' && !isExhausted) return 'credits-fallback'
60:
61:   if (priority === 'apiKey' && !hasCredential) return 'no-usage'
62:
63:   if (hasCredential && !authorized)
64:     return credentialName ? 'api-unavailable' : 'api-required-configure'
65:   return 'api-required-add'
66: }
```

凭据选择被建模为 9 个穷举变体（13–22 行），由 `deriveVariant` 纯函数从 5 个输入派生（43–66 行），输入里的 `authorized` 显式允许 `undefined`（47 行），即「权限未知」是合法状态。破坏性变体独立成集合并导出判定函数（35–41 行），UI 只消费 `isDestructiveVariant`，不各自判断。

**证据 2 — Dify：变体 → 状态点 + 凭据名，缺失凭据走「需配置」而非空白**

`/tmp/opencode/ref-repos/langgenius_dify/web/app/components/header/account-setting/model-provider-page/model-selector/popup-item.tsx`

```
 79:     const { canUseCredential, canCreateCredential, canManageCredential } = useCredentialPermissions()
...
 81:     const state = useCredentialPanelInfo(currentProvider)
...
 85:     const isApiKeyActive = state.variant === 'api-active' || state.variant === 'api-fallback'
 86:     const { credentialName } = state
```

```
175:                 ) : credentialName ? (
176:                   <>
177:                     <StatusDot size="small" status={isApiKeyActive ? 'success' : 'error'} />
178:                     <span className="ml-1 truncate text-text-tertiary">{credentialName}</span>
179:                   </>
180:                 ) : (
181:                   <>
182:                     <StatusDot size="small" status="disabled" />
183:                     <span className="ml-1 truncate text-text-tertiary">
184:                       {t(($) => $['modelProvider.selector.configureRequired'], {
185:                         ns: 'modelProvider',
186:                       })}
187:                     </span>
188:                   </>
189:                 )}
190:                 {canOpenCredentialDropdown && (
```

三个能力权限位（`canUseCredential` / `canCreateCredential` / `canManageCredential`，79 行）来自独立 hook，与展示态分离。行内三态：活动凭据显示绿点 + 名称（177–178 行）；有名称但未授权显示红点 + 名称（177 行同一组件换 status）；无凭据显示灰点 + 「需配置」文案（182–187 行），不留空白。

**采用决策**：凭据选择采用「穷举变体 + 纯函数派生 + 权限位与展示态分离」。Climber `SettingsPage.credentials.test.tsx` 与 `AuthApiKeysPage` 沿用此结构，把「已配置但无权限」「未配置需添加」「需先配置再使用」三态区分开，替换当前的布尔式存在性判断。

**适配限制**：Dify 变体含 `credits-*` 五态（13–19 行），源于其计费试用体系。Climber 无登录、无计费，`UsagePriority` 应收敛为单一 `apiKey` 优先级，`credits` 相关 5 个变体不得移植；照搬会引入无数据来源的状态。

### 3.4 异常反馈

**证据 1 — LobeHub：从错误消息正则抽出具体对象名并导向修复动作**

`/tmp/opencode/ref-repos/lobehub_lobe-chat/src/features/Settings/provider/detail/ollama/CheckError.tsx`

```
32: const UNRESOLVED_MODEL_REGEXP = /model "([\w+,.-]+)" not found/;
...
43:   const errorBody: OllamaErrorResponse = error?.body;
44:
45:   const errorMessage = errorBody.error?.message;
46:
47:   if (error?.type === 'OllamaServiceUnavailable') return <OllamaSetupGuide />;
48:
49:   // error of not pull the model
50:   const unresolvedModel = errorMessage?.match(UNRESOLVED_MODEL_REGEXP)?.[1];
51:
52:   if (unresolvedModel) {
53:     return (
54:       <Container setError={setError}>
55:         <InvalidModel model={unresolvedModel} />
56:       </Container>
57:     );
58:   }
```

服务不可用与「模型未拉取」是两条独立路径（47 行 vs 50–57 行）。后者从原始错误消息中抽出具体模型名（32、50 行）传给修复组件（55 行），异常反馈直接指向可操作对象，而非展示一段错误文本。`setError` 透传（39、41 行）使错误可被清除。

**证据 2 — Dify：额度耗尽用警示色 + 独立图标，优先于凭据名展示**

`/tmp/opencode/ref-repos/langgenius_dify/web/app/components/header/account-setting/model-provider-page/model-selector/popup-item.tsx`

```
162:                   ) : (
163:                     <>
164:                       <span
165:                         aria-hidden="true"
166:                         className="i-ri-alert-fill size-3 shrink-0 text-text-warning-secondary"
167:                       />
168:                       <span className="ml-1 truncate text-text-warning">
169:                         {t(($) => $['modelProvider.selector.creditsExhausted'], {
170:                           ns: 'modelProvider',
171:                         })}
172:                       </span>
173:                     </>
174:                   )
```

异常态在三元链中占据优先分支（162–174 行），排在凭据名之前。装饰图标 `aria-hidden`（165 行）由文字承担语义，警示色走 `text-text-warning` 系令牌（166、168 行），不引入裸色值。

**采用决策**：异常反馈采用「按错误类型分流到具体修复动作」，并把可恢复提示排在对象信息之前。Climber 任务 40/41/42 的失败态统一按此组织：`ApiKeysPage` 的凭据失效、`PluginsPage` 的启动失败、`DoctorPage` 的健康检查失败各自给出可点击的下一步，而非统一一句「操作失败」。

**适配限制**：上游正则匹配英文错误串（`CheckError.tsx:32`）绑定特定服务端实现，Climber 后端错误码与文案均未冻结，此路径不可直接移植。可迁移的是「先分类再渲染」的结构，具体分类依据须先完成任务 13 的字段来源表。

### 3.5 任务 08 映射

| Climber 落点 | 采用项 | 适配限制 |
| --- | --- | --- |
| 36 `AgentsPage` / 39 资源列表 | 固定行高 + 单开展开 + 显式超扫（§3.1） | 不引入窗口化，避免破坏 `role="list"` 与方向键契约 |
| 40 `SettingsPage` / `ModelConfig` | 单一加载守卫 + 两段式详情（§3.2 证据 2） | 防抖输入不适用于显式保存模型 |
| 40 凭据选择 / 41 MCP 配置 | 穷举变体 + 权限位分离（§3.3） | `credits-*` 五态无数据来源，须剔除 |
| 40 / 41 / 42 失败态 | 按类型分流到修复动作（§3.4） | 错误分类依据待任务 13 字段来源表冻结 |

---

## 4. 任务 22：会话分组、过滤与真实上下文摘要

**真实三态：未开始。**

### 4.1 当前实现核对

`frontend-react/src/components/workspace/SessionSidebar.tsx`

```
270:       <div className="min-h-0 flex-1 overflow-y-auto p-2" aria-busy={loadingSessions}>
...
277:         <ul aria-labelledby={headingId} className="space-y-1">
278:         {sessions.map((s, idx) => (
```

- 第 309–310 行是单一 `<ul>` + `sessions.map`，无分组容器、无分组标题、无 `role="group"`。
- 全文件检索 `group|filter|confirm|undo` 只命中 1 处，是第 313 行 Tailwind `group` 类名（用于行内 hover 样式），与会话分组无关。
- 时间格式化仅出现 1 处，属检查点区域：

```
377:                 <span className="text-[var(--color-text-muted)]">{new Date(msg.timestamp).toLocaleTimeString()}</span>
```

会话行本身不渲染任何时间。

- 删除路径为直接调用，无确认与撤销：

```
181:       await api.deleteSession(id);
...
193:     deleteSession(id);
195:   }, [deleteSession, refreshSessions, sessions]);
```

`api.deleteSession` 失败走 `deleteError` 提示（255–259 行 `role="alert"`），成功即从 store 移除。任务 22 要求的「删除有确认或已实现的可撤销机制」两者皆无。

### 4.2 前置条件已就绪的部分

- `src/store/workspace.ts:60-64`：`tokenUsage?: SessionTokenUsage` 为可选，注释明确「Absent until a backend payload actually reports it」，编造的 `{ used: 0, limit: 200000 }` 已移除（V10 的修复在本轮仍然成立）。
- `src/store/workspace.ts:94-99`：`normalizeSessionStatus` 把未识别状态归入 `unknown`，注释写明「which every surface renders as 'not reported'」。

因此「未知上下文」的数据语义已在 store 层建立，但 `SessionSidebar` 未读取 `tokenUsage`，也未把 `unknown` 状态与「上下文未上报」区分呈现。任务 22 的四项验收标准中，时间分组、标题过滤、删除确认或撤销全部未实现；未知上下文区分仅在数据层就绪。

---

## 5. 任务 24：可解释的命令匹配排序

**真实三态：未开始。**

### 5.1 当前实现核对

`frontend-react/src/components/workspace/CommandPalette.tsx`

```
33:   const filtered = useMemo(() => {
34:     if (!query.trim()) return allItems.slice(0, MAX_DEFAULT_RESULTS);
35:     const q = query.trim().toLowerCase();
36:     return allItems.filter(item =>
37:       item.label.toLowerCase().includes(q) ||
38:       item.keywords.toLowerCase().includes(q) ||
39:       item.group.toLowerCase().includes(q)
40:     );
41:   }, [query, allItems]);
```

- 第 36–40 行是布尔 `filter`，三路 `includes` 或运算。命中即保留，顺序完全由 `allItems` 的原始声明顺序决定，无任何打分或分档。
- 第 34 行空查询规则为 `slice(0, 8)`，`MAX_DEFAULT_RESULTS = 8`（第 7 行），前 8 项按声明顺序硬取。任务 24 要求的「空查询推荐规则写明」缺失——代码里有行为，文档与测试里没有规则说明。
- 无拼写偏差容错：英文查询无编辑距离，中文查询无分词或首字母匹配。

### 5.2 缺失项逐条对照

| 任务 24 验收标准 | 现状 |
| --- | --- |
| 完整名称 / 前缀 / 关键词 / 模糊匹配的优先级 | 无。仅三路并列 `includes`（37–39 行） |
| 稳定同分规则 | 不适用——无分数，顺序即声明顺序 |
| 全部 25 项可搜索 | 满足（`allItems` 来自 `ALL_NAV_ITEMS_BASE`，24–31 行，无硬编码白名单） |
| 中英文、空白、拼写偏差与无命中的确定测试 | 未找到证据。`src/components/workspace/__tests__/CommandPalette.test.tsx` 覆盖键盘导航与边界（任务 23），未覆盖匹配算法分级 |
| 空查询推荐规则写明 | 未成文。第 34 行为实现，规则说明缺失 |

`ALL_NAV_ITEMS_BASE` 的 25 项与 `keywords` 字段为算法提供了完整输入，实现成本集中在打分函数与同分排序，属于可直接落地的改造，无需后端配合。

---

## 6. 任务 26：统一应用导航与搜索结果去向

**真实三态：未开始。**

### 6.1 当前实现核对

`frontend-react/src/components/workspace/GlobalSearch.tsx`

```
 48: interface GlobalSearchProps {
 49:   isOpen: boolean;
 50:   onClose: () => void;
 51: }
```

Props 只有开关与关闭（48–51 行），没有 `onNavigate` 或任何跳转出口。命令面板有 `onNavigate`（`CommandPalette.tsx:11`），搜索组件缺失同一能力。

```
157:               } else if (event.key === 'Enter' && filtered[activeIndex]) {
158:                 // Enter reveals the full preview of the highlighted result.
159:                 event.preventDefault();
160:                 const key = resultKey(filtered[activeIndex]);
161:                 setExpanded(expanded === key ? null : key);
162:               }
```

Enter 分支（157–162 行）只做 `setExpanded` 切换，输入框焦点不动，无路由变化。`RESULT_TYPES` 只有 `document` / `memory` / `group` 三类（第 13 行），三类均无对应详情页，因此「有详情页的结果定位真实对象」当前无对象可定位。

### 6.2 缺失项逐条对照

| 任务 26 验收标准 | 现状 |
| --- | --- |
| 完成任务 09 的全部入口核对 | 阻塞。任务 09 自身为进行中，25 项入口/组件/主操作/接口/三态矩阵未成文 |
| 路由高亮/标题一致 | 未验证。当前 `e2e/01-navigation.spec.ts` 只断言 hash 与标题（15–35 行） |
| 有详情页的结果定位真实对象 | 无实现。无导航回调；`document` / `memory` / `group` 也无详情路由 |
| 无详情页明确标为预览 | 部分。Enter 后有 `expanded` 预览态（161 行），但界面无「预览，不可跳转」的显式标识 |
| 切页保留有效会话，失效对象有反馈 | 未实现。无切页动作，因此无失效对象处理路径 |
| 移动端可访问其余功能的入口 | 归任务 47。`AdaptiveMobileLayout` 已有 More 入口，本项未处理搜索结果的移动端去向 |

---

## 7. 任务 46：双主题视觉与品牌回归

**真实三态：未开始。**

### 7.1 现有截图资产核对

`frontend-react/artifacts/ui-acceptance/` 有 3 个 PNG，读取实测尺寸：

| 文件 | 尺寸 | 主题 | 路由 | 主内容 |
| --- | --- | --- | --- | --- |
| `desktop-1440.png` | 1440 × 1000 | light | `#dashboard` | 空白（后端未起） |
| `tablet-768.png` | 768 × 1024 | light | 未记录 | 空白 |
| `mobile-375.png` | 375 × 812 | light | Settings | 仅「Loading」骨架 |

三者均为亮色单主题、单路由、无基线对比、无差异记录，与任务 46 要求的「1440×900 亮暗截图覆盖各路由和主状态」差距为全部主状态与全部暗色场景。`desktop-1440.png` 的导航清单虽然完整可见（CORE 12 项 + MANAGE 3 项），但主内容区空白，无法用于任何视觉判读。

### 7.2 缺失的基础设施

| 任务 46 验收标准 | 现状 |
| --- | --- |
| 亮暗双主题截图 | 只有 light。主题开关由 `src/hooks/useTheme.tsx:47,68-74`（`localStorage['climber-theme']` + `<html data-theme>`）控制，测试可直接注入 |
| 覆盖各路由 | 只有 dashboard 与 settings 两个路由 |
| 覆盖主状态 | 无。空图即无状态覆盖 |
| 对比度 4.5:1 / 3:1 实测 | 无任何测量记录。`src/index.css:218` 的 `[data-theme="light"]` 覆盖块与 `src/index.css:6` 的 `@custom-variant dark` 未被量化验证 |
| 硬编码色逐项解释或迁移 | 未开始。`src/components/charts/BarChart.tsx` 在本轮工作树中被修改，但无逐项解释文档 |
| 截图差异经人工确认 | 无基线即无差异 |

### 7.3 可执行方案（Playwright，双主题 × 主要页面）

以下方案基于项目已有设施，不需要新增依赖。参考实现为 LibreChat 的双主题视觉回归（见 `ROUND11_ACCEPTANCE_CHECKLIST_2026-09-26.md` §2）。

**第 0 步：主题注入与断言。** 复用 `e2e/helpers.ts:3-10` 的 `gotoApp` 模式，扩展出 `gotoAppWithTheme(page, theme)`：

```ts
async function gotoAppWithTheme(page: Page, theme: 'light' | 'dark') {
  await page.addInitScript((t) => {
    localStorage.setItem('i18next_lng', 'en');
    localStorage.setItem('climber-theme', t);
  }, theme);
  await page.goto('/');
  // useTheme.tsx:70-71 会把 data-theme 写到 <html>，等它落位再截图
  await expect(page.locator('html')).toHaveAttribute('data-theme', theme);
  await page.evaluate(() => document.fonts.ready);
}
```

`data-theme` 属性断言直接对应 `useTheme.tsx:71`，可防止主题未生效时的假基线。

**第 1 步：配置独立套件。** 新增 `e2e/playwright.config.visual.ts`，从 `playwright.config.ts` 继承并改三处：`testMatch: /.*visual\.spec\.ts/`、`retries: 0`（基线比对不允许重试掩盖偶发像素）、`testDir: './e2e'`。`retries: 0` 与 LibreChat `playwright.config.a11y.ts:10`、`playwright.config.benchmark.ts:23` 的选择一致：测量类套件的重试会污染基线。

**第 2 步：数据来源用路由拦截，不依赖后端。** 后端未启动时空白截图无判读价值。用 `page.route` 固定 API 响应，使每个页面渲染出确定内容：

```ts
await page.route(/\/api\/v1\/sessions/, route => route.fulfill({
  status: 200, contentType: 'application/json',
  body: JSON.stringify(SESSION_FIXTURE),   // 20 会话，含 running/failed/completed/unknown 四种状态
}));
```

夹具需覆盖四种主状态（正常列表、加载中、请求失败、空列表）与三态原语（`EmptyState`、`PanelState` 的 loading/error 分支）。

**第 3 步：页面矩阵。** 双主题 × 主要页面，建议 12 组起步：

| 主题 | 页面 |
| --- | --- |
| light / dark | `#chat`（消息区 + 工具调用 + 推理折叠 + 输入区增长态） |
| light / dark | `#agents`（0 / 1 / 多项 + 长名称 + 删除确认） |
| light / dark | `#settings`（凭据已配置 / 未配置 / 需配置三态） |
| light / dark | 命令面板打开态 + 全局搜索打开态（弹层、双主题下的 overlay 与 border） |
| light / dark | 右面板四分组全展开 |

覆盖口径参照 LibreChat `message-visual.spec.ts:22-26` 的 `THEMES × VIEWPORTS` 矩阵结构，但本项目 46 任务只要求 1440×900 单视口，故视口维度省略。

**第 4 步：比对参数。**

```ts
const VISUAL_OPTIONS = {
  animations: 'disabled' as const,
  caret: 'hide' as const,
  maxDiffPixels: 20,
  scale: 'css' as const,
};
```

参数取自 LibreChat `message-visual.spec.ts:29-34`，四项各有明确作用：关动画与光标消除时序噪声，`maxDiffPixels: 20` 为绝对像素容差，`scale: 'css'` 保证 1 CSS px = 1 图像 px。`reduced-motion` 规则已存在于 `src/index.css`，与 `animations: 'disabled'` 方向一致。

**第 5 步：基线生成与平台固定。** 基线只在 Linux CI 镜像上生成，用 `test.skip(process.platform !== 'linux', ...)` 固定平台，理由与实现参照 LibreChat `message-visual.spec.ts:91`。基线目录建议 `e2e/__snapshots__/visual/`，与 `playwright.config.ts` 的 `outputDir` 分离，避免 `globalTimeout: 15 * 60_000`（第 9 行）触发清理时被删。

**第 6 步：对比度实测，作为截图之外的独立证据。** 截图比对无法回答「普通文字是否达 4.5:1」。用 `page.evaluate` 读取计算样式与实际背景色做相对亮度计算，对每页每个令牌对输出一次测量：

```ts
const RATIOS = await page.evaluate(() => {
  // 对每个 [data-theme] 下取 --color-text-primary/secondary/muted 与
  // --color-bg-surface-1/2/3 的计算值，转 sRGB 后算 WCAG 相对亮度比
  // 字号 >= 18.66px 或 >= 14px bold 走 3:1，其余走 4.5:1
});
```

令牌清单来源为 `src/index.css:12-192`（暗色）与 `src/index.css:218-260`（亮色覆盖）。结果落盘为 JSON，与截图基线同目录，形成两条独立证据链：像素一致性 + 数值合规性。

**第 7 步：硬编码色登记。** 对 `src/pages`、`src/components`、`src/layout` 扫描裸色值（hex、`rgb(`、`hsl(`），逐条登记为「已迁移为令牌」或「已验证的例外 + 理由」。此项可与 V8 的中文扫描合并为同一脚本，同批落盘。

**执行顺序约束**：46 依赖任务 11 的令牌清单与 44 的状态原语接入面（V15 当前 9/25 页）。在 44 收敛前，基线会随页面改造频繁失效。建议先完成 44 的 16 页接入，再生成基线。

---

## 8. 任务 48：长列表与流式性能回归

**真实三态：未开始。**

### 8.1 当前实现核对

`frontend-react/src/useChat.ts` — 流式更新的成本模型：

```
100:           setMessages(prev =>
101:             prev.map(msg =>
102:               msg.id === assistantId
103:                 ? { ...msg, reasoning: (msg.reasoning || '') + event.delta }
104:                 : msg
105:             )
106:           );
```

```
126:         case 'tool_result': {
127:           setMessages(prev =>
128:             prev.map(msg => {
```

七个事件分支（`content` / `reasoning` / `tool_call` / `tool_result` / `done` / `error`）每一个都执行一次全量 `prev.map(...)`。`grep -c "throttle|debounce|batch|requestAnimationFrame" src/useChat.ts` 返回 **0**，即无节流、无批处理、无帧对齐。每个 SSE 分片触发一次 O(n) 数组拷贝与 n 个消息对象的浅比较。

`frontend-react/src/components/agent/ChatInterface.tsx`：

```
357:             <div data-transcript className="flex flex-col gap-5">
358:               {messages.map(msg => (
359:                 <React.Fragment key={msg.id}>{renderMessage(msg)}</React.Fragment>
360:               ))}
361:             </div>
```

消息区全量渲染，1000 条消息即 1000 次 `renderMessage(msg)` 调用。`src/components/chat/MessageContent.tsx` 检索 `memo|useMemo` 无命中，消息组件未做记忆化，因此任一分片到达都会重跑全部消息的渲染。

`frontend-react/src/components/workspace/SessionSidebar.tsx:309-310`：`sessions.map` 平铺，无虚拟化。

`@tanstack/react-virtual` 在 `package.json:34` 声明为依赖，`grep -rn "react-virtual|useVirtualizer" src/` 返回 0 处使用——依赖已引入但未落地。

全仓无性能测试文件，无基线记录。

### 8.2 可执行方案（基线测量）

以下方案分四条，全部可在本地无后端条件下执行，测量对象与任务 48 验收标准「仅本地功能性能验证」一致。

**测量 A — 长列表交互延迟 p95。** 目标：筛选与切会话 10 次采样，p95 ≤ 200ms。

固定数据集：200 会话（`api/sessions` 夹具，标题长度分 3 档：10 / 60 / 200 字符，覆盖截断与换行两种形态），状态覆盖 `running` / `failed` / `unknown`。

```ts
// 每次采样：注入 200 会话 → 触发筛选键入 → 等首行可见 → 记录耗时
const t0 = performance.now();
await filterInput.fill(query);
await firstRow.waitFor({ state: 'visible' });
samples.push(performance.now() - t0);
```

夹具注入走 `page.route`，与 46 第 2 步同源。10 次采样取 p95，计算方式参照 LibreChat `e2e/benchmarks/agent-startup.latency.spec.ts:87-107` 的 `percentile` 与 `summarize`（线性插值 + p50/p95/mean/min/max 五值）。

**测量 B — 流式渲染上界。** 目标：1000 条消息下流式追加时长任务可控。

固定数据集：1000 消息（`api/sessions/{id}/messages` 夹具），其中 1 条为正在流式输出的助手消息。

用 `PerformanceObserver` 采集 longtask，并以渲染次数为辅助指标：

```ts
const observer = new PerformanceObserver(list => {
  for (const entry of list.getEntries()) longTasks.push(entry.duration);
});
observer.observe({ entryTypes: ['longtask'] });
```

阈值口径参照 LibreChat `e2e/benchmarks-reasoning/reasoning-stream.perf.spec.ts` 的三类上界：

```
192:     expect(thinkingContentRenders).toBeLessThan(framesUpperBound);
195:     expect(thinkingContentRenders).toBeLessThan(thinkChunks / 4);
...
215:     expect(worstLongTask).toBeLessThan(250);
216:     expect(longTaskTotal).toBeLessThan(streamMs * 0.1);
217:     expect(streamTotals.time).toBeLessThan(streamMs * 0.25);
```

- `renders < chunks / 4`（195 行）：渲染次数必须显著低于分片数，直接暴露「每片一次 setState」模式。Climber 当前 `useChat.ts:100-171` 满足不了这条。
- `worstLongTask < 250`（215 行）：单次长任务上限。
- `longTaskTotal < streamMs * 0.1`（216 行）：长任务总时长占流式窗口 10% 以内。
- `streamTotals.time < streamMs * 0.25`（217 行）：脚本总执行占流式窗口 25% 以内。

这四条把「卡顿」从主观描述变成可断言的数值。分片速率必须固定（LibreChat 在 `playwright.config.reasoning-perf.ts:20-24` 用 `MOCK_LLM_CHUNK_DELAY_MS = '1'` 钉死并注明「Pinned, not defaulted: the render-count thresholds are calibrated against this delivery rate」），Climber 侧需用 `page.route` 模拟 SSE 响应体并固定 `delta` 间隔。

**测量 C — 监听器与请求无泄漏。** 目标：连续开关面板无累计增长。

```ts
// 开启前
const before = { listeners: 0, requests: 0 };
page.on('request', () => before.requests++);
// 20 轮「开右面板 → 关闭 → 等待卸载」
const after = { listeners: 0, requests: 0 };
// 断言 after.listeners <= before.listeners + 常数，且 20 轮的请求数呈线性而非超线性
```

`PanelState.tsx` 已有取消旧请求写入（`RIGHT_PANEL_SPEC_2026-09-26.md` §5 与任务 30 证据），本测量验证其在真实挂载/卸载下成立。`useChat.ts:173` 的 effect 依赖 `[sessionId, isStreaming]`，`useTheme.tsx:76-93` 的 `matchMedia` 监听有 cleanup，这两处是重点观测对象。

**测量 D — 滚动位置稳定。** 目标：流式追加不抢滚动。

```ts
await transcript.evaluate(el => el.scrollTop = 240);  // 手动上滚
// 追加 50 个分片
const kept = await transcript.evaluate(el => el.scrollTop);
expect(kept).toBe(240);   // 手动上滚位置保持
// 另测：一键回最新按钮后 scrollTop 应贴底
```

`ChatInterface.tsx` 已有 `scrollRef` 与 `followOutput` 控制（`SOURCE_DESIGN_REVIEW_20_2026-09-26.md` §2.2 第 32 行记录），本测量给出该机制的数值证据。

**机器与基线记录。** 每次运行必须记录 `availableParallelism()`、`loadavg()`、浏览器版本、视口尺寸与数据集规模，写入与 LibreChat `agent-startup.latency.spec.ts:338-362` 同结构的 JSON 报告（`cold` / `warmups` / `samples` / `host` / `raw` / `summary` 六个字段），并用 `testInfo.attach` 落盘。缺少 `host` 与 `raw` 的性能数字无法跨机比较，等于没有基线。

**实施前提。** 测量 B 的四条阈值中，`renders < chunks / 4` 在当前 `useChat.ts` 实现下必然失败。因此 48 的基线测量会立刻暴露需要先做的两处改造：分片节流或帧批处理，以及消息组件 `memo`。建议 48 按「先跑测量拿到失败基线 → 按数据改造 → 复测达标」推进，改造前先执行 A、C、D 三项（这三项当前预期可过或接近通过），避免一次性改动面过大。

---

## 9. 任务 50：跨模块验收与交付结项

**真实三态：未开始。**

任务 50 的验收标准是「前置任务全部满足各自标准」，因此其状态完全由前置项决定。当前门槛缺口：

| 门槛 | 状态 | 证据 |
| --- | --- | --- |
| 46 双主题视觉与品牌回归 | 未开始 | §7，无基线无对比度实测 |
| 48 长列表与流式性能回归 | 未开始 | §8，无性能测试无基线 |
| 49 当前快照全量自动验证 | 进行中 | 账本第 3 节 V1–V4 通过；D3 构建产物为 10:36 旧快照、D6 Playwright 未执行 |
| 22 / 24 / 26 实现类缺口 | 未开始 | §4、§5、§6 |
| 串行联调链路 | 无记录 | 配置模型→建会话→发送/停止→工具/权限→产物/错误恢复 |

补充事实：`frontend-react/e2e/02-agents.spec.ts` 与 `e2e/helpers.ts` 在本轮工作树中已修改（`git status --porcelain` 显示 ` M`），修改内容是选择器适配（`article[aria-label=...]` 改 `li[aria-label=...]`、`[data-dropdown-trigger]` 改 `button[aria-label]`）与 429 退避重试（`e2e/helpers.ts:23-30`）。这说明 E2E 存在适配需求，且**尚未在修改后的代码上执行过一次**——`02-agents.spec.ts` 的新选择器是否与 `AgentsPage` 当前 DOM 匹配，尚无任何验证。

`frontend-react/scripts/acceptance-session-sync.cjs` 存在一条会话同步验收脚本（`POST /sessions → 打开 /#chat → 断言侧栏出现 → 点击后 ControlBar 标题一致 → 右栏 config 展示该会话数据 → 清理`），它是串行联调链路的现成骨架，但需要 `localhost:8000` 后端在线，且本轮无执行记录。

---

## 10. 并行工作流对本节结论的影响

核验期间（12:13–12:29）`frontend-react/src` 与 `frontend-react/scripts` 有并行工作流在改动，本节已在定稿前按最新工作树复核行号。观察到三处变化：

| 文件 | mtime | 变化 | 对本节结论的影响 |
| --- | --- | --- | --- |
| `src/components/workspace/SessionSidebar.tsx` | 12:24:36 | 行号整体下移（列表由 277–278 移至 309–310，时间格式化由 377 移至 409，删除由 181/193 移至 187/199） | 无。`group\|filter\|confirm\|undo` 复检仍为 0 命中，任务 22 仍为未开始 |
| `src/index.css` | 12:20:47 | `[data-theme="light"]` 由 197 移至 218 | 无。46 仍缺实测记录 |
| `scripts/check-translations.py` | 12:28:36 | **已重写** | 见下 |

翻译检查脚本的重写直接消解了账本第 3 节的 D2：

```
22: LOCALES_DIR = PROJECT_ROOT / "src" / "locales"
24: LEGACY_LOCALES_DIR = PROJECT_ROOT / "public" / "locales"
...
132: def report_legacy_drift() -> Dict:
133:     """Compare the legacy public/locales copy against the runtime src/locales.
...
135:     This never affects the exit code: the legacy tree is dead weight at runtime,
136:     so the actionable signal is that the two trees have drifted apart.
```

脚本现已读取运行时目录 `src/locales`（第 22 行），旧的 `public/locales` 降级为不影响退出码的漂移警告（第 24、132–136 行）。因此：

- **D2 与门槛项 G-4 的脚本侧前置已解除。** 仍需在当前快照重跑一次记录退出码与实际键数，V4 的「6 语言 328 键」结论不可直接沿用。
- 本节未执行该脚本，故 G-4 不标完成。

**行号稳定性提示**：本节所有 `frontend-react/src` 行号基于 12:29 的工作树。并行工作流仍在推进，行号可能再次位移。复核时应以符号名与检索关键字为主（本文 §10 的 W1–W14 已给出可复现的检索式），行号作为定位辅助。

## 10. 本轮核验方式说明

| 编号 | 核验方式 | 结论 |
| --- | --- | --- |
| W1 | 读取 `CommandPalette.tsx:24-41` | 三处 `includes` 并列布尔过滤，无评分 |
| W2 | 读取 `GlobalSearch.tsx:48-51,157-162` | Props 无导航回调；Enter 仅切 `expanded` |
| W3 | 读取 `SessionSidebar.tsx:308-310,409` + 全文件 `group\|filter\|confirm\|undo` 检索 | 无分组、无过滤、无确认/撤销；唯一时间格式化属检查点 |
| W4 | 读取 `useChat.ts:100-171` + 检索 `throttle\|debounce\|batch\|requestAnimationFrame` | 7 个事件分支各一次全量 `setMessages(prev => prev.map)`；节流关键词 0 命中 |
| W5 | 读取 `ChatInterface.tsx:357-361`、`MessageContent.tsx` 检索 `memo` | 消息区全量渲染，消息组件未记忆化 |
| W6 | 检索 `react-virtual\|useVirtualizer` 于 `src/` | 0 命中；依赖声明在 `package.json:34` |
| W7 | 读取 `artifacts/ui-acceptance/*.png` 三张并实测尺寸 | 3 张单主题单路由截图，主内容空白，无基线无差异记录 |
| W8 | 读取 `useTheme.tsx:47,68-74`、`index.css:6,218`、`playwright.config.ts:12-13,29-40` | 主题可经 `localStorage['climber-theme']` 注入；E2E 有 chromium/mobile 双 project、CI retries 2、forbidOnly |
| W9 | 检索 `TerminalPage\|WorkflowsPage\|NotificationsPage\|DoctorPage\|EvalPage\|CostPage` 于 `src/pages/__tests__/` | 0 命中，V17 仍成立（13 个测试文件，无上述六项） |
| W10 | 检索 `useAsyncData\|EmptyState` 于 `src/pages/*.tsx` | 9 页命中，V15 仍成立 |
| W11 | 读取 OpenHands 4 文件、Cline 3 文件、LobeHub 3 文件、Dify 2 文件、LibreChat 2 文件、CopilotKit 1 文件 | 任务 07 共 8 处、任务 08 共 8 处、结项验收清单 15 处，全部带行号 |
| W12 | 枚举 `SWE-agent_SWE-agent` 全部 HTML | 4 个，无 React/Vue/Svelte 组件；证据层级降级为轨迹/文档级 |
| W13 | `git status --porcelain` | 202 项变更，`frontend-react/src` 166 项；`e2e/02-agents.spec.ts`、`e2e/helpers.ts`、3 张截图为 ` M` |
| W14 | `git log --oneline -3` | HEAD `c0ab630a`（2026-09-26 04:03:40 UTC）；本轮未新增提交 |

未执行任何命令验证：typecheck、lint、build、Vitest、Playwright。本次判定基于源码读取与文件检索，账本第 3 节的 V1–V20 证据仍为当前唯一的命令级证据。
