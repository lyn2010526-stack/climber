import { useState, useEffect, useCallback } from 'react';
import {
  Clock, Plus, Trash2, ToggleLeft, ToggleRight,
  Shield, Search, RefreshCw, AlertCircle,
} from 'lucide-react';
import { api } from '../api';
import { PageHeader } from '../components/ui/PageHeader';
import { Card, CardContent } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Badge } from '../components/ui/Badge';
import { Input } from '../components/ui/Input';
import { EmptyState } from '../components/ui/EmptyState';
import { SkeletonList } from '../components/ui/Skeleton';

interface ScheduledTask {
  id: string;
  name: string;
  description: string;
  cron: string;
  type: string;
  enabled: boolean;
  last_run: number | null;
  next_run: number | null;
  run_count: number;
}

const TYPE_ICONS: Record<string, typeof Shield> = {
  inspect: Search,
  audit: Shield,
  backup: RefreshCw,
  custom: Clock,
};

const TYPE_COLORS: Record<string, string> = {
  inspect: 'bg-blue-500/10 text-blue-400 border-blue-500/20',
  audit: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
  backup: 'bg-green-500/10 text-green-400 border-green-500/20',
  custom: 'bg-[var(--color-bg-surface-2)] text-[var(--color-text-muted)] border-[var(--color-border-subtle)]',
};

export function SchedulerPage() {
  const [tasks, setTasks] = useState<ScheduledTask[]>([]);
  const [showAdd, setShowAdd] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [newTask, setNewTask] = useState({ name: '', description: '', cron: '*/5 * * * *', type: 'custom' });

  const fetchTasks = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.listSchedulerTasks();
      setTasks(data);
    } catch {
      setError('加载定时任务失败');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchTasks();
  }, [fetchTasks]);

  const toggleTask = async (id: string) => {
    try {
      await api.updateSchedulerTask(id, {});
      fetchTasks();
    } catch { /* skip */ }
  };

  const deleteTask = async (id: string) => {
    try {
      await api.deleteSchedulerTask(id);
      fetchTasks();
    } catch { /* skip */ }
  };

  const addTask = async () => {
    if (!newTask.name) return;
    try {
      await api.createSchedulerTask({
        name: newTask.name,
        description: newTask.description,
        cron: newTask.cron,
        task_type: newTask.type,
      });
      setShowAdd(false);
      setNewTask({ name: '', description: '', cron: '*/5 * * * *', type: 'custom' });
      fetchTasks();
    } catch { /* skip */ }
  };

  const formatTime = (ts: number | null) => {
    if (!ts) return '从未';
    return new Date(ts).toLocaleString();
  };

  if (loading) {
    return (
      <div className="h-full overflow-y-auto page-transition">
        <div className="p-4 md:p-6 lg:p-8 max-w-4xl mx-auto">
          <PageHeader title="定时任务" description="周期性检查和自动化任务" icon={<Clock size={20} />} />
          <SkeletonList count={3} />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="h-full flex items-center justify-center">
        <Card variant="default" className="max-w-sm mx-auto">
          <CardContent className="p-6 text-center">
            <AlertCircle size={32} className="text-[var(--color-error)] mx-auto mb-3" />
            <p className="text-sm text-[var(--color-text-secondary)] mb-4">{error}</p>
            <Button variant="primary" size="sm" onClick={fetchTasks}>重试</Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="h-full overflow-y-auto page-transition">
      <div className="p-4 md:p-6 lg:p-8 max-w-4xl mx-auto">
        <PageHeader
          title="定时任务"
          description="周期性检查和自动化任务"
          icon={<Clock size={20} />}
          actions={
            <Button
              variant="primary"
              size="sm"
              icon={<Plus size={14} />}
              onClick={() => setShowAdd(!showAdd)}
            >
              添加任务
            </Button>
          }
        />

        {showAdd && (
          <Card variant="default" className="mb-6">
            <CardContent className="p-5 space-y-3">
              <Input
                placeholder="任务名称"
                value={newTask.name}
                onChange={(e) => setNewTask({ ...newTask, name: e.target.value })}
              />
              <Input
                placeholder="描述"
                value={newTask.description}
                onChange={(e) => setNewTask({ ...newTask, description: e.target.value })}
              />
              <div className="flex gap-3">
                <Input
                  placeholder="Cron 表达式"
                  value={newTask.cron}
                  onChange={(e) => setNewTask({ ...newTask, cron: e.target.value })}
                  className="font-mono"
                />
                <select
                  value={newTask.type}
                  onChange={(e) => setNewTask({ ...newTask, type: e.target.value })}
                  className="px-3 py-2 bg-[var(--color-bg-surface-2)] border border-[var(--color-border-subtle)] rounded-xl text-xs text-[var(--color-text-primary)] focus:outline-none focus:border-[var(--color-accent)]/50"
                >
                  <option value="custom">自定义</option>
                  <option value="inspect">检查</option>
                  <option value="audit">审计</option>
                  <option value="backup">备份</option>
                </select>
              </div>
              <div className="flex justify-end gap-2 pt-1">
                <Button variant="ghost" size="sm" onClick={() => setShowAdd(false)}>取消</Button>
                <Button variant="primary" size="sm" onClick={addTask} disabled={!newTask.name}>创建</Button>
              </div>
            </CardContent>
          </Card>
        )}

        {tasks.length === 0 ? (
          <EmptyState
            icon="file"
            title="暂无定时任务"
            description="点击「添加任务」创建一个"
          />
        ) : (
          <div className="space-y-3 stagger-children">
            {tasks.map((task) => {
              const Icon = TYPE_ICONS[task.type] || Clock;
              const colorClass = TYPE_COLORS[task.type] || TYPE_COLORS['custom'];
              return (
                <Card key={task.id} variant="default" className={task.enabled ? '' : 'opacity-60'}>
                  <CardContent className="p-4">
                    <div className="flex items-start gap-3">
                      <div className={`w-8 h-8 rounded-xl flex items-center justify-center shrink-0 border ${colorClass}`}>
                        <Icon size={14} />
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-semibold text-[var(--color-text-primary)]">{task.name}</span>
                          <Badge variant="default" size="xs">{task.type}</Badge>
                        </div>
                        {task.description && (
                          <p className="text-xs text-[var(--color-text-muted)] mt-0.5">{task.description}</p>
                        )}
                        <div className="flex flex-wrap items-center gap-3 mt-2 text-[10px] text-[var(--color-text-muted)]">
                          <span className="font-mono">{task.cron}</span>
                          <span>上次：{formatTime(task.last_run)}</span>
                          <span>执行 {task.run_count} 次</span>
                        </div>
                      </div>
                      <div className="flex items-center gap-1 shrink-0">
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => toggleTask(task.id)}
                          title={task.enabled ? '禁用' : '启用'}
                        >
                          {task.enabled ? (
                            <ToggleRight size={18} className="text-[var(--color-accent)]" />
                          ) : (
                            <ToggleLeft size={18} className="text-[var(--color-text-muted)]" />
                          )}
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => deleteTask(task.id)}
                          className="text-[var(--color-text-muted)] hover:text-[var(--color-error)]"
                        >
                          <Trash2 size={14} />
                        </Button>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
