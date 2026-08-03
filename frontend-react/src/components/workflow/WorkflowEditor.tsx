import { useState, useCallback, useRef } from 'react';
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  addEdge,
  useNodesState,
  useEdgesState,
  BackgroundVariant,
} from '@xyflow/react';
import type { Connection, Edge, Node } from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import {
  Play, Save,
  FileInput, Bot, Wrench, GitBranch, FileOutput,
} from 'lucide-react';
import { nodeTypes, createWorkflowNode } from './WorkflowNodes';
import { PropertiesPanel } from './PropertiesPanel';
import { api } from '../../api';

interface WorkflowEditorProps {
  onSave?: (workflow: { id: string; nodes: Node[]; edges: Edge[] }) => void;
  onRun?: (workflow: { id: string; result: any }) => void;
  initialNodes?: Node[];
  initialEdges?: Edge[];
  workflowId?: string;
}

const NODE_PALETTE = [
  { type: 'input', label: 'Input', icon: FileInput, description: 'User input variables' },
  { type: 'llm', label: 'LLM', icon: Bot, description: 'Call a language model' },
  { type: 'tool', label: 'Tool', icon: Wrench, description: 'Execute a tool' },
  { type: 'condition', label: 'Condition', icon: GitBranch, description: 'Branch by condition' },
  { type: 'output', label: 'Output', icon: FileOutput, description: 'Return results' },
];

