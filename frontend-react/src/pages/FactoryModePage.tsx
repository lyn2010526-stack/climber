import { useState, useRef } from 'react';
import { Play, Square, Brain, Wrench, CheckCircle, AlertCircle, Loader2 } from 'lucide-react';
import { PageHeader } from '../components/ui/PageHeader';
import { Card, CardContent } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Badge } from '../components/ui/Badge';
import { EmptyState } from '../components/ui/EmptyState';

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

function getStatusIcon(status: string) {
  switch (status) {
    case 'completed': return <CheckCircle size={16} className="text-[var(--color-success)]" />;
    case 'failed': return <AlertCircle size={16} className="text-[var(--color-error)]" />;
    case 'running': return <Loader2 size={16} className="text-[var(--color-accent)] animate-spin" />;
    case 'retrying': return <Loader2 size={16} className="text-amber-400 animate-spin" />;
    default: return <div className="w-4 h-4 rounded-full border border-[var(--color-border-subtle)]" />;
  }
}

export function FactoryModePage() {
  const [goal, setGoal] = useState('');
  const [isRunning, setIsRunning] = useState(false);
  const [plan, setPlan] = useState<PlanStep[]>([]);
  const [tasks, setTasks] = useState<SubTask[]>([]);
  const [finalReport, setFinalReport] = useState('');
  const [selectedSkills, setSelectedSkills] = useState<string[]>(['code_executor', 'web_search']);
  const [selectedPrompt, setSelectedPrompt] = useState('senior-engineer');
  const abortRef = useRef(false);

  const toggleSkill = (id: string) => {
    setSelectedSkills(prev => prev.includes(id) ? prev.filter(s => s !== id) : [...prev, id]);
  };

  const startExecution = async () => {
    if (!goal.trim()) return;
    abortRef.current = false;
    setIsRunning(true);
    setFinalReport('');
    setTasks([]);
    setPlan([]);

    try {
      const res = await fetch('/api/v1/skills/autonomous/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          goal,
          skills: selectedSkills,
          prompt_template: selectedPrompt,
        }),
      });

      if (!res.ok) throw new Error('启动失败');

      const reader = res.body?.getReader();
      if (!reader) throw new Error('无数据流');

      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done || abortRef.current) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue;
          const data = line.slice(6);
          if (data === '[DONE]') break;

          try {
            const event = JSON.parse(data);
            handleEvent(event);
          } catch { /* skip */ }
        }
      }
    } catch (e) {
      console.error('Execution error:', e);
    } finally {
      setIsRunning(false);
    }
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
    abortRef.current = true;
    setIsRunning(false);
  };

  return (
    <div className="h-full overflow-y-auto page-transition">
      <div className="p-4 md:p-6 lg:p-8 max-w-5xl mx-auto">
        <PageHeader
          title="自主执行模式"
          description="规划、分解、执行、自愈、综合结果"
          icon={<Brain size={20} />}
        />

        <Card variant="default" className="mb-6">
          <CardContent className="p-6">
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
                    className={`px-4 py-2 rounded-xl text-xs font-medium border transition-all duration-200 ${
                      selectedSkills.includes(s.id)
                        ? 'bg-[var(--color-accent)]/15 border-[var(--color-accent)]/30 text-[var(--color-text-primary)]'
                        : 'bg-[var(--color-bg-surface-2)] border-[var(--color-border-subtle)] text-[var(--color-text-muted)] hover:border-[var(--color-accent)]/30'
                    }`}
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
                className="px-4 py-2.5 bg-[var(--color-bg-surface-2)] border border-[var(--color-border-subtle)] rounded-xl text-sm text-[var(--color-text-primary)] focus:outline-none focus:border-[var(--color-accent)]/50 transition-all duration-200"
              >
                {PROMPTS.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
              </select>
            </div>

            <div className="mt-6 flex gap-3">
              {!isRunning ? (
                <Button
                  variant="primary"
                  icon={<Play size={16} />}
                  onClick={startExecution}
                  disabled={!goal.trim()}
                >
                  开始执行
                </Button>
              ) : (
                <Button
                  variant="destructive"
                  icon={<Square size={16} />}
                  onClick={stopExecution}
                >
                  停止
                </Button>
              )}
            </div>
          </CardContent>
        </Card>

        {plan.length === 0 && tasks.length === 0 && !finalReport && (
          <EmptyState
            icon="file"
            title="等待执行"
            description="设置目标并点击「开始执行」"
          />
        )}

        {plan.length > 0 && (
          <Card variant="default" className="mb-6">
            <CardContent className="p-6">
              <h3 className="font-semibold text-sm text-[var(--color-text-primary)] mb-4 flex items-center gap-2">
                <Wrench size={16} className="text-[var(--color-accent)]" /> 执行计划
              </h3>
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
                        <p className="text-xs text-amber-400 mt-1">重试 #{task.retries}</p>
                      )}
                    </div>
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
