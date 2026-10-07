import { useEffect, useRef, useState } from 'react';
import { ChevronDown, ChevronRight, Plus, RotateCcw, Save, X } from 'lucide-react';
import { useI18n } from '../../i18n';
import { cn } from '../../lib/utils';
import { Button } from '../ui/Button';
import { api } from '../../api';
import { useAnchoredStore } from '../../store/anchored';
import { INFO_CARD_ORDER, METER_ORDER, buildMeterSnapshot } from '../../store/anchored';
import type { InfoCardId, MeterSnapshot, TaskLane } from '../../store/anchored';
import { TaskTracePanel } from '../anchored/TaskTracePanel';
import { ArtifactPreview } from '../anchored/ArtifactPreview';
import { MemoryArchivePanel } from '../anchored/MemoryArchivePanel';
import { WorkbenchIcon, type WorkbenchIconName } from '../ui/WorkbenchIcon';
import { ScrollProgress } from '../motion/ScrollProgress';
import { ScrollReveal } from '../motion/ScrollReveal';
import { Parallax } from '../motion/Parallax';
import './codex-suite.css';

const CARD_ICON: Record<InfoCardId, WorkbenchIconName> = {
  taskBoard: 'task', tokenMeter: 'meter', subAgentTree: 'tree', filePreview: 'preview', ruleEditor: 'knowledge',
  memoryArchive: 'knowledge',
};

const CARD_TITLE_KEY: Record<InfoCardId, string> = {
  taskBoard: 'anchored.cards.task_board',
  tokenMeter: 'anchored.cards.token_meter',
  subAgentTree: 'anchored.cards.sub_agent_tree',
  filePreview: 'anchored.cards.file_preview',
  ruleEditor: 'anchored.cards.rule_editor',
  memoryArchive: 'anchored.cards.memory_archive',
};

/* The locale files carry no titles for the sixth card and no subtitles at all,
   and they may not be edited, so every card resolves its text against an
   explicit default rather than rendering a raw key. */
const CARD_TITLE_FALLBACK: Record<InfoCardId, string> = {
  taskBoard: '任务看板',
  tokenMeter: 'Token 计量',
  subAgentTree: '子代理任务树',
  filePreview: '文件预览',
  ruleEditor: '规则编辑器',
  memoryArchive: '记忆归档',
};

const CARD_SUBTITLE_KEY: Record<InfoCardId, string> = {
  taskBoard: 'anchored.cards.task_board_sub',
  tokenMeter: 'anchored.cards.token_meter_sub',
  subAgentTree: 'anchored.cards.sub_agent_tree_sub',
  filePreview: 'anchored.cards.file_preview_sub',
  ruleEditor: 'anchored.cards.rule_editor_sub',
  memoryArchive: 'anchored.cards.memory_archive_sub',
};

const CARD_SUBTITLE_FALLBACK: Record<InfoCardId, string> = {
  taskBoard: '泳道任务与实时进度',
  tokenMeter: '按轮统计的用量与趋势',
  subAgentTree: '子代理调用与耗时',
  filePreview: '文件工具的输出产物',
  ruleEditor: 'Soul / 记忆 / 项目规则',
  memoryArchive: 'L0 摘要与按需明细',
};

/**
 * 右侧五卡片的统一外壳：标题行为折叠开关，右侧槽位承载各自的卡片动作
 * （新建任务 / 重置 / 展开折叠 / 关闭 / 保存）。开关按钮始终是标题内第一个
 * 按钮并持有 aria-expanded 与 aria-controls，动作按钮排在它之后。
 */
