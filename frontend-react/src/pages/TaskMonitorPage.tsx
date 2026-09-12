import { useState, useEffect, useCallback } from 'react';
import { Square, CheckCircle2, XCircle, Plus } from 'lucide-react';
import { api, type TaskDetail, type TaskSummary } from '../api';
import { Card, CardContent } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Badge } from '../components/ui/Badge';
import { Input } from '../components/ui/Input';
import { EmptyState } from '../components/ui/EmptyState';

function statusColor(status: string) {
  switch (status) {
    case 'completed': return 'text-[var(--color-success)]';
    case 'failed': case 'cancelled': return 'text-[var(--color-error)]';
    case 'running': case 'waiting_approval': return 'text-[var(--color-accent)]';
    default: return 'text-[var(--color-text-muted)]';
  }
}

function TaskListItem({ task, isSelected, onClick }: { task: TaskSummary; isSelected: boolean; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className={`w-full text-left px-4 py-3 border-b border-[var(--color-border-subtle)] transition-all duration-200 border-l-2 ${
        isSelected
          ? 'bg-[var(--color-accent)]/5 border-l-[var(--color-accent)]'
          : 'hover:bg-[var(--color-bg-surface-2)] border-l-transparent'
      }`}
    >
      <div className="flex items-center justify-between gap-2">
        <span className="text-xs font-semibold text-[var(--color-text-primary)] truncate">{task.objective}</span>
        <span className={`text-[10px] font-medium shrink-0 ${statusColor(task.status)}`}>
          {task.status}
        </span>
      </div>
      {task.status === 'running' && (
        <div className="mt-2 w-full h-1.5 bg-[var(--color-bg-surface-3)] rounded-full overflow-hidden">
          <div
            className="h-full bg-[var(--color-accent)] rounded-full transition-all duration-300"
            style={{ width: `${(task.progress / Math.max(task.total_steps, 1)) * 100}%` }}
          />
        </div>
      )}
    </button>
  );
}

export default function TaskMonitorPage() {
  const [tasks, setTasks] = useState<TaskSummary[]>([]);
  const [selectedTask, setSelectedTask] = useState<TaskDetail | null>(null);
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null);
  const [newTask, setNewTask] = useState('');
  const [loading, setLoading] = useState(false);

  const fetchTasks = useCallback(async () => {
    try {
      const data = await api.listTasks();
      setTasks(data);
      const first = data[0];
      if (first) {
        setSelectedTaskId(current => current || first.task_id);
      }
    } catch { /* skip */ }
  }, []);

  useEffect(() => {
    fetchTasks();
  }, [fetchTasks]);

  useEffect(() => {
    if (!selectedTaskId) return;
    api.getTask(selectedTaskId).then(task => {
      setSelectedTask(task);
      setTasks(previous => previous.map(item => item.task_id === task.task_id ? task : item));
    }).catch(() => {});
  }, [selectedTaskId]);

  const createTask = async () => {
    if (!newTask.trim()) return;
    setLoading(true);
    try {
      const data = await api.createTask({
        task_type: 'agent_run',
        payload: { objective: newTask },
      });
      setNewTask('');
      fetchTasks();
      setSelectedTaskId(data.task_id);
    } catch { /* skip */ }
    setLoading(false);
  };

  const stopTask = async (taskId: string) => {
    try {
      await api.stopTask(taskId);
      fetchTasks();
    } catch { /* skip */ }
  };

  return (
    <div className="h-full flex flex-col md:flex-row">
      <div className="w-full md:w-72 lg:w-80 border-b md:border-b-0 md:border-r border-[var(--color-border-subtle)] flex flex-col shrink-0">
        <div className="p-4 border-b border-[var(--color-border-subtle)]">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-sm font-semibold text-[var(--color-text-primary)]">自主任务</h2>
            <Badge variant="info" size="xs">{tasks.length}</Badge>
          </div>
          <div className="flex gap-2">
            <Input
              value={newTask}
              onChange={e => setNewTask(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && createTask()}
              placeholder="描述一个任务..."
              className="text-xs"
            />
            <Button
              variant="primary"
              size="icon"
              onClick={createTask}
              disabled={loading || !newTask.trim()}
              loading={loading}
            >
              <Plus size={16} />
            </Button>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto">
          {tasks.length === 0 && (
            <div className="p-6 text-center">
              <p className="text-xs text-[var(--color-text-muted)]">暂无任务</p>
              <p className="text-[10px] text-[var(--color-text-muted)]/60 mt-1">在上方描述一个任务</p>
            </div>
          )}
          {tasks.map(task => (
            <TaskListItem
              key={task.task_id}
              task={task}
              isSelected={selectedTaskId === task.task_id}
              onClick={() => setSelectedTaskId(task.task_id)}
            />
          ))}
        </div>
      </div>

      <div className="flex-1 flex flex-col min-w-0">
        {selectedTask ? (
          <>
            <div className="p-4 border-b border-[var(--color-border-subtle)] flex items-center justify-between shrink-0">
              <div className="min-w-0">
                <h3 className="text-sm font-semibold text-[var(--color-text-primary)] truncate">{selectedTask.objective}</h3>
                <p className="text-xs text-[var(--color-text-muted)] mt-0.5">
                  第 {selectedTask.progress}/{selectedTask.total_steps} 步
                </p>
              </div>
              {selectedTask.status === 'running' && (
                <Button
                  variant="destructive"
                  size="sm"
                  icon={<Square size={12} />}
                  onClick={() => stopTask(selectedTask.task_id)}
                >
                  取消
                </Button>
              )}
            </div>

            <div className="flex-1 overflow-y-auto p-4 space-y-3">
              {selectedTask.result && (
                <Card variant="default" className="border-[var(--color-success)]/30 bg-[var(--color-success)]/5">
                  <CardContent className="p-5">
                    <div className="flex items-center gap-2 mb-2">
                      <CheckCircle2 size={14} className="text-[var(--color-success)]" />
                      <span className="text-xs font-semibold text-[var(--color-success)]">任务完成</span>
                    </div>
                    <p className="text-xs text-[var(--color-text-secondary)] leading-relaxed whitespace-pre-wrap">
                      {String(selectedTask.result.output ?? JSON.stringify(selectedTask.result, null, 2))}
                    </p>
                  </CardContent>
                </Card>
              )}

              {selectedTask.status === 'failed' && (
                <Card variant="default" className="border-[var(--color-error)]/30 bg-[var(--color-error)]/5">
                  <CardContent className="p-5">
                    <div className="flex items-center gap-2 mb-2">
                      <XCircle size={14} className="text-[var(--color-error)]" />
                      <span className="text-xs font-semibold text-[var(--color-error)]">任务失败</span>
                    </div>
                    <p className="text-xs text-[var(--color-text-secondary)] leading-relaxed">{selectedTask.error || '任务执行失败'}</p>
                  </CardContent>
                </Card>
              )}
            </div>
          </>
        ) : (
          <div className="flex-1 flex items-center justify-center">
            <EmptyState
              icon="file"
              title="选择一个任务"
              description="从左侧选择任务或创建新任务"
            />
          </div>
        )}
      </div>
    </div>
  );
}
