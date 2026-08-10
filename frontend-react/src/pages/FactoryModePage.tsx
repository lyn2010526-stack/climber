import { useState, useRef } from 'react';
import { Play, Square, Brain, Wrench, CheckCircle, AlertCircle, Loader2 } from 'lucide-react';
import { api } from '../api';

interface SubTask {
  id: string;
  description: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'retrying';
  result?: string;
  retries?: number;
}

interface PlanStep {
  step: number;
  action: string;
  tool?: string;
  status: 'pending' | 'running' | 'done' | 'error';
}

export function FactoryModePage() {
  const [goal, setGoal] = useState('');
  const [isRunning, setIsRunning] = useState(false);
  const [plan, setPlan] = useState<PlanStep[]>([]);
  const [tasks, setTasks] = useState<SubTask[]>([]);
  const [finalReport, setFinalReport] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [selectedSkills, setSelectedSkills] = useState<string[]>(['code_executor', 'web_search']);
  const [selectedPrompt, setSelectedPrompt] = useState('senior-engineer');
  const abortRef = useRef<(() => void) | null>(null);

  const skills = [
    { id: 'code_executor', name: 'Code Executor', icon: '\u2699\ufe0f' },
    { id: 'web_search', name: 'Web Search', icon: '\ud83d\udd0d' },
    { id: 'file_manager', name: 'File Manager', icon: '\ud83d\udcc1' },
    { id: 'data_analyzer', name: 'Data Analyzer', icon: '\ud83d\udcca' },
    { id: 'task_planner', name: 'Task Planner', icon: '\ud83d\udccb' },
    { id: 'code_reviewer', name: 'Code Reviewer', icon: '\ud83d\udee1\ufe0f' },
  ];

  const prompts = [
    { id: 'senior-engineer', name: 'Senior Engineer' },
    { id: 'code-reviewer', name: 'Code Reviewer' },
    { id: 'architect', name: 'System Architect' },
    { id: 'research-analyst', name: 'Research Analyst' },
    { id: 'data-scientist', name: 'Data Scientist' },
  ];

  const toggleSkill = (id: string) => {
    setSelectedSkills(prev => prev.includes(id) ? prev.filter(s => s !== id) : [...prev, id]);
  };

  const startExecution = async () => {
    if (!goal.trim()) return;
    if (abortRef.current) abortRef.current();
    abortRef.current = null;
    setIsRunning(true);
    setError(null);
    setFinalReport('');
    setTasks([]);
    setPlan([]);

    abortRef.current = api.runAutonomousSkillStream(goal, selectedSkills, selectedPrompt, (event) => {
      if (event.type === 'error') {
        setError(event.data?.detail || '执行失败');
        setIsRunning(false);
        return;
      }
      if (event.type === 'done') {
        setIsRunning(false);
        return;
      }
      handleEvent(event);
    });
  };

  const handleEvent = (event: any) => {
    switch (event.type) {
      case 'plan':
        setPlan(event.data.steps || []);
        break;
      case 'task_start':
        setTasks(prev => [...prev, {
          id: event.data.task_id || String(Date.now()),
          description: event.data.description || '',
          status: 'running',
        }]);
        break;
      case 'task_complete':
        setTasks(prev => prev.map(t =>
          t.id === event.data.task_id ? { ...t, status: 'completed', result: event.data.result } : t
        ));
        break;
      case 'task_retry':
        setTasks(prev => prev.map(t =>
          t.id === event.data.task_id ? { ...t, status: 'retrying', retries: event.data.retries } : t
        ));
        break;
      case 'task_failed':
        setTasks(prev => prev.map(t =>
          t.id === event.data.task_id ? { ...t, status: 'failed' } : t
        ));
        break;
      case 'synthesize':
        setFinalReport(event.data.report || '');
        break;
    }
  };

  const stopExecution = () => {
    if (abortRef.current) {
      abortRef.current();
      abortRef.current = null;
    }
    setIsRunning(false);
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed': return <CheckCircle size={16} className="text-[var(--color-success)]" />;
      case 'failed': return <AlertCircle size={16} className="text-[var(--color-error)]" />;
      case 'running': return <Loader2 size={16} className="text-[var(--color-accent)] animate-spin" />;
      case 'retrying': return <Loader2 size={16} className="text-amber-400 animate-spin" />;
      default: return <div className="w-4 h-4 rounded-full border border-[var(--color-border-subtle)]" />;
    }
  };

  return (
    <div className="h-full overflow-y-auto p-8">
      <div className="max-w-5xl mx-auto">
        <div className="mb-8">
          <h2 className="text-2xl font-bold text-[var(--color-text-primary)] flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-2xl bg-[var(--color-accent)]/10 flex items-center justify-center border border-[var(--color-accent)]/20">
              <Brain size={20} className="text-[var(--color-accent)]" />
            </div>
            自主执行模式
          </h2>
          <p className="text-[var(--color-text-secondary)] text-sm mt-2">
            自主执行：规划、分解、执行、自愈、综合结果
          </p>
        </div>

        <div className="bg-[var(--color-bg-surface-1)] border border-[var(--color-border-subtle)] rounded-3xl p-6 mb-6">
          <label className="block text-sm font-medium text-[var(--color-text-secondary)] mb-2">目标</label>
          <textarea
            value={goal}
            onChange={(e) => setGoal(e.target.value)}
              placeholder="描述你想要智能体完成的目标..."
            rows={3}
            className="w-full bg-[var(--color-bg-surface-2)] border border-[var(--color-border-subtle)] rounded-2xl px-5 py-3 text-sm text-[var(--color-text-primary)] placeholder:text-[var(--color-text-muted)] focus:outline-none focus:border-[var(--color-accent)]/50 resize-none transition-all duration-200"
          />

          <div className="mt-4">
            <label className="block text-sm font-medium text-[var(--color-text-secondary)] mb-2">技能</label>
            <div className="flex flex-wrap gap-2">
              {skills.map(s => (
                <button
                  key={s.id}
                  onClick={() => toggleSkill(s.id)}
                  className={`px-4 py-2 rounded-2xl text-sm font-medium border transition-all duration-200 ${
                    selectedSkills.includes(s.id)
                      ? 'bg-[var(--color-accent)]/15 border-[var(--color-accent)]/30 text-[var(--color-text-primary)]'
                      : 'bg-white/[0.03] border-[var(--color-border-subtle)] text-[var(--color-text-muted)] hover:border-[var(--color-accent)]/30'
                  }`}
                >
                  {s.icon} {s.name}
                </button>
              ))}
            </div>
          </div>

          <div className="mt-4">
            <label className="block text-sm font-medium text-[var(--color-text-secondary)] mb-2">专家角色</label>
            <select
              value={selectedPrompt}
              onChange={(e) => setSelectedPrompt(e.target.value)}
              className="px-4 py-2.5 bg-[var(--color-bg-surface-2)] border border-[var(--color-border-subtle)] rounded-2xl text-sm text-[var(--color-text-primary)] focus:outline-none focus:border-[var(--color-accent)]/50 transition-all duration-200"
            >
              {prompts.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
            </select>
          </div>

          <div className="mt-6 flex gap-3">
            {!isRunning ? (
              <button
                onClick={startExecution}
                disabled={!goal.trim()}
                className="flex items-center gap-2 px-6 py-2.5 bg-[var(--color-accent)] hover:bg-[var(--color-accent-hover)] text-white rounded-2xl text-sm font-semibold disabled:opacity-40 transition-all duration-200 active:scale-[0.97]"
              >
                 <Play size={16} /> 开始执行
              </button>
            ) : (
              <button
                onClick={stopExecution}
                className="flex items-center gap-2 px-6 py-2.5 bg-[var(--color-error)] hover:bg-red-600 text-white rounded-2xl text-sm font-semibold transition-all duration-200 active:scale-[0.97]"
              >
                 <Square size={16} /> 停止
              </button>
            )}
          </div>

          {error && (
            <div className="mt-4 flex items-center gap-2 p-4 bg-red-900/20 border border-[var(--color-error)]/40 rounded-2xl text-sm text-red-300">
              <AlertCircle size={16} className="shrink-0" />
              {error}
            </div>
          )}
        </div>

        {plan.length > 0 && (
          <div className="bg-[var(--color-bg-surface-1)] border border-[var(--color-border-subtle)] rounded-3xl p-6 mb-6">
             <h3 className="font-semibold text-[var(--color-text-primary)] mb-4 flex items-center gap-2">
               <Wrench size={16} className="text-[var(--color-accent)]" /> 执行计划
             </h3>
            <div className="space-y-2.5">
              {plan.map(step => (
                <div key={step.step} className="flex items-center gap-3 text-sm">
                  <span className="w-6 h-6 rounded-full bg-[var(--color-accent)]/10 text-[var(--color-accent)] flex items-center justify-center text-xs font-bold">
                    {step.step}
                  </span>
                  <span className={step.status === 'done' ? 'text-[var(--color-text-muted)] line-through' : 'text-[var(--color-text-primary)]'}>
                    {step.action}
                  </span>
                  {step.tool && (
                    <span className="px-2.5 py-0.5 bg-white/[0.03] text-[var(--color-text-muted)] rounded-xl text-xs font-medium border border-[var(--color-border-subtle)]">{step.tool}</span>
                  )}
                  {step.status === 'running' && <Loader2 size={14} className="text-[var(--color-accent)] animate-spin" />}
                  {step.status === 'done' && <CheckCircle size={14} className="text-[var(--color-success)]" />}
                  {step.status === 'error' && <AlertCircle size={14} className="text-[var(--color-error)]" />}
                </div>
              ))}
            </div>
          </div>
        )}

        {tasks.length > 0 && (
          <div className="bg-[var(--color-bg-surface-1)] border border-[var(--color-border-subtle)] rounded-3xl p-6 mb-6">
             <h3 className="font-semibold text-[var(--color-text-primary)] mb-4">子任务执行</h3>
            <div className="space-y-3">
              {tasks.map(task => (
                <div key={task.id} className="flex items-start gap-3 p-4 bg-white/[0.03] rounded-2xl border border-[var(--color-border-subtle)]">
                  {getStatusIcon(task.status)}
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-[var(--color-text-primary)]">{task.description}</p>
                    {task.result && (
                      <p className="text-xs text-[var(--color-text-muted)] mt-1 line-clamp-2">{task.result}</p>
                    )}
                    {task.retries !== undefined && task.retries > 0 && (
                      <p className="text-xs text-amber-400 mt-1">重试 #{task.retries}</p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {finalReport && (
          <div className="bg-[var(--color-bg-surface-1)] border border-[var(--color-accent)]/30 rounded-3xl p-6">
             <h3 className="font-semibold text-[var(--color-text-primary)] mb-4 flex items-center gap-2">
               <CheckCircle size={16} className="text-[var(--color-success)]" /> 最终报告
             </h3>
            <div className="text-sm text-[var(--color-text-secondary)] whitespace-pre-wrap leading-relaxed">
              {finalReport}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
