import { useState, useEffect, useRef, useCallback } from 'react';
import { Play, Square, CheckCircle2, XCircle, Loader2, Clock, Terminal, Globe, FileText } from 'lucide-react';

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
      const res = await fetch('/api/v1/tasks/');
      if (res.ok) {
        const data = await res.json();
        setTasks(data);
        if (data.length > 0 && !selectedTaskId) {
          setSelectedTaskId(data[0].id);
        }
      }
    } catch { /* skip */ }
  }, [selectedTaskId]);

  useEffect(() => {
    fetchTasks();
  }, []);

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
      const res = await fetch('/api/v1/tasks/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          description: newTask,
          provider: 'openai',
          model_id: 'gpt-4o',
          api_key: '',
        }),
      });
      if (res.ok) {
        const data = await res.json();
        setNewTask('');
        fetchTasks();
        setSelectedTaskId(data.task_id);
      }
    } catch { /* skip */ }
    setLoading(false);
  };

  const cancelTask = async (taskId: string) => {
    try {
      await fetch(`/api/v1/tasks/${taskId}/cancel`, {
        method: 'POST',
      });
      fetchTasks();
    } catch { /* skip */ }
  };

  const selectedTask = tasks.find(t => t.id === selectedTaskId);

  const statusColor = (status: string) => {
    switch (status) {
      case 'completed': return 'text-green-400';
      case 'failed': case 'cancelled': return 'text-red-400';
      case 'running': case 'waiting_approval': return 'text-blue-400';
      default: return 'text-gray-400';
    }
  };

  const stepStatusIcon = (status: string) => {
    switch (status) {
      case 'completed': return <CheckCircle2 size={14} className="text-green-400" />;
      case 'failed': return <XCircle size={14} className="text-red-400" />;
      case 'running': return <Loader2 size={14} className="text-blue-400 animate-spin" />;
      default: return <Clock size={14} className="text-gray-500" />;
    }
  };

  return (
    <div className="h-full flex">
      {/* Task List */}
      <div className="w-72 border-r border-white/5 flex flex-col">
        <div className="p-4 border-b border-white/5">
          <h2 className="text-sm font-semibold text-gray-100 mb-3">自主任务</h2>
          <div className="flex gap-2">
            <input
              type="text"
              value={newTask}
              onChange={e => setNewTask(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && createTask()}
               placeholder="描述一个任务..."
              className="flex-1 px-3 py-2 bg-white/5 border border-white/10 rounded-2xl text-xs text-gray-100 placeholder:text-gray-600 focus:outline-none focus:border-[#007AFF]/50 transition-all duration-200"
            />
            <button
              onClick={createTask}
              disabled={loading || !newTask.trim()}
              className="px-3 py-2 bg-[#007AFF] hover:bg-[#007AFF]/90 disabled:bg-white/10 disabled:text-gray-500 text-white rounded-2xl transition-all duration-200 active:scale-[0.97]"
            >
              {loading ? <Loader2 size={14} className="animate-spin" /> : <Play size={14} />}
            </button>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto">
          {tasks.length === 0 && (
            <div className="p-4 text-center text-gray-500 text-xs">
               暂无任务。在上方描述一个任务。
            </div>
          )}
          {tasks.map(task => (
            <button
              key={task.id}
              onClick={() => setSelectedTaskId(task.id)}
              className={`w-full text-left px-4 py-3 border-b border-white/5 transition-all duration-200 ${
                selectedTaskId === task.id ? 'bg-white/[0.08] border-l-2 border-l-[#007AFF]' : 'hover:bg-white/5 border-l-2 border-l-transparent'
              }`}
            >
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-gray-200 truncate">{task.title}</span>
                <span className={`text-[10px] font-medium ${statusColor(task.status)}`}>
                  {task.status}
                </span>
              </div>
              {task.status === 'running' && (
                <div className="mt-1.5 w-full h-1 bg-white/10 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-[#007AFF] rounded-full transition-all"
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
            <div className="p-4 border-b border-white/5 flex items-center justify-between">
              <div>
                <h3 className="text-sm font-semibold text-gray-100">{selectedTask.title}</h3>
                <p className="text-xs text-gray-500 mt-0.5">
                  {selectedTask.steps.length} steps &middot; {selectedToolCalls(selectedTask)} tool calls
                  {selectedTask.duration && ` · ${selectedTask.duration}s`}
                </p>
              </div>
              {selectedTask.status === 'running' && (
                <button
                  onClick={() => cancelTask(selectedTask.id)}
                  className="flex items-center gap-1.5 px-4 py-2 bg-red-500/10 text-red-400 rounded-2xl text-xs font-semibold hover:bg-red-500/20 transition-all duration-200 border border-red-500/20"
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
                  <div key={step.id} className="bg-white/[0.04] border border-white/[0.08] rounded-2xl overflow-hidden backdrop-blur-sm">
                    <div className="flex items-center gap-3 px-4 py-3">
                      <div className="p-1.5 rounded-xl bg-white/5 text-gray-400">
                        <Icon size={14} />
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="text-[10px] text-gray-500 font-mono font-medium">#{idx + 1}</span>
                          <span className="text-xs text-gray-200 truncate font-medium">{step.description}</span>
                        </div>
                      </div>
                      {stepStatusIcon(step.status)}
                      {step.duration && (
                        <span className="text-[10px] text-gray-500 font-mono">{step.duration}s</span>
                      )}
                    </div>
                    {(step.output || step.error) && (
                      <div className="px-4 pb-3">
                        <pre className="text-[10px] text-gray-400 bg-white/5 rounded-xl p-3 max-h-32 overflow-auto font-mono border border-white/10">
                          {step.error || step.output}
                        </pre>
                      </div>
                    )}
                  </div>
                );
              })}

              {selectedTask.result && (
                <div className="bg-green-500/10 border border-green-500/30 rounded-2xl p-5">
                  <div className="flex items-center gap-2 mb-1">
                    <CheckCircle2 size={14} className="text-green-400" />
                     <span className="text-xs font-semibold text-green-400">任务完成</span>
                  </div>
                  <p className="text-xs text-gray-300">{selectedTask.result}</p>
                </div>
              )}

              {selectedTask.error && (
                <div className="bg-red-500/10 border border-red-500/30 rounded-2xl p-5">
                  <div className="flex items-center gap-2 mb-1">
                    <XCircle size={14} className="text-red-400" />
                     <span className="text-xs font-semibold text-red-400">任务失败</span>
                  </div>
                  <p className="text-xs text-gray-300">{selectedTask.error}</p>
                </div>
              )}
            </div>
          </>
        ) : (
          <div className="flex-1 flex items-center justify-center text-gray-500 text-sm">
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
