import { useState, useEffect, useCallback } from 'react';
import {
  Clock, Plus, Trash2, ToggleLeft, ToggleRight,
  Shield, Search, RefreshCw,
} from 'lucide-react';
import { api } from '../api';

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
  custom: 'bg-gray-500/10 text-gray-500',
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
    } catch (e) {
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
    const d = new Date(ts);
    return d.toLocaleString();
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
           <span className="text-sm text-gray-500">加载任务中...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <p className="text-sm text-gray-400">{error}</p>
          <button onClick={fetchTasks} className="mt-3 px-4 py-1.5 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700">
             重试
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full overflow-y-auto p-6">
      <div className="max-w-4xl mx-auto space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-lg font-semibold text-gray-200">定时任务</h1>
            <p className="text-xs text-gray-500 mt-0.5">周期性检查和自动化任务</p>
          </div>
          <button
            onClick={() => setShowAdd(!showAdd)}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs bg-blue-600/10 text-blue-400 rounded-lg hover:bg-blue-600/20 transition-colors"
          >
             <Plus size={12} /> 添加任务
          </button>
        </div>

        {showAdd && (
          <div className="p-4 bg-gray-800/50 border border-gray-700 rounded-xl space-y-3">
            <input
              type="text"
               placeholder="任务名称"
              value={newTask.name}
              onChange={(e) => setNewTask({ ...newTask, name: e.target.value })}
              className="w-full px-3 py-2 bg-gray-700 border border-gray-700 rounded-lg text-xs text-gray-200 placeholder:text-gray-500 focus:outline-none focus:border-blue-500/50"
            />
            <input
              type="text"
               placeholder="描述"
              value={newTask.description}
              onChange={(e) => setNewTask({ ...newTask, description: e.target.value })}
              className="w-full px-3 py-2 bg-gray-700 border border-gray-700 rounded-lg text-xs text-gray-200 placeholder:text-gray-500 focus:outline-none focus:border-blue-500/50"
            />
            <div className="flex gap-3">
              <input
                type="text"
                 placeholder="Cron 表达式"
                value={newTask.cron}
                onChange={(e) => setNewTask({ ...newTask, cron: e.target.value })}
                className="flex-1 px-3 py-2 bg-gray-700 border border-gray-700 rounded-lg text-xs text-gray-200 font-mono placeholder:text-gray-500 focus:outline-none focus:border-blue-500/50"
              />
              <select
                value={newTask.type}
                onChange={(e) => setNewTask({ ...newTask, type: e.target.value })}
                className="px-3 py-2 bg-gray-700 border border-gray-700 rounded-lg text-xs text-gray-200 focus:outline-none focus:border-blue-500/50"
              >
                 <option value="custom">自定义</option>
                 <option value="inspect">检查</option>
                 <option value="audit">审计</option>
                 <option value="backup">备份</option>
              </select>
            </div>
            <div className="flex justify-end gap-2">
               <button onClick={() => setShowAdd(false)} className="px-3 py-1.5 text-xs text-gray-500 hover:text-gray-200">取消</button>
               <button onClick={addTask} className="px-3 py-1.5 text-xs bg-blue-600 text-white rounded-lg hover:bg-blue-700">创建</button>
            </div>
          </div>
        )}

        <div className="space-y-2">
          {tasks.length === 0 && (
            <div className="p-8 text-center text-gray-500 text-sm">
               暂无定时任务。点击"添加任务"创建一个。
            </div>
          )}
          {tasks.map((task) => {
            const Icon = TYPE_ICONS[task.type] || Clock;
            return (
              <div
                key={task.id}
                className={`p-4 bg-gray-800/50 border rounded-xl transition-all ${
                  task.enabled ? 'border-gray-700' : 'border-gray-700/50 opacity-60'
                }`}
              >
                <div className="flex items-start gap-3">
                  <div className={`w-8 h-8 rounded-lg flex items-center justify-center shrink-0 ${TYPE_COLORS[task.type] || TYPE_COLORS['custom']}`}>
                    <Icon size={14} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium text-gray-200">{task.name}</span>
                       <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium ${TYPE_COLORS[task.type] || TYPE_COLORS['custom']}`}>
                        {task.type}
                      </span>
                    </div>
                    <p className="text-xs text-gray-500 mt-0.5">{task.description}</p>
                    <div className="flex items-center gap-4 mt-2 text-[10px] text-gray-500">
                      <span className="font-mono">{task.cron}</span>
                      <span>上次：{formatTime(task.last_run)}</span>
                      <span>执行次数：{task.run_count}</span>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => toggleTask(task.id)}
                      className="p-1 text-gray-500 hover:text-blue-400 transition-colors"
                      title={task.enabled ? 'Disable' : 'Enable'}
                    >
                       {task.enabled ? <ToggleRight size={18} className="text-blue-400" /> : <ToggleLeft size={18} />}
                    </button>
                    <button
                      onClick={() => deleteTask(task.id)}
                      className="p-1 text-gray-500 hover:text-red-400 transition-colors"
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
