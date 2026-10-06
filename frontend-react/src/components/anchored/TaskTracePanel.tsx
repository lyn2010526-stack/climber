import { useEffect, useState } from 'react';
import { api } from '../../api';
import type { TaskDetail } from '../../api';
import { buildGroupTaskForest, consumeTaskEvents, getGroupTaskSnapshot, isTerminalTask, listTaskGroups, mergeTaskEvent, TaskStreamError, type GroupSnapshot, type LiveTask } from './taskApi';
import { Button } from '../ui/Button';
import { WorkbenchIcon } from '../ui/WorkbenchIcon';
import { useI18n } from '../../i18n';
import '../workspace/codex-suite.css';

interface TraceSummary {
  id: string;
  session_id: string;
  name: string;
  status: string;
  duration_ms: number | null;
  error: string | null;
  spans: unknown[];
}

const LANES = [
  { labelKey: 'anchored.trace.lane_pending', states: ['pending', 'paused'] },
  { labelKey: 'anchored.trace.lane_running', states: ['running', 'retrying'] },
  { labelKey: 'anchored.trace.lane_done', states: ['completed', 'failed', 'cancelled'] },
] as const;

export function TaskTracePanel({ sessionId, kind }: { sessionId?: string | null; kind: 'tasks' | 'traces' }) {
  const { t } = useI18n();
  const [rows, setRows] = useState<Array<LiveTask | TraceSummary>>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [refresh, setRefresh] = useState(0);
  useEffect(() => {
    let active = true;
    let timer: ReturnType<typeof setTimeout>;
    const streams = new Map<string, AbortController>();
    const cursors = new Map<string, { epoch: string; sequence: number }>();
    const liveRows = new Map<string, LiveTask>();
    const streamErrors = new Map<string, string>();
    const retries = new Map<string, { failures: number; nextAt: number }>();
    function recordFailure(id: string, cause: unknown) {
      const failures = (retries.get(id)?.failures ?? 0) + 1;
      const exhausted = failures > 3 || (cause instanceof TaskStreamError && (!cause.retryable || cause.retryAfterMs > 120000));
      const delay = Math.min(120000, Math.max(5000 * 2 ** (failures - 1), cause instanceof TaskStreamError ? cause.retryAfterMs : 0));
      retries.set(id, { failures, nextAt: exhausted ? Infinity : Date.now() + delay });
      const message = cause instanceof Error ? cause.message : t('anchored.trace.stream_error');
      streamErrors.set(id, t('anchored.trace.stream_note', { id, message, note: exhausted ? t('anchored.trace.stream_retry_stopped') : t('anchored.trace.stream_retry_in', { seconds: delay / 1000 }) }));
      setError([...streamErrors.values()].join('; '));
    }
    setRows([]);
    setError(null);
    async function load() {
      try {
        const data = kind === 'tasks' ? await api.listTasks({ limit: 50 }) : await api.listTraces();
        if (!active) return;
        if (!Array.isArray(data)) throw new Error(t('anchored.trace.invalid_payload'));
        setError(null);
        if (kind === 'traces') setRows(data.filter((row: TraceSummary) => row.session_id === sessionId));
        else {
          const ids = new Set(data.map((task: LiveTask) => task.task_id));
          for (const [id, stream] of streams) {
            if (!ids.has(id)) { stream.abort(); streams.delete(id); }
          }
          for (const id of liveRows.keys()) if (!ids.has(id)) {
            liveRows.delete(id); cursors.delete(id); streamErrors.delete(id); retries.delete(id);
          }
          for (const task of data as LiveTask[]) {
            // Unversioned discovery rows cannot overwrite a versioned SSE snapshot.
            if (!cursors.has(task.task_id)) liveRows.set(task.task_id, task);
            if (isTerminalTask(liveRows.get(task.task_id)?.status ?? task.status) || streams.has(task.task_id)
              || Date.now() < (retries.get(task.task_id)?.nextAt ?? 0)) continue;
            const stream = new AbortController();
            streams.set(task.task_id, stream);
            let awaitingSnapshot = true;
            void consumeTaskEvents(task.task_id, stream.signal, event => {
              if (!active || stream.signal.aborted) return;
              const current = liveRows.get(task.task_id);
              if (!current) return;
              if (awaitingSnapshot && event.type !== 'snapshot') return;
              if (!awaitingSnapshot && event.epoch !== cursors.get(task.task_id)?.epoch) {
                throw new TaskStreamError(t('anchored.trace.epoch_changed'));
              }
              const updated = mergeTaskEvent(current, event, awaitingSnapshot ? undefined : cursors.get(task.task_id));
              if (updated === current) return;
              awaitingSnapshot = false;
              cursors.set(task.task_id, { epoch: event.epoch, sequence: event.sequence });
              liveRows.set(task.task_id, updated);
              streamErrors.delete(task.task_id);
              setError(streamErrors.size ? [...streamErrors.values()].join('; ') : null);
              setRows([...liveRows.values()]);
              if (isTerminalTask(updated.status)) stream.abort();
            }).then(() => {
              if (active && !stream.signal.aborted && !isTerminalTask(liveRows.get(task.task_id)?.status ?? '')) {
                recordFailure(task.task_id, new Error(t('anchored.trace.stream_interrupted')));
              }
            }).catch(cause => {
              if (active && !stream.signal.aborted) {
                recordFailure(task.task_id, cause);
              }
            }).finally(() => { if (streams.get(task.task_id) === stream) streams.delete(task.task_id); });
          }
          setRows([...liveRows.values()]);
          if (streamErrors.size) setError([...streamErrors.values()].join('; '));
        }
      } catch (cause) {
        if (active) setError(cause instanceof Error ? cause.message : t('anchored.trace.load_failed'));
      } finally {
        if (active) {
          setLoading(false);
          timer = setTimeout(() => { void load(); }, 5000);
        }
      }
    }
    setLoading(true);
    if (kind === 'traces' && !sessionId) { setLoading(false); return; }
    void load();
    return () => { active = false; clearTimeout(timer); for (const stream of streams.values()) stream.abort(); };
  }, [kind, sessionId, refresh]);

  const tasks = rows as LiveTask[];
  const traces = rows as TraceSummary[];
  return (
    <div data-testid={`anchored-${kind}-panel`} className="space-y-[var(--space-2)] text-[length:var(--text-2xs)] text-[var(--color-text-secondary)]">
      <p className="cx-card-meta">{kind === 'tasks' ? t('anchored.trace.kind_tasks') : t('anchored.trace.kind_traces')}</p>
      {kind === 'traces' && <GroupTaskTree key={sessionId ?? ''} />}
      {loading && <p role="status">{t('anchored.trace.loading')}</p>}
      {error && <div role="alert" className="rounded-[var(--radius-md)] border border-[var(--color-error)]/30 bg-[var(--color-error-subtle)] px-[var(--space-2)] py-[var(--space-1)]">{error}<Button size="xs" variant="ghost" onClick={() => setRefresh(value => value + 1)}>{t('anchored.trace.retry')}</Button></div>}
      {!loading && !error && rows.length === 0 && <p>{t('anchored.trace.empty')}</p>}
      {kind === 'tasks' ? (
        <div className="space-y-[var(--space-2)]">
          {LANES.map(lane => {
            const laneTasks = tasks.filter(task => (lane.states as readonly string[]).includes(task.status));
            return (
            <section key={lane.labelKey} aria-label={t(lane.labelKey)} className="min-w-0 space-y-[var(--space-1)]">
               <h4 className="flex items-center gap-[var(--space-1)]"><WorkbenchIcon name="task" size={12} />{t(lane.labelKey)}<span className="cx-count ml-auto">{laneTasks.length}</span></h4>
              {laneTasks.map(task => (
                <TaskRow key={task.task_id} task={task} />
              ))}
            </section>
            );
          })}
        </div>
      ) : traces.map(trace => (
        <details key={trace.id} className="rounded-[var(--radius-sm)] border border-[var(--color-border-subtle)] p-[var(--space-1)]">
          <summary className="cursor-pointer" title={trace.id}>{trace.name} · {trace.status} · {trace.duration_ms === null ? t('anchored.trace.duration_unreported') : `${trace.duration_ms}ms`}</summary>
          {trace.error && <p className="text-[var(--color-error)]">{trace.error}</p>}
          <pre className="max-h-[var(--anchored-result-height)] overflow-auto whitespace-pre-wrap [overflow-wrap:anywhere]">{JSON.stringify(trace.spans, null, 2)}</pre>
        </details>
      ))}
      {kind === 'tasks' && tasks.some(task => !LANES.some(lane => (lane.states as readonly string[]).includes(task.status))) && <p>{t('anchored.trace.unmapped_status', { list: tasks.filter(task => !LANES.some(lane => (lane.states as readonly string[]).includes(task.status))).map(task => `${task.task_id}: ${task.status}`).join('; ') })}</p>}
    </div>
  );
}

