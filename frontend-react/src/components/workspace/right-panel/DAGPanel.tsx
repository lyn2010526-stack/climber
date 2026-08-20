import { useState, useEffect } from 'react';
import { GitBranch } from 'lucide-react';
import { api } from '../../../api';

export function DAGPanel() {
  const [nodes, setNodes] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const fetchStatus = async () => {
      setLoading(true);
      try {
        const data = await api.getClusterStatus();
          if (data.plan) {
            setNodes(data.plan.map((p: any) => ({
              id: p.id || String(Math.random()),
              label: p.description || p.task || 'Unknown',
              status: p.status || 'pending',
            })));
          }
      } catch { /* skip */ }
      setLoading(false);
    };
    fetchStatus();
  }, []);

  if (loading) {
    return (
      <div className="space-y-3">
        <p className="text-xs text-[var(--color-text-muted)]">正在加载工作流状态...</p>
        <div className="space-y-2">
          {[1, 2, 3].map(i => (
            <div key={i} className="flex items-center gap-2 animate-pulse">
              <div className="w-3 h-3 rounded-full bg-white/10" />
              <div className="h-3 w-32 bg-white/5 rounded-xl" />
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (nodes.length === 0) {
    return (
      <div className="space-y-3">
        <p className="text-xs text-[var(--color-text-muted)]">任务依赖图</p>
        <div className="text-center py-8">
          <GitBranch size={24} className="mx-auto text-[var(--color-text-muted)]" />
           <p className="text-xs text-[var(--color-text-muted)] mt-2">暂无活跃工作流</p>
           <p className="text-[10px] text-[var(--color-text-muted)] mt-1">创建工作流后，这里会显示任务依赖</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-3">
       <p className="text-xs text-[var(--color-text-muted)]">任务依赖图 — 根据需求自动规划</p>
      <div className="space-y-1">
        {nodes.map((node, i) => (
          <div key={node.id} className="flex items-center gap-2">
            <div className="flex flex-col items-center">
              <div className={`w-3 h-3 rounded-full border-2 ${
                node.status === 'completed' ? 'bg-green-500 border-green-500' :
                node.status === 'running' ? 'bg-[#007AFF] border-[#007AFF] animate-pulse' :
                'border-[var(--color-border-subtle)]'
              }`} />
              {i < nodes.length - 1 && <div className="w-0.5 h-4 bg-white/10" />}
            </div>
             <span className={`min-w-0 truncate text-xs ${
              node.status === 'completed' ? 'text-green-400' :
              node.status === 'running' ? 'text-blue-400 font-medium' :
              'text-[var(--color-text-muted)]'
            }`}>
              {node.label}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
