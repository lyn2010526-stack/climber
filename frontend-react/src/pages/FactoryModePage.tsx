import { useState, useRef, useEffect, useCallback } from 'react';
import { Play, Square, Brain, Wrench, CheckCircle, AlertCircle, Loader2, Clock, Package, RefreshCw } from 'lucide-react';
import { PageHeader } from '../components/ui/PageHeader';
import { Card, CardContent } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Badge } from '../components/ui/Badge';
import { EmptyState } from '../components/ui/EmptyState';
import { Progress } from '../components/ui/Progress';
import { api, type ArcBenchStatus, type TaskSummary } from '../api';

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
  { id: 'code_executor', name: 'Code Executor', icon: '⚙️' },
  { id: 'web_search', name: 'Web Search', icon: '🔍' },
  { id: 'file_manager', name: 'File Manager', icon: '📁' },
  { id: 'data_analyzer', name: 'Data Analyzer', icon: '📊' },
  { id: 'task_planner', name: 'Task Planner', icon: '📋' },
  { id: 'code_reviewer', name: 'Code Reviewer', icon: '🛡️' },
];

const PROMPTS = [
  { id: 'senior-engineer', name: 'Senior Engineer' },
  { id: 'code-reviewer', name: 'Code Reviewer' },
  { id: 'architect', name: 'System Architect' },
  { id: 'research-analyst', name: 'Research Analyst' },
  { id: 'data-scientist', name: 'Data Scientist' },
];

const STAGES = [
  { key: 'plan', label: '规划', icon: Brain },
  { key: 'task', label: '执行', icon: Wrench },
  { key: 'synthesize', label: '综合', icon: CheckCircle },
] as const;

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
    case 'running': return <Loader2 size={16} className="text-[var(--color-accent)] animate-spin" />;
    case 'retrying': return <Loader2 size={16} className="text-amber-400 animate-spin" />;
    default: return <div className="w-4 h-4 rounded-full border border-[var(--color-border-subtle)]" />;
  }
}

function formatDuration(totalSeconds: number) {
  const seconds = Math.max(Math.floor(totalSeconds), 0);
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
}

function formatTimestamp(iso?: string | null) {
  if (!iso) return '—';
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return date.toLocaleString();
}

function formatPhase(phase: string) {
  const labels: Record<string, string> = {
    idle: '尚未运行',
    design: '设计/规划',
    implementation: '实现',
    test: '测试',
    final_check: '最终检查',
    rehearsal: '启动预演',
    acceptance: '验收',
    completed: '已完成',
    failed: '失败',
    running: '运行中',
  };
  return labels[phase] || phase;
}

