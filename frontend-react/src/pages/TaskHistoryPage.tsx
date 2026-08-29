import { useState, useEffect } from 'react';
import { Clock, CheckCircle2, AlertCircle, Copy, Download, ChevronRight } from 'lucide-react';
import { api } from '../api';
import type { TaskDetail, TaskSummary } from '../types/api';

type TaskRecord = TaskSummary & Partial<TaskDetail>;

const STATUS_LABELS: Record<string, string> = {
  pending: '等待中',
  running: '执行中',
  reviewing: '审查中',
  completed: '已完成',
  partial: '部分完成',
  failed: '失败',
  stopped: '已停止',
};

const STATUS_COLORS: Record<string, string> = {
  pending: 'text-[var(--color-text-muted)]',
  reviewing: 'text-amber-400',
  completed: 'text-green-400',
  partial: 'text-amber-400',
  failed: 'text-red-400',
  stopped: 'text-[var(--color-text-muted)]',
};

export function TaskHistoryPage() {
  const [tasks, setTasks] = useState<TaskSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(false);
  const [selectedTask, setSelectedTask] = useState<TaskRecord | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);

  useEffect(() => {
    loadTasks();
  }, []);

  const loadTasks = async () => {
    setLoading(true);
    setLoadError(false);
    try {
      const data = await api.listTasks();
      setTasks(data);
    } catch (e) {
      console.error('Failed to load tasks:', e);
      setLoadError(true);
    } finally {
      setLoading(false);
    }
  };

  const openTask = async (task: TaskSummary) => {
    setDetailLoading(true);
    try {
      setSelectedTask(await api.getTask(task.id));
    } catch {
      setSelectedTask(task);
    } finally {
      setDetailLoading(false);
    }
  };

  const copyOutput = (text: string) => {
    navigator.clipboard.writeText(text);
  };

  const downloadOutput = (task: TaskRecord) => {
    const blob = new Blob([task.final_output || ''], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `task-${task.id.slice(0, 8)}-output.txt`;
    a.click();
    URL.revokeObjectURL(url);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-2 border-[var(--color-accent)] border-t-transparent rounded-full animate-spin" />
          <span className="text-sm text-[var(--color-text-muted)]">加载任务历史...</span>
        </div>
      </div>
    );
  }

  if (selectedTask) {
    return (
      <div className="h-full flex flex-col">
          <div className="flex items-center gap-2 p-3 border-b border-[var(--color-border-subtle)]">
          <button
            onClick={() => setSelectedTask(null)}
            className="text-xs text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] transition-colors"
          >
            返回列表
          </button>
          <ChevronRight size={10} className="text-[var(--color-text-muted)]" />
          <span className="text-xs text-[var(--color-text-secondary)]">任务详情</span>
        </div>
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {detailLoading && <p className="text-[10px] text-[var(--color-text-muted)]">加载详情中...</p>}
          <div className="space-y-2">
            <h3 className="text-sm font-medium text-[var(--color-text-primary)]">{selectedTask.description}</h3>
            <div className="flex items-center gap-3 text-[10px] text-[var(--color-text-muted)]">
              <span>ID: {selectedTask.id.slice(0, 8)}...</span>
               <span>轮次: {selectedTask.current_round ?? 0}/{selectedTask.max_rounds ?? '—'}</span>
               <span>Tokens: {(selectedTask.total_tokens ?? 0).toLocaleString()}</span>
            </div>
            <div className="flex items-center gap-2">
              <span className={`text-[10px] ${STATUS_COLORS[selectedTask.status] || 'text-[var(--color-text-muted)]'}`}>
                {STATUS_LABELS[selectedTask.status] || selectedTask.status}
              </span>
            </div>
          </div>
          {selectedTask.final_output && (
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <h4 className="text-xs font-medium text-[var(--color-text-secondary)]">最终产出</h4>
                <div className="flex items-center gap-2">
                  <button
                     onClick={() => copyOutput(selectedTask.final_output || '')}
                    className="text-[10px] text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] flex items-center gap-1 transition-colors"
                  >
                    <Copy size={10} /> 复制
                  </button>
                  <button
                    onClick={() => downloadOutput(selectedTask)}
                    className="text-[10px] text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] flex items-center gap-1 transition-colors"
                  >
                    <Download size={10} /> 导出
                  </button>
                </div>
              </div>
              <pre className="p-3 bg-[var(--color-bg-surface-1)] border border-[var(--color-border-subtle)] rounded-xl text-xs text-[var(--color-text-primary)] whitespace-pre-wrap font-mono">
                {selectedTask.final_output}
              </pre>
            </div>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      <div className="p-4 border-b border-[var(--color-border-subtle)]">
        <h2 className="text-sm font-medium text-[var(--color-text-primary)]">任务历史</h2>
        <p className="text-[10px] text-[var(--color-text-muted)] mt-1">共 {tasks.length} 个任务</p>
      </div>
      <div className="flex-1 overflow-y-auto">
        {loadError ? (
          <div role="alert" className="text-center py-12">
            <p className="text-xs text-[var(--color-error)]">加载任务历史失败</p>
            <button
              type="button"
              onClick={() => void loadTasks()}
              className="mt-3 rounded-lg border border-[var(--color-border-subtle)] px-3 py-2 text-xs text-[var(--color-text-primary)] transition-colors hover:bg-[var(--color-bg-surface-2)]"
            >
              重试加载任务历史
            </button>
          </div>
        ) : tasks.length === 0 ? (
          <div className="text-center py-12">
            <p className="text-xs text-[var(--color-text-muted)]">暂无任务记录</p>
            <p className="text-[10px] text-[var(--color-text-muted)] mt-1">在群组中创建任务后，这里会显示历史记录</p>
          </div>
        ) : (
          <div className="divide-y divide-[var(--color-border-subtle)]">
            {tasks.map((task) => (
               <div
                 key={task.id}
                 onClick={() => void openTask(task)}
                 onKeyDown={(event) => {
                   if (event.key === 'Enter' || event.key === ' ') {
                     event.preventDefault();
                     void openTask(task);
                   }
                 }}
                 role="button"
                 tabIndex={0}
                 className="group cursor-pointer p-3 transition-colors duration-150 hover:bg-[var(--color-bg-surface-2)]"
               >
                <div className="flex items-start justify-between gap-2">
                  <div className="flex-1 min-w-0">
                    <p className="text-xs text-[var(--color-text-primary)] truncate group-hover:text-white transition-colors">{task.description}</p>
                    <div className="flex items-center gap-2 mt-1">
                      <span className={`text-[10px] ${STATUS_COLORS[task.status] || 'text-[var(--color-text-muted)]'}`}>
                        {STATUS_LABELS[task.status] || task.status}
                      </span>
                      <span className="text-[10px] text-[var(--color-text-muted)]">
                         {task.created_at ? new Date(task.created_at).toLocaleString('zh-CN') : '时间未知'}
                      </span>
                    </div>
                  </div>
                  <div className="flex items-center gap-1 text-[var(--color-text-muted)]">
                    {task.status === 'completed' ? (
                      <CheckCircle2 size={12} className="text-[var(--color-success)]" />
                    ) : task.status === 'failed' ? (
                      <AlertCircle size={12} className="text-[var(--color-error)]" />
                    ) : (
                      <Clock size={10} />
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
