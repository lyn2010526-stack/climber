import { useState, useEffect, useCallback } from 'react';
import { Square, CheckCircle2, XCircle, Plus } from 'lucide-react';
import { api } from '../api';
import { Card, CardContent } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Badge } from '../components/ui/Badge';
import { Input } from '../components/ui/Input';
import { EmptyState } from '../components/ui/EmptyState';

interface Task {
  id: string;
  group_id: string;
  description: string;
  status: string;
  worker_id: string | null;
  current_round: number;
  max_rounds: number;
  total_tokens: number;
  final_output?: string;
  created_at: string;
}

interface TaskGroup {
  id: string;
  name: string;
}

function statusColor(status: string) {
  switch (status) {
    case 'completed': return 'text-[var(--color-success)]';
    case 'failed': case 'cancelled': return 'text-[var(--color-error)]';
    case 'running': case 'waiting_approval': return 'text-[var(--color-accent)]';
    default: return 'text-[var(--color-text-muted)]';
  }
}

function TaskListItem({ task, isSelected, onClick }: { task: Task; isSelected: boolean; onClick: () => void }) {
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
        <span className="text-xs font-semibold text-[var(--color-text-primary)] truncate">{task.description}</span>
        <span className={`text-[10px] font-medium shrink-0 ${statusColor(task.status)}`}>
          {task.status}
        </span>
      </div>
      {task.status === 'running' && (
        <div className="mt-2 w-full h-1.5 bg-[var(--color-bg-surface-3)] rounded-full overflow-hidden">
          <div
            className="h-full bg-[var(--color-accent)] rounded-full transition-all duration-300"
            style={{ width: `${(task.current_round / Math.max(task.max_rounds, 1)) * 100}%` }}
          />
        </div>
      )}
    </button>
  );
}

export default function TaskMonitorPage() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [groups, setGroups] = useState<TaskGroup[]>([]);
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null);
  const [selectedGroupId, setSelectedGroupId] = useState('');
  const [newTask, setNewTask] = useState('');
  const [loading, setLoading] = useState(false);

  const fetchTasks = useCallback(async () => {
    try {
      const data = await api.listTasks();
      setTasks(data);
      if (data.length > 0) {
        setSelectedTaskId(current => current || data[0].id);
      }
    } catch { /* skip */ }
  }, []);

  useEffect(() => {
    fetchTasks();
  }, [fetchTasks]);

  useEffect(() => {
    api.listGroups().then(data => {
      setGroups(data);
      if (data.length > 0) setSelectedGroupId(data[0].id);
    }).catch(() => {});
  }, []);

  useEffect(() => {
    if (!selectedTaskId) return;
    api.getTask(selectedTaskId).then(task => {
      setTasks(previous => previous.map(item => item.id === task.id ? task : item));
    }).catch(() => {});
  }, [selectedTaskId]);

  const createTask = async () => {
    if (!newTask.trim()) return;
    setLoading(true);
    try {
      const data = await api.createTask({
        group_id: selectedGroupId,
        description: newTask,
      });
      setNewTask('');
      fetchTasks();
      setSelectedTaskId(data.id);
    } catch { /* skip */ }
    setLoading(false);
  };

  const stopTask = async (taskId: string) => {
    try {
      await api.stopTask(taskId);
      fetchTasks();
    } catch { /* skip */ }
  };

  const selectedTask = tasks.find(t => t.id === selectedTaskId);
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
              disabled={loading || !newTask.trim() || !selectedGroupId}
              loading={loading}
            >
              <Plus size={16} />
            </Button>
          </div>
          <select
            value={selectedGroupId}
            onChange={event => setSelectedGroupId(event.target.value)}
            className="mt-2 w-full px-3 py-2 rounded border border-[var(--color-border-subtle)] bg-[var(--color-bg-surface)] text-xs"
          >
            <option value="">请选择协作组</option>
            {groups.map(group => <option key={group.id} value={group.id}>{group.name}</option>)}
          </select>
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
              key={task.id}
              task={task}
              isSelected={selectedTaskId === task.id}
              onClick={() => setSelectedTaskId(task.id)}
            />
          ))}
        </div>
      </div>

      <div className="flex-1 flex flex-col min-w-0">
        {selectedTask ? (
          <>
            <div className="p-4 border-b border-[var(--color-border-subtle)] flex items-center justify-between shrink-0">
              <div className="min-w-0">
                <h3 className="text-sm font-semibold text-[var(--color-text-primary)] truncate">{selectedTask.description}</h3>
                <p className="text-xs text-[var(--color-text-muted)] mt-0.5">
                  第 {selectedTask.current_round}/{selectedTask.max_rounds} 轮 &middot; {selectedTask.total_tokens} tokens
                </p>
              </div>
              {selectedTask.status === 'running' && (
                <Button
                  variant="destructive"
                  size="sm"
                  icon={<Square size={12} />}
                  onClick={() => stopTask(selectedTask.id)}
                >
                  取消
                </Button>
              )}
            </div>

            <div className="flex-1 overflow-y-auto p-4 space-y-3">
              {selectedTask.final_output && (
                <Card variant="default" className="border-[var(--color-success)]/30 bg-[var(--color-success)]/5">
                  <CardContent className="p-5">
                    <div className="flex items-center gap-2 mb-2">
                      <CheckCircle2 size={14} className="text-[var(--color-success)]" />
                      <span className="text-xs font-semibold text-[var(--color-success)]">任务完成</span>
                    </div>
                    <p className="text-xs text-[var(--color-text-secondary)] leading-relaxed">{selectedTask.final_output}</p>
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
                    <p className="text-xs text-[var(--color-text-secondary)] leading-relaxed">任务执行失败</p>
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