function ReportedDetails({ objective, result, error }: { objective?: unknown; result?: unknown; error?: unknown }) {
  const { t } = useI18n();
  const value = (data: unknown) => data === undefined || data === null || data === ''
    ? t('anchored.status.unreported') : typeof data === 'string' ? data : JSON.stringify(data, null, 2);
  const fields = [
    { key: 'objective', label: t('anchored.info.tree_goal'), data: objective },
    { key: 'result', label: t('anchored.info.tree_result'), data: result },
    { key: 'error', label: t('anchored.info.tree_error'), data: error },
  ];
  return <dl className="space-y-[var(--space-1)] py-[var(--space-1)]">
    {fields.map(field =>
      <div key={field.key}>
        <dt className="text-[var(--color-text-muted)]">{field.label}</dt>
        <dd className={`max-h-[var(--anchored-result-height)] overflow-auto whitespace-pre-wrap [overflow-wrap:anywhere] ${field.key === 'error' && field.data ? 'text-[var(--color-error)]' : ''}`}>{value(field.data)}</dd>
      </div>)}
  </dl>;
}

function TaskRow({ task }: { task: LiveTask }) {
  const { t } = useI18n();
  const [open, setOpen] = useState(false);
  const [detail, setDetail] = useState<TaskDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [refresh, setRefresh] = useState(0);
  useEffect(() => {
    if (!open) return;
    let active = true;
    setLoading(true);
    setDetail(null);
    setError(null);
    void api.getTask(task.task_id).then(data => {
      if (active) setDetail(data);
    }).catch(cause => {
      if (active) setError(cause instanceof Error ? cause.message : t('anchored.trace.detail_load_failed'));
    }).finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [open, task.task_id, task.status, task.progress, refresh]);
  return <details open={open} onToggle={event => setOpen(event.currentTarget.open)} className="border-b border-[var(--color-border-subtle)] py-[var(--space-1)]">
    <summary className="cursor-pointer rounded-[var(--radius-md)] hover:bg-[var(--color-bg-surface-2)] focus-visible:outline-none focus-visible:shadow-[var(--focus-ring)]">
      <span className="block truncate text-[13px] text-[var(--color-text-primary)]" title={task.objective}>{task.objective || task.task_id}</span>
      <span className="cx-mono">{task.status} · {task.progress}/{task.total_steps}</span>
    </summary>
    {(task.interruption_reason || task.error) && <p className="text-[var(--color-error)]">{task.interruption_reason || task.error}</p>}
    {open && <>
      <p>{t('anchored.trace.task_id', { id: task.task_id })}</p>
      <time>{task.created_at ? new Date(task.created_at).toLocaleString() : t('anchored.trace.time_unreported')}</time>
      {loading && <p role="status">{t('anchored.trace.detail_loading')}</p>}
      {error && <div role="alert">{error}<Button size="xs" variant="ghost" onClick={() => setRefresh(value => value + 1)}>{t('anchored.trace.retry_detail')}</Button></div>}
      <ReportedDetails objective={task.objective || detail?.objective} result={detail?.result} error={task.error ?? detail?.error} />
    </>}
  </details>;
}

function GroupTaskTree() {
  const { t } = useI18n();
  const [groups, setGroups] = useState<Array<{ id: string; name: string }>>([]);
  const [groupId, setGroupId] = useState('');
  const [snapshot, setSnapshot] = useState<GroupSnapshot | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [refresh, setRefresh] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    let timer: ReturnType<typeof setTimeout>;
    setSnapshot(null);
    setError(null);
    setLoading(true);
    async function load() {
      try {
        if (groupId) {
          const data = await getGroupTaskSnapshot(groupId, controller.signal);
          if (!controller.signal.aborted) setSnapshot(data);
        } else {
          const data = await listTaskGroups(controller.signal);
          if (!Array.isArray(data)) throw new Error(t('anchored.trace.group_payload_invalid'));
          if (!controller.signal.aborted) setGroups(data);
        }
        if (!controller.signal.aborted) setError(null);
      } catch (cause) {
        if (!controller.signal.aborted) setError(cause instanceof Error ? cause.message : t('anchored.trace.group_load_failed'));
      } finally {
        if (!controller.signal.aborted) {
          setLoading(false);
          if (groupId) timer = setTimeout(() => { void load(); }, 5000);
        }
      }
    }
    void load();
    return () => { controller.abort(); clearTimeout(timer); };
  }, [groupId, refresh]);
  const forest = buildGroupTaskForest(snapshot?.task_tree?.nodes ?? []);
  return <section aria-label={t('anchored.trace.group_tree_label')} className="space-y-[var(--space-2)]">
    <label className="block">{t('anchored.trace.group_tree_label')}
      <select aria-label={t('anchored.trace.group_pick')} value={groupId} onChange={event => setGroupId(event.target.value)} className="cx-select w-full">
        <option value="">{t('anchored.trace.group_pick_account')}</option>
        {groups.map(group => <option key={group.id} value={group.id}>{group.name}</option>)}
      </select>
    </label>
    <p className="text-[var(--color-text-muted)]">{t('anchored.trace.group_hint')}</p>
    {loading && <p role="status">{t('anchored.trace.group_loading')}</p>}
    {error && <div role="alert">{error}<Button size="xs" variant="ghost" onClick={() => setRefresh(value => value + 1)}>{t('anchored.trace.retry_group')}</Button></div>}
    {!loading && !error && groupId && forest.length === 0 && <p>{t('anchored.trace.group_empty')}</p>}
    {snapshot?.task_tree?.task_id && <p>{t('anchored.trace.root_task', { id: snapshot.task_tree.task_id })}</p>}
    <ul className="space-y-[var(--space-1)]">{forest.map(node => <GroupNode key={node.node_id} node={node} />)}</ul>
  </section>;
}

