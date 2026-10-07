import { useState, useEffect, useCallback, useRef } from 'react';
import { pageIcons as icons } from '../lib/icons';

const { stop: Square, successCircle: CheckCircle2, errorCircle: XCircle, add: Plus, refresh: RefreshCw, workflow: GitBranch, pause: Pause, play: Play, retry: RotateCcw, undo: Undo2, hand: Hand, check: Check } = icons;
import { useI18n } from '../i18n';
import { formatDateTime } from '../i18n/utils';
import { taskStatusColor, taskStatusLabel } from '../components/collaboration/taskStatus';
import { api, type TaskDetail, type TaskSummary, type SubtaskItem } from '../api';
import { consumeTaskEvents, mergeTaskEvent, type LiveTask, type TaskEvent } from '../components/anchored/taskApi';
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
      className={`w-full text-left px-4 py-2.5 border-b border-[var(--color-border-subtle)] transition-colors duration-200 border-l-2 motion-reduce:transition-none ${
        isSelected
          ? 'bg-[var(--color-bg-surface-2)] border-l-[var(--color-accent)]'
          : 'hover:bg-[var(--color-bg-surface-2)] border-l-transparent'
      }`}
    >
      <div className="flex items-center justify-between gap-2">
        <span className="text-[length:var(--text-xs)] font-semibold text-[var(--color-text-primary)] truncate">{task.objective}</span>
        <span className={`text-[length:var(--text-2xs)] font-medium shrink-0 ${taskStatusColor(task.status)}`}>
          {taskStatusLabel(task.status, t)}
        </span>
      </div>
      <div className="mt-1 flex items-center justify-between gap-2 text-[length:var(--text-xs)] tabular-nums text-[var(--color-text-muted)]">
        <span>{task.created_at && Number.isFinite(Date.parse(task.created_at)) ? formatDateTime(task.created_at) : '-'}</span>
        <span>{task.progress}/{task.total_steps}</span>
      </div>
      {task.status === 'running' && (
        <div className="mt-2 w-full h-1.5 bg-[var(--color-bg-surface-3)] rounded-[var(--radius-pill)] overflow-hidden">
          <div
            className="h-full bg-[var(--color-accent)] rounded-[var(--radius-pill)] transition-all duration-300 motion-reduce:transition-none"
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
  const [subtasks, setSubtasks] = useState<SubtaskItem[]>([]);
  const [subtasksLoading, setSubtasksLoading] = useState(false);
  const [subtasksError, setSubtasksError] = useState(false);
  const [claiming, setClaiming] = useState(false);
  const [reportingId, setReportingId] = useState<string | null>(null);
  const [actionBusy, setActionBusy] = useState<string | null>(null);
  const suppressStreamRefreshRef = useRef(false);
  const detailLoadedRef = useRef(false);
  const taskEventControllerRef = useRef<AbortController | null>(null);

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
    // A previous fetch failing must not leave the banner up once this one
    // succeeds (R13-43).
    setError(false);
    setSelectedTask(null);
    detailLoadedRef.current = false;
    setDetailLoading(true);
    api.getTask(selectedTaskId).then(task => {
      if (!active) return;
      setSelectedTask(task);
      detailLoadedRef.current = true;
      // The detail payload can drop created_at; keep the list's timestamp so
      // the summary row does not lose it when the detail overwrites it (R9-04).
      setTasks(previous => previous.map(item => item.task_id === task.task_id ? { ...task, created_at: task.created_at ?? item.created_at } : item));
    }).catch(() => { if (active) setError(true); }).finally(() => { if (active) setDetailLoading(false); });
    return () => { active = false; };
  }, [selectedTaskId, revision]);

  const fetchSubtasks = useCallback(async (taskId: string) => {
    setSubtasksLoading(true);
    setSubtasksError(false);
    try {
      const data = await api.listSubtasks(taskId);
      setSubtasks(data.subtasks);
    } catch {
      setSubtasks([]);
      setSubtasksError(true);
    } finally {
      setSubtasksLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!selectedTaskId) return;
    setSubtasks([]);
    fetchSubtasks(selectedTaskId);
  }, [selectedTaskId, fetchSubtasks, revision]);

  const claimNext = async () => {
    if (!selectedTaskId || claiming) return;
    setClaiming(true);
    setError(false);
    try {
      await api.claimSubtasks(selectedTaskId, 'ui-worker', 1);
      await fetchSubtasks(selectedTaskId);
      setRevision(value => value + 1);
    } catch { setError(true); } finally { setClaiming(false); }
  };

  const completeSubtask = async (subtaskId: string) => {
    if (!selectedTaskId || reportingId) return;
    setReportingId(subtaskId);
    setError(false);
    try {
      await api.completeSubtask(selectedTaskId, subtaskId, 'ui-worker', { accepted: true });
      await fetchSubtasks(selectedTaskId);
      setRevision(value => value + 1);
    } catch { setError(true); } finally { setReportingId(null); }
  };

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
    suppressStreamRefreshRef.current = true;
    taskEventControllerRef.current?.abort();
    try {
      const response = await api.stopTask(taskId);
      if (response.cancelled) {
        setSelectedTask(previous => previous ? { ...previous, status: 'cancelled' } : previous);
        setTasks(previous => previous.map(item => item.task_id === taskId ? { ...item, status: 'cancelled' } : item));
      }
    } catch { setError(true); } finally {
      suppressStreamRefreshRef.current = false;
      setStopping(false);
    }
  };

  type ControlAction = 'pause' | 'resume' | 'retry' | 'rollback';

  useEffect(() => {
    if (!selectedTaskId) return;
    const controller = new AbortController();
    taskEventControllerRef.current = controller;
    const applyEvent = (event: TaskEvent) => {
      setSelectedTask(previous => {
        const current = previous ?? {
          task_id: selectedTaskId,
          objective: '',
          status: 'pending',
          progress: 0,
          total_steps: 0,
        };
        const merged = mergeTaskEvent(current as LiveTask, event);
        setTasks(items => items.map(item => item.task_id === selectedTaskId ? { ...item, ...merged } : item));
        return merged as TaskDetail;
      });
    };
    void consumeTaskEvents(selectedTaskId, controller.signal, applyEvent).catch(() => {
      if (!controller.signal.aborted && detailLoadedRef.current && !suppressStreamRefreshRef.current) {
        setRevision(value => value + 1);
      }
    });
    return () => {
      controller.abort();
      if (taskEventControllerRef.current === controller) taskEventControllerRef.current = null;
    };
  }, [selectedTaskId]);

  const controlTask = async (action: ControlAction) => {
    if (!selectedTaskId || actionBusy) return;
    setActionBusy(action);
    setError(false);
    try {
      if (action === 'pause') await api.pauseTask(selectedTaskId);
      else if (action === 'resume') await api.resumeTask(selectedTaskId);
      else if (action === 'retry') await api.retryTask(selectedTaskId);
      else await api.rollbackTask(selectedTaskId);
      fetchTasks();
      setRevision(value => value + 1);
    } catch { setError(true); } finally { setActionBusy(null); }
  };

  // Backend rejects invalid transitions with 409; these gates only decide
  // which buttons are offered for the current status.
  const controlAvailability: Record<ControlAction, boolean> = selectedTask ? {
    pause: selectedTask.status === 'running',
    resume: selectedTask.status === 'paused',
    retry: ['failed', 'cancelled'].includes(selectedTask.status),
    rollback: ['completed', 'failed', 'paused'].includes(selectedTask.status),
  } : { pause: false, resume: false, retry: false, rollback: false };

  return (
    <div className="h-full min-h-0 min-w-0 flex flex-col md:flex-row">
      <div className="w-full max-h-[45%] md:max-h-none md:w-80 lg:w-96 border-b md:border-b-0 md:border-r border-[var(--color-border-subtle)] flex flex-col shrink-0">
        <div className="p-4 border-b border-[var(--color-border-subtle)]">
          <div className="flex items-center justify-between mb-3">
            <h1 className="text-[length:var(--text-base)] font-semibold text-[var(--color-text-primary)]">{t('navigation.tasks')}</h1>
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
              <p className="mt-1 text-[length:var(--text-2xs)] text-[var(--color-text-muted)]">{t('task_monitor.list_error_hint')}</p>
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
              <div className="flex shrink-0 items-start gap-2">
                <div className="flex flex-wrap items-center gap-1" role="group" aria-label={t('task_monitor.controls_aria')}>
                  <Button
                    variant="outline"
                    size="xs"
                    icon={<Pause size={12} />}
                    disabled={!controlAvailability.pause || actionBusy !== null}
                    loading={actionBusy === 'pause'}
                    onClick={() => controlTask('pause')}
                  >
                    {t('task_monitor.pause_action')}
                  </Button>
                  <Button
                    variant="outline"
                    size="xs"
                    icon={<Play size={12} />}
                    disabled={!controlAvailability.resume || actionBusy !== null}
                    loading={actionBusy === 'resume'}
                    onClick={() => controlTask('resume')}
                  >
                    {t('task_monitor.resume_action')}
                  </Button>
                  <Button
                    variant="outline"
                    size="xs"
                    icon={<RotateCcw size={12} />}
                    disabled={!controlAvailability.retry || actionBusy !== null}
                    loading={actionBusy === 'retry'}
                    onClick={() => controlTask('retry')}
                  >
                    {t('task_monitor.retry_action')}
                  </Button>
                  <Button
                    variant="outline"
                    size="xs"
                    icon={<Undo2 size={12} />}
                    disabled={!controlAvailability.rollback || actionBusy !== null}
                    loading={actionBusy === 'rollback'}
                    onClick={() => controlTask('rollback')}
                  >
                    {t('task_monitor.rollback_action')}
                  </Button>
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
            </div>

            <div className="flex-1 overflow-y-auto p-4 space-y-3">
              {selectedTask.result !== null && selectedTask.result !== undefined && (
                <Card variant="default">
                  <CardContent className="p-3">
                    <div className="flex items-center gap-2 mb-2">
                      <CheckCircle2 size={14} className="text-[var(--color-success)]" />
                      <span className="text-xs font-semibold text-[var(--color-text-primary)]">{t('task_monitor.output_heading')}</span>
                    </div>
                    <p className="text-xs text-[var(--color-text-secondary)] leading-relaxed whitespace-pre-wrap">
                      {typeof selectedTask.result === 'object' && selectedTask.result !== null && 'output' in selectedTask.result
                        ? String((selectedTask.result as { output?: unknown }).output ?? '')
                        : JSON.stringify(selectedTask.result, null, 2)}
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

              <Card variant="default">
                <CardContent className="p-3">
                  <div className="flex items-center justify-between gap-2 mb-3">
                    <div className="flex items-center gap-2">
                      <GitBranch size={14} className="text-[var(--color-accent)]" />
                      <span className="text-xs font-semibold text-[var(--color-text-primary)]">{t('task_monitor.subtasks_heading')}</span>
                      {!subtasksLoading && subtasks.length > 0 && (
                        <span className="text-[10px] text-[var(--color-text-muted)] tabular-nums">
                          {t('task_monitor.subtasks_count', { claimed: subtasks.filter(s => s.status === 'claimed').length, done: subtasks.filter(s => ['completed', 'failed'].includes(s.status)).length, total: subtasks.length })}
                        </span>
                      )}
                    </div>
                    <Button
                      variant="outline"
                      size="xs"
                      icon={<Hand size={12} />}
                       disabled={claiming || subtasksLoading || subtasksError}
                      onClick={claimNext}
                    >
                      {claiming ? t('task_monitor.claiming') : t('task_monitor.claim_action')}
                    </Button>
                  </div>

                  {subtasksLoading ? (
                    <p role="status" className="py-3 text-xs text-[var(--color-text-muted)]">{t('common.loading')}</p>
                  ) : subtasksError ? (
                    <div role="alert" className="py-3 text-xs text-[var(--color-error)]">
                      <p>{t('task_monitor.subtasks_error')}</p>
                      <button type="button" className="mt-1 underline" onClick={() => selectedTaskId && fetchSubtasks(selectedTaskId)}>
                        {t('common.retry')}
                      </button>
                    </div>
                  ) : subtasks.length === 0 ? (
                    <p className="py-3 text-xs text-[var(--color-text-muted)]">{t('task_monitor.subtasks_empty')}</p>
                  ) : (
                    <ul className="space-y-2" aria-label={t('task_monitor.subtasks_aria')}>
                      {subtasks.map(subtask => (
                         <li key={subtask.subtask_id} className="rounded-[var(--radius-md)] border border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-2)] p-2.5">
                          <div className="flex items-start justify-between gap-2">
                            <div className="min-w-0">
                              <p className="text-xs text-[var(--color-text-primary)] break-words">{subtask.description}</p>
                              <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-[length:var(--text-2xs)] text-[var(--color-text-muted)]">
                                <span className={taskStatusColor(subtask.status)}>
                                  {taskStatusLabel(subtask.status, t)}
                                </span>
                                {subtask.dependencies.length > 0 && (
                                  <span className="font-mono">{subtask.dependencies.join(', ')}</span>
                                )}
                                {subtask.claimed_by && <span>{subtask.claimed_by}</span>}
                              </div>
                              {subtask.error && <p className="mt-1 text-[length:var(--text-2xs)] text-[var(--color-error)] break-words">{subtask.error}</p>}
                            </div>
                            {subtask.status === 'claimed' && subtask.claimed_by === 'ui-worker' && (
                              <Button
                                variant="ghost"
                                size="xs"
                                icon={<Check size={12} />}
                                 disabled={reportingId === subtask.subtask_id}
                                 onClick={() => completeSubtask(subtask.subtask_id)}
                               >
                                 {reportingId === subtask.subtask_id ? t('common.loading') : t('task_monitor.complete_action')}
                              </Button>
                            )}
                          </div>
                        </li>
                      ))}
                    </ul>
                  )}
                </CardContent>
              </Card>
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
