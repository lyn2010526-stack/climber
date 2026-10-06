import { create } from 'zustand';
import { api, ApiRequestError } from '../api';
import i18n from '../i18n/config';

/**
 * 锚定式三栏 UI 的状态层。
 *
 * 职责边界：会话、消息、权限等业务事实仍以 `store/workspace.ts` 与后端为唯一
 * 真相来源；这里只承载"界面本身"的状态——面板显隐（按触发规则自动执行）、
 * 弹窗栈（输入区上方堆叠、完成即销毁）、任务看板、子 Agent 任务树、文件
 * 预览与规则编辑。所有数值型指标（Token、缓存命中率）只保存后端上报的值，
 * 上报缺失时保持 `null`，界面据此显示"未上报"，绝不用本地估值冒充。
 */

/** 底部状态栏的四种 Agent 状态（异常之外的三种 + 异常）。 */
export type AgentRunState = 'thinking' | 'executing_tool' | 'awaiting_input' | 'error';

/** Pi 外层循环快照：轮数、当前子输入、已完成项与两队待办。 */
export interface LoopStatusSnapshot {
  outerRound: number;
  currentInput: string;
  completed: string[];
  followupQueue: string[];
  steeringQueue: string[];
  noProgressCount: number;
}

/** 任务看板三泳道。 */
export type TaskLane = 'pending' | 'running' | 'completed';

export interface AnchoredTask {
  id: string;
  name: string;
  lane: TaskLane;
  /** 阻塞原因：存在即按阻塞任务渲染（红色边框 + 底部小字）。 */
  blockedReason?: string;
  updatedAt: number;
}

export interface SubAgentNode {
  id: string;
  name: string;
  status: 'running' | 'success' | 'error';
  /** 后端未上报耗时时保持 undefined，界面显示"未上报"。 */
  durationMs?: number;
  detail?: string;
  children: SubAgentNode[];
}

/** 弹窗栈成员：审批 / 参数配置 / 输入确认。完成或取消后销毁。 */
export interface AnchoredPopup {
  id: string;
  kind: 'approval' | 'params' | 'confirm';
  title: string;
  description?: string;
  /** approval */
  severity?: 'low' | 'medium' | 'high';
  command?: string;
  path?: string;
  /** params */
  fields?: Array<{ key: string; label: string; value: string; placeholder?: string }>;
  /** confirm / params */
  confirmLabel?: string;
  payload?: Record<string, unknown>;
}

export type PreviewLineMarker = 'add' | 'del' | 'change' | 'ctx';

export interface FilePreviewEntry {
  id: string;
  name: string;
  path: string;
  lines: Array<{ marker: PreviewLineMarker; text: string }>;
}

export interface RuleDocument {
  id: string;
  kind: 'soul' | 'memory' | 'project';
  title: string;
  content: string;
  revision: string | null;
  scope: 'user';
}

function ruleError(error: unknown): string {
  if (error instanceof ApiRequestError && error.data && typeof error.data === 'object' && 'detail' in error.data) {
    const detail = (error.data as { detail?: unknown }).detail;
    if (typeof detail === 'string') return detail;
  }
  return error instanceof Error ? error.message : i18n.t('store_anchored.rule_request_failed');
}

/** Default account rule entries, localized at creation time. */
function defaultRuleEntries(): RuleDocument[] {
  return [
    { id: 'soul', kind: 'soul', title: i18n.t('store_anchored.rule_soul'), content: '', revision: null, scope: 'user' },
    { id: 'memory', kind: 'memory', title: i18n.t('store_anchored.rule_memory'), content: '', revision: null, scope: 'user' },
    { id: 'project', kind: 'project', title: i18n.t('store_anchored.rule_project'), content: '', revision: null, scope: 'user' },
  ];
}

/** 右侧信息面板卡片的固定顺序与默认展开态。 */
export type InfoCardId = 'taskBoard' | 'tokenMeter' | 'subAgentTree' | 'filePreview' | 'ruleEditor' | 'memoryArchive';

