import { useState, useEffect, useRef, useCallback } from 'react';
import { Play, Square, CheckCircle2, XCircle, Loader2, Clock, Terminal, Globe, FileText, ChevronDown } from 'lucide-react';
import { api } from '../../api';
import type { TaskSummary } from '../../types/api';

interface TaskStep {
  id: string;
  type: 'command' | 'browser' | 'file' | 'reasoning' | 'question';
  description: string;
  status: string;
  output: string;
  error: string;
  duration: number | null;
  tool_call: any;
}

type Task = TaskSummary & {
  title?: string;
  steps?: TaskStep[];
  current_step_idx?: number;
  result?: string;
  error?: string;
  duration?: number | null;
};

const STEP_ICONS: Record<string, typeof Terminal> = {
  command: Terminal,
  browser: Globe,
  file: FileText,
  reasoning: Clock,
  question: Clock,
};

const STATUS_LABELS: Record<string, string> = {
  completed: '已完成',
  running: '运行中',
  failed: '失败',
  cancelled: '已取消',
  waiting_approval: '等待审批',
  pending: '排队中',
};

export function MobileTasksPage() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [newTask, setNewTask] = useState('');
  const [loading, setLoading] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  const fetchTasks = useCallback(async () => {
    try {
      const data = await api.listTasks();
      setTasks(data);
    } catch { /* skip */ }
  }, []);

  useEffect(() => {
    fetchTasks();
  }, [fetchTasks]);

  useEffect(() => {
    if (!expandedId) return;

    const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const ws = new WebSocket(
      `${proto}//${window.location.host}/api/v1/ws/task/${expandedId}`
    );
    wsRef.current = ws;

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        fetchTasks();

        if (msg.type === 'task_state') {
          setTasks(prev => {
            const idx = prev.findIndex(t => t.id === msg.task.id);
            if (idx >= 0) {
              const updated = [...prev];
              updated[idx] = msg.task;
              return updated;
            }
            return [msg.task, ...prev];
          });
        }
      } catch { /* skip */ }
    };

    ws.onerror = () => { /* skip */ };

    return () => {
      ws.close();
      wsRef.current = null;
    };
  }, [expandedId, fetchTasks]);

  const createTask = async () => {
    if (!newTask.trim()) return;
    setLoading(true);
    try {
      const data = await api.createTask({
        description: newTask,
        provider: 'openai',
        model_id: 'gpt-4o',
        api_key: '',
      });
      setNewTask('');
      fetchTasks();
      setExpandedId(data.task_id);
    } catch { /* skip */ }
    setLoading(false);
  };

  const cancelTask = async (taskId: string) => {
    try {
      await api.cancelTask(taskId);
      fetchTasks();
    } catch { /* skip */ }
  };

  const expandedTask = tasks.find(t => t.id === expandedId);

  const statusColor = (status: string) => {
    switch (status) {
      case 'completed': return 'text-[var(--color-success)]';
      case 'failed': case 'cancelled': return 'text-[var(--color-error)]';
      case 'running': case 'waiting_approval': return 'text-[var(--color-accent)]';
      default: return 'text-[var(--color-text-muted)]';
    }
  };

  const stepStatusIcon = (status: string) => {
    switch (status) {
      case 'completed': return <CheckCircle2 size={14} className="text-[var(--color-success)] shrink-0" />;
      case 'failed': return <XCircle size={14} className="text-[var(--color-error)] shrink-0" />;
      case 'running': return <Loader2 size={14} className="text-[var(--color-accent)] animate-spin shrink-0" />;
      default: return <Clock size={14} className="text-[var(--color-text-muted)] shrink-0" />;
    }
  };

  return (
    <div className="mobile-page-container">
      <div className="px-4 py-4">
        <div className="mb-4">
          <h2 className="text-lg font-bold" style={{ color: 'var(--color-text-primary)' }}>
            任务监控
          </h2>
          <p className="text-xs mt-1" style={{ color: 'var(--color-text-muted)' }}>
            查看和管理你的自主执行任务
          </p>
        </div>

        <div className="flex gap-2 mb-4">
          <input
            type="text"
            value={newTask}
            onChange={e => setNewTask(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && createTask()}
            placeholder="描述一个任务..."
            className="flex-1 px-3 py-2.5 bg-[var(--color-bg-surface-2)] border border-[var(--color-border-subtle)] rounded-2xl text-xs text-[var(--color-text-primary)] placeholder:text-[var(--color-text-muted)] focus:outline-none focus:border-[var(--color-accent)]/50 transition-all duration-200"
          />
          <button
            onClick={createTask}
            disabled={loading || !newTask.trim()}
            className="shrink-0 min-w-[44px] px-3 py-2.5 bg-[var(--color-accent)] hover:bg-[var(--color-accent-hover)] disabled:bg-[var(--color-bg-surface-2)] disabled:text-[var(--color-text-muted)] text-white rounded-2xl transition-all duration-200 active:scale-[0.97]"
          >
            {loading ? <Loader2 size={14} className="animate-spin" /> : <Play size={14} />}
          </button>
        </div>

        {tasks.length === 0 && (
          <div className="p-8 text-center text-[var(--color-text-muted)] text-xs">
            暂无任务。在上方描述一个任务。
          </div>
        )}

        <div className="space-y-3">
          {tasks.map(task => (
            <div
              key={task.id}
              className="bg-[var(--color-bg-surface-1)] border border-[var(--color-border-subtle)] rounded-2xl overflow-hidden"
            >
              <button
                onClick={() => setExpandedId(expandedId === task.id ? null : task.id)}
                className="w-full text-left px-4 py-3.5 transition-all duration-200 active:bg-[var(--color-bg-surface-2)]"
              >
                <div className="flex items-center justify-between gap-3">
                  <span className="text-xs font-semibold text-[var(--color-text-primary)] truncate">
                    {task.title || task.description || task.id.slice(0, 8)}
                  </span>
                  <span className={`text-[10px] font-medium shrink-0 ${statusColor(task.status)}`}>
                    {STATUS_LABELS[task.status] || task.status}
                  </span>
                </div>
                {task.status === 'running' && (
                  <div className="mt-2 w-full h-1 bg-[var(--color-bg-surface-3)] rounded-full overflow-hidden">
                    <div
                      className="h-full bg-[var(--color-accent)] rounded-full transition-all"
                      style={{ width: `${task.max_rounds && task.current_round != null ? Math.min(100, (task.current_round / task.max_rounds) * 100) : 20}%` }}
                    />
                  </div>
                )}
                {task.status !== 'running' && (task.steps?.length ?? 0) > 0 && (
                  <div className="mt-1.5 text-[10px] text-[var(--color-text-muted)]">
                    {task.steps?.length} 步
                    {task.duration != null && ` · ${task.duration}s`}
                  </div>
                )}
              </button>

              {expandedId === task.id && expandedTask && (
                <div className="border-t border-[var(--color-border-subtle)] px-4 pb-4 pt-3 space-y-2.5">
                  {task.status === 'running' && (
                    <button
                      onClick={() => cancelTask(task.id)}
                      className="flex items-center justify-center gap-1.5 w-full py-2.5 bg-[var(--color-error)]/10 text-[var(--color-error)] border border-[var(--color-error)]/20 rounded-2xl text-xs font-semibold active:bg-[var(--color-error)]/20 transition-all duration-200"
                    >
                      <Square size={12} /> 取消任务
                    </button>
                  )}

                  {(expandedTask.steps ?? []).map((step, idx) => {
                    const Icon = STEP_ICONS[step.type] || Terminal;
                    return (
                      <div key={step.id} className="bg-[var(--color-bg-surface-2)] border border-[var(--color-border-subtle)] rounded-xl overflow-hidden">
                        <div className="flex items-center gap-3 px-3 py-2.5">
                          <div className="p-1.5 rounded-lg bg-[var(--color-bg-surface-2)] border border-[var(--color-border-subtle)] text-[var(--color-text-muted)]">
                            <Icon size={13} />
                          </div>
                          <div className="flex-1 min-w-0">
                            <span className="text-[10px] text-[var(--color-text-muted)] font-mono font-medium mr-1.5">#{idx + 1}</span>
                            <span className="text-[11px] text-[var(--color-text-primary)] leading-snug">{step.description}</span>
                          </div>
                          {stepStatusIcon(step.status)}
                        </div>
                        {(step.output || step.error) && (
                          <pre className="text-[10px] text-[var(--color-text-muted)] bg-black/20 border-t border-[var(--color-border-subtle)] p-3 max-h-36 overflow-auto font-mono whitespace-pre-wrap break-all">
                            {step.error || step.output}
                          </pre>
                        )}
                      </div>
                    );
                  })}

                  {expandedTask.result && (
                    <div className="bg-[var(--color-success)]/10 border border-[var(--color-success)]/30 rounded-xl p-3">
                      <div className="flex items-center gap-1.5 mb-1">
                        <CheckCircle2 size={13} className="text-[var(--color-success)]" />
                        <span className="text-[11px] font-semibold text-[var(--color-success)]">任务完成</span>
                      </div>
                      <p className="text-[11px] text-[var(--color-text-secondary)]">{expandedTask.result}</p>
                    </div>
                  )}

                  {expandedTask.error && (
                    <div className="bg-[var(--color-error)]/10 border border-[var(--color-error)]/30 rounded-xl p-3">
                      <div className="flex items-center gap-1.5 mb-1">
                        <XCircle size={13} className="text-[var(--color-error)]" />
                        <span className="text-[11px] font-semibold text-[var(--color-error)]">任务失败</span>
                      </div>
                      <p className="text-[11px] text-[var(--color-text-secondary)]">{expandedTask.error}</p>
                    </div>
                  )}

                  <div className="flex items-center justify-center gap-1 text-[10px] text-[var(--color-text-muted)]">
                    <ChevronDown size={12} />
                    点击收起
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
