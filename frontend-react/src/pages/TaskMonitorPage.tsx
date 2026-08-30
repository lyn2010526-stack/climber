import { useState, useEffect, useRef, useCallback } from 'react';
import { Play, Square, CheckCircle2, XCircle, Loader2, Clock, Terminal, Globe, FileText } from 'lucide-react';
import { api } from '../api';
import type { TaskSummary, TaskDetail } from '../types/api';

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

interface TaskDetailWithSteps extends TaskDetail {
  steps?: TaskStep[];
  current_step_idx?: number;
  title?: string;
  result?: string;
  error?: string;
  total_tool_calls?: number;
  duration?: number | null;
}

const STEP_ICONS: Record<string, typeof Terminal> = {
  command: Terminal,
  browser: Globe,
  file: FileText,
  reasoning: Clock,
  question: Clock,
};

export default function TaskMonitorPage() {
  const [tasks, setTasks] = useState<TaskSummary[]>([]);
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null);
  const [selectedTask, setSelectedTask] = useState<TaskDetail | null>(null);
  const [taskLoading, setTaskLoading] = useState(false);
  const [newTask, setNewTask] = useState('');
  const [loading, setLoading] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  // Fetch existing tasks
  const fetchTasks = useCallback(async () => {
    try {
      const data = await api.listTasks();
      setTasks(data);
      setSelectedTaskId((currentId) => currentId ?? data[0]?.id ?? null);
    } catch { /* skip */ }
  }, []);

  useEffect(() => {
    fetchTasks();
  }, [fetchTasks]);

  useEffect(() => {
    if (!selectedTaskId) {
      setSelectedTask(null);
      return;
    }
    setTaskLoading(true);
    api.getTask(selectedTaskId).then((data: any) => {
      setSelectedTask(data as TaskDetailWithSteps);
    }).catch(() => {
      setSelectedTask(null);
    }).finally(() => {
      setTaskLoading(false);
    });
  }, [selectedTaskId]);

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
          if (msg.task.id === selectedTaskId) {
            setSelectedTask(msg.task as TaskDetailWithSteps);
          }
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
              className="px-3 py-2 bg-[var(--color-accent)] hover:bg-[var(--color-accent-hover)] disabled:bg-[var(--color-bg-surface-2)] disabled:text-[var(--color-text-muted)] text-white rounded-2xl transition-all duration-200 active:scale-[0.97]"
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
                selectedTaskId === task.id ? 'bg-[var(--color-bg-surface-3)] border-l-[var(--color-accent)]' : 'hover:bg-[var(--color-bg-surface-2)] border-l-transparent'
              }`}
            >
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-[var(--color-text-primary)] truncate">{task.description || task.id.slice(0, 8)}</span>
                <span className={`text-[10px] font-medium ${statusColor(task.status)}`}>
                  {task.status}
                </span>
              </div>
              {task.status === 'running' && task.current_round != null && task.max_rounds != null && task.max_rounds > 0 && (
                <div className="mt-1.5 w-full h-1 bg-[var(--color-bg-surface-3)] rounded-full overflow-hidden">
                  <div
                    className="h-full bg-[var(--color-accent)] rounded-full transition-all"
                    style={{ width: `${(task.current_round / task.max_rounds) * 100}%` }}
                  />
                </div>
              )}
            </button>
          ))}
        </div>
      </div>

      {/* Task Detail */}
      <div className="flex-1 flex flex-col">
        {taskLoading ? (
          <div className="flex-1 flex items-center justify-center">
            <Loader2 size={20} className="animate-spin text-[var(--color-text-muted)]" />
          </div>
        ) : selectedTask ? (
          <>
            {/* Header */}
            <div className="p-4 border-b border-[var(--color-border-subtle)] flex items-center justify-between">
              <div>
                <h3 className="text-sm font-semibold text-[var(--color-text-primary)]">{selectedTask.description || selectedTask.id.slice(0, 8)}</h3>
                <p className="text-xs text-[var(--color-text-muted)] mt-0.5">
                  {selectedTask.current_round != null && selectedTask.max_rounds != null
                    ? `Round ${selectedTask.current_round}/${selectedTask.max_rounds}`
                    : 'No round info'}
                  {selectedTask.total_tokens != null && ` · ${selectedTask.total_tokens} tokens`}
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
              {(() => {
                const steps = (selectedTask as TaskDetailWithSteps).steps;
                if (!steps || steps.length === 0) {
                  return (
                    <div className="text-center text-[var(--color-text-muted)] text-xs py-8">
                      {selectedTask.status === 'running' ? '任务执行中...' : '暂无步骤数据'}
                    </div>
                  );
                }
                return steps.map((step, idx) => {
                  const Icon = STEP_ICONS[step.type] || Terminal;
                  return (
                    <div key={step.id} className="bg-[var(--color-bg-surface-1)] border border-[var(--color-border-subtle)] rounded-2xl overflow-hidden">
                      <div className="flex items-center gap-3 px-4 py-3">
                        <div className="p-1.5 rounded-xl bg-[var(--color-bg-surface-2)] border border-[var(--color-border-subtle)] text-[var(--color-text-muted)]">
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
                });
              })()}

              {selectedTask.final_output && (
                <div className="bg-[var(--color-success)]/10 border border-[var(--color-success)]/30 rounded-2xl p-5">
                  <div className="flex items-center gap-2 mb-1">
                    <CheckCircle2 size={14} className="text-[var(--color-success)]" />
                     <span className="text-xs font-semibold text-[var(--color-success)]">任务完成</span>
                  </div>
                  <p className="text-xs text-[var(--color-text-secondary)]">{selectedTask.final_output}</p>
                </div>
              )}

              {selectedTask.human_review_status === 'rejected' && (
                <div className="bg-[var(--color-error)]/10 border border-[var(--color-error)]/30 rounded-2xl p-5">
                  <div className="flex items-center gap-2 mb-1">
                    <XCircle size={14} className="text-[var(--color-error)]" />
                     <span className="text-xs font-semibold text-[var(--color-error)]">任务失败</span>
                  </div>
                  <p className="text-xs text-[var(--color-text-secondary)]">任务被拒绝或取消</p>
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