export const INFO_CARD_ORDER: readonly InfoCardId[] = [
  'taskBoard',
  'tokenMeter',
  'subAgentTree',
  'filePreview',
  'ruleEditor',
  'memoryArchive',
];

const DEFAULT_CARD_OPEN: Record<InfoCardId, boolean> = {
  taskBoard: true,
  tokenMeter: true,
  subAgentTree: false,
  filePreview: false,
  ruleEditor: false,
  memoryArchive: false,
};

/** 配置档：切换全局生效，同步调整 UI 复杂度与右侧面板数量。 */
export type ProfileId = 'minimal' | 'standard' | 'full';

export const PROFILE_ORDER: readonly ProfileId[] = ['minimal', 'standard', 'full'];

/** 每个配置档可见的右侧卡片集合；切换时未收录的卡片自动收起。 */
export const PROFILE_CARDS: Record<ProfileId, readonly InfoCardId[]> = {
  minimal: ['taskBoard'],
  standard: ['taskBoard', 'tokenMeter'],
  full: INFO_CARD_ORDER,
};

/** 一轮回合的用量；任何来源未上报的字段保持 null。 */
export interface TurnUsage {
  input: number | null;
  output: number | null;
  cacheSaved: number | null;
  total: number | null;
}

/** Token 计量仪表盘的六个指标；后端未上报的一律 null。 */
export interface MeterSnapshot {
  cumulativeInputTokens: number | null;
  cumulativeOutputTokens: number | null;
  cacheHitRate: number | null;
  estimatedCost: number | null;
  todayTokens: number | null;
  avgTurnTokens: number | null;
}

const EMPTY_METER: MeterSnapshot = {
  cumulativeInputTokens: null,
  cumulativeOutputTokens: null,
  cacheHitRate: null,
  estimatedCost: null,
  todayTokens: null,
  avgTurnTokens: null,
};

const PROFILE_STORAGE_KEY = 'anchored.active-profile';
const TREND_WINDOW = 10;

function readStoredProfile(): ProfileId {
  try {
    const raw = localStorage.getItem(PROFILE_STORAGE_KEY);
    return raw === 'minimal' || raw === 'standard' ? raw : 'full';
  } catch {
    return 'full';
  }
}

function writeStoredProfile(profile: ProfileId): void {
  try {
    localStorage.setItem(PROFILE_STORAGE_KEY, profile);
  } catch {
    // 忽略持久化失败：配置档仅是本地偏好。
  }
}

/** 配置档生效：未收录的右侧卡片一律收起。 */
export function applyProfileToCards(
  open: Record<InfoCardId, boolean>,
  profile: ProfileId,
): Record<InfoCardId, boolean> {
  const allowed = PROFILE_CARDS[profile];
  const next = { ...open };
  for (const card of INFO_CARD_ORDER) {
    if (!allowed.includes(card)) next[card] = false;
  }
  return next;
}

/** 计量指标标签的固定顺序（TokenMeter 渲染与快照测试共用）。 */
export const METER_ORDER: ReadonlyArray<{ key: keyof MeterSnapshot; labelKey: string }> = [
  { key: 'cumulativeInputTokens', labelKey: 'anchored.meter.cumulative_input' },
  { key: 'cumulativeOutputTokens', labelKey: 'anchored.meter.cumulative_output' },
  { key: 'cacheHitRate', labelKey: 'anchored.meter.cache_hit_rate' },
  { key: 'estimatedCost', labelKey: 'anchored.meter.estimated_cost' },
  { key: 'todayTokens', labelKey: 'anchored.meter.today_tokens' },
  { key: 'avgTurnTokens', labelKey: 'anchored.meter.avg_turn_tokens' },
];

export interface CostRecord {
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  created_at: string;
}

