import { useEffect, useMemo, useState } from 'react';
import {
  AlertCircle,
  CheckCircle2,
  Clock3,
  Loader2,
  PauseCircle,
  Play,
  RefreshCw,
  Square,
} from 'lucide-react';
import { api } from '../../api';
import type { TaskSummary } from '../../types/api';
import {
  getTaskStatusPresentation,
  matchesTaskQueueFilter,
  summarizeTasks,
  type TaskQueueFilter,
} from './taskQueue';

const FILTERS: Array<{ id: TaskQueueFilter; label: string }> = [
  { id: 'all', label: '全部' },
  { id: 'active', label: '执行中' },
  { id: 'review', label: '待审阅' },
  { id: 'completed', label: '已交付' },
  { id: 'failed', label: '异常' },
];

const TONE_CLASSES = {
  muted: 'text-[var(--color-text-muted)]',
  accent: 'text-[var(--color-accent)]',
  warning: 'text-amber-400',
  success: 'text-[var(--color-success)]',
  error: 'text-[var(--color-error)]',
} as const;

function StatusIcon({ status }: { status: string }) {
  if (status === 'running') return <Loader2 size={13} className="animate-spin text-[var(--color-accent)]" />;
  if (['completed', 'partial'].includes(status)) return <CheckCircle2 size={13} className="text-[var(--color-success)]" />;
  if (['failed', 'cancelled', 'stopped'].includes(status)) return <AlertCircle size={13} className="text-[var(--color-error)]" />;
  if (['waiting_approval', 'reviewing'].includes(status)) return <PauseCircle size={13} className="text-amber-400" />;
  return <Clock3 size={13} className="text-[var(--color-text-muted)]" />;
}

function formatAge(value?: string) {
  if (!value) return '刚刚创建';
  const elapsed = Math.max(0, Date.now() - new Date(value).getTime());
  const minutes = Math.floor(elapsed / 60000);
  if (minutes < 1) return '刚刚更新';
  if (minutes < 60) return `${minutes} 分钟前`;
  return `${Math.floor(minutes / 60)} 小时前`;
}

