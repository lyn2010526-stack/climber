import { useState, useRef, useEffect, useCallback } from 'react';
import { Play, Square, Brain, Wrench, CheckCircle, AlertCircle, Loader2, Clock, Package, RefreshCw, Code, Search, Folder, ChartColumn, ListChecks, ShieldCheck, ArrowRight } from 'lucide-react';
import { PageHeader } from '../components/ui/PageHeader';
import { Card, CardContent } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Badge } from '../components/ui/Badge';
import { EmptyState } from '../components/ui/EmptyState';
import { Progress } from '../components/ui/Progress';
import { api, type ArcBenchStatus, type TaskSummary } from '../api';
import { type TFunction } from '../i18n';
import { useI18n, formatDateTime } from '../i18n/utils';
import { formatDuration } from '../lib/duration';
import { toggleListItem } from '../lib/listSelection';

interface SubTask {
  id: string;
  description: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'retrying';
  result?: string;
  retries?: number;
  retryError?: string;
}

interface PlanStep {
  step: number;
  action: string;
  tool?: string;
  status: 'pending' | 'running' | 'done' | 'error';
}

type RunPhase = 'idle' | 'planning' | 'running' | 'synthesizing' | 'done' | 'failed' | 'cancelling' | 'cancelled' | 'interrupted';

interface FactoryAgent {
  id: string;
  name: string;
  provider: string;
  model_id: string;
  is_active: boolean;
}

const SKILLS = [
  { id: 'code_executor', name: 'Code Executor', icon: Code },
  { id: 'web_search', name: 'Web Search', icon: Search },
  { id: 'file_manager', name: 'File Manager', icon: Folder },
  { id: 'data_analyzer', name: 'Data Analyzer', icon: ChartColumn },
  { id: 'task_planner', name: 'Task Planner', icon: ListChecks },
  { id: 'code_reviewer', name: 'Code Reviewer', icon: ShieldCheck },
];

const PROMPTS = [
  { id: 'senior-engineer', name: 'Senior Engineer' },
  { id: 'code-reviewer', name: 'Code Reviewer' },
  { id: 'architect', name: 'System Architect' },
  { id: 'research-analyst', name: 'Research Analyst' },
  { id: 'data-scientist', name: 'Data Scientist' },
];

const STAGE_KEYS = ['plan', 'task', 'synthesize'] as const;

const STAGE_ICONS: Record<(typeof STAGE_KEYS)[number], typeof Brain> = {
  plan: Brain,
  task: Wrench,
  synthesize: CheckCircle,
};

const ARC_PHASE_COLOR: Record<string, 'success' | 'warning' | 'primary' | 'destructive' | 'default'> = {
  acceptance: 'success',
  completed: 'success',
  failed: 'destructive',
  idle: 'default',
};

function getStatusIcon(status: string) {
  switch (status) {
    case 'completed': return <CheckCircle size={16} className="text-[var(--color-success)]" />;
    case 'failed': return <AlertCircle size={16} className="text-[var(--color-error)]" />;
    case 'running': return <Loader2 size={16} className="text-[var(--color-accent-foreground)] animate-spin" />;
    case 'retrying': return <Loader2 size={16} className="text-[var(--color-warning)] animate-spin" />;
    default: return <div className="w-4 h-4 rounded-full border border-[var(--color-border-subtle)]" />;
  }
}

function formatClock(totalSeconds: number) {
  return formatDuration(totalSeconds, 'seconds');
}

/** An unparseable stamp is shown verbatim: it is the only evidence there is. */
function formatTimestamp(iso?: string | null) {
  if (!iso) return '—';
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return formatDateTime(date);
}

/**
 * The ARC-Bench phase vocabulary. A phase the backend adds later is rendered as
 * the raw value rather than being dropped.
 */
function formatPhase(phase: string, t: TFunction) {
  return t(`factory_mode.arc_phase.${phase}`, phase);
}