/** 把后端上报的用量与计费记录换算成仪表盘快照；缺失来源一律保持 null。 */
export function buildMeterSnapshot(
  usage: Record<string, unknown> | null | undefined,
  records: CostRecord[],
  now: number = Date.now(),
): { meter: MeterSnapshot; turnTrend: TurnUsage[] } {
  const numberAt = (value: unknown): number | null => (typeof value === 'number' && Number.isFinite(value) ? value : null);
  const dayStart = new Date(now);
  dayStart.setHours(0, 0, 0, 0);
  const rows = records.filter((row) => Number.isFinite(row.total_tokens));
  const recent = [...rows].sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()).slice(0, TREND_WINDOW).reverse();
  return {
    meter: {
      cumulativeInputTokens: rows.length ? rows.reduce((sum, row) => sum + (row.prompt_tokens || 0), 0) : null,
      cumulativeOutputTokens: rows.length ? rows.reduce((sum, row) => sum + (row.completion_tokens || 0), 0) : null,
      cacheHitRate: numberAt(usage?.['cache_hit_rate'] ?? usage?.['cacheHitRate']),
      estimatedCost: numberAt(usage?.['total_cost'] ?? usage?.['totalCost']),
      todayTokens: rows.length ? rows.filter((row) => new Date(row.created_at).getTime() >= dayStart.getTime()).reduce((sum, row) => sum + row.total_tokens, 0) : null,
      avgTurnTokens: recent.length
        ? Math.round(recent.reduce((sum, row) => sum + row.total_tokens, 0) / recent.length)
        : null,
    },
    turnTrend: recent.map((row) => ({
      input: numberAt(row.prompt_tokens),
      output: numberAt(row.completion_tokens),
      cacheSaved: null,
      total: numberAt(row.total_tokens),
    })),
  };
}

/** 触发规则表：任务结束 5 秒后自动折叠的三张卡片。 */
const AUTO_COLLAPSE_CARDS: readonly InfoCardId[] = ['taskBoard', 'subAgentTree', 'filePreview'];
const AUTO_COLLAPSE_DELAY_MS = 5000;

interface AnchoredState {
  agentState: AgentRunState;
  /** 状态栏补充文案（异常时携带原因）。 */
  agentStateMessage: string | null;
  cardsOpen: Record<InfoCardId, boolean>;
  /** 任务看板是否有"新任务"待展示（用于角标而非展开态本身）。 */
  tasks: AnchoredTask[];
  subAgentTree: SubAgentNode[];
  /** 失败工具的 id 集合：命中即自动展开该工具结果块。 */
  failedToolIds: string[];
  /** 正在执行中的工具 id 集合：驱动状态栏"执行工具"与卡片运行态。 */
  runningToolIds: string[];
  /** 本轮是否已进入规划阶段（任务看板已按触发规则展开）。 */
  planning: boolean;
  previews: FilePreviewEntry[];
  activePreviewId: string | null;
  rules: RuleDocument[];
  ruleDrafts: Record<string, string>;
  rulesLoaded: boolean;
  rulesLoading: boolean;
  ruleSavingId: string | null;
  ruleConflictId: string | null;
  rulesError: string | null;
  rulesMessage: string | null;
  popups: AnchoredPopup[];
  /** 以下指标后端未上报时保持 null。 */
  cacheHitRate: number | null;
  turnTokens: number | null;
  /** 激活配置档（本地持久化）；切换同步调整右侧面板可见集合。 */
  profile: ProfileId;
  /** Token 计量仪表盘快照与近 10 回合用量趋势。 */
  meter: MeterSnapshot;
  turnTrend: TurnUsage[];
  /** 回合结束自增，驱动仪表盘重新拉取计费数据。 */
  meterRefreshTick: number;
  /** Pi 外层循环最近一次快照；会话切换或流结束后的下一帧前保持现值。 */
  loopStatus: LoopStatusSnapshot | null;

