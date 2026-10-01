import { useState, useEffect, useCallback } from 'react';
import { Square, CheckCircle2, XCircle, Plus, RefreshCw } from 'lucide-react';
import { useI18n } from '../i18n';
import { formatDateTime } from '../i18n/utils';
import { taskStatusColor, taskStatusLabel } from '../components/collaboration/taskStatus';
import { api, type TaskDetail, type TaskSummary } from '../api';
import { Card, CardContent } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Badge } from '../components/ui/Badge';
import { Input } from '../components/ui/Input';
import { EmptyState } from '../components/ui/EmptyState';
import { SkeletonList } from '../components/ui/Skeleton';

function TaskListItem({ task, isSelected, onClick }: { task: TaskSummary; isSelected: boolean; onClick: () => void }) {
  const { t } = useI18n();
  return (
    <button type="button"
      onClick={onClick}
      aria-pressed={isSelected}
      className={`w-full text-left px-4 py-3 border-b border-[var(--color-border-subtle)] transition-all duration-200 border-l-2 ${
        isSelected
          ? 'bg-[var(--color-bg-surface-2)] border-l-[var(--color-accent)]'
          : 'hover:bg-[var(--color-bg-surface-2)] border-l-transparent'
      }`}
    >
      <div className="flex items-center justify-between gap-2">
        <span className="text-xs font-semibold text-[var(--color-text-primary)] truncate">{task.objective}</span>
        <span className={`text-[10px] font-medium shrink-0 ${taskStatusColor(task.status)}`}>
          {taskStatusLabel(task.status, t)}
        </span>
      </div>
      <div className="mt-1 flex items-center justify-between gap-2 text-xs tabular-nums text-[var(--color-text-muted)]">
        <span>{task.created_at && Number.isFinite(Date.parse(task.created_at)) ? formatDateTime(task.created_at) : '-'}</span>
        <span>{task.progress}/{task.total_steps}</span>
      </div>
      {task.status === 'running' && (
        <div className="mt-2 w-full h-1.5 bg-[var(--color-bg-surface-3)] rounded-full overflow-hidden">
          <div
            className="h-full bg-[var(--color-accent)] rounded-full transition-all duration-300"
            style={{ width: `${(task.progress / Math.max(task.total_steps, 1)) * 100}%` }}
          />
        </div>
      )}
    </button>
  );
}