function CardShell({
  card,
  title,
  subtitle,
  open,
  onToggle,
  actions,
  children,
}: {
  card: InfoCardId;
  title: string;
  subtitle: string;
  open: boolean;
  onToggle: () => void;
  actions?: React.ReactNode;
  children: React.ReactNode;
}) {
  const bodyId = `anchored-card-body-${card}`;
  return (
    <section
      data-testid={`anchored-card-${card}`}
      data-open={open}
      className="cx-card mx-[var(--space-2)] my-[var(--space-1-5)] shrink-0 overflow-hidden"
    >
      <h3 className="flex items-center">
        <button
          type="button"
          aria-expanded={open}
          aria-controls={bodyId}
          onClick={onToggle}
          className="cx-row flex min-h-[var(--control-height-sm)] min-w-0 flex-1 items-center gap-[var(--space-2)] px-[var(--space-4)] py-[var(--space-2-5)] text-left focus-visible:outline-none focus-visible:shadow-[var(--focus-ring)]"
        >
          {open ? <ChevronDown size={13} aria-hidden="true" /> : <ChevronRight size={13} aria-hidden="true" />}
          <WorkbenchIcon name={CARD_ICON[card]} className="shrink-0 text-[var(--color-text-secondary)]" />
          <span className="flex min-w-0 flex-1 flex-col">
            <span className="cx-card-title truncate">
              {title}
            </span>
            <span className="cx-card-sub truncate">
              {subtitle}
            </span>
          </span>
        </button>
        {actions && <span className="flex shrink-0 items-center pr-[var(--space-3)]">{actions}</span>}
      </h3>
      {open && (
        <div id={bodyId} className="cx-hairline space-y-[var(--space-2)] px-[var(--space-4)] py-[var(--space-3)]">
          {children}
        </div>
      )}
    </section>
  );
}

const LANE_ORDER: readonly TaskLane[] = ['pending', 'running', 'completed'];
const LANE_LABEL_KEY: Record<TaskLane, string> = {
  pending: 'anchored.board.pending',
  running: 'anchored.board.running',
  completed: 'anchored.board.completed',
};
const LANE_TONE: Record<TaskLane, string> = {
  pending: 'border-[var(--color-border-subtle)] text-[var(--color-text-secondary)]',
  running: 'border-[var(--color-info)]/40 text-[var(--color-info)]',
  completed: 'border-[var(--color-success)]/40 text-[var(--color-success)]',
};

const LANE_STATUS_KEY: Record<TaskLane, string> = {
  pending: 'anchored.board.pending',
  running: 'anchored.board.running',
  completed: 'anchored.board.completed',
};

/** 时间戳：有上报才显示，缺失时不伪造。 */
function formatUpdated(updatedAt: number | undefined): string | null {
  if (typeof updatedAt !== 'number' || !Number.isFinite(updatedAt)) return null;
  return new Date(updatedAt).toLocaleTimeString();
}

function TaskBoard() {
  const { t } = useI18n();
  const tasks = useAnchoredStore((s) => s.tasks);
  const moveTask = useAnchoredStore((s) => s.moveTask);
  const [draggingId, setDraggingId] = useState<string | null>(null);
  const [dropLane, setDropLane] = useState<TaskLane | null>(null);
  return (
    <div className="space-y-[var(--space-2)]" data-testid="anchored-task-board">
      <p className="cx-card-sub">{t('anchored.info.board_hint')}</p>
      {tasks.length === 0 && (
        <p className="cx-card-meta">{t('anchored.board.empty')}</p>
      )}
      <ScrollReveal stagger={70} className="space-y-[var(--space-2)]" testId="anchored-task-board-lanes">
      {LANE_ORDER.map((lane) => {
        const laneTasks = tasks.filter((task) => task.lane === lane);
        return (
          <div
            key={lane}
            data-testid={`anchored-lane-${lane}`}
            onDragOver={(event) => {
              if (!draggingId) return;
              event.preventDefault();
              setDropLane(lane);
            }}
            onDragLeave={() => setDropLane((current) => (current === lane ? null : current))}
            onDrop={(event) => {
              event.preventDefault();
              const id = draggingId ?? event.dataTransfer.getData('text/plain');
              if (id) moveTask(id, lane);
              setDraggingId(null);
              setDropLane(null);
            }}
            className={cn(
              'rounded-[var(--radius-md)] border border-dashed p-[var(--space-1)] transition-colors',
              dropLane === lane ? 'border-[var(--color-border-accent)]' : 'border-transparent',
            )}
          >
            <p className={cn('mb-[var(--space-1)] flex items-center justify-between text-[length:var(--text-2xs)] font-medium tracking-wide', LANE_TONE[lane])}>
              <span>{t(LANE_LABEL_KEY[lane])}</span>
              <span className="cx-count">{laneTasks.length}</span>
            </p>
            <ul className="space-y-[var(--space-1)]">
              {laneTasks.map((task) => {
                const updated = formatUpdated(task.updatedAt);
                return (
                  <li
                    key={task.id}
                    draggable
                    data-testid={`anchored-task-${task.id}`}
                    onDragStart={(event) => {
                      setDraggingId(task.id);
                      event.dataTransfer.setData('text/plain', task.id);
                      event.dataTransfer.effectAllowed = 'move';
                    }}
                    onDragEnd={() => {
                      setDraggingId(null);
                      setDropLane(null);
                    }}
            className={cn(
              'cx-row flex min-h-[64px] cursor-grab flex-col justify-between gap-[var(--space-1)] rounded-[var(--radius-md)] border bg-[var(--color-bg-surface-2)] px-[var(--space-2)] py-[var(--space-1-5)] text-[13px] text-[var(--color-text-primary)] hover:border-[var(--color-border-default)]',
              task.blockedReason ? 'border-[var(--color-error)]/50' : 'border-[var(--color-border-subtle)]',
            )}
          >
            <span className="block truncate" title={task.name}>{task.name}</span>
            <span className="flex items-center justify-between gap-[var(--space-1)] text-[12px] text-[var(--color-text-muted)]">
              <span className="cx-pill">{t(LANE_STATUS_KEY[task.lane])}</span>
              {updated && <time className="cx-mono">{updated}</time>}
            </span>
                    {task.blockedReason && (
                      <span className="block text-[length:var(--text-2xs)] text-[var(--color-error)]">
                        {task.blockedReason}
                      </span>
                    )}
                  </li>
                );
              })}
            </ul>
          </div>
        );
      })}
      </ScrollReveal>
    </div>
  );
}