export function WorkflowEditor({
  onSave,
  onRun,
  initialNodes = [],
  initialEdges = [],
  workflowId,
}: WorkflowEditorProps) {
  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);
  const [selectedNode, setSelectedNode] = useState<Node | null>(null);
  const [workflowName, setWorkflowName] = useState('Untitled Workflow');
  const [saving, setSaving] = useState(false);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const reactFlowWrapper = useRef<HTMLDivElement>(null);

  const onConnect = useCallback(
    (params: Connection) => setEdges((eds) => addEdge({ ...params, animated: true }, eds)),
    [setEdges]
  );

  const onDragOver = useCallback((event: React.DragEvent) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = 'move';
  }, []);

  const onDrop = useCallback(
    (event: React.DragEvent) => {
      event.preventDefault();
      const type = event.dataTransfer.getData('application/reactflow');
      if (!type || !reactFlowWrapper.current) return;

      const bounds = reactFlowWrapper.current.getBoundingClientRect();
      const position = {
        x: event.clientX - bounds.left - 80,
        y: event.clientY - bounds.top - 20,
      };

      const newNode = createWorkflowNode(type, position);
      setNodes((nds) => nds.concat(newNode));
    },
    [setNodes]
  );

  const onNodeClick = useCallback((_: React.MouseEvent, node: Node) => {
    setSelectedNode(node);
  }, []);

  const onPaneClick = useCallback(() => {
    setSelectedNode(null);
  }, []);

  const deleteSelectedNode = useCallback(() => {
    if (selectedNode) {
      setNodes((nds) => nds.filter((n) => n.id !== selectedNode.id));
      setEdges((eds) => eds.filter((e) => e.source !== selectedNode.id && e.target !== selectedNode.id));
      setSelectedNode(null);
    }
  }, [selectedNode, setNodes, setEdges]);

  const updateNodeData = useCallback(
    (nodeId: string, data: Record<string, any>) => {
      setNodes((nds) =>
        nds.map((n) => (n.id === nodeId ? { ...n, data: { ...n.data, ...data } } : n))
      );
      if (selectedNode?.id === nodeId) {
        setSelectedNode((prev) => prev ? { ...prev, data: { ...prev.data, ...data } } : null);
      }
    },
    [selectedNode, setNodes]
  );

  const handleSave = async () => {
    setSaving(true);
    setError(null);
    try {
      const payload = {
        name: workflowName,
        nodes: nodes.map((n) => ({ id: n.id, type: n.type, data: n.data, position: n.position })),
        edges: edges.map((e) => ({ id: e.id, source: e.source, target: e.target, condition: (e as any).condition })),
      };

      let result;
      if (workflowId) {
        result = await api.updateWorkflow(workflowId, payload);
      } else {
        result = await api.createWorkflow(payload);
      }

      onSave?.({ id: result.id, nodes, edges });
    } catch (e: any) {
      setError(e.message || '保存工作流失败');
    } finally {
      setSaving(false);
    }
  };

  const handleRun = async () => {
    if (!workflowId) {
      setError('请先保存工作流再运行');
      return;
    }
    setRunning(true);
    setError(null);
    try {
      const result = await api.runWorkflow(workflowId, {});
      onRun?.({ id: workflowId, result });
    } catch (e: any) {
      setError(e.message || '运行工作流失败');
    } finally {
      setRunning(false);
    }
  };

  return (
    <div className="flex h-full">
      {/* Canvas */}
      <div className="flex-1 flex flex-col">
        {/* Toolbar */}
         <div className="h-10 flex items-center px-4 border-b border-[var(--color-border-subtle)] bg-[var(--color-bg-surface)]/50 gap-3">
          <input
            type="text"
            value={workflowName}
            onChange={(e) => setWorkflowName(e.target.value)}
            className="text-xs font-medium text-[var(--color-text-primary)] bg-transparent border-none focus:outline-none"
          />
          <div className="ml-auto flex items-center gap-1">
            <button
              onClick={handleSave}
              disabled={saving}
               className="flex items-center gap-1 px-2 py-1 text-[10px] text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] bg-[var(--color-bg-surface-elevated)] rounded transition-colors disabled:opacity-50"
            >
              <Save size={11} />
              {saving ? '保存中...' : 'Save'}
            </button>
            <button
              onClick={handleRun}
              disabled={running || !workflowId}
              className="flex items-center gap-1 px-2 py-1 text-[10px] text-white bg-blue-600 rounded hover:bg-blue-600/90 transition-colors disabled:opacity-50"
            >
              <Play size={11} />
              {running ? '运行中...' : 'Run'}
            </button>
          </div>
        </div>

        {error && (
          <div className="px-4 py-2 bg-red-500/10 border-b border-red-500/30 text-xs text-red-400">
            {error}
          </div>
        )}

        {/* Flow Canvas */}
        <div ref={reactFlowWrapper} className="flex-1">
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            onNodeClick={onNodeClick}
            onPaneClick={onPaneClick}
            onDrop={onDrop}
            onDragOver={onDragOver}
            nodeTypes={nodeTypes}
            fitView
             className="bg-[var(--color-bg-deep)]"
          >
            <Background variant={BackgroundVariant.Dots} gap={16} size={1} color="rgba(255,255,255,0.05)" />
             <Controls className="!bg-[var(--color-bg-surface)] !border-[var(--color-border-subtle)] !shadow-lg [&>button]:!bg-[var(--color-bg-surface)] [&>button]:!border-[var(--color-border-subtle)] [&>button]:!text-[var(--color-text-muted)] [&>button:hover]:!bg-[var(--color-bg-surface-elevated)]/50" />
            <MiniMap
               className="!bg-[var(--color-bg-surface)] !border-[var(--color-border-subtle)]"
              nodeColor={(n) => {
                const colors: Record<string, string> = {
                  input: '#6366f1',
                  llm: '#a855f7',
                  tool: '#10b981',
                  condition: '#f59e0b',
                  output: '#3b82f6',
                };
                return colors[n.type || ''] || '#64748b';
              }}
            />
          </ReactFlow>
        </div>
      </div>

       {/* Right Panel */}
       <div className="w-64 border-l border-[var(--color-border-subtle)] bg-[var(--color-bg-surface)]/30 flex flex-col">
        {/* Node Palette */}
         <div className="p-3 border-b border-[var(--color-border-subtle)]">
           <h3 className="text-[10px] font-semibold text-[var(--color-text-muted)] uppercase tracking-wider mb-2">
            Node Palette
          </h3>
          <div className="space-y-1">
            {NODE_PALETTE.map(({ type, label, icon: Icon, description }) => (
              <div
                key={type}
                draggable
                onDragStart={(e) => {
                  e.dataTransfer.setData('application/reactflow', type);
                  e.dataTransfer.effectAllowed = 'move';
                }}
                className="flex items-center gap-2 px-2 py-2 rounded-lg bg-[var(--color-bg-surface-elevated)] border border-[var(--color-border-subtle)] cursor-grab hover:border-[var(--color-accent)]/30 transition-colors"
              >
                <Icon size={13} className="text-blue-400" />
                <div className="flex-1 min-w-0">
                   <p className="text-[11px] font-medium text-[var(--color-text-primary)]">{label}</p>
                   <p className="text-[9px] text-[var(--color-text-muted)] truncate">{description}</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Properties Panel */}
        <div className="flex-1 overflow-y-auto">
          {selectedNode ? (
            <PropertiesPanel
              node={selectedNode}
              onUpdate={updateNodeData}
              onDelete={deleteSelectedNode}
            />
          ) : (
            <div className="p-4 text-center">
                <p className="text-[10px] text-[var(--color-text-muted)]">选择节点以编辑属性</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