export default function TaskMonitorPage() {
  const { t } = useI18n();
  const [tasks, setTasks] = useState<TaskSummary[]>([]);
  const [selectedTask, setSelectedTask] = useState<TaskDetail | null>(null);
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null);
  const [newTask, setNewTask] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(false);
  /**
   * The list request failing is a different fact from the list being empty.
   * Sharing one flag made a failed fetch render "no tasks" next to a zero
   * badge, which reads as a backend that holds nothing.
   */
  const [listError, setListError] = useState(false);
  const [listLoading, setListLoading] = useState(true);
  const [stopping, setStopping] = useState(false);
  const [detailLoading, setDetailLoading] = useState(false);
  const [revision, setRevision] = useState(0);

  const fetchTasks = useCallback(async () => {
    setListLoading(true);
    try {
      const data = await api.listTasks();
      setTasks(data);
      setListError(false);
      const first = data[0];
      if (first) {
        setSelectedTaskId(current => current || first.task_id);
      }
    } catch { setListError(true); } finally { setListLoading(false); }
  }, []);

  useEffect(() => {
    fetchTasks();
  }, [fetchTasks]);

  useEffect(() => {
    if (!selectedTaskId) return;
    let active = true;
    setSelectedTask(null);
    setDetailLoading(true);
    api.getTask(selectedTaskId).then(task => {
      if (!active) return;
      setSelectedTask(task);
      setTasks(previous => previous.map(item => item.task_id === task.task_id ? task : item));
    }).catch(() => { if (active) setError(true); }).finally(() => { if (active) setDetailLoading(false); });
    return () => { active = false; };
  }, [selectedTaskId, revision]);

  const createTask = async () => {
    if (loading || !newTask.trim()) return;
    setLoading(true);
    setError(false);
    try {
      const data = await api.createTask({
        task_type: 'agent_run',
        payload: { objective: newTask },
      });
      setNewTask('');
      fetchTasks();
      setSelectedTaskId(data.task_id);
    } catch { setError(true); }
    setLoading(false);
  };

  const stopTask = async (taskId: string) => {
    if (stopping) return;
    setStopping(true);
    setError(false);
    try {
      await api.stopTask(taskId);
      fetchTasks();
      setRevision(value => value + 1);
    } catch { setError(true); } finally { setStopping(false); }
  };

  return (
    <div className="h-full min-h-0 min-w-0 flex flex-col md:flex-row">
      <div className="w-full max-h-[45%] md:max-h-none md:w-80 lg:w-96 border-b md:border-b-0 md:border-r border-[var(--color-border-subtle)] flex flex-col shrink-0">
        <div className="p-4 border-b border-[var(--color-border-subtle)]">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-sm font-semibold text-[var(--color-text-primary)]">{t('navigation.tasks')}</h2>
          <div className="flex items-center gap-2">
            {/* A failed list has no count to report; 0 would claim the
                backend returned no tasks. */}
            <Badge variant="default" size="xs" aria-label={listError ? t('task_monitor.list_count_unreported') : undefined}>
              {listError ? t('collaboration.not_reported') : tasks.length}
            </Badge>
            <Button variant="ghost" size="icon" aria-label={t('common.refresh')} onClick={() => { setError(false); setListError(false); fetchTasks(); setRevision(value => value + 1); }}><RefreshCw size={14} /></Button>
          </div>
          </div>
          <div className="flex gap-2">
            <Input
              value={newTask}
              onChange={e => setNewTask(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && createTask()}
              placeholder={t('task_monitor.objective_placeholder')}
              aria-label={t('navigation.tasks')}
              className="text-xs"
            />
            <Button
              variant="primary"
              size="icon"
              onClick={createTask}
              disabled={loading || !newTask.trim()}
              loading={loading}
              aria-label={t('common.add')}
            >
              <Plus size={16} />
            </Button>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto" aria-busy={listLoading}>
          {listError ? (
            <div role="alert" className="p-6 text-center">
              <p className="text-xs text-[var(--color-text-secondary)]">{t('task_monitor.list_error')}</p>
              <p className="mt-1 text-[11px] text-[var(--color-text-muted)]">{t('task_monitor.list_error_hint')}</p>
            </div>
          ) : listLoading ? (
            <div role="status" className="p-4">
              <SkeletonList count={2} />
            </div>
          ) : tasks.length === 0 ? (
            <EmptyState
              className="min-h-0 py-8 px-4"
              icon="inbox"
              title={t('task_monitor.empty')}
            />
          ) : null}
          {!listError && tasks.map(task => (
            <TaskListItem
              key={task.task_id}
              task={task}
              isSelected={selectedTaskId === task.task_id}
              onClick={() => setSelectedTaskId(task.task_id)}
            />
          ))}
        </div>
      </div>

      <div className="flex-1 flex flex-col min-w-0 min-h-0">
        {error && <div role="alert" className="flex items-center gap-3 px-4 py-2 text-xs text-[var(--color-error)]">{t('common.error')}<button type="button" className="underline" onClick={() => { setError(false); fetchTasks(); setRevision(value => value + 1); }}>{t('common.retry')}</button></div>}
        {selectedTask ? (
          <>
            <div className="p-4 border-b border-[var(--color-border-subtle)] flex items-center justify-between gap-3 shrink-0">
              <div className="min-w-0">
                <h3 className="text-sm font-semibold text-[var(--color-text-primary)] truncate">{selectedTask.objective}</h3>
                <p className="text-xs text-[var(--color-text-muted)] mt-0.5">
                  {t('task_monitor.step_progress', { done: selectedTask.progress, total: selectedTask.total_steps })}
                </p>
                <div className="mt-1 flex flex-wrap gap-x-3 gap-y-1 text-xs text-[var(--color-text-muted)]"><span className={taskStatusColor(selectedTask.status)}>{taskStatusLabel(selectedTask.status, t)}</span><span>{selectedTask.created_at && Number.isFinite(Date.parse(selectedTask.created_at)) ? formatDateTime(selectedTask.created_at) : '-'}</span></div>
              </div>
              {selectedTask.status === 'running' && (
                <Button
                  variant="destructive"
                  size="sm"
                  icon={<Square size={12} />}
                  onClick={() => stopTask(selectedTask.task_id)}
                  disabled={stopping}
                >
                  {t('common.cancel')}
                </Button>
              )}
            </div>

            <div className="flex-1 overflow-y-auto p-4 space-y-3">
              {selectedTask.result && (
                <Card variant="default">
                  <CardContent className="p-3">
                    <div className="flex items-center gap-2 mb-2">
                      <CheckCircle2 size={14} className="text-[var(--color-success)]" />
                      <span className="text-xs font-semibold text-[var(--color-text-primary)]">{t('task_monitor.output_heading')}</span>
                    </div>
                    <p className="text-xs text-[var(--color-text-secondary)] leading-relaxed whitespace-pre-wrap">
                      {String(selectedTask.result.output ?? JSON.stringify(selectedTask.result, null, 2))}
                    </p>
                  </CardContent>
                </Card>
              )}

              {selectedTask.status === 'failed' && (
                <Card variant="default">
                  <CardContent className="p-3">
                    <div className="flex items-center gap-2 mb-2">
                      <XCircle size={14} className="text-[var(--color-error)]" />
                      <span className="text-xs font-semibold text-[var(--color-error)]">{t('task_monitor.failed_heading')}</span>
                    </div>
                    <p className="text-xs text-[var(--color-text-secondary)] leading-relaxed">{selectedTask.error || t('task_monitor.failed_fallback')}</p>
                  </CardContent>
                </Card>
              )}
            </div>
          </>
        ) : (
          <div className="flex-1 flex items-center justify-center">
            <EmptyState
              className="min-h-0"
              icon={detailLoading ? 'queued' : 'inbox'}
              title={detailLoading ? t('common.loading') : t('common.select')}
            />
          </div>
        )}
      </div>
    </div>
  );
}