function GroupNode({ node }: { node: ReturnType<typeof buildGroupTaskForest>[number] }) {
  const { t } = useI18n();
  const reported = node as typeof node & { objective?: unknown; result?: unknown; error?: unknown; metadata?: { objective?: unknown; result?: unknown; error?: unknown } };
  return <li className="space-y-[var(--space-1)]">
    <details className={node.status === 'failed' ? 'text-[var(--color-error)]' : ''}>
      <summary className="cursor-pointer rounded-[var(--radius-sm)] py-[var(--space-1)] hover:bg-[var(--color-bg-surface-2)] focus-visible:outline-none focus-visible:shadow-[var(--focus-ring)]"><WorkbenchIcon name="task" size={12} /> {node.task_name} · {node.status} · {node.elapsed_ms == null ? t('anchored.trace.duration_unreported') : `${node.elapsed_ms}ms`}</summary>
      <p>{t('anchored.trace.task_id', { id: node.node_id })}</p>
      <ReportedDetails objective={reported.objective ?? reported.metadata?.objective} result={reported.result ?? reported.metadata?.result} error={reported.error ?? reported.metadata?.error} />
      {node.children.length > 0 && <ul className="space-y-[var(--space-1)] border-l border-[var(--color-border-subtle)] pl-[var(--space-2)]">{node.children.map(child => <GroupNode key={child.node_id} node={child} />)}</ul>}
    </details>
  </li>;
}
