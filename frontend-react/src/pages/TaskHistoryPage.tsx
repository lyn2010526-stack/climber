import { useState, useEffect } from 'react';
import { Clock, CheckCircle2, AlertCircle, Copy, Download, ChevronRight } from 'lucide-react';

interface TaskRecord {
  id: string;
  group_id: string;
  description: string;
  status: string;
  current_round: number;
  max_rounds: number;
  final_output: string;
  total_tokens: number;
  started_at: string;
  completed_at: string;
  created_at: string;
}

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
  pending: 'text-gray-500',
  running: 'text-blue-400',
  reviewing: 'text-amber-400',
  completed: 'text-green-400',
  partial: 'text-amber-400',
  failed: 'text-red-400',
  stopped: 'text-gray-500',
};

export function TaskHistoryPage() {
  const [tasks, setTasks] = useState<TaskRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedTask, setSelectedTask] = useState<TaskRecord | null>(null);

  useEffect(() => {
    loadTasks();
  }, []);

  const loadTasks = async () => {
    try {
      const resp = await fetch('/api/v1/tasks');
      if (resp.ok) {
        const data = await resp.json();
        setTasks(data);
      }
    } catch (e) {
      console.error('Failed to load tasks:', e);
    } finally {
      setLoading(false);
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
      <div className="h-full flex items-center justify-center">
        <p className="text-xs text-gray-500">加载任务历史...</p>
      </div>
    );
  }

  if (selectedTask) {
    return (
      <div className="h-full flex flex-col">
        <div className="flex items-center gap-2 p-3 border-b border-gray-700">
          <button
            onClick={() => setSelectedTask(null)}
            className="text-xs text-gray-500 hover:text-gray-200"
          >
            返回列表
          </button>
          <ChevronRight size={10} className="text-gray-600" />
          <span className="text-xs text-gray-400">任务详情</span>
        </div>
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          <div className="space-y-2">
            <h3 className="text-sm font-medium text-gray-200">{selectedTask.description}</h3>
            <div className="flex items-center gap-3 text-[10px] text-gray-500">
              <span>ID: {selectedTask.id.slice(0, 8)}...</span>
              <span>轮次: {selectedTask.current_round}/{selectedTask.max_rounds}</span>
              <span>Tokens: {selectedTask.total_tokens.toLocaleString()}</span>
            </div>
            <div className="flex items-center gap-2">
              <span className={`text-[10px] ${STATUS_COLORS[selectedTask.status] || 'text-gray-500'}`}>
                {STATUS_LABELS[selectedTask.status] || selectedTask.status}
              </span>
            </div>
          </div>
          {selectedTask.final_output && (
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <h4 className="text-xs font-medium text-gray-300">最终产出</h4>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => copyOutput(selectedTask.final_output)}
                    className="text-[10px] text-gray-500 hover:text-gray-200 flex items-center gap-1"
                  >
                    <Copy size={10} /> 复制
                  </button>
                  <button
                    onClick={() => downloadOutput(selectedTask)}
                    className="text-[10px] text-gray-500 hover:text-gray-200 flex items-center gap-1"
                  >
                    <Download size={10} /> 导出
                  </button>
                </div>
              </div>
              <pre className="p-3 bg-gray-800/50 border border-gray-700 rounded-lg text-xs text-gray-300 whitespace-pre-wrap font-mono">
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
      <div className="p-4 border-b border-gray-700">
        <h2 className="text-sm font-medium text-gray-200">任务历史</h2>
        <p className="text-[10px] text-gray-500 mt-1">共 {tasks.length} 个任务</p>
      </div>
      <div className="flex-1 overflow-y-auto">
        {tasks.length === 0 ? (
          <div className="text-center py-12">
            <p className="text-xs text-gray-500">暂无任务记录</p>
            <p className="text-[10px] text-gray-500 mt-1">在群组中创建任务后，这里会显示历史记录</p>
          </div>
        ) : (
          <div className="divide-y divide-gray-700/50">
            {tasks.map((task) => (
              <div
                key={task.id}
                onClick={() => setSelectedTask(task)}
                className="p-3 hover:bg-gray-800/30 cursor-pointer transition-colors"
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="flex-1 min-w-0">
                    <p className="text-xs text-gray-200 truncate">{task.description}</p>
                    <div className="flex items-center gap-2 mt-1">
                      <span className={`text-[10px] ${STATUS_COLORS[task.status] || 'text-gray-500'}`}>
                        {STATUS_LABELS[task.status] || task.status}
                      </span>
                      <span className="text-[10px] text-gray-600">
                        {new Date(task.created_at).toLocaleString('zh-CN')}
                      </span>
                    </div>
                  </div>
                  <div className="flex items-center gap-1 text-gray-600">
                    {task.status === 'completed' ? (
                      <CheckCircle2 size={12} className="text-green-400" />
                    ) : task.status === 'failed' ? (
                      <AlertCircle size={12} className="text-red-400" />
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
