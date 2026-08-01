import { useState, useEffect, useCallback, useMemo } from 'react';
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  type Node,
  type Edge,
  Position,
  BackgroundVariant,
  MarkerType,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { CheckCircle2, XCircle, Loader2, Clock, GitBranch } from 'lucide-react';
import { api } from '../../api';

interface TaskNodeData {
  label: string;
  status: string;
  dependencies: string[];
  result?: string;
  error?: string;
  [key: string]: unknown;
}

interface GraphTask {
  id: string;
  title: string;
  status: string;
  dependencies: string[];
  result?: string;
  error?: string;
}

const STATUS_COLORS: Record<string, { bg: string; border: string; text: string }> = {
  completed: { bg: '#22c55e20', border: '#22c55e', text: '#22c55e' },
  running: { bg: '#3b82f620', border: '#3b82f6', text: '#3b82f6' },
  waiting_approval: { bg: '#f59e0b20', border: '#f59e0b', text: '#f59e0b' },
  failed: { bg: '#ef444420', border: '#ef4444', text: '#ef4444' },
  cancelled: { bg: '#6b728020', border: '#6b7280', text: '#6b7280' },
  pending: { bg: '#6b728020', border: '#6b7280', text: '#9ca3af' },
};

function TaskNode({ data }: { data: TaskNodeData }) {
  const colors = STATUS_COLORS[data.status] || STATUS_COLORS.pending;

  return (
    <div
      className="px-4 py-3 rounded-xl border-2 min-w-[180px] max-w-[280px]"
      style={{
        background: colors.bg,
        borderColor: colors.border,
      }}
    >
      <div className="flex items-center gap-2">
        <StatusIcon status={data.status} />
        <span
          className="text-xs font-semibold truncate"
          style={{ color: colors.text }}
          title={data.label}
        >
          {data.label}
        </span>
      </div>
      {data.status === 'completed' && data.result && (
        <div className="mt-1 text-[10px] text-gray-400 truncate" title={data.result as string}>
          {data.result}
        </div>
      )}
      {data.status === 'failed' && data.error && (
        <div className="mt-1 text-[10px] text-red-400 truncate" title={data.error as string}>
          {data.error}
        </div>
      )}
      {data.dependencies.length > 0 && (
        <div className="mt-1 text-[10px] text-gray-500 flex items-center gap-1">
          <GitBranch size={10} />
          {data.dependencies.length} 依赖
        </div>
      )}
    </div>
  );
}

function StatusIcon({ status }: { status: string }) {
  switch (status) {
    case 'completed':
      return <CheckCircle2 size={14} className="text-green-400 shrink-0" />;
    case 'running':
      return <Loader2 size={14} className="text-blue-400 animate-spin shrink-0" />;
    case 'failed':
    case 'cancelled':
      return <XCircle size={14} className="text-red-400 shrink-0" />;
    default:
      return <Clock size={14} className="text-gray-500 shrink-0" />;
  }
}

const nodeTypes = { taskNode: TaskNode };

export function TaskDAGVisualizer() {
  const [tasks, setTasks] = useState<GraphTask[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchTasks = useCallback(async () => {
    try {
      const data = await api.listTasks();
      setTasks(data.map((t: any) => ({
        id: t.id,
        title: t.title || t.description?.slice(0, 60) || t.id.slice(0, 8),
        status: t.status || 'pending',
        dependencies: t.dependencies || [],
        result: t.result,
        error: t.error,
      })));
    } catch { /* skip */ }
    setLoading(false);
  }, []);

  useEffect(() => {
    fetchTasks();
    const interval = setInterval(fetchTasks, 5000);
    return () => clearInterval(interval);
  }, [fetchTasks]);

  const { nodes, edges } = useMemo(() => {
    const nodeMap: Record<string, Node<TaskNodeData>> = {};
    const edgeList: Edge[] = [];

    tasks.forEach((task, idx) => {
      const row = Math.floor(idx / 3);
      const col = idx % 3;
      nodeMap[task.id] = {
        id: task.id,
        type: 'taskNode',
        position: { x: col * 300 + 50, y: row * 120 + 50 },
        data: {
          label: task.title,
          status: task.status,
          dependencies: task.dependencies,
          result: task.result,
          error: task.error,
        },
        sourcePosition: Position.Bottom,
        targetPosition: Position.Top,
      };
    });

    tasks.forEach((task) => {
      task.dependencies.forEach((depId) => {
        if (nodeMap[depId]) {
          edgeList.push({
            id: `${depId}-${task.id}`,
            source: depId,
            target: task.id,
            animated: true,
            style: { stroke: '#4b5563', strokeWidth: 2 },
            markerEnd: { type: MarkerType.ArrowClosed, color: '#4b5563' },
          });
        }
      });
    });

    return { nodes: Object.values(nodeMap), edges: edgeList };
  }, [tasks]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 size={20} className="animate-spin text-blue-400" />
      </div>
    );
  }

  if (tasks.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-gray-500">
        <GitBranch size={32} className="mb-2 opacity-30" />
        <p className="text-xs">暂无任务依赖图</p>
        <p className="text-[10px] mt-1">创建带有依赖的任务后将在此显示 DAG 图</p>
      </div>
    );
  }

  return (
    <div className="h-full w-full">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        fitView
        fitViewOptions={{ padding: 0.2 }}
        minZoom={0.3}
        maxZoom={2}
      >
        <Background variant={BackgroundVariant.Dots} gap={20} size={1} color="#374151" />
        <Controls className="!bg-gray-900 !border-gray-700 !rounded-lg" />
        <MiniMap
          className="!bg-gray-900 !border-gray-700"
          nodeColor={(n) => {
            const d = n.data as TaskNodeData;
            return STATUS_COLORS[d?.status]?.border || '#6b7280';
          }}
          maskColor="#00000080"
        />
      </ReactFlow>
    </div>
  );
}