  setAgentState: (state: AgentRunState, message?: string | null) => void;
  /** 触发规则⑪：写入外层循环快照（LOOP_STATUS 帧）。 */
  setLoopStatus: (snapshot: LoopStatusSnapshot | null) => void;
  /** 触发规则①：进入规划阶段 → 展开任务看板并登记规划任务。 */
  beginPlanning: (name?: string) => void;
  /** 触发规则②：开始调用工具 → 记录运行中工具、状态栏切"执行工具"。 */
  noteToolCall: (toolCallId: string, name: string) => void;
  /** 触发规则③：工具执行完成 → 结束运行态；失败则记录待自动展开。 */
  noteToolResult: (toolCallId: string, error?: string) => void;
  /** 触发规则⑩：出现错误 → 状态栏变红并携带原因。 */
  noteError: (message: string) => void;
  toggleCard: (card: InfoCardId) => void;
  setCardOpen: (card: InfoCardId, open: boolean) => void;
  setProfile: (profile: ProfileId) => void;
  setMeter: (snapshot: MeterSnapshot, turnTrend: TurnUsage[]) => void;
  addTask: (name: string, lane?: TaskLane) => void;
  moveTask: (id: string, lane: TaskLane) => void;
  expandForNewTask: (name: string) => void;
  expandForSubTask: (node: Omit<SubAgentNode, 'children'>) => void;
  markToolFailed: (toolCallId: string) => void;
  openFilePreview: (entry: Omit<FilePreviewEntry, 'id'>) => void;
  closeFilePreview: (id: string) => void;
  setActivePreview: (id: string) => void;
  loadRules: () => Promise<void>;
  setRuleDraft: (id: string, content: string) => void;
  saveRule: (id: string, content: string) => Promise<boolean>;
  pushPopup: (popup: Omit<AnchoredPopup, 'id'>) => string;
  resolvePopup: (id: string) => void;
  noteTurnStart: () => void;
  noteTurnEnd: () => void;
  setUsage: (usage: { cacheHitRate?: number | null; turnTokens?: number | null }) => void;
}

let popupSeq = 0;
let taskSeq = 0;
let previewSeq = 0;
let autoCollapseTimer: ReturnType<typeof setTimeout> | null = null;
let rulesEpoch = 0;
const initialProfile = readStoredProfile();

/** 由 useChat 派生"执行中"的判断需要它；保持为导出的纯函数便于测试。 */
export function turnIsSettled(isStreaming: boolean, hasError: boolean): boolean {
  return !isStreaming && !hasError;
}

