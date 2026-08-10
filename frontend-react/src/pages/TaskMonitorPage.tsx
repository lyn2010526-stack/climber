import { useState, useEffect, useRef, useCallback } from 'react';
import { Play, Square, CheckCircle2, XCircle, Loader2, Clock, Terminal, Globe, FileText } from 'lucide-react';
import { api } from '../api';

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

interface Task {
  id: string;
  title: string;
  description: string;
  status: string;
  steps: TaskStep[];
  current_step_idx: number;
  result: string;
  error: string;
  total_tool_calls: number;
  duration: number | null;
}

const STEP_ICONS: Record<string, typeof Terminal> = {
  command: Terminal,
  browser: Globe,
  file: FileText,
  reasoning: Clock,
  question: Clock,
};

export default function TaskMonitorPage() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null);
  const [newTask, setNewTask] = useState('');
  const [loading, setLoading] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  // Fetch existing tasks
  const fetchTasks = useCallback(async () => {
    try {
      const data = await api.listTasks();
      setTasks(data as unknown as Task[]);
      if (data.length > 0 && !selectedTaskId) {
        setSelectedTaskId(data[0]?.id ?? null);
      }
    } catch { /* skip */ }
  }, []);

  useEffect(() => {
    fetchTasks();
  }, [fetchTasks]);

  // WebSocket for selected task
  useEffect(() => {
    if (!selectedTaskId) return;

    const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const ws = new WebSocket(
      `${proto}//${window.location.host}/api/v1/ws/task/${selectedTaskId}`
    );
    wsRef.current = ws;

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        // Refresh task list on any event
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
  }, [selectedTaskId, fetchTasks]);

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
      setSelectedTaskId(data.task_id);
    } catch { /* skip */ }
    setLoading(false);
  };

  const cancelTask = async (taskId: string) => {
    try {
      await api.cancelTask(taskId);
      fetchTasks();
    } catch { /* skip */ }
  };

  const selectedTask = tasks.find(t => t.id === selectedTaskId);

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
      case 'completed': return <CheckCircle2 size={14} className="text-[var(--color-success)]" />;
      case 'failed': return <XCircle size={14} className="text-[var(--color-error)]" />;
      case 'running': return <Loader2 size={14} className="text-[var(--color-accent)] animate-spin" />;
      default: return <Clock size={14} className="text-[var(--color-text-muted)]" />;
    }
  };

  return (
    <div className="h-full flex">
      {/* Task List */}
      <div className="w-72 border-r border-[var(--color-border-subtle)] flex flex-col">
        <div className="p-4 border-b border-[var(--color-border-subtle)]">
          <h2 className="text-sm font-semibold text-[var(--color-text-primary)] mb-3">自主任务</h2>
          <div className="flex gap-2">
            <input
              type="text"
              value={newTask}
              onChange={e => setNewTask(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && createTask()}
               placeholder="描述一个任务..."
              className="flex-1 px-3 py-2 bg-[var(--color-bg-surface-2)] border border-[var(--color-border-subtle)] rounded-2xl text-xs text-[var(--color-text-primary)] placeholder:text-[var(--color-text-muted)] focus:outline-none focus:border-[var(--color-accent)]/50 transition-all duration-200"
            />
            <button
              onClick={createTask}
              disabled={loading || !newTask.trim()}
              className="px-3 py-2 bg-[var(--color-accent)] hover:bg-[var(--color-accent-hover)] disabled:bg-white/[0.03] disabled:text-[var(--color-text-muted)] text-white rounded-2xl transition-all duration-200 active:scale-[0.97]"
            >
              {loading ? <Loader2 size={14} className="animate-spin" /> : <Play size={14} />}
            </button>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto">
          {tasks.length === 0 && (
            <div className="p-4 text-center text-[var(--color-text-muted)] text-xs">
               暂无任务。在上方描述一个任务。
            </div>
          )}
          {tasks.map(task => (
            <button
              key={task.id}
              onClick={() => setSelectedTaskId(task.id)}
              className={`w-full text-left px-4 py-3 border-b border-[var(--color-border-subtle)] transition-all duration-200 border-l-2 ${
                selectedTaskId === task.id ? 'bg-white/[0.06] border-l-[var(--color-accent)]' : 'hover:bg-white/[0.03] border-l-transparent'
              }`}
            >
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-[var(--color-text-primary)] truncate">{task.title}</span>
                <span className={`text-[10px] font-medium ${statusColor(task.status)}`}>
                  {task.status}
                </span>
              </div>
              {task.status === 'running' && (
                <div className="mt-1.5 w-full h-1 bg-white/[0.06] rounded-full overflow-hidden">
                  <div
                    className="h-full bg-[var(--color-accent)] rounded-full transition-all"
                    style={{ width: `${((task.current_step_idx + 1) / Math.max(task.steps.length, 1)) * 100}%` }}
                  />
                </div>
              )}
            </button>
          ))}
        </div>
      </div>

      {/* Task Detail */}
      <div className="flex-1 flex flex-col">
        {selectedTask ? (
          <>
            {/* Header */}
            <div className="p-4 border-b border-[var(--color-border-subtle)] flex items-center justify-between">
              <div>
                <h3 className="text-sm font-semibold text-[var(--color-text-primary)]">{selectedTask.title}</h3>
                <p className="text-xs text-[var(--color-text-muted)] mt-0.5">
                  {selectedTask.steps.length} steps &middot; {selectedToolCalls(selectedTask)} tool calls
                  {selectedTask.duration && ` · ${selectedTask.duration}s`}
                </p>
              </div>
              {selectedTask.status === 'running' && (
                <button
                  onClick={() => cancelTask(selectedTask.id)}
                  className="flex items-center gap-1.5 px-4 py-2 bg-[var(--color-error)]/10 text-[var(--color-error)] border border-[var(--color-error)]/20 rounded-2xl text-xs font-semibold hover:bg-[var(--color-error)]/20 transition-all duration-200"
                >
                   <Square size={12} /> 取消
                </button>
              )}
            </div>

            {/* Steps */}
            <div className="flex-1 overflow-y-auto p-4 space-y-3">
              {selectedTask.steps.map((step, idx) => {
                const Icon = STEP_ICONS[step.type] || Terminal;
                return (
                  <div key={step.id} className="bg-[var(--color-bg-surface-1)] border border-[var(--color-border-subtle)] rounded-2xl overflow-hidden">
                    <div className="flex items-center gap-3 px-4 py-3">
                      <div className="p-1.5 rounded-xl bg-white/[0.03] border border-[var(--color-border-subtle)] text-[var(--color-text-muted)]">
                        <Icon size={14} />
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="text-[10px] text-[var(--color-text-muted)] font-mono font-medium">#{idx + 1}</span>
                          <span className="text-xs text-[var(--color-text-primary)] truncate font-medium">{step.description}</span>
                        </div>
                      </div>
                      {stepStatusIcon(step.status)}
                      {step.duration && (
                        <span className="text-[10px] text-[var(--color-text-muted)] font-mono">{step.duration}s</span>
                      )}
                    </div>
                    {(step.output || step.error) && (
                      <div className="px-4 pb-3">
                        <pre className="text-[10px] text-[var(--color-text-muted)] bg-[var(--color-bg-surface-2)] border border-[var(--color-border-subtle)] rounded-xl p-3 max-h-32 overflow-auto font-mono">
                          {step.error || step.output}
                        </pre>
                      </div>
                    )}
                  </div>
                );
              })}

              {selectedTask.result && (
                <div className="bg-[var(--color-success)]/10 border border-[var(--color-success)]/30 rounded-2xl p-5">
                  <div className="flex items-center gap-2 mb-1">
                    <CheckCircle2 size={14} className="text-[var(--color-success)]" />
                     <span className="text-xs font-semibold text-[var(--color-success)]">任务完成</span>
                  </div>
                  <p className="text-xs text-[var(--color-text-secondary)]">{selectedTask.result}</p>
                </div>
              )}

              {selectedTask.error && (
                <div className="bg-[var(--color-error)]/10 border border-[var(--color-error)]/30 rounded-2xl p-5">
                  <div className="flex items-center gap-2 mb-1">
                    <XCircle size={14} className="text-[var(--color-error)]" />
                     <span className="text-xs font-semibold text-[var(--color-error)]">任务失败</span>
                  </div>
                  <p className="text-xs text-[var(--color-text-secondary)]">{selectedTask.error}</p>
                </div>
              )}
            </div>
          </>
        ) : (
          <div className="flex-1 flex items-center justify-center text-[var(--color-text-muted)] text-sm">
              选择一个任务或创建新任务
          </div>
        )}
      </div>
    </div>
  );
}

function selectedToolCalls(task: Task): number {
  return task.steps.filter(s => s.status === 'completed' && s.type !== 'reasoning').length;
}
