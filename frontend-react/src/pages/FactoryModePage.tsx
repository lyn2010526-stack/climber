import { useState, useRef } from 'react';
import { Play, Square, Brain, Wrench, CheckCircle, AlertCircle, Loader2 } from 'lucide-react';

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
  const [selectedSkills, setSelectedSkills] = useState<string[]>(['code_executor', 'web_search']);
  const [selectedPrompt, setSelectedPrompt] = useState('senior-engineer');
  const abortRef = useRef(false);

  const skills = [
    { id: 'code_executor', name: 'Code Executor', icon: '⚙️' },
    { id: 'web_search', name: 'Web Search', icon: '🔍' },
    { id: 'file_manager', name: 'File Manager', icon: '📁' },
    { id: 'data_analyzer', name: 'Data Analyzer', icon: '📊' },
    { id: 'task_planner', name: 'Task Planner', icon: '📋' },
    { id: 'code_reviewer', name: 'Code Reviewer', icon: '🛡️' },
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
    abortRef.current = false;
    setIsRunning(true);
    setFinalReport('');
    setTasks([]);
    setPlan([]);

    try {
      const res = await fetch('/api/v1/skills/autonomous/run', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
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
          } catch (e) { /* skip */ }
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

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed': return <CheckCircle size={16} className="text-green-400" />;
      case 'failed': return <AlertCircle size={16} className="text-red-400" />;
      case 'running': return <Loader2 size={16} className="text-blue-400 animate-spin" />;
      case 'retrying': return <Loader2 size={16} className="text-amber-400 animate-spin" />;
      default: return <div className="w-4 h-4 rounded-full border border-gray-700" />;
    }
  };

  return (
    <div className="h-full overflow-y-auto p-8">
      <div className="max-w-5xl mx-auto">
        <div className="mb-8">
          <h2 className="text-2xl font-bold text-white flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-2xl bg-blue-500/10 flex items-center justify-center">
              <Brain size={20} className="text-blue-400" />
            </div>
            自主执行模式
          </h2>
          <p className="text-gray-400 text-sm mt-2">
            自主执行：规划、分解、执行、自愈、综合结果
          </p>
        </div>

        {/* Goal input */}
        <div className="bg-white/[0.04] border border-white/[0.08] rounded-3xl p-6 mb-6 backdrop-blur-sm">
          <label className="block text-sm font-medium text-gray-400 mb-2">目标</label>
          <textarea
            value={goal}
            onChange={(e) => setGoal(e.target.value)}
              placeholder="描述你想要智能体完成的目标..."
            rows={3}
            className="w-full bg-white/5 border border-white/10 rounded-2xl px-5 py-3 text-sm text-gray-100 placeholder:text-gray-600 focus:outline-none focus:border-[#007AFF]/50 resize-none transition-all duration-200"
          />

          {/* Skills selection */}
          <div className="mt-4">
            <label className="block text-sm font-medium text-gray-400 mb-2">技能</label>
            <div className="flex flex-wrap gap-2">
              {skills.map(s => (
                <button
                  key={s.id}
                  onClick={() => toggleSkill(s.id)}
                  className={`px-4 py-2 rounded-2xl text-sm font-medium border transition-all duration-200 ${
                    selectedSkills.includes(s.id)
                      ? 'bg-[#007AFF]/20 border-[#007AFF]/30 text-white shadow-lg shadow-blue-500/10'
                      : 'bg-white/5 border-white/10 text-gray-400 hover:border-[#007AFF]/30'
                  }`}
                >
                  {s.icon} {s.name}
                </button>
              ))}
            </div>
          </div>

          {/* Prompt template */}
          <div className="mt-4">
            <label className="block text-sm font-medium text-gray-400 mb-2">专家角色</label>
            <select
              value={selectedPrompt}
              onChange={(e) => setSelectedPrompt(e.target.value)}
              className="px-4 py-2.5 bg-white/5 border border-white/10 rounded-2xl text-sm text-gray-200 focus:outline-none focus:border-[#007AFF]/50 transition-all duration-200"
            >
              {prompts.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
            </select>
          </div>

          {/* Start/Stop */}
          <div className="mt-6 flex gap-3">
            {!isRunning ? (
              <button
                onClick={startExecution}
                disabled={!goal.trim()}
                className="flex items-center gap-2 px-6 py-2.5 bg-[#007AFF] hover:bg-[#007AFF]/90 text-white rounded-2xl text-sm font-semibold disabled:opacity-40 transition-all duration-200 active:scale-[0.97] shadow-lg shadow-blue-500/20"
              >
                 <Play size={16} /> 开始执行
              </button>
            ) : (
              <button
                onClick={stopExecution}
                className="flex items-center gap-2 px-6 py-2.5 bg-red-500/90 hover:bg-red-500 text-white rounded-2xl text-sm font-semibold transition-all duration-200 active:scale-[0.97] shadow-lg shadow-red-500/20"
              >
                 <Square size={16} /> 停止
              </button>
            )}
          </div>
        </div>

        {/* Plan */}
        {plan.length > 0 && (
          <div className="bg-white/[0.04] border border-white/[0.08] rounded-3xl p-6 mb-6 backdrop-blur-sm">
             <h3 className="font-semibold text-gray-200 mb-4 flex items-center gap-2">
               <Wrench size={16} className="text-blue-400" /> 执行计划
             </h3>
            <div className="space-y-2.5">
              {plan.map(step => (
                <div key={step.step} className="flex items-center gap-3 text-sm">
                  <span className="w-6 h-6 rounded-full bg-blue-500/10 text-blue-400 flex items-center justify-center text-xs font-bold">
                    {step.step}
                  </span>
                  <span className={step.status === 'done' ? 'text-gray-500 line-through' : 'text-gray-200'}>
                    {step.action}
                  </span>
                  {step.tool && (
                    <span className="px-2.5 py-0.5 bg-white/5 text-gray-500 rounded-xl text-xs font-medium border border-white/10">{step.tool}</span>
                  )}
                  {step.status === 'running' && <Loader2 size={14} className="text-blue-400 animate-spin" />}
                  {step.status === 'done' && <CheckCircle size={14} className="text-green-400" />}
                  {step.status === 'error' && <AlertCircle size={14} className="text-red-400" />}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Tasks */}
        {tasks.length > 0 && (
          <div className="bg-white/[0.04] border border-white/[0.08] rounded-3xl p-6 mb-6 backdrop-blur-sm">
             <h3 className="font-semibold text-gray-200 mb-4">子任务执行</h3>
            <div className="space-y-3">
              {tasks.map(task => (
                <div key={task.id} className="flex items-start gap-3 p-4 bg-white/5 rounded-2xl border border-white/10">
                  {getStatusIcon(task.status)}
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-gray-200">{task.description}</p>
                    {task.result && (
                      <p className="text-xs text-gray-500 mt-1 line-clamp-2">{task.result}</p>
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

        {/* Final Report */}
        {finalReport && (
          <div className="bg-white/[0.04] border border-[#007AFF]/30 rounded-3xl p-6 backdrop-blur-sm">
             <h3 className="font-semibold text-gray-200 mb-4 flex items-center gap-2">
               <CheckCircle size={16} className="text-green-400" /> 最终报告
             </h3>
            <div className="text-sm text-gray-300 whitespace-pre-wrap leading-relaxed">
              {finalReport}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