export const useAnchoredStore = create<AnchoredState>((set, get) => ({
  agentState: 'awaiting_input',
  agentStateMessage: null,
  cardsOpen: applyProfileToCards({ ...DEFAULT_CARD_OPEN }, initialProfile),
  tasks: [],
  subAgentTree: [],
  failedToolIds: [],
  runningToolIds: [],
  planning: false,
  previews: [],
  activePreviewId: null,
  rules: defaultRuleEntries(),
  ruleDrafts: {},
  rulesLoaded: false,
  rulesLoading: false,
  ruleSavingId: null,
  ruleConflictId: null,
  rulesError: null,
  rulesMessage: null,
  popups: [],
  cacheHitRate: null,
  turnTokens: null,
  profile: initialProfile,
  meter: { ...EMPTY_METER },
  turnTrend: [],
  meterRefreshTick: 0,
  loopStatus: null,

  setAgentState: (state, message = null) =>
    set({ agentState: state, agentStateMessage: message ?? null }),

  setLoopStatus: (snapshot) => set({ loopStatus: snapshot }),

  /** 触发规则①：用户发起新任务进入规划 → 展开任务看板；默认不全展开其他卡片。 */
  beginPlanning: (name = '') => {
    if (autoCollapseTimer !== null) {
      clearTimeout(autoCollapseTimer);
      autoCollapseTimer = null;
    }
    const title = name.trim() || i18n.t('store_anchored.current_task');
    const id = `anchored-task-${Date.now()}-${taskSeq++}`;
    set((s) => ({
      planning: true,
      agentState: 'thinking',
      agentStateMessage: null,
      cardsOpen: { ...s.cardsOpen, taskBoard: true },
      tasks: [...s.tasks, { id, name: title, lane: 'pending', updatedAt: Date.now() }],
    }));
  },

  /** 触发规则②：开始调用工具 → 记录运行中工具、插入工具卡对应状态、状态栏切"执行工具"。 */
  noteToolCall: (toolCallId, _name) => {
    if (autoCollapseTimer !== null) {
      clearTimeout(autoCollapseTimer);
      autoCollapseTimer = null;
    }
    set((s) => ({
      agentState: 'executing_tool',
      agentStateMessage: null,
      runningToolIds: s.runningToolIds.includes(toolCallId)
        ? s.runningToolIds
        : [...s.runningToolIds, toolCallId],
    }));
  },

  /** 触发规则③：工具完成 → 移出运行态；失败则加入待展开集合并更新状态栏。 */
  noteToolResult: (toolCallId, error) => {
    const failed = Boolean(error && error.trim());
    set((s) => ({
      runningToolIds: s.runningToolIds.filter((id) => id !== toolCallId),
      failedToolIds: failed && !s.failedToolIds.includes(toolCallId)
        ? [...s.failedToolIds, toolCallId]
        : s.failedToolIds,
      agentState: failed ? 'error' : s.agentState,
      agentStateMessage: failed ? (error?.trim() ?? null) : s.agentStateMessage,
    }));
  },

  /** 触发规则⑩：出现错误 / 异常 → 状态栏变红，携带原因供提示与重试。 */
  noteError: (message) =>
    set({ agentState: 'error', agentStateMessage: message || null }),

  toggleCard: (card) =>
    set((s) => ({ cardsOpen: { ...s.cardsOpen, [card]: !s.cardsOpen[card] } })),

  setCardOpen: (card, open) =>
    set((s) => (s.cardsOpen[card] === open ? s : { cardsOpen: { ...s.cardsOpen, [card]: open } })),

  /** 配置档切换全局生效：未收录的右侧卡片自动收起，激活档持久化。 */
  setProfile: (profile) => {
    writeStoredProfile(profile);
    set((s) => ({ profile, cardsOpen: applyProfileToCards(s.cardsOpen, profile) }));
  },

  setMeter: (snapshot, turnTrend) => set({ meter: snapshot, turnTrend }),

  addTask: (name, lane = 'pending') =>
    set((s) => ({
      tasks: [
        ...s.tasks,
        {
          id: `anchored-task-${Date.now()}-${taskSeq++}`,
          name,
          lane,
          updatedAt: Date.now(),
        },
      ],
    })),

  moveTask: (id, lane) =>
    set((s) => ({
      tasks: s.tasks.map((task) =>
        task.id === id ? { ...task, lane, blockedReason: undefined, updatedAt: Date.now() } : task,
      ),
    })),

  /** 触发规则：用户发起新任务 → 自动展开任务看板并登记任务。 */
  expandForNewTask: (name) => {
    if (autoCollapseTimer !== null) {
      clearTimeout(autoCollapseTimer);
      autoCollapseTimer = null;
    }
    const id = `anchored-task-${Date.now()}-${taskSeq++}`;
    set((s) => ({
      cardsOpen: { ...s.cardsOpen, taskBoard: true },
      tasks: [...s.tasks, { id, name, lane: 'pending', updatedAt: Date.now() }],
    }));
  },

  /** 触发规则：Agent 拆分出子任务 → 自动展开子 Agent 任务树并新增节点。 */
  expandForSubTask: (node) =>
    set((s) => ({
      cardsOpen: { ...s.cardsOpen, subAgentTree: true },
      subAgentTree: s.subAgentTree.some((entry) => entry.id === node.id)
        ? s.subAgentTree.map((entry) => entry.id === node.id ? { ...entry, ...node } : entry)
        : [...s.subAgentTree, { ...node, children: [] as SubAgentNode[] }],
    })),

  /** 触发规则：工具执行完成且失败 → 自动展开该工具结果块。 */
  markToolFailed: (toolCallId) =>
    set((s) => ({
      failedToolIds: s.failedToolIds.includes(toolCallId)
        ? s.failedToolIds
        : [...s.failedToolIds, toolCallId],
    })),

  /** 触发规则：Agent 编辑代码/文件 → 自动展开文件预览并高亮变更。 */
  openFilePreview: (entry) => {
    const id = `anchored-preview-${Date.now()}-${previewSeq++}`;
    set((s) => {
      const existing = s.previews.find((p) => p.path === entry.path);
      if (existing) {
        return {
          cardsOpen: { ...s.cardsOpen, filePreview: true },
          previews: s.previews.map((p) => (p.id === existing.id ? { ...entry, id: existing.id } : p)),
          activePreviewId: existing.id,
        };
      }
      return {
        cardsOpen: { ...s.cardsOpen, filePreview: true },
        previews: [...s.previews, { ...entry, id }],
        activePreviewId: s.activePreviewId ?? id,
      };
    });
  },

  closeFilePreview: (id) =>
    set((s) => {
      const previews = s.previews.filter((p) => p.id !== id);
      return {
        previews,
        activePreviewId:
          s.activePreviewId === id ? previews.at(-1)?.id ?? null : s.activePreviewId,
      };
    }),

  setActivePreview: (id) => set({ activePreviewId: id }),

  loadRules: async () => {
    if (get().rulesLoading || get().ruleSavingId) return;
    const epoch = rulesEpoch;
    const hadConflict = get().ruleConflictId !== null;
    set({ rulesLoading: true, rulesError: null, rulesMessage: null });
    try {
      const rules = await api.getUiRules();
      if (epoch !== rulesEpoch) return;
      set({ rules, rulesLoaded: true, ruleConflictId: null, rulesMessage: hadConflict ? i18n.t('store_anchored.rules_conflict') : null });
    } catch (error) {
      if (epoch === rulesEpoch) set({ rulesError: ruleError(error) });
    } finally {
      if (epoch === rulesEpoch) set({ rulesLoading: false });
    }
  },

  setRuleDraft: (id, content) => set((s) => ({ ruleDrafts: { ...s.ruleDrafts, [id]: content }, rulesMessage: null })),

  saveRule: async (id, content) => {
    const state = get();
    const rule = state.rules.find((entry) => entry.id === id);
    if (!rule || !state.rulesLoaded || state.rulesLoading || state.ruleSavingId || state.ruleConflictId === id) return false;
    const epoch = rulesEpoch;
    set({ ruleSavingId: id, rulesError: null, rulesMessage: null });
    try {
      const saved = await api.putUiRules(rule.kind, { content, revision: rule.revision });
      if (epoch !== rulesEpoch) return false;
      set((s) => {
        const ruleDrafts = { ...s.ruleDrafts };
        if (ruleDrafts[id] === content) delete ruleDrafts[id];
        return { rules: s.rules.map((entry) => entry.id === id ? saved : entry), ruleDrafts, rulesMessage: i18n.t('store_anchored.rules_saved') };
      });
      return true;
    } catch (error) {
      if (epoch === rulesEpoch) set({ rulesError: ruleError(error), ruleConflictId: error instanceof ApiRequestError && error.status === 409 ? id : get().ruleConflictId });
      return false;
    } finally {
      if (epoch === rulesEpoch) set({ ruleSavingId: null });
    }
  },

  /** 弹窗栈：按触发顺序堆叠，最新的在最上层（渲染时倒序）。 */
  pushPopup: (popup) => {
    const id = `anchored-popup-${Date.now()}-${popupSeq++}`;
    set((s) => ({ popups: [...s.popups, { ...popup, id }] }));
    return id;
  },

  /** 完成 / 取消后销毁，不残留。 */
  resolvePopup: (id) =>
    set((s) => ({ popups: s.popups.filter((popup) => popup.id !== id) })),

  noteTurnStart: () => {
    if (autoCollapseTimer !== null) {
      clearTimeout(autoCollapseTimer);
      autoCollapseTimer = null;
    }
    set({ agentState: 'thinking', agentStateMessage: null });
  },

  /** 触发规则：任务执行结束 5 秒后自动折叠任务看板、任务树、文件预览。 */
  noteTurnEnd: () => {
    set((s) => ({
      agentState: 'awaiting_input',
      agentStateMessage: null,
      meterRefreshTick: s.meterRefreshTick + 1,
    }));
    if (autoCollapseTimer !== null) clearTimeout(autoCollapseTimer);
    autoCollapseTimer = setTimeout(() => {
      autoCollapseTimer = null;
      const { cardsOpen, previews } = get();
      const next = { ...cardsOpen };
      let changed = false;
      for (const card of AUTO_COLLAPSE_CARDS) {
        if (next[card]) {
          next[card] = false;
          changed = true;
        }
      }
      set(changed ? { cardsOpen: next, activePreviewId: previews.length ? get().activePreviewId : null } : {});
    }, AUTO_COLLAPSE_DELAY_MS);
  },

  setUsage: ({ cacheHitRate, turnTokens }) =>
    set((s) => ({
      cacheHitRate: cacheHitRate === undefined ? s.cacheHitRate : cacheHitRate,
      turnTokens: turnTokens === undefined ? s.turnTokens : turnTokens,
    })),
}));