export function FactoryModePage() {
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
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [recentRuns, setRecentRuns] = useState<TaskSummary[]>([]);
  const [arcbench, setArcbench] = useState<ArcBenchStatus | null>(null);
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
  const startedAtRef = useRef<number | null>(null);
  const runIdRef = useRef(0);
  const terminalRef = useRef<RunPhase | null>(null);

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
    try {
      const runs = await api.listTasks({ limit: 5 });
      setRecentRuns(runs);
    } catch { /* persistence read is best-effort */ }
  }, []);

  const loadArcbenchStatus = useCallback(async () => {
    try {
      setArcbench(await api.getArcbenchStatus());
    } catch { /* read-only card is best-effort */ }
  }, []);

  useEffect(() => {
    loadRecentRuns();
    loadArcbenchStatus();
    loadConfiguration();
    return () => {
      runIdRef.current += 1;
      stopStreamRef.current?.();
    };
  }, [loadRecentRuns, loadArcbenchStatus, loadConfiguration]);

  useEffect(() => {
    if (!isRunning || !startedAtRef.current) return;
    const timer = window.setInterval(() => {
      setElapsedSeconds((Date.now() - (startedAtRef.current ?? Date.now())) / 1000);
    }, 1000);
    return () => window.clearInterval(timer);
  }, [isRunning]);

  const toggleSkill = (id: string) => {
    setSelectedSkills(prev => prev.includes(id) ? prev.filter(s => s !== id) : [...prev, id]);
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
    setElapsedSeconds(0);
    setResolvedModel('');
    startedAtRef.current = Date.now();

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
        setProgressLines(prev => [...prev.slice(-49), event.data.reason ? `已回退到自动计划: ${event.data.reason}` : '已回退到自动计划']);
        break;
      case 'factory_start':
        taskIdRef.current = event.data.task_id || null;
        break;
      case 'task_start':
        setPlan(prev => prev.map(step =>
          step.step === event.data.step ? { ...step, status: 'running' } : step
        ));
        setTasks(prev => [...prev, {
          id: event.data.task_id || String(Date.now()),
          description: event.data.description || '',
          status: 'running',
        }]);
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
        setTasks(prev => prev.map(t =>
          t.id === event.data.task_id ? { ...t, status: 'completed', result: event.data.result } : t
        ));
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
        setErrorMessage(event.data.error || 'Factory step failed');
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
          setErrorMessage(event.data.error || '任务已取消');
          break;
        }
        terminalRef.current = 'failed';
        setPhase('failed');
        setErrorMessage(event.data.error || 'Factory execution failed');
        setTasks(prev => [...prev, {
          id: event.data.task_id || `error-${Date.now()}`,
          description: event.data.error || 'Factory execution failed',
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
        setPhase('synthesizing');
        setFinalReport(event.data.report || '');
        break;
      case 'error':
        terminalRef.current = 'failed';
        setErrorMessage(event.data?.detail || event.data?.error || '执行失败');
        setPhase('failed');
        break;
    }
  };

  const handleClose = () => {
    stopStreamRef.current = null;
    startedAtRef.current = null;
    setIsRunning(false);
    if (terminalRef.current) {
      setPhase(terminalRef.current);
    } else {
      setPhase('interrupted');
      setErrorMessage('事件流已结束，尚未收到任务终态。请在最近运行中确认后台状态。');
    }
    loadRecentRuns();
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
        setErrorMessage('已停止接收事件；后台取消状态尚未确认，请刷新最近运行。');
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
        startedAtRef.current = null;
        loadRecentRuns();
      }
    }
  };

  const doneSteps = plan.filter(step => step.status === 'done').length;
  const planProgress = plan.length > 0 ? (doneSteps / plan.length) * 100 : 0;
  const activeStageIndex = phase === 'planning' ? 0 : phase === 'running' ? 1 : phase === 'synthesizing' || phase === 'done' ? 2 : -1;
  const arcPhaseColor = ARC_PHASE_COLOR[arcbench?.phase || 'idle'] || 'default';

  return (
    <div className="h-full overflow-y-auto page-transition">
      <div className="p-4 md:p-6 lg:p-8 max-w-5xl mx-auto">
        <PageHeader
          title="自主执行主控台"
          description="规划、分解、执行、自愈、综合结果 · 连接 ARC-Bench 交付状态"
          icon={<Brain size={20} />}
        />

        {arcbench && (
          <Card variant="default" className="mb-6">
            <CardContent className="p-5">
              <div className="flex items-center justify-between mb-3">
                <h3 className="font-semibold text-sm text-[var(--color-text-primary)] flex items-center gap-2">
                  <Package size={16} className="text-[var(--color-accent)]" /> ARC-Bench 交付状态
                </h3>
                <Button
                  variant="ghost"
                  size="sm"
                  icon={<RefreshCw size={14} />}
                  onClick={loadArcbenchStatus}
                  disabled={isRunning}
                />
              </div>
              {!arcbench.available ? (
                <p className="text-sm text-[var(--color-text-muted)]">{arcbench.message}</p>
              ) : (
                <div className="space-y-3">
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge variant={arcPhaseColor} size="sm">{formatPhase(arcbench.phase)}</Badge>
                    <span className="text-xs text-[var(--color-text-secondary)]">{arcbench.phase_detail}</span>
                    {arcbench.updated_at && (
                      <span className="text-xs text-[var(--color-text-muted)] tabular-nums ml-auto">{arcbench.updated_at}</span>
                    )}
                  </div>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
                    <div className="rounded-xl bg-[var(--color-bg-surface-2)] border border-[var(--color-border-subtle)] px-3 py-2">
                      <p className="text-[var(--color-text-muted)] mb-1">验收结果</p>
                      {arcbench.acceptance?.ran ? (
                        <p className="text-[var(--color-text-primary)] tabular-nums">
                          {arcbench.acceptance.passed} 通过 · {arcbench.acceptance.failed} 失败
                        </p>
                      ) : <p className="text-[var(--color-text-muted)]">未运行</p>}
                    </div>
                    <div className="rounded-xl bg-[var(--color-bg-surface-2)] border border-[var(--color-border-subtle)] px-3 py-2">
                      <p className="text-[var(--color-text-muted)] mb-1">打包产物</p>
                      <p className={arcbench.pack_exists ? 'text-[var(--color-success)] truncate' : 'text-[var(--color-text-muted)]'}>
                        {arcbench.pack_artifact ? arcbench.pack_artifact.split('/').pop() : '无'}
                      </p>
                    </div>
                    <div className="rounded-xl bg-[var(--color-bg-surface-2)] border border-[var(--color-border-subtle)] px-3 py-2">
                      <p className="text-[var(--color-text-muted)] mb-1">Trace 目录</p>
                      <p className={arcbench.trace_exists ? 'text-[var(--color-success)]' : 'text-[var(--color-text-muted)]'}>
                        {arcbench.trace_exists ? '存在' : '缺失'}
                      </p>
                    </div>
                    <div className="rounded-xl bg-[var(--color-bg-surface-2)] border border-[var(--color-border-subtle)] px-3 py-2">
                      <p className="text-[var(--color-text-muted)] mb-1">输出目录</p>
                      <p className="text-[var(--color-text-primary)] truncate">{arcbench.output_dir || '—'}</p>
                    </div>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        )}

        <Card variant="default" className="mb-6">
          <CardContent className="p-6">
            <div className="mb-5 space-y-3 text-sm text-[var(--color-text-secondary)]">
              <label htmlFor="factory-config" className="block font-medium">模型配置来源</label>
              <select id="factory-config" value={configChoice} onChange={e => setConfigChoice(e.target.value)} disabled={isRunning}
                className="w-full rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-2)] p-3">
                <option value="auto">自动选择当前 owner 最近配置完整的 Agent</option>
                {agents.map(agent => <option key={agent.id} value={agent.id}>{agent.name} · {agent.provider} / {agent.model_id}</option>)}
                <option value="provider">使用已保存的供应商凭据并指定模型</option>
              </select>
              {configChoice === 'provider' && (
                <div className="grid gap-3 sm:grid-cols-2">
                  <label>供应商
                    <select aria-label="供应商" value={provider} onChange={e => { setProvider(e.target.value); setModel(''); }} disabled={isRunning}
                      className="mt-1 w-full rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-2)] p-3">
                      <option value="">请选择已保存凭据的供应商</option>
                      {providers.map(value => <option key={value} value={value}>{value}</option>)}
                    </select>
                  </label>
                  <label>模型 ID
                    <input aria-label="模型 ID" value={model} onChange={e => setModel(e.target.value)} disabled={isRunning}
                      placeholder="填写该供应商账户可用的模型 ID"
                      className="mt-1 w-full rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-2)] p-3" />
                  </label>
                </div>
              )}
              <p>在 API Keys 保存并启用模型供应商凭据；在 Agent 配置中保存对应供应商和模型，或在此指定模型 ID。凭据按当前 owner 匹配。</p>
              <p>配置记录与连接验证分别展示。服务可达、凭据有效、模型可用均待实际调用验证；Ollama 免 Key 仍需服务运行并已安装所选模型。</p>
              <div className="flex flex-wrap items-center gap-4">
                <a href="#apikeys" className="text-[var(--color-accent)] underline">配置模型 API Keys</a>
                <a href="#agents" className="text-[var(--color-accent)] underline">配置 Agent 模型</a>
                <Button variant="ghost" size="sm" onClick={loadConfiguration} disabled={isRunning || configLoading}>刷新配置</Button>
              </div>
              {configLoading && <p role="status">正在读取配置记录...</p>}
              {configError && <p role="alert">配置读取失败：{configError}</p>}
              {!configLoading && !configError && <p>已读取 {agents.length} 个启用 Agent、{providers.length} 个供应商凭据配置；运行时由后端校验 owner 和配置完整性。</p>}
              {resolvedModel && <p>本次后端选择：{resolvedModel}</p>}
            </div>
            <label className="block text-sm font-medium text-[var(--color-text-secondary)] mb-2">目标</label>
            <textarea
              value={goal}
              onChange={(e) => setGoal(e.target.value)}
              placeholder="描述你想要智能体完成的目标..."
              rows={3}
              className="w-full bg-[var(--color-bg-surface-2)] border border-[var(--color-border-subtle)] rounded-xl px-4 py-3 text-sm text-[var(--color-text-primary)] placeholder:text-[var(--color-text-muted)] focus:outline-none focus:border-[var(--color-accent)]/50 resize-none transition-all duration-200"
            />

            <div className="mt-5">
              <label className="block text-sm font-medium text-[var(--color-text-secondary)] mb-2">技能</label>
              <div className="flex flex-wrap gap-2">
                {SKILLS.map(s => (
                  <button
                    key={s.id}
                    onClick={() => toggleSkill(s.id)}
                    disabled={isRunning}
                    className={`px-4 py-2 rounded-xl text-xs font-medium border transition-all duration-200 ${
                      selectedSkills.includes(s.id)
                        ? 'bg-[var(--color-accent)]/15 border-[var(--color-accent)]/30 text-[var(--color-text-primary)]'
                        : 'bg-[var(--color-bg-surface-2)] border-[var(--color-border-subtle)] text-[var(--color-text-muted)] hover:border-[var(--color-accent)]/30'
                    } disabled:opacity-50`}
                  >
                    {s.icon} {s.name}
                  </button>
                ))}
              </div>
            </div>

            <div className="mt-5">
              <label className="block text-sm font-medium text-[var(--color-text-secondary)] mb-2">专家角色</label>
              <select
                value={selectedPrompt}
                onChange={(e) => setSelectedPrompt(e.target.value)}
                disabled={isRunning}
                className="px-4 py-2.5 bg-[var(--color-bg-surface-2)] border border-[var(--color-border-subtle)] rounded-xl text-sm text-[var(--color-text-primary)] focus:outline-none focus:border-[var(--color-accent)]/50 transition-all duration-200 disabled:opacity-50"
              >
                {PROMPTS.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
              </select>
            </div>

            <div className="mt-6 flex items-center gap-3">
              {!isRunning ? (
                <Button
                  variant="primary"
                  icon={<Play size={16} />}
                  onClick={startExecution}
                  disabled={!goal.trim() || (configChoice === 'provider' && (!provider || !model.trim()))}
                >
                  开始执行
                </Button>
              ) : (
                <Button
                  variant="destructive"
                  icon={<Square size={16} />}
                  onClick={stopExecution}
                  disabled={phase === 'cancelling'}
                >
                  停止
                </Button>
              )}
              {isRunning && (
                <span className="flex items-center gap-1.5 text-xs text-[var(--color-text-muted)] tabular-nums">
                  <Clock size={14} /> 已运行 {formatDuration(elapsedSeconds)}
                </span>
              )}
              <span role="status" className="text-xs text-[var(--color-text-secondary)]">
                {({ idle: '尚未运行', planning: '规划中', running: '执行中', synthesizing: '综合中', done: '已完成', failed: '执行失败', cancelling: '正在请求取消', cancelled: '已取消', interrupted: '执行状态待确认' })[phase]}
              </span>
            </div>
          </CardContent>
        </Card>

        {plan.length === 0 && tasks.length === 0 && !finalReport && !isRunning && recentRuns.length === 0 && (
          <EmptyState
            icon="file"
            title="等待执行"
            description="设置目标并点击「开始执行」"
          />
        )}

        {errorMessage && (
          <div role="alert" className="mb-6 rounded-xl border border-[var(--color-error)]/30 bg-[var(--color-error-subtle)] px-4 py-3 text-sm text-[var(--color-error)]">
            {errorMessage}
          </div>
        )}

        {plan.length > 0 && (
          <Card variant="default" className="mb-6">
            <CardContent className="p-6">
              <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
                <h3 className="font-semibold text-sm text-[var(--color-text-primary)] flex items-center gap-2">
                  <Wrench size={16} className="text-[var(--color-accent)]" /> 执行计划
                  <span className="text-xs font-normal text-[var(--color-text-muted)] tabular-nums">
                    {doneSteps}/{plan.length} 步完成
                  </span>
                </h3>
                {isRunning && (
                  <span className="flex items-center gap-1.5 text-xs text-[var(--color-text-muted)] tabular-nums">
                    <Clock size={14} /> {formatDuration(elapsedSeconds)}
                  </span>
                )}
              </div>

              <Progress value={planProgress} max={100} size="sm" color={phase === 'failed' ? 'danger' : 'primary'} className="mb-4" />

              <div className="flex items-center gap-2 mb-5">
                {STAGES.map((stage, index) => {
                  const Icon = stage.icon;
                  const isActive = index === activeStageIndex;
                  const isDone = index < activeStageIndex || (phase === 'done' && index < STAGES.length);
                  return (
                    <div key={stage.key} className="flex items-center gap-2">
                      <Badge
                        variant={isActive ? 'primary' : isDone ? 'success' : 'default'}
                        size="sm"
                        icon={<Icon size={11} />}
                      >
                        {stage.label}
                      </Badge>
                      {index < STAGES.length - 1 && <span className="text-[var(--color-text-muted)]">→</span>}
                    </div>
                  );
                })}
              </div>

              {fellBackToAutoPlan && (
                <div className="mb-4 rounded-xl border border-[var(--color-warning)]/30 bg-[var(--color-warning-subtle)] px-4 py-2.5 text-xs text-[var(--color-warning)]">
                  已回退到自动计划
                </div>
              )}

              <div className="space-y-3">
                {plan.map(step => (
                  <div key={step.step} className="flex items-center gap-3">
                    <span className="w-6 h-6 rounded-full bg-[var(--color-accent)]/10 text-[var(--color-accent)] flex items-center justify-center text-xs font-bold shrink-0 border border-[var(--color-accent)]/20">
                      {step.step}
                    </span>
                    <span className={`text-sm flex-1 ${step.status === 'done' ? 'text-[var(--color-text-muted)] line-through' : 'text-[var(--color-text-primary)]'}`}>
                      {step.action}
                    </span>
                    {step.tool && (
                      <Badge variant="default" size="xs">{step.tool}</Badge>
                    )}
                    {step.status === 'running' && <Loader2 size={14} className="text-[var(--color-accent)] animate-spin shrink-0" />}
                    {step.status === 'done' && <CheckCircle size={14} className="text-[var(--color-success)] shrink-0" />}
                    {step.status === 'error' && <AlertCircle size={14} className="text-[var(--color-error)] shrink-0" />}
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}

        {progressLines.length > 0 && (
          <Card variant="default" className="mb-6">
            <CardContent className="p-6">
              <h3 className="font-semibold text-sm text-[var(--color-text-primary)] mb-3 flex items-center gap-2">
                <Loader2 size={14} className="text-[var(--color-accent)] animate-spin" /> 实时进度
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
          <Card variant="default" className="mb-6">
            <CardContent className="p-6">
              <h3 className="font-semibold text-sm text-[var(--color-text-primary)] mb-4">子任务执行</h3>
              <div className="space-y-3 stagger-children">
                {tasks.map(task => (
                  <div key={task.id} className="flex items-start gap-3 p-4 bg-[var(--color-bg-surface-2)] rounded-xl border border-[var(--color-border-subtle)]">
                    <div className="shrink-0 mt-0.5">{getStatusIcon(task.status)}</div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm text-[var(--color-text-primary)]">{task.description}</p>
                      {task.result && (
                        <p className="text-xs text-[var(--color-text-muted)] mt-1 line-clamp-2">{task.result}</p>
                      )}
                      {task.retries !== undefined && task.retries > 0 && (
                        <p className="text-xs text-amber-400 mt-1">
                          重试 #{task.retries}{task.retryError ? `: ${task.retryError}` : ''}
                        </p>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}

        {recentRuns.length > 0 && (
          <Card variant="default" className="mb-6">
            <CardContent className="p-6">
              <h3 className="font-semibold text-sm text-[var(--color-text-primary)] mb-4">最近运行</h3>
              <div className="space-y-2">
                {recentRuns.map(run => (
                  <div key={run.task_id} className="flex items-center gap-3 p-3 bg-[var(--color-bg-surface-2)] rounded-xl border border-[var(--color-border-subtle)]">
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
          <Card variant="default" className="border-[var(--color-accent)]/30">
            <CardContent className="p-6">
              <h3 className="font-semibold text-sm text-[var(--color-text-primary)] mb-4 flex items-center gap-2">
                <CheckCircle size={16} className="text-[var(--color-success)]" /> 最终报告
              </h3>
              <div className="text-sm text-[var(--color-text-secondary)] whitespace-pre-wrap leading-relaxed">
                {finalReport}
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