export function TaskQueuePanel() {
  const [tasks, setTasks] = useState<TaskSummary[]>([]);
  const [filter, setFilter] = useState<TaskQueueFilter>('all');
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadTasks = async (manual = false) => {
    if (manual) setRefreshing(true);
    try {
      const nextTasks = await api.listTasks({ limit: 50 });
      setTasks(nextTasks);
      setSelectedId((current) => current && nextTasks.some((task) => task.id === current) ? current : nextTasks[0]?.id || null);
      setError(null);
    } catch {
      setError('任务状态暂时无法获取');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    void loadTasks();
    const interval = window.setInterval(() => void loadTasks(), 15000);
    return () => window.clearInterval(interval);
  }, []);

  const summary = useMemo(() => summarizeTasks(tasks), [tasks]);
  const visibleTasks = useMemo(
    () => tasks.filter((task) => matchesTaskQueueFilter(task, filter)),
    [filter, tasks],
  );
  const selectedTask = tasks.find((task) => task.id === selectedId);

  const stopTask = async (taskId: string) => {
    await api.cancelTask(taskId);
    await loadTasks(true);
  };

  return (
    <section className="space-y-3" aria-label="任务执行队列">
      <div className="flex items-start justify-between gap-2">
        <div>
          <div className="flex items-center gap-2">
            <Play size={14} className="text-[var(--color-accent)]" />
            <h2 className="text-xs font-semibold text-[var(--color-text-primary)]">任务执行队列</h2>
          </div>
          <p className="mt-1 text-[10px] text-[var(--color-text-muted)]">监控长任务、审批节点与交付状态</p>
        </div>
        <button
          type="button"
          onClick={() => void loadTasks(true)}
          disabled={refreshing}
          className="flex h-7 w-7 items-center justify-center rounded-lg text-[var(--color-text-muted)] transition-colors hover:bg-[var(--color-bg-surface-2)] hover:text-[var(--color-text-primary)] disabled:opacity-50"
          aria-label="刷新任务队列"
          title="刷新"
        >
          <RefreshCw size={13} className={refreshing ? 'animate-spin' : ''} />
        </button>
      </div>

      <div className="grid grid-cols-4 gap-1.5" aria-label="任务统计">
        {[
          ['执行中', summary.active, 'accent'],
          ['待审阅', summary.review, 'warning'],
          ['已交付', summary.completed, 'success'],
          ['异常', summary.failed, 'error'],
        ].map(([label, value, tone]) => (
          <div key={label} className="border border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-1)] px-2 py-2">
            <div className={`text-sm font-semibold ${TONE_CLASSES[tone as keyof typeof TONE_CLASSES]}`}>{value}</div>
            <div className="mt-0.5 text-[9px] text-[var(--color-text-muted)]">{label}</div>
          </div>
        ))}
      </div>

      <div className="flex gap-1 overflow-x-auto pb-0.5" role="tablist" aria-label="任务筛选">
        {FILTERS.map((item) => (
          <button
            key={item.id}
            type="button"
            role="tab"
            aria-selected={filter === item.id}
            onClick={() => setFilter(item.id)}
            className={`shrink-0 border px-2 py-1 text-[10px] transition-colors ${filter === item.id
              ? 'border-[var(--color-accent)]/50 bg-[var(--color-accent)]/10 text-[var(--color-text-primary)]'
              : 'border-[var(--color-border-subtle)] text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)]'}`}
          >
            {item.label}
          </button>
        ))}
      </div>

      {error && <p role="status" className="text-[10px] text-[var(--color-error)]">{error}</p>}
      {loading ? (
        <div className="flex items-center justify-center gap-2 py-8 text-[10px] text-[var(--color-text-muted)]" role="status">
          <Loader2 size={14} className="animate-spin" /> 加载任务队列
        </div>
      ) : visibleTasks.length === 0 ? (
        <div className="border border-dashed border-[var(--color-border-subtle)] px-3 py-8 text-center" role="status">
          <Clock3 size={18} className="mx-auto text-[var(--color-text-muted)]" />
          <p className="mt-2 text-[11px] text-[var(--color-text-secondary)]">当前筛选暂无任务</p>
          <p className="mt-1 text-[10px] text-[var(--color-text-muted)]">任务创建后会在这里持续更新</p>
        </div>
      ) : (
        <div className="space-y-1.5" role="list">
          {visibleTasks.map((task) => {
            const presentation = getTaskStatusPresentation(task.status);
            const progress = task.max_rounds && task.current_round != null
              ? Math.min(100, Math.round((task.current_round / task.max_rounds) * 100))
              : null;
            return (
              <div
                key={task.id}
                role="listitem"
                className={`border px-2.5 py-2 transition-colors ${selectedId === task.id
                  ? 'border-[var(--color-accent)]/50 bg-[var(--color-accent)]/[0.06]'
                  : 'border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-1)] hover:bg-[var(--color-bg-surface-2)]'}`}
              >
                <button type="button" onClick={() => setSelectedId(task.id)} className="w-full text-left" aria-label={`查看任务 ${task.description}`}>
                  <div className="flex items-start gap-2">
                    <span className="mt-0.5 shrink-0"><StatusIcon status={task.status} /></span>
                    <span className="min-w-0 flex-1">
                      <span className="block truncate text-[11px] font-medium text-[var(--color-text-primary)]">{task.description || task.id.slice(0, 8)}</span>
                      <span className="mt-1 flex items-center gap-2 text-[9px] text-[var(--color-text-muted)]">
                        <span className={TONE_CLASSES[presentation.tone]}>{presentation.label}</span>
                        <span>{formatAge(task.started_at || task.created_at)}</span>
                        {task.total_tokens != null && <span>{task.total_tokens.toLocaleString()} tokens</span>}
                      </span>
                    </span>
                  </div>
                </button>
                {progress != null && (
                  <div className="mt-2 h-1 overflow-hidden bg-[var(--color-bg-surface-3)]" aria-label={`执行进度 ${progress}%`}>
                    <div className="h-full bg-[var(--color-accent)] transition-all" style={{ width: `${progress}%` }} />
                  </div>
                )}
                {selectedId === task.id && task.status === 'running' && (
                  <button type="button" onClick={() => void stopTask(task.id)} className="mt-2 inline-flex items-center gap-1 text-[10px] text-[var(--color-error)] hover:underline">
                    <Square size={10} /> 停止任务
                  </button>
                )}
              </div>
            );
          })}
        </div>
      )}

      {selectedTask && (
        <div className="border-t border-[var(--color-border-subtle)] pt-3" aria-live="polite">
          <div className="flex items-center justify-between gap-2">
            <span className="text-[10px] font-semibold text-[var(--color-text-secondary)]">当前任务</span>
            <span className="font-mono text-[9px] text-[var(--color-text-muted)]">{selectedTask.id.slice(0, 10)}</span>
          </div>
          <p className="mt-1 line-clamp-2 text-[11px] text-[var(--color-text-primary)]">{selectedTask.description}</p>
          <div className="mt-2 grid grid-cols-2 gap-2 text-[9px] text-[var(--color-text-muted)]">
            <span>Agent: {selectedTask.worker_id || '自动分配'}</span>
            <span>轮次: {selectedTask.current_round ?? 0}/{selectedTask.max_rounds ?? '—'}</span>
          </div>
        </div>
      )}
    </section>
  );
}