/** 测试与重置用：回到初始界面状态。 */
export function resetAnchoredStore(): void {
  rulesEpoch += 1;
  if (autoCollapseTimer !== null) {
    clearTimeout(autoCollapseTimer);
    autoCollapseTimer = null;
  }
  useAnchoredStore.setState({
    agentState: 'awaiting_input',
    agentStateMessage: null,
    cardsOpen: applyProfileToCards({ ...DEFAULT_CARD_OPEN }, readStoredProfile()),
    tasks: [],
    subAgentTree: [],
    failedToolIds: [],
    runningToolIds: [],
    planning: false,
    previews: [],
    activePreviewId: null,
    rules: defaultRuleEntries(),
    ruleDrafts: {},
    rulesLoaded: false,
    rulesLoading: false,
    ruleSavingId: null,
    ruleConflictId: null,
    rulesError: null,
    rulesMessage: null,
    popups: [],
    cacheHitRate: null,
    turnTokens: null,
    profile: readStoredProfile(),
    meter: { ...EMPTY_METER },
    turnTrend: [],
    meterRefreshTick: 0,
  });
}

const SUB_TASK_TOOL_PATTERN = /(^|[_-])(task|subagent|agent|spawn|delegate|crew)([_-]|$)/i;
const FILE_EDIT_TOOL_PATTERN = /(^|[_-])(write|edit|patch|apply|create|delete|remove|move|rename)([_-]|$)/i;

/** 工具名是否属于"拆分子任务"类（触发任务树展开）。 */
export function isSubTaskTool(name: string): boolean {
  return SUB_TASK_TOOL_PATTERN.test(name);
}

/** 工具名是否属于"编辑代码/文件"类（触发文件预览展开）。 */
export function isFileEditTool(name: string): boolean {
  return FILE_EDIT_TOOL_PATTERN.test(name);
}

const MARKER_MAP: Record<string, PreviewLineMarker> = {
  '+': 'add',
  '-': 'del',
  '~': 'change',
};

/** 把工具参数或结果文本粗化为文件预览行（新增/删除/修改/上下文）。 */
export function toPreviewLines(text: string): Array<{ marker: PreviewLineMarker; text: string }> {
  return text
    .split('\n')
    .filter((line, index, all) => line.length > 0 || (index > 0 && index < all.length - 1))
    .slice(0, 400)
    .map((line) => {
      const first = line[0] ?? '';
      const marker = MARKER_MAP[first];
      return marker && !line.startsWith('---') && !line.startsWith('+++')
        ? { marker, text: line.slice(1) }
        : { marker: 'ctx' as const, text: line };
    });
}