export function FactoryModePage() {
  const { t } = useI18n();
  const [goal, setGoal] = useState('');
  const [isRunning, setIsRunning] = useState(false);
  const [phase, setPhase] = useState<RunPhase>('idle');
  const [plan, setPlan] = useState<PlanStep[]>([]);
  const [tasks, setTasks] = useState<SubTask[]>([]);
  const [finalReport, setFinalReport] = useState('');
  const [errorMessage, setErrorMessage] = useState('');
  const [selectedSkills, setSelectedSkills] = useState<string[]>(['code_executor', 'web_search']);
  const [selectedPrompt, setSelectedPrompt] = useState('senior-engineer');
  const [fellBackToAutoPlan, setFellBackToAutoPlan] = useState(false);
  const [progressLines, setProgressLines] = useState<string[]>([]);
  /**
   * Elapsed time is read from the backend's own `started_at` / `finished_at`
   * columns. A locally ticking counter measures the browser clock, not the run,
   * so it stays unreported until the task record actually carries both stamps.
   */
  const [durationSeconds, setDurationSeconds] = useState<number | null>(null);
  const [recentRuns, setRecentRuns] = useState<TaskSummary[]>([]);
  const [recentRunsError, setRecentRunsError] = useState<string | null>(null);
  const [arcbench, setArcbench] = useState<ArcBenchStatus | null>(null);
  const [arcbenchError, setArcbenchError] = useState<string | null>(null);
  const [agents, setAgents] = useState<FactoryAgent[]>([]);
  const [providers, setProviders] = useState<string[]>([]);
  const [configChoice, setConfigChoice] = useState('auto');
  const [provider, setProvider] = useState('');
  const [model, setModel] = useState('');
  const [configLoading, setConfigLoading] = useState(false);
  const [configError, setConfigError] = useState('');
  const [resolvedModel, setResolvedModel] = useState('');

  const stopStreamRef = useRef<(() => void) | null>(null);
  const taskIdRef = useRef<string | null>(null);
  const runIdRef = useRef(0);
  const terminalRef = useRef<RunPhase | null>(null);
  /**
   * Set when the stream delivers a `synthesize` event. Stage completion follows
   * reported events, so a run that ends with `factory_completed` and no
   * synthesis never shows the synthesis stage as finished.
   */
  const [synthesizeReported, setSynthesizeReported] = useState(false);

  const loadConfiguration = useCallback(async () => {
    setConfigLoading(true);
    setConfigError('');
    try {
      const [savedAgents, keys] = await Promise.all([api.listAgents(), api.listApiKeys()]);
      setAgents(savedAgents.filter((agent: FactoryAgent) => agent.is_active));
      setProviders([...new Set<string>(keys.filter((key: { is_active: boolean }) => key.is_active)
        .map((key: { provider: string }) => key.provider))]);
    } catch (error) {
      setConfigError(error instanceof Error ? error.message : String(error));
    } finally {
      setConfigLoading(false);
    }
  }, []);

  const loadRecentRuns = useCallback(async () => {
    setRecentRunsError(null);
    try {
      const runs = await api.listTasks({ limit: 5 });
      setRecentRuns(runs);
    } catch (e) {
      // A failed read leaves the list unreported. Swallowing it made the section
      // disappear, which reads the same as "this workspace has no runs".
      setRecentRunsError(e instanceof Error ? e.message : t('factory_mode.errors.load_runs'));
    }
  }, [t]);

  const loadArcbenchStatus = useCallback(async () => {
    setArcbenchError(null);
    try {
      setArcbench(await api.getArcbenchStatus());
    } catch (e) {
      setArcbenchError(e instanceof Error ? e.message : t('factory_mode.errors.load_arcbench'));
    }
  }, [t]);

  useEffect(() => {
    loadRecentRuns();
    loadArcbenchStatus();
    loadConfiguration();
    return () => {
      runIdRef.current += 1;
      stopStreamRef.current?.();
    };
  }, [loadRecentRuns, loadArcbenchStatus, loadConfiguration]);

  /**
   * Derive the run duration from the stored task record. Both timestamps must
   * be present and parseable; a half-reported record stays unreported rather
   * than being measured from one stamp to the browser's "now".
   */
  const loadTaskDuration = useCallback(async (taskId: string | null) => {
    if (!taskId) { setDurationSeconds(null); return; }
    try {
      const task = await api.getTask(taskId);
      const started = task?.created_at ? Date.parse(task.created_at) : NaN;
      const finished = (task as { finished_at?: string | null } | null)?.finished_at
        ? Date.parse((task as { finished_at?: string | null }).finished_at as string)
        : NaN;
      if (!Number.isFinite(started) || !Number.isFinite(finished) || finished < started) {
        setDurationSeconds(null);
        return;
      }
      setDurationSeconds((finished - started) / 1000);
    } catch {
      setDurationSeconds(null);
    }
  }, []);

  const toggleSkill = (id: string) => {
    setSelectedSkills(prev => toggleListItem(prev, id));
  };

  const startExecution = async () => {
    if (!goal.trim() || isRunning) return;
    if (configChoice === 'provider' && (!provider || !model.trim())) return;
    const runId = ++runIdRef.current;
    terminalRef.current = null;
    taskIdRef.current = null;
    setPhase('planning');
    setIsRunning(true);
    setFinalReport('');
    setErrorMessage('');
    setTasks([]);
    setPlan([]);
    setFellBackToAutoPlan(false);
    setProgressLines([]);
    setDurationSeconds(null);
    setResolvedModel('');
    setSynthesizeReported(false);

    const payload = {
      goal, skills: selectedSkills, prompt_template: selectedPrompt,
      ...(configChoice === 'provider' ? { provider, model: model.trim() }
        : configChoice !== 'auto' ? { agent_id: configChoice } : {}),
    };
    stopStreamRef.current = api.runAutonomousSkillStream(
      payload,
      event => { if (runIdRef.current === runId) handleEvent(event); },
      () => { if (runIdRef.current === runId) handleClose(); },
    );
  };

  const handleEvent = (event: { type: string; data: any }) => {
    switch (event.type) {
      case 'factory_config':
        taskIdRef.current = event.data.task_id || null;
        setResolvedModel(`${event.data.provider} / ${event.data.model}`);
        break;
      case 'planning':
        setPhase('planning');
        break;
      case 'plan':
        setPhase('running');
        setPlan(event.data.steps || []);
        break;
      case 'plan_fallback':
        setFellBackToAutoPlan(true);
        setProgressLines(prev => [...prev.slice(-49), event.data.reason
          ? t('factory_mode.fallback_to_auto_plan_with_reason', { reason: event.data.reason })
          : t('factory_mode.fallback_to_auto_plan')]);
        break;
      case 'factory_start':
        taskIdRef.current = event.data.task_id || null;
        break;
      case 'task_start':
        setPlan(prev => prev.map(step =>
          step.step === event.data.step ? { ...step, status: 'running' } : step
        ));
         setTasks(prev => {
           const id = event.data.task_id || String(Date.now());
           const existing = prev.find(task => task.id === id);
           if (existing) return prev.map(task => task.id === id ? { ...task, status: 'running' } : task);
           return [...prev, { id, description: event.data.description || '', status: 'running' }];
         });
        break;
      case 'progress':
        if (event.data?.message) {
          setProgressLines(prev => [...prev.slice(-49), String(event.data.message)]);
        }
        break;
      case 'task_complete':
        setPlan(prev => prev.map(step =>
          step.step === event.data.step ? { ...step, status: 'done' } : step
        ));
         setTasks(prev => {
           const taskId = event.data.task_id;
           const updated = prev.map(t => t.id === taskId ? { ...t, status: 'completed' as const, result: event.data.result } : t);
             return updated.some(t => t.id === taskId) ? updated : [...updated, {
               id: taskId || `completed-${Date.now()}`,
               description: event.data.description || t('factory_mode.step_completed'),
               status: 'completed' as const,
               result: event.data.result,
             }];
         });
        break;
      case 'task_retry':
        setTasks(prev => prev.map(t =>
          t.id === event.data.task_id ? {
            ...t,
            status: 'retrying',
            retries: event.data.retries,
            retryError: event.data.error,
          } : t
        ));
        break;
      case 'task_failed':
        terminalRef.current = 'failed';
        setPhase('failed');
        setErrorMessage(event.data.error || t('factory_mode.errors.step_failed'));
        setPlan(prev => prev.map(step =>
          step.step === event.data.step ? { ...step, status: 'error' } : step
        ));
        setTasks(prev => prev.map(t =>
          t.id === event.data.task_id ? { ...t, status: 'failed', result: event.data.error } : t
        ));
        break;
      case 'factory_failed':
        if (event.data.status === 'cancelled') {
          terminalRef.current = 'cancelled';
          setPhase('cancelled');
          setErrorMessage(event.data.error || t('factory_mode.errors.cancelled'));
          break;
        }
        terminalRef.current = 'failed';
        setPhase('failed');
        setErrorMessage(event.data.error || t('factory_mode.errors.execution_failed'));
        setTasks(prev => [...prev, {
          id: event.data.task_id || `error-${Date.now()}`,
          description: event.data.error || t('factory_mode.errors.execution_failed'),
          status: 'failed',
        }]);
        break;
      case 'factory_completed':
        if (!terminalRef.current) {
          terminalRef.current = 'done';
          setPhase('done');
        }
        break;
      case 'synthesize':
        if (terminalRef.current) break;
        setSynthesizeReported(true);
        setPhase('synthesizing');
        setFinalReport(event.data.report || '');
        break;
      case 'error':
        terminalRef.current = 'failed';
        setErrorMessage(event.data?.detail || event.data?.error || t('factory_mode.errors.execution_failed'));
        setPhase('failed');
        break;
    }
  };

  const handleClose = () => {
    stopStreamRef.current = null;
    setIsRunning(false);
    if (terminalRef.current) {
      setPhase(terminalRef.current);
    } else {
      setPhase('interrupted');
      setErrorMessage(t('factory_mode.errors.stream_ended_unconfirmed'));
    }
    loadRecentRuns();
    loadTaskDuration(taskIdRef.current);
  };

  const stopExecution = async () => {
    const runId = ++runIdRef.current;
    const stopStream = stopStreamRef.current;
    setPhase('cancelling');
    try {
      const result = taskIdRef.current ? await api.stopTask(taskIdRef.current) : null;
      if (runIdRef.current !== runId) return;
      if (result?.cancelled) {
        terminalRef.current = 'cancelled';
        setPhase('cancelled');
      } else {
        setPhase('interrupted');
        setErrorMessage(t('factory_mode.errors.stop_unconfirmed'));
      }
    } catch (error) {
      if (runIdRef.current !== runId) return;
      setPhase('interrupted');
      setErrorMessage(error instanceof Error ? error.message : String(error));
    } finally {
      stopStream?.();
      if (runIdRef.current === runId) {
        stopStreamRef.current = null;
        setIsRunning(false);
        loadRecentRuns();
        loadTaskDuration(taskIdRef.current);
      }
    }
  };

  const doneSteps = plan.filter(step => step.status === 'done').length;
  const planProgress = plan.length > 0 ? (doneSteps / plan.length) * 100 : 0;
  const activeStageIndex = phase === 'planning' ? 0 : phase === 'running' ? 1 : phase === 'synthesizing' || phase === 'done' ? 2 : -1;
  /**
   * A stage counts as finished when the stream has moved past it, or when the
   * stream explicitly reported it. `phase === 'done'` alone proved nothing
   * about synthesis, so it no longer marks every stage complete.
   */
  const isStageDone = (index: number) =>
    index < activeStageIndex || (index === 2 && synthesizeReported);
  const arcPhaseColor = ARC_PHASE_COLOR[arcbench?.phase || 'idle'] || 'default';

  const deliveryStatus = arcbenchError ? (
      <div role="alert" className="mt-4 rounded-lg border border-[var(--color-error)]/30 bg-[var(--color-error-subtle)] px-4 py-3 text-xs text-[var(--color-error)]">
       {t('factory_mode.delivery.status_not_reported', { detail: arcbenchError })}
      <button type="button" className="ml-2 underline" onClick={loadArcbenchStatus}>{t('common.retry')}</button>
    </div>
  ) : arcbench && (
          <Card variant="default" padding="none" className="mt-4 rounded-lg shadow-none">
            <CardContent className="p-5">
              <div className="flex items-center justify-between mb-3">
                <h3 className="font-semibold text-sm text-[var(--color-text-primary)] flex items-center gap-2">
                  <Package size={16} className="text-[var(--color-accent-foreground)]" /> {t('factory_mode.delivery.title')}
                </h3>
                <Button
                  variant="ghost"
                  size="sm"
                  icon={<RefreshCw size={14} />}
                  aria-label={t('factory_mode.delivery.refresh_aria')}
                  onClick={loadArcbenchStatus}
                  disabled={isRunning}
                />
              </div>
              {!arcbench.available ? (
                <p className="text-sm text-[var(--color-text-muted)]">{arcbench.message}</p>
              ) : (
                <div className="space-y-3">
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge variant={arcPhaseColor} size="sm">{formatPhase(arcbench.phase, t)}</Badge>
                    <span className="text-xs text-[var(--color-text-secondary)]">{arcbench.phase_detail}</span>
                    {arcbench.updated_at && (
                      <span className="text-xs text-[var(--color-text-muted)] tabular-nums ml-auto">
                        {formatDateTime(arcbench.updated_at)}
                      </span>
                    )}
                  </div>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
                    <div className="rounded-xl bg-[var(--color-bg-surface-2)] border border-[var(--color-border-subtle)] px-3 py-2">
                      <p className="text-[var(--color-text-muted)] mb-1">{t('factory_mode.delivery.acceptance')}</p>
                      {arcbench.acceptance?.ran ? (
                        <p className="text-[var(--color-text-primary)] tabular-nums">
                          {t('factory_mode.delivery.acceptance_counts', {
                            passed: arcbench.acceptance.passed,
                            failed: arcbench.acceptance.failed,
                          })}
                        </p>
                      ) : <p className="text-[var(--color-text-muted)]">{t('factory_mode.delivery.not_run')}</p>}
                    </div>
                    <div className="rounded-xl bg-[var(--color-bg-surface-2)] border border-[var(--color-border-subtle)] px-3 py-2">
                      <p className="text-[var(--color-text-muted)] mb-1">{t('factory_mode.delivery.pack_artifact')}</p>
                      <p className={arcbench.pack_exists ? 'text-[var(--color-success)] truncate' : 'text-[var(--color-text-muted)]'}>
                        {arcbench.pack_artifact ? arcbench.pack_artifact.split('/').pop() : t('factory_mode.delivery.none')}
                      </p>
                    </div>
                    <div className="rounded-xl bg-[var(--color-bg-surface-2)] border border-[var(--color-border-subtle)] px-3 py-2">
                      <p className="text-[var(--color-text-muted)] mb-1">{t('factory_mode.delivery.trace_dir')}</p>
                      <p className={arcbench.trace_exists ? 'text-[var(--color-success)]' : 'text-[var(--color-text-muted)]'}>
                        {arcbench.trace_exists ? t('factory_mode.delivery.present') : t('factory_mode.delivery.missing')}
                      </p>
                    </div>
                    <div className="rounded-xl bg-[var(--color-bg-surface-2)] border border-[var(--color-border-subtle)] px-3 py-2">
                      <p className="text-[var(--color-text-muted)] mb-1">{t('factory_mode.delivery.output_dir')}</p>
                      <p className="text-[var(--color-text-primary)] truncate">{arcbench.output_dir || '—'}</p>
                    </div>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        );

  return (
    <div className="h-full overflow-y-auto">
      <div className="p-4 md:p-6 max-w-5xl mx-auto">
        <PageHeader title={t('factory_mode.title')} icon={<ListChecks size={20} />} />
        <Card variant="default" padding="none" className="mb-4 rounded-lg shadow-none">
          <CardContent className="p-4">
            <h2 className="mb-3 text-sm font-semibold text-[var(--color-text-primary)]">{t('factory_mode.task_and_control')}</h2>
            <label htmlFor="factory-goal" className="block text-sm font-medium text-[var(--color-text-secondary)] mb-2">{t('factory_mode.goal_label')}</label>
            <textarea
              id="factory-goal"
              value={goal}
              onChange={(e) => setGoal(e.target.value)}
              disabled={isRunning}
              placeholder={t('factory_mode.goal_placeholder')}
              rows={3}
              className="w-full bg-[var(--color-bg-surface-2)] border border-[var(--color-border-subtle)] rounded-lg px-3 py-2 text-sm text-[var(--color-text-primary)] placeholder:text-[var(--color-text-muted)] focus-visible:outline-[var(--color-accent)] resize-y disabled:opacity-60"
            />
            <div className="mt-4 space-y-3 text-sm text-[var(--color-text-secondary)]">
              <label htmlFor="factory-config" className="block font-medium">{t('factory_mode.config_source_label')}</label>
              <select id="factory-config" value={configChoice} onChange={e => setConfigChoice(e.target.value)} disabled={isRunning}
                className="w-full rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-2)] p-3">
                <option value="auto">{t('factory_mode.config_source_auto')}</option>
                {agents.map(agent => <option key={agent.id} value={agent.id}>{agent.name} · {agent.provider} / {agent.model_id}</option>)}
                <option value="provider">{t('factory_mode.config_source_provider')}</option>
              </select>
              {configChoice === 'provider' && (
                <div className="grid gap-3 sm:grid-cols-2">
                  <label>{t('factory_mode.provider_label')}
                    <select aria-label={t('factory_mode.provider_label')} value={provider} onChange={e => { setProvider(e.target.value); setModel(''); }} disabled={isRunning}
                      className="mt-1 w-full rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-2)] p-3">
                      <option value="">{t('factory_mode.provider_placeholder')}</option>
                      {providers.map(value => <option key={value} value={value}>{value}</option>)}
                    </select>
                  </label>
                  <label>{t('factory_mode.model_id_label')}
                    <input aria-label={t('factory_mode.model_id_label')} value={model} onChange={e => setModel(e.target.value)} disabled={isRunning}
                      placeholder={t('factory_mode.model_id_placeholder')}
                      className="mt-1 w-full rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-2)] p-3" />
                  </label>
                </div>
              )}
              <p className="text-xs text-[var(--color-text-muted)]">{t('factory_mode.credentials_hint')}</p>
              <p className="text-xs text-[var(--color-text-muted)]"><span className="font-medium">{t('factory_mode.health_pending_label')}</span>{t('factory_mode.health_pending_detail')}</p>
              <div className="flex flex-wrap items-center gap-4">
                <a href="#apikeys" className="text-[var(--color-accent-foreground)] underline">{t('factory_mode.link_api_keys')}</a>
                <a href="#agents" className="text-[var(--color-accent-foreground)] underline">{t('factory_mode.link_agents')}</a>
                <Button variant="ghost" size="sm" onClick={loadConfiguration} disabled={isRunning || configLoading}>{t('factory_mode.refresh_config')}</Button>
              </div>
              {configLoading && <p role="status">{t('factory_mode.reading_config')}</p>}
              {configError && <p role="alert">{t('factory_mode.config_read_failed', { detail: configError })}</p>}
              {!configLoading && !configError && <p>{t('factory_mode.config_read_summary', { agents: agents.length, providers: providers.length })}</p>}
              {resolvedModel && <p>{t('factory_mode.backend_choice', { model: resolvedModel })}</p>}
            </div>

            <div className="mt-5">
              <label className="block text-sm font-medium text-[var(--color-text-secondary)] mb-2">{t('factory_mode.skills_label')}</label>
              <div className="flex flex-wrap gap-2">
                {SKILLS.map(s => (
                  <button type="button"
                    key={s.id}
                    onClick={() => toggleSkill(s.id)}
                     disabled={isRunning}
                     aria-pressed={selectedSkills.includes(s.id)}
                     className={`inline-flex items-center gap-2 px-3 py-2 rounded-md text-xs font-medium border focus-visible:outline-[var(--color-accent)] ${
                      selectedSkills.includes(s.id)
                        ? 'bg-[var(--color-accent-subtle)] border-[var(--color-border-accent)] text-[var(--color-text-primary)]'
                        : 'bg-[var(--color-bg-surface-2)] border-[var(--color-border-subtle)] text-[var(--color-text-muted)] hover:border-[var(--color-border-accent)]'
                    } disabled:opacity-50`}
                  >
                    <s.icon size={14} aria-hidden="true" /> {s.name}
                  </button>
                ))}
              </div>
            </div>

            <div className="mt-5">
              <label htmlFor="factory-prompt" className="block text-sm font-medium text-[var(--color-text-secondary)] mb-2">{t('factory_mode.expert_role_label')}</label>
              <select
                id="factory-prompt"
                value={selectedPrompt}
                onChange={(e) => setSelectedPrompt(e.target.value)}
                disabled={isRunning}
                className="px-4 py-2.5 bg-[var(--color-bg-surface-2)] border border-[var(--color-border-subtle)] rounded-xl text-sm text-[var(--color-text-primary)] focus:outline-none focus:border-[var(--color-accent)]/50 transition-all duration-200 disabled:opacity-50"
              >
                {PROMPTS.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
              </select>
            </div>

            <div className="mt-4 flex flex-wrap items-center gap-3 border-t border-[var(--color-border-subtle)] pt-4">
              {!isRunning ? (
                <Button
                  variant="primary"
                  icon={<Play size={16} />}
                  onClick={startExecution}
                  disabled={!goal.trim() || (configChoice === 'provider' && (!provider || !model.trim()))}
                >
                  {t('factory_mode.start')}
                </Button>
              ) : (
                <Button
                  variant="destructive"
                  icon={<Square size={16} />}
                  onClick={stopExecution}
                  disabled={phase === 'cancelling'}
                >
                  {t('factory_mode.stop')}
                </Button>
              )}
              {/* A run in flight has no recorded end stamp yet, so the clock
                  reads as unreported until the task record carries both. */}
              {(isRunning || durationSeconds !== null) && (
                <span className="flex items-center gap-1.5 text-xs text-[var(--color-text-muted)] tabular-nums">
                  <Clock size={14} aria-hidden="true" />
                  {durationSeconds === null
                    ? t('factory_mode.duration_not_reported')
                    : t('factory_mode.running_for', { clock: formatClock(durationSeconds) })}
                </span>
              )}
              <span role="status" className="text-xs text-[var(--color-text-secondary)]">
                {t(`factory_mode.phase.${phase}`)}
              </span>
            </div>
          </CardContent>
        </Card>

        {plan.length === 0 && tasks.length === 0 && !finalReport && !isRunning && recentRuns.length === 0 && !recentRunsError && (
          <EmptyState
            icon="file"
            title={t('factory_mode.waiting_title')}
            description={t('factory_mode.waiting_description')}
          />
        )}

        {errorMessage && (
          <div role="alert" className="mb-6 rounded-xl border border-[var(--color-error)]/30 bg-[var(--color-error-subtle)] px-4 py-3 text-sm text-[var(--color-error)]">
            {errorMessage}
          </div>
        )}

        {plan.length > 0 && (
          <Card variant="default" padding="none" className="mb-4 rounded-lg shadow-none">
            <CardContent className="p-4">
              <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
                <h3 className="font-semibold text-sm text-[var(--color-text-primary)] flex items-center gap-2">
                  <Wrench size={16} className="text-[var(--color-accent-foreground)]" /> {t('factory_mode.plan_title')}
                  <span className="text-xs font-normal text-[var(--color-text-muted)] tabular-nums">
                    {t('factory_mode.plan_progress', { done: doneSteps, total: plan.length })}
                  </span>
                </h3>
                {durationSeconds !== null && (
                  <span className="flex items-center gap-1.5 text-xs text-[var(--color-text-muted)] tabular-nums">
                    <Clock size={14} aria-hidden="true" /> {formatClock(durationSeconds)}
                  </span>
                )}
              </div>

              <Progress value={planProgress} max={100} size="sm" color={phase === 'failed' ? 'danger' : 'primary'} className="mb-4" />

              <div className="flex items-center gap-2 mb-5">
                {STAGE_KEYS.map((stageKey, index) => {
                  const Icon = STAGE_ICONS[stageKey];
                  const isActive = index === activeStageIndex;
                  const isDone = isStageDone(index);
                  return (
                    <div key={stageKey} className="flex items-center gap-2">
                      <Badge
                        variant={isActive ? 'primary' : isDone ? 'success' : 'default'}
                        size="sm"
                        icon={<Icon size={11} />}
                      >
                        {t(`factory_mode.stage.${stageKey}`)}
                      </Badge>
                      {index < STAGE_KEYS.length - 1 && <ArrowRight size={16} aria-hidden="true" className="shrink-0 text-[var(--color-text-muted)]" />}
                    </div>
                  );
                })}
              </div>

              {fellBackToAutoPlan && (
                <div className="mb-4 rounded-xl border border-[var(--color-warning)]/30 bg-[var(--color-warning-subtle)] px-4 py-2.5 text-xs text-[var(--color-warning)]">
                  {t('factory_mode.fallback_to_auto_plan')}
                </div>
              )}

              <div className="space-y-3">
                {plan.map(step => (
                  <div key={step.step} className="flex items-center gap-3">
                    <span className="w-6 h-6 rounded-full bg-[var(--color-accent-subtle)] text-[var(--color-accent-foreground)] flex items-center justify-center text-xs font-bold shrink-0 border border-[var(--color-border-accent)]">
                      {step.step}
                    </span>
                    <span className={`text-sm flex-1 ${step.status === 'done' ? 'text-[var(--color-text-muted)] line-through' : 'text-[var(--color-text-primary)]'}`}>
                      {step.action}
                    </span>
                    {step.tool && (
                      <Badge variant="default" size="xs">{step.tool}</Badge>
                    )}
                    {step.status === 'running' && <Loader2 size={14} className="text-[var(--color-accent-foreground)] animate-spin shrink-0" />}
                    {step.status === 'done' && <CheckCircle size={14} className="text-[var(--color-success)] shrink-0" />}
                    {step.status === 'error' && <AlertCircle size={14} className="text-[var(--color-error)] shrink-0" />}
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}

        {progressLines.length > 0 && (
          <Card variant="default" padding="none" className="mb-4 rounded-lg shadow-none">
            <CardContent className="p-4">
              <h3 className="font-semibold text-sm text-[var(--color-text-primary)] mb-3 flex items-center gap-2">
                <ListChecks size={14} className="text-[var(--color-text-muted)]" /> {t('factory_mode.live_progress')}
              </h3>
              <div className="max-h-48 overflow-y-auto space-y-1.5 rounded-xl bg-[var(--color-bg-surface-2)] border border-[var(--color-border-subtle)] p-3">
                {progressLines.slice(-30).map((line, index) => (
                  <p key={`${index}-${line}`} className="text-xs text-[var(--color-text-secondary)] font-mono leading-relaxed">
                    {line}
                  </p>
                ))}
              </div>
            </CardContent>
          </Card>
        )}

        {tasks.length > 0 && (
          <Card variant="default" padding="none" className="mb-4 rounded-lg shadow-none">
            <CardContent className="p-4">
              <h3 className="font-semibold text-sm text-[var(--color-text-primary)] mb-4">{t('factory_mode.subtasks')}</h3>
              <div className="divide-y divide-[var(--color-border-subtle)]">
                {tasks.map(task => (
                  <div key={task.id} className="flex items-start gap-3 py-3">
                    <div className="shrink-0 mt-0.5">{getStatusIcon(task.status)}</div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm text-[var(--color-text-primary)]">{task.description}</p>
                      {task.result && (
                        <details className="text-xs text-[var(--color-text-muted)] mt-1">
                          <summary className="cursor-pointer">{t('factory_mode.view_result')}</summary>
                          <p className="mt-2 whitespace-pre-wrap break-words">{task.result}</p>
                        </details>
                      )}
                      {task.retries !== undefined && task.retries > 0 && (
                        <p className="text-xs text-[var(--color-warning)] mt-1">
                          {t('factory_mode.retries', { count: task.retries })}
                          {task.retryError ? `: ${task.retryError}` : ''}
                        </p>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}

        {recentRunsError ? (
          <div role="alert" className="mb-4 rounded-xl border border-[var(--color-error)]/30 bg-[var(--color-error-subtle)] px-4 py-3 text-xs text-[var(--color-error)]">
            {t('factory_mode.recent_runs_not_reported', { detail: recentRunsError })}
            <button type="button" className="ml-2 underline" onClick={loadRecentRuns}>{t('common.retry')}</button>
          </div>
        ) : recentRuns.length > 0 && (
          <Card variant="default" padding="none" className="mb-4 rounded-lg shadow-none">
            <CardContent className="p-4">
              <div className="flex items-center justify-between mb-3">
                <h3 className="font-semibold text-sm text-[var(--color-text-primary)]">{t('factory_mode.recent_runs')}</h3>
                <Button variant="ghost" size="sm" icon={<RefreshCw size={14} />} onClick={loadRecentRuns}>{t('factory_mode.refresh_recent_runs')}</Button>
              </div>
              <div className="space-y-2">
                {recentRuns.map(run => (
                  <div key={run.task_id} className="flex items-center gap-3 py-3 border-b border-[var(--color-border-subtle)] last:border-0">
                    {getStatusIcon(run.status)}
                    <div className="flex-1 min-w-0">
                      <p className="text-sm text-[var(--color-text-primary)] truncate">{run.objective || run.task_id}</p>
                      <p className="text-xs text-[var(--color-text-muted)] mt-0.5 tabular-nums">
                        {run.task_id} · {formatTimestamp(run.created_at)}
                      </p>
                    </div>
                    <Badge variant={run.status === 'completed' ? 'success' : run.status === 'failed' ? 'destructive' : 'default'} size="xs">
                      {run.status}
                    </Badge>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}

        {finalReport && (
          <Card variant="default" padding="none" className="rounded-lg shadow-none">
            <CardContent className="p-4">
              <h3 className="font-semibold text-sm text-[var(--color-text-primary)] mb-4 flex items-center gap-2">
                <CheckCircle size={16} className="text-[var(--color-success)]" /> {t('factory_mode.final_report')}
              </h3>
              <div className="text-sm text-[var(--color-text-secondary)] whitespace-pre-wrap break-words leading-relaxed">
                {finalReport}
              </div>
            </CardContent>
          </Card>
        )}
        {deliveryStatus}
      </div>
    </div>
  );
}
