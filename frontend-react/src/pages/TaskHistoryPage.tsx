import { useState, useEffect } from 'react';
import { Copy, Download, ChevronRight, RefreshCw } from 'lucide-react';
import { api, type TaskSummary, type TaskDetail } from '../api';
import { useI18n } from '../i18n';
import { formatDateTime } from '../i18n/utils';
import {
  TASK_STATUS_LABEL_KEYS,
  reportedNumber,
  taskStatusColor,
  taskStatusLabel,
} from '../components/collaboration/taskStatus';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { EmptyState } from '../components/ui/EmptyState';
import { SkeletonList } from '../components/ui/Skeleton';

const taskOutput = (task: TaskDetail | null): string => {
  if (!task?.result) return '';
  const output = (task.result as Record<string, unknown>).output;
  return typeof output === 'string' ? output : JSON.stringify(output ?? '', null, 2);
};

export function TaskHistoryPage() {
  const { t } = useI18n();
  const [tasks, setTasks] = useState<TaskSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedTask, setSelectedTask] = useState<TaskDetail | null>(null);
  const [error, setError] = useState(false);
  const [opening, setOpening] = useState<string | null>(null);
  const [query, setQuery] = useState('');
  const [status, setStatus] = useState('');
  const formatTime = (value: string | null | undefined) => value && Number.isFinite(Date.parse(value))
    ? formatDateTime(value) : '-';
  const filteredTasks = tasks.filter(task => (!status || task.status === status)
    && `${task.objective} ${task.task_id}`.toLocaleLowerCase().includes(query.trim().toLocaleLowerCase()));

  useEffect(() => {
    loadTasks();
  }, []);

  const loadTasks = async () => {
    setLoading(true);
    setError(false);
    try {
      const data = await api.listTasks();
      setTasks(data);
    } catch {
      setError(true);
    } finally {
      setLoading(false);
    }
  };

  const openTask = async (taskId: string) => {
    setOpening(taskId);
    setError(false);
    try {
      setSelectedTask(await api.getTask(taskId));
    } catch {
      setSelectedTask(null);
      setError(true);
    } finally {
      setOpening(null);
    }
  };

  const copyOutput = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text);
    } catch {
      setError(true);
    }
  };

  const downloadOutput = (task: TaskDetail) => {
    const blob = new Blob([taskOutput(task) || ''], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `task-${task.task_id.slice(0, 8)}-output.txt`;
    a.click();
    URL.revokeObjectURL(url);
  };

  if (loading) {
    return (
      <div className="h-full min-h-0 min-w-0 flex flex-col text-[var(--color-text-primary)]" aria-busy="true">
        <div className="flex-1 min-h-0 overflow-y-auto p-4">
          <div role="status" aria-label={t('common.loading')}>
            <SkeletonList count={3} />
          </div>
        </div>
      </div>
    );
  }

  if (selectedTask) {
    const output = taskOutput(selectedTask);
    const tokens = (selectedTask.result as Record<string, unknown> | undefined)?.tokens_used;
    return (
      <div className="h-full flex flex-col">
        <div className="flex items-center gap-2 p-3 border-b border-[var(--color-border-subtle)]">
          <button type="button"
            onClick={() => setSelectedTask(null)}
            className="text-xs text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] transition-colors"
          >
            {t('common.back')}
          </button>
          <ChevronRight size={10} className="text-[var(--color-text-muted)]" />
          <span className="text-xs text-[var(--color-text-secondary)]">{t('task_history.detail_heading')}</span>
        </div>
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          <Card padding="md" className="space-y-2">
            <h3 className="text-sm font-medium text-[var(--color-text-primary)]">{selectedTask.objective}</h3>
            <div className="flex flex-wrap items-center gap-3 text-xs text-[var(--color-text-muted)]">
              <span className="font-mono break-all">ID: {selectedTask.task_id}</span>
              <span>{t('common.created')}: {formatTime(selectedTask.created_at)}</span>
              <span>{t('task_history.steps', { done: reportedNumber(selectedTask.progress, t), total: reportedNumber(selectedTask.total_steps, t) })}</span>
              {typeof tokens === 'number' && <span>Tokens: {tokens.toLocaleString()}</span>}
            </div>
            <div className="flex items-center gap-2">
              <span className={`text-xs ${taskStatusColor(selectedTask.status)}`}>
                {taskStatusLabel(selectedTask.status, t)}
              </span>
            </div>
          </Card>
          {error && <p role="alert" className="text-xs text-[var(--color-error)]">{t('common.error')} · {t('common.try_again')}</p>}
          {output && (
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <h4 className="text-xs font-medium text-[var(--color-text-secondary)]">{t('task_history.final_output')}</h4>
                <div className="flex items-center gap-2">
                  <button type="button"
                    onClick={() => copyOutput(output)}
                    className="text-[10px] text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] flex items-center gap-1 transition-colors"
                  >
                    <Copy size={10} /> {t('common.copy')}
                  </button>
                  <button type="button"
                    onClick={() => downloadOutput(selectedTask)}
                    className="text-[10px] text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] flex items-center gap-1 transition-colors"
                  >
                    <Download size={10} /> {t('common.export')}
                  </button>
                </div>
              </div>
              <Card padding="none" className="overflow-hidden">
                <pre className="p-3 bg-[var(--color-bg-surface-1)] text-xs text-[var(--color-text-primary)] whitespace-pre-wrap break-words font-mono">
                  {output}
                </pre>
              </Card>
            </div>
          )}
          {selectedTask.error && (
            <Card padding="none" className="overflow-hidden border-[var(--color-error)]/30">
              <pre className="p-3 bg-[var(--color-bg-surface-1)] text-xs text-[var(--color-error)] whitespace-pre-wrap break-words font-mono">
                {selectedTask.error}
              </pre>
            </Card>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="h-full min-h-0 min-w-0 flex flex-col text-[var(--color-text-primary)]">
      <div className="px-4 py-3 border-b border-[var(--color-border-subtle)] flex items-center justify-between gap-3">
        <h2 className="text-sm font-semibold">{t('navigation.task_history')} <span className="ml-2 font-normal text-[var(--color-text-muted)] tabular-nums">{filteredTasks.length} / {tasks.length}</span></h2>
        <Button variant="secondary" size="sm" icon={<RefreshCw size={14} />} onClick={loadTasks}>{t('common.refresh')}</Button>
      </div>
      <div className="flex flex-wrap gap-2 px-4 py-2 border-b border-[var(--color-border-subtle)]">
        <input aria-label={t('common.search')} placeholder={t('common.search')} value={query} onChange={event => setQuery(event.target.value)} className="min-w-0 flex-1 rounded-md border border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-1)] px-3 py-2 text-xs" />
        <select aria-label={t('common.status')} value={status} onChange={event => setStatus(event.target.value)} className="rounded-md border border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-1)] px-3 py-2 text-xs">
          <option value="">{t('common.all')}</option>
          {Array.from(new Set([...Object.keys(TASK_STATUS_LABEL_KEYS), ...tasks.map(task => task.status)])).map(value => <option key={value} value={value}>{taskStatusLabel(value, t)}</option>)}
        </select>
      </div>
      {error && <div role="alert" className="flex items-center gap-3 px-4 py-2 text-xs text-[var(--color-error)]">{t('right_panel.states.load_failed')}<button type="button" onClick={loadTasks} className="underline">{t('common.retry')}</button></div>}
      <div className="flex-1 min-h-0 overflow-auto">
        <table className="w-full min-w-[640px] text-left text-xs">
          <thead className="sticky top-0 bg-[var(--color-bg-surface-2)] text-[var(--color-text-muted)]"><tr>
            {[t('navigation.tasks'), t('common.status'), t('common.created'), t('common.actions')].map(label => <th key={label} scope="col" className="px-4 py-2 font-medium whitespace-nowrap">{label}</th>)}
          </tr></thead>
          <tbody className="divide-y divide-[var(--color-border-subtle)]">
            {filteredTasks.map(task => <tr key={task.task_id} className="hover:bg-[var(--color-bg-surface-2)]">
              <td className="px-4 py-3 max-w-xs"><p className="truncate" title={task.objective}>{task.objective}</p><p className="mt-1 font-mono text-[var(--color-text-muted)] truncate" title={task.task_id}>{task.task_id}</p></td>
              <td className={`px-4 py-3 whitespace-nowrap ${taskStatusColor(task.status)}`}>{taskStatusLabel(task.status, t)}</td>
              <td className="px-4 py-3 whitespace-nowrap tabular-nums text-[var(--color-text-secondary)]">{formatTime(task.created_at)}</td>
              <td className="px-4 py-2"><button type="button" disabled={opening !== null} onClick={() => openTask(task.task_id)} aria-label={`${t('common.open')}: ${task.objective}`} className="inline-flex items-center gap-1 rounded-md px-2 py-2 hover:bg-[var(--color-bg-surface-3)] disabled:opacity-50">{opening === task.task_id ? t('common.loading') : t('common.open')}<ChevronRight size={14} /></button></td>
            </tr>)}
          </tbody>
        </table>
        {!error && filteredTasks.length === 0 && (
          <Card padding="none" className="m-4 overflow-hidden">
            <EmptyState
              className="w-full"
              icon="search"
              title={t(tasks.length ? 'common.no_results' : 'common.no_data')}
            />
          </Card>
        )}
      </div>
    </div>
  );
}
