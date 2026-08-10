import { useState, useEffect, useCallback } from 'react';
import { Clock, Plus, Trash2, ToggleLeft, ToggleRight, Shield, Search, RefreshCw } from 'lucide-react';
import { api } from '../../api';

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
  inspect: 'bg-blue-600/10 text-blue-400',
  audit: 'bg-amber-500/10 text-amber-400',
  backup: 'bg-green-500/10 text-green-400',
  custom: 'bg-[var(--color-bg-surface-2)] text-[var(--color-text-muted)]',
};

export function MobileSchedulerPage() {
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
    const target = tasks.find(t => t.id === id);
    if (!target) return;
    try {
      await api.updateSchedulerTask(id, { enabled: !target.enabled });
      setTasks(prev => prev.map(t => t.id === id ? { ...t, enabled: !target.enabled } : t));
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

  return (
    <div className="mobile-page-container">
      <div className="px-4 py-4">
        <div className="flex items-start justify-between mb-4">
          <div>
            <h2 className="text-lg font-bold" style={{ color: 'var(--color-text-primary)' }}>
              定时任务
            </h2>
            <p className="text-xs mt-1" style={{ color: 'var(--color-text-muted)' }}>
              周期性检查和自动化任务
            </p>
          </div>
          <button
            onClick={() => setShowAdd(!showAdd)}
            className="flex items-center gap-1.5 px-3 py-2.5 text-xs bg-[var(--color-accent)]/10 text-[var(--color-accent)] border border-[var(--color-accent)]/20 rounded-2xl font-semibold transition-all duration-200 active:scale-[0.95]"
          >
            <Plus size={14} /> {showAdd ? '收起' : '添加任务'}
          </button>
        </div>

        {showAdd && (
          <div className="p-4 bg-[var(--color-bg-surface-1)] border border-[var(--color-border-subtle)] rounded-2xl space-y-3 mb-4">
            <input
              type="text"
              placeholder="任务名称"
              value={newTask.name}
              onChange={(e) => setNewTask({ ...newTask, name: e.target.value })}
              className="w-full px-3 py-2.5 bg-[var(--color-bg-surface-2)] border border-[var(--color-border-subtle)] rounded-xl text-sm text-[var(--color-text-primary)] placeholder:text-[var(--color-text-muted)] focus:outline-none focus:border-[var(--color-accent)]/50 transition-all duration-200"
            />
            <input
              type="text"
              placeholder="描述"
              value={newTask.description}
              onChange={(e) => setNewTask({ ...newTask, description: e.target.value })}
              className="w-full px-3 py-2.5 bg-[var(--color-bg-surface-2)] border border-[var(--color-border-subtle)] rounded-xl text-sm text-[var(--color-text-primary)] placeholder:text-[var(--color-text-muted)] focus:outline-none focus:border-[var(--color-accent)]/50 transition-all duration-200"
            />
            <input
              type="text"
              placeholder="Cron 表达式"
              value={newTask.cron}
              onChange={(e) => setNewTask({ ...newTask, cron: e.target.value })}
              className="w-full px-3 py-2.5 bg-[var(--color-bg-surface-2)] border border-[var(--color-border-subtle)] rounded-xl text-sm text-[var(--color-text-primary)] font-mono placeholder:text-[var(--color-text-muted)] focus:outline-none focus:border-[var(--color-accent)]/50 transition-all duration-200"
            />
            <select
              value={newTask.type}
              onChange={(e) => setNewTask({ ...newTask, type: e.target.value })}
              className="w-full px-3 py-2.5 bg-[var(--color-bg-surface-2)] border border-[var(--color-border-subtle)] rounded-xl text-sm text-[var(--color-text-primary)] focus:outline-none focus:border-[var(--color-accent)]/50 transition-all duration-200"
            >
              <option value="custom">自定义</option>
              <option value="inspect">检查</option>
              <option value="audit">审计</option>
              <option value="backup">备份</option>
            </select>
            <div className="flex justify-end gap-2 pt-1">
              <button onClick={() => setShowAdd(false)} className="px-4 py-2.5 text-xs text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] transition-colors">
                取消
              </button>
              <button onClick={addTask} className="px-4 py-2.5 text-xs bg-[var(--color-accent)] text-white rounded-xl hover:bg-[var(--color-accent-hover)] transition-all duration-200">
                创建
              </button>
            </div>
          </div>
        )}

        {loading && (
          <div className="flex items-center justify-center py-12">
            <div className="w-7 h-7 border-2 border-[var(--color-accent)] border-t-transparent rounded-full animate-spin" />
          </div>
        )}

        {error && (
          <div className="flex flex-col items-center gap-3 py-12">
            <p className="text-sm text-[var(--color-text-secondary)]">{error}</p>
            <button onClick={fetchTasks} className="px-4 py-2.5 bg-[var(--color-accent)] text-white rounded-xl text-sm hover:bg-[var(--color-accent-hover)] transition-colors">
              重试
            </button>
          </div>
        )}

        {!loading && !error && (
          <div className="space-y-3">
            {tasks.length === 0 && (
              <div className="py-10 text-center text-[var(--color-text-muted)] text-sm">
                暂无定时任务。点击"添加任务"创建一个。
              </div>
            )}
            {tasks.map((task) => {
              const Icon = TYPE_ICONS[task.type] || Clock;
              return (
                <div
                  key={task.id}
                  className={`p-4 bg-[var(--color-bg-surface-1)] border border-[var(--color-border-subtle)] rounded-2xl transition-all duration-200 ${task.enabled ? '' : 'opacity-60'}`}
                >
                  <div className="flex items-start gap-3">
                    <div className={`w-9 h-9 rounded-xl flex items-center justify-center shrink-0 border border-[var(--color-border-subtle)] ${TYPE_COLORS[task.type] || TYPE_COLORS['custom']}`}>
                      <Icon size={14} />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium text-[var(--color-text-primary)] truncate">{task.name}</span>
                        <span className={`px-1.5 py-0.5 rounded-lg text-[10px] font-medium border border-[var(--color-border-subtle)] shrink-0 ${TYPE_COLORS[task.type] || TYPE_COLORS['custom']}`}>
                          {task.type}
                        </span>
                      </div>
                      <p className="text-xs text-[var(--color-text-muted)] mt-0.5">{task.description}</p>
                      <div className="flex flex-wrap items-center gap-x-3 gap-y-1 mt-2 text-[10px] text-[var(--color-text-muted)]">
                        <span className="font-mono">{task.cron}</span>
                        <span>上次：{formatTime(task.last_run)}</span>
                        <span>执行次数：{task.run_count}</span>
                      </div>
                    </div>
                    <div className="flex flex-col items-center gap-1.5 shrink-0">
                      <button
                        onClick={() => toggleTask(task.id)}
                        className="p-2 text-[var(--color-text-muted)] hover:text-[var(--color-accent)] transition-colors"
                        title={task.enabled ? 'Disable' : 'Enable'}
                      >
                        {task.enabled ? <ToggleRight size={20} className="text-[var(--color-accent)]" /> : <ToggleLeft size={20} />}
                      </button>
                      <button
                        onClick={() => deleteTask(task.id)}
                        className="p-2 text-[var(--color-text-muted)] hover:text-[var(--color-error)] transition-colors"
                      >
                        <Trash2 size={15} />
                      </button>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