function TokenMeter() {
  const { t } = useI18n();
  const meter = useAnchoredStore((s) => s.meter);
  const turnTrend = useAnchoredStore((s) => s.turnTrend);
  const totals = turnTrend.map((turn) => turn.total).filter((total): total is number => total !== null);
  const trendMax = totals.length ? Math.max(...totals) : 0;
  const renderValue = (value: number | null, suffix = '') =>
    value === null || Number.isNaN(value) ? (
      <span className="text-[var(--color-text-muted)]">{t('anchored.status.unreported')}</span>
    ) : (
      <span className="tabular-nums">{value.toLocaleString()}{suffix}</span>
    );
  return (
    <div className="space-y-[var(--space-2)]" data-testid="anchored-token-meter">
      <dl className="grid grid-cols-3 gap-x-[var(--space-2)] gap-y-[var(--space-1-5)]">
        {METER_ORDER.map(({ key, labelKey }) => (
          <div key={key} className="min-w-0">
            <dt className="cx-card-meta mb-[var(--space-0-5)] truncate">
              {t(labelKey)}
            </dt>
            <dd className="cx-mono text-[length:var(--text-xs)] text-[var(--color-text-secondary)]">
              {renderValue(
                meter[key],
                key === 'cacheHitRate' ? '%' : key === 'estimatedCost' ? '' : '',
              )}
            </dd>
          </div>
        ))}
      </dl>
      <div>
        <p className="cx-card-meta mb-[var(--space-1)]">
          {t('anchored.meter.trend')}
        </p>
        {totals.length === 0 ? (
          <p className="cx-card-meta">
            {t('anchored.meter.trend_empty')}
          </p>
        ) : (
          <div
            className="flex h-10 items-end gap-[var(--space-0-5)]"
            data-testid="anchored-meter-trend"
            role="img"
            aria-label={t('anchored.meter.trend')}
          >
            {totals.map((total, index) => (
              <div
                key={index}
                title={`${total.toLocaleString()}`}
                className="min-w-[4px] flex-1 rounded-t-[2px] bg-[var(--color-accent-foreground)]/60"
                style={{ height: `${trendMax > 0 ? Math.max(8, Math.round((total / trendMax) * 100)) : 8}%` }}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

const NODE_TONE: Record<string, string> = {
  running: 'text-[var(--color-info)]',
  success: 'text-[var(--color-success)]',
  error: 'text-[var(--color-error)]',
};

function SubAgentTree({ forceOpen }: { forceOpen: boolean | null }) {
  const { t } = useI18n();
  const tree = useAnchoredStore((s) => s.subAgentTree);
  if (tree.length === 0) {
    return (
      <p className="cx-card-meta" data-testid="anchored-sub-agent-tree">
        {t('anchored.tree.empty')}
      </p>
    );
  }
  function Node({ node }: { node: (typeof tree)[number] }) {
    const [open, setOpen] = useState(forceOpen ?? false);
    return (
      <li className="text-[length:var(--text-xs)]">
        <details
          open={open}
          className={NODE_TONE[node.status]}
        >
          <summary
            onClick={(event) => {
              event.preventDefault();
              setOpen((current) => !current);
            }}
            className="flex cursor-pointer items-center gap-[var(--space-1-5)] rounded-[var(--radius-sm)] py-[var(--space-1)] hover:bg-[var(--color-bg-surface-2)] focus-visible:outline-none focus-visible:shadow-[var(--focus-ring)]"
          >
            <WorkbenchIcon name="task" />
            <span className="min-w-0 flex-1 truncate text-[var(--color-text-primary)]">{node.name}</span>
            <span className="cx-mono shrink-0 text-[var(--color-text-muted)]">
              {node.durationMs === undefined ? t('anchored.status.unreported') : `${(node.durationMs / 1000).toFixed(1)}s`}
            </span>
          </summary>
          <dl className="space-y-[var(--space-1)] text-[length:var(--text-2xs)]">
            <div><dt className="text-[var(--color-text-muted)]">{t('anchored.info.tree_goal')}</dt><dd className="whitespace-pre-wrap [overflow-wrap:anywhere]">{node.detail || t('anchored.status.unreported')}</dd></div>
            <div><dt className="text-[var(--color-text-muted)]">{t('anchored.info.tree_result')}</dt><dd>{t('anchored.status.unreported')}</dd></div>
            <div><dt className="text-[var(--color-text-muted)]">{t('anchored.info.tree_error')}</dt><dd>{t('anchored.status.unreported')}</dd></div>
          </dl>
          {node.children.length > 0 && (
            <ul className="mt-[var(--space-1)] space-y-[var(--space-1)] border-l border-[var(--color-border-subtle)] pl-[var(--space-2)]">
              {node.children.map((child) => (
                <Node key={`${child.id}:${String(forceOpen)}`} node={child} />
              ))}
            </ul>
          )}
        </details>
      </li>
    );
  }
  return (
    <ul className="space-y-[var(--space-1)]" data-testid="anchored-sub-agent-tree">
      {tree.map((node) => (
        <Node key={`${node.id}:${String(forceOpen)}`} node={node} />
      ))}
    </ul>
  );
}

const RULE_KIND_KEY = {
  soul: 'anchored.rules.soul',
  memory: 'anchored.rules.memory',
  project: 'anchored.rules.project',
} as const;

/**
 * 打开规则卡片时按需加载一次；草稿与冲突态存在 store，跨折叠保留。
 * 保存按钮渲染在卡片头部，因此把选中项与保存动作提升到这里供头部使用。
 */
function useRuleEditorState(enabled: boolean) {
  const rules = useAnchoredStore((s) => s.rules);
  const saveRule = useAnchoredStore((s) => s.saveRule);
  const loadRules = useAnchoredStore((s) => s.loadRules);
  const setRuleDraft = useAnchoredStore((s) => s.setRuleDraft);
  const drafts = useAnchoredStore((s) => s.ruleDrafts);
  const loaded = useAnchoredStore((s) => s.rulesLoaded);
  const loading = useAnchoredStore((s) => s.rulesLoading);
  const savingId = useAnchoredStore((s) => s.ruleSavingId);
  const conflictId = useAnchoredStore((s) => s.ruleConflictId);
  const error = useAnchoredStore((s) => s.rulesError);
  const message = useAnchoredStore((s) => s.rulesMessage);
  const [activeId, setActiveId] = useState(rules[0]?.id ?? 'soul');
  useEffect(() => {
    if (enabled && !useAnchoredStore.getState().rulesLoaded) void loadRules();
  }, [enabled, loadRules]);
  const active = rules.find((rule) => rule.id === activeId) ?? rules[0];
  const value = active ? drafts[active.id] ?? active.content : '';
  return { rules, active, activeId, setActiveId, value, setRuleDraft, loadRules, saveRule,
    loaded, loading, savingId, conflictId, error, message };
}

type RuleEditorState = ReturnType<typeof useRuleEditorState>;

function RuleEditorSaveAction({ editor }: { editor: RuleEditorState }) {
  const { t } = useI18n();
  const { active, value, loaded, loading, savingId, conflictId, saveRule } = editor;
  if (!active) return null;
  return (
    <Button
      type="button"
      size="xs"
      disabled={!loaded || loading || savingId !== null || conflictId === active.id || value === active.content}
      onClick={() => {
        void saveRule(active.id, value);
      }}
    >
      <Save size={12} aria-hidden="true" />
      {savingId === active.id ? t('anchored.info.rule_saving') : t('anchored.rules.save')}
    </Button>
  );
}

function RuleEditorBody({ editor }: { editor: RuleEditorState }) {
  const { t } = useI18n();
  const { rules, active, setActiveId, value, setRuleDraft, loadRules,
    loaded, loading, savingId, conflictId, error, message } = editor;
  if (!active) return null;
  return (
    <div data-testid="anchored-rule-editor">
      <div className="mb-[var(--space-1-5)] flex gap-[var(--space-1)]">
        {rules.map((rule) => (
          <button
            key={rule.id}
            type="button"
            aria-pressed={rule.id === active.id}
            onClick={() => {
              setActiveId(rule.id);
            }}
            className={cn(
              'cx-chip flex-1 justify-center',
              rule.id === active.id ? '' : 'border-[var(--color-border-subtle)]',
            )}
          >
            {t(RULE_KIND_KEY[rule.kind])}
          </button>
        ))}
      </div>
      <textarea
        value={value}
        onChange={(event) => setRuleDraft(active.id, event.target.value)}
        disabled={!loaded || loading}
        maxLength={32000}
        aria-label={t(RULE_KIND_KEY[active.kind])}
        className="h-40 w-full resize-y rounded-[var(--radius-md)] border border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-2)] p-[var(--space-2)] font-mono text-[length:var(--text-xs)] leading-[var(--leading-normal)] text-[var(--color-text-primary)] transition-colors hover:border-[var(--color-border-default)] focus:border-[var(--color-border-accent)] focus:outline-none"
      />
      <p className="cx-card-meta">{t('anchored.info.rule_hint')}</p>
      {loading && <p role="status">{t('anchored.info.rule_loading')}</p>}
      {error && <p role="alert" className="text-[length:var(--text-2xs)] text-[var(--color-error)]">{conflictId ? t('anchored.info.rule_conflict') : t('anchored.info.rule_failed')} {error}</p>}
      {message && <p role="status" className="text-[length:var(--text-2xs)] text-[var(--color-text-muted)]">{message}</p>}
      <div className="mt-[var(--space-1-5)] flex justify-end">
        <Button type="button" size="xs" disabled={loading || savingId !== null} onClick={() => void loadRules()}>
          {conflictId ? t('anchored.info.rule_reload_conflict') : t('anchored.info.rule_reload')}
        </Button>
      </div>
    </div>
  );
}

/** 任务看板头部「新建任务」：登记到待执行泳道。 */
function NewTaskAction() {
  const { t } = useI18n();
  const addTask = useAnchoredStore((s) => s.addTask);
  const count = useAnchoredStore((s) => s.tasks.length);
  return (
    <Button
      type="button"
      size="xs"
      variant="ghost"
      aria-label={t('anchored.info.new_task')}
      title={t('anchored.info.new_task')}
      onClick={() => addTask(t('anchored.info.new_task_name', { n: count + 1 }))}
    >
      <Plus size={12} aria-hidden="true" />
      {t('anchored.info.new_task')}
    </Button>
  );
}

const EMPTY_METER: MeterSnapshot = Object.fromEntries(
  METER_ORDER.map(({ key }) => [key, null]),
) as unknown as MeterSnapshot;

export function AnchoredInfoPanel({ sessionId }: { sessionId?: string | null }) {
  const { t } = useI18n();
  const panelRef = useRef<HTMLElement | null>(null);
  const cardsOpen = useAnchoredStore((s) => s.cardsOpen);
  const toggleCard = useAnchoredStore((s) => s.toggleCard);
  const setMeter = useAnchoredStore((s) => s.setMeter);
  const meterRefreshTick = useAnchoredStore((s) => s.meterRefreshTick);
  const previews = useAnchoredStore((s) => s.previews);
  const activePreviewId = useAnchoredStore((s) => s.activePreviewId);
  const closeFilePreview = useAnchoredStore((s) => s.closeFilePreview);
  const ruleEditor = useRuleEditorState(cardsOpen.ruleEditor);
  const [treeForceOpen, setTreeForceOpen] = useState<boolean | null>(null);
  // 计量仪表盘：挂载与每回合结束后拉取计费数据；失败时保持 null（"未上报"）。
  useEffect(() => {
    let active = true;
    Promise.all([api.getCostUsage(), api.listCostRecords(sessionId ?? '')])
      .then(([usage, records]) => {
        if (!active) return;
        const { meter, turnTrend } = buildMeterSnapshot(
          usage as Record<string, unknown> | null | undefined,
          Array.isArray(records) ? records : [],
        );
        setMeter(meter, turnTrend);
      })
      .catch(() => {
        /* 计费数据不可用时保持空快照。 */
      });
    return () => {
      active = false;
    };
  }, [sessionId, meterRefreshTick, setMeter]);

  const ruleEditorOpen = cardsOpen.ruleEditor;
  const resetMeter = () => setMeter(EMPTY_METER, []);
  const activePreview = previews.find((entry) => entry.id === activePreviewId) ?? previews.at(-1);

  const cardActions: Partial<Record<InfoCardId, React.ReactNode>> = {
    taskBoard: <NewTaskAction />,
    tokenMeter: (
      <Button
        type="button"
        size="xs"
        variant="ghost"
        aria-label={t('anchored.info.reset')}
        title={t('anchored.info.reset')}
        onClick={resetMeter}
      >
        <RotateCcw size={12} aria-hidden="true" />
        {t('anchored.info.reset')}
      </Button>
    ),
    subAgentTree: (
      <Button
        type="button"
        size="xs"
        variant="ghost"
        onClick={() => setTreeForceOpen((current) => (current === true ? false : true))}
      >
        {treeForceOpen === true ? t('anchored.info.collapse_all') : t('anchored.info.expand_all')}
      </Button>
    ),
    filePreview: activePreview ? (
      <>
        <span className="max-w-[16ch] truncate font-mono text-[length:var(--text-2xs)] text-[var(--color-text-muted)]" title={activePreview.path}>
          {activePreview.name}
        </span>
        <Button
          type="button"
          size="xs"
          variant="ghost"
          aria-label={t('anchored.info.preview_close', { name: activePreview.name })}
          title={t('anchored.info.preview_close', { name: activePreview.name })}
          onClick={() => closeFilePreview(activePreview.id)}
        >
          <X size={12} aria-hidden="true" />
        </Button>
      </>
    ) : undefined,
    ruleEditor: <RuleEditorSaveAction editor={ruleEditor} />,
  };

  return (
    <aside
      ref={panelRef}
      data-testid="anchored-info-panel"
      aria-label={t('anchored.panel.label')}
      className="flex h-full min-w-0 flex-col overflow-y-auto border-l border-[var(--color-border-subtle)] bg-[var(--color-bg-page)]"
    >
      <ScrollProgress
        containerRef={panelRef}
        variant="segments"
        segments={INFO_CARD_ORDER.length}
        testId="anchored-info-panel-progress"
        ariaLabel={t('scroll.progress.panel_label', { defaultValue: '信息面板阅读进度' })}
        className="sticky top-0 z-10 shrink-0 border-b border-[var(--color-border-subtle)] bg-[var(--color-bg-page)] px-[var(--space-2-5)] py-[var(--space-1-5)]"
      />
      <div aria-hidden="true" className="relative h-[var(--space-2)] shrink-0 overflow-hidden">
        <Parallax
          speed={0.35}
          maxShift={6}
          containerRef={panelRef}
          ariaHidden
          testId="anchored-info-panel-decor"
          className="absolute inset-x-0 -top-[var(--space-2)] h-[var(--space-6)]"
          style={{ background: 'linear-gradient(to bottom, var(--color-accent-subtle), transparent)' }}
        />
      </div>
      {INFO_CARD_ORDER.map((card) => (
        <ScrollReveal key={card} className="shrink-0" offset="0px 0px -8% 0px">
          <CardShell
            card={card}
            title={t(CARD_TITLE_KEY[card], { defaultValue: CARD_TITLE_FALLBACK[card] })}
            subtitle={t(CARD_SUBTITLE_KEY[card], { defaultValue: CARD_SUBTITLE_FALLBACK[card] })}
            open={cardsOpen[card]}
            onToggle={() => toggleCard(card)}
            actions={cardActions[card]}
          >
            {card === 'taskBoard' && <><TaskBoard /><TaskTracePanel kind="tasks" sessionId={sessionId} /></>}
            {card === 'tokenMeter' && <TokenMeter />}
            {card === 'subAgentTree' && <><SubAgentTree forceOpen={treeForceOpen} /><TaskTracePanel kind="traces" sessionId={sessionId} /></>}
            {card === 'filePreview' && <ArtifactPreview />}
            {card === 'ruleEditor' && (ruleEditorOpen ? <RuleEditorBody editor={ruleEditor} /> : null)}
            {card === 'memoryArchive' && <MemoryArchivePanel sessionId={sessionId} />}
          </CardShell>
        </ScrollReveal>
      ))}
    </aside>
  );
}
