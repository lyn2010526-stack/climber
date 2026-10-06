import { useState, useCallback, useRef, useEffect } from 'react';
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
  FileInput, Bot, Wrench, GitBranch, FileOutput, FlaskConical,
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
  workflowName?: string;
}

const NODE_PALETTE = [
  { type: 'input', label: 'Input', icon: FileInput, description: 'User input variables' },
  { type: 'llm', label: 'LLM', icon: Bot, description: 'Call a language model' },
  { type: 'tool', label: 'Tool', icon: Wrench, description: 'Execute a tool' },
  { type: 'simulation', label: 'Simulation', icon: FlaskConical, description: 'Run a scientific experiment' },
  { type: 'condition', label: 'Condition', icon: GitBranch, description: 'Branch by condition' },
  { type: 'output', label: 'Output', icon: FileOutput, description: 'Return results' },
];

// Stable empty references so the sync effects below do not fire on every render
// for callers that omit initialNodes / initialEdges.
const EMPTY_NODES: Node[] = [];
const EMPTY_EDGES: Edge[] = [];

export function WorkflowEditor({
  onSave,
  onRun,
  initialNodes = EMPTY_NODES,
  initialEdges = EMPTY_EDGES,
  workflowId,
  workflowName,
}: WorkflowEditorProps) {
  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);
  const [selectedNode, setSelectedNode] = useState<Node | null>(null);
  const [name, setName] = useState(workflowName || 'Untitled Workflow');
  const [saving, setSaving] = useState(false);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const reactFlowWrapper = useRef<HTMLDivElement>(null);

  // useNodesState only seeds from the initial value; when the parent loads a
  // workflow asynchronously the canvas must adopt it instead of staying empty (R13-49).
  useEffect(() => {
    setNodes(initialNodes);
  }, [initialNodes, setNodes]);

  useEffect(() => {
    setEdges(initialEdges);
  }, [initialEdges, setEdges]);

  useEffect(() => {
    if (workflowName !== undefined) setName(workflowName);
  }, [workflowName]);

  useEffect(() => {
    setSelectedNode(null);
  }, [workflowId]);

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
         name: name.trim() || 'Untitled Workflow',
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
    <div className="flex h-full min-h-0 flex-col md:flex-row">
      {/* Canvas */}
      <div className="min-h-[240px] min-w-0 flex-1 flex flex-col">
        {/* Toolbar */}
         <div className="min-h-12 shrink-0 flex items-center px-3 border-b border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-1)] gap-2">
          <input
             type="text"
             aria-label="Workflow name"
             value={name}
             onChange={(e) => setName(e.target.value)}
            className="min-w-0 w-full rounded-[var(--radius-sm)] px-2 py-2 text-sm font-medium text-[var(--color-text-primary)] bg-transparent focus:outline-none focus:ring-1 focus:ring-[var(--color-border-strong)]"
          />
          <div className="ml-auto flex shrink-0 items-center gap-2">
            <button type="button"
              onClick={handleSave}
              disabled={saving}
               className="flex min-h-11 md:min-h-8 items-center gap-1.5 px-3 text-xs text-[var(--color-text-primary)] border border-[var(--color-border-default)] hover:bg-[var(--color-bg-surface-2)] rounded-[var(--radius-sm)] disabled:opacity-50"
            >
              <Save size={14} />
              {saving ? '保存中...' : 'Save'}
            </button>
            <button type="button"
              onClick={handleRun}
              disabled={running || !workflowId}
              className="flex min-h-11 md:min-h-8 items-center gap-1.5 px-3 text-xs text-[var(--color-accent-text)] bg-[var(--color-accent)] rounded-[var(--radius-sm)] hover:bg-[var(--color-accent-hover)] disabled:bg-[var(--color-bg-disabled)] disabled:text-[var(--color-text-secondary)]"
            >
              <Play size={14} />
              {running ? '运行中...' : 'Run'}
            </button>
          </div>
        </div>

        {error && (
          <div role="alert" className="px-3 py-2 bg-[var(--color-error-subtle)] border-b border-[var(--color-border-subtle)] text-xs text-[var(--color-error)]">
            {error}
          </div>
        )}

        {/* Flow Canvas */}
        <div ref={reactFlowWrapper} className="min-h-0 flex-1">
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
             className="bg-[var(--color-bg-page)] [&_.react-flow__edge-path]:stroke-[var(--color-text-muted)]"
          >
            <Background variant={BackgroundVariant.Dots} gap={20} size={1} color="var(--color-border-strong)" />
             <Controls className="!bg-[var(--color-bg-surface)] !border-[var(--color-border-subtle)] !shadow-lg [&>button]:!bg-[var(--color-bg-surface)] [&>button]:!border-[var(--color-border-subtle)] [&>button]:!text-[var(--color-text-muted)] [&>button:hover]:!bg-[var(--color-bg-surface-elevated)]/50" />
            <MiniMap
              className="hidden md:block !bg-[var(--color-bg-surface-1)] border !border-[var(--color-border-default)] !rounded-[var(--radius-sm)]"
              style={{ width: 120, height: 80 }}
              nodeColor="var(--color-text-muted)"
              maskColor="var(--color-bg-surface-2)"
            />
          </ReactFlow>
        </div>
      </div>

       {/* Right Panel */}
       <aside aria-label="Workflow configuration" className="h-[45%] min-h-0 w-full shrink-0 border-t md:border-t-0 md:border-l border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-1)] flex flex-col md:h-full md:w-72 lg:w-80">
        {/* Node Palette */}
         <div className="p-3 shrink-0 border-b border-[var(--color-border-subtle)]">
           <h3 className="text-xs font-semibold text-[var(--color-text-secondary)] mb-2">
            Node Palette
          </h3>
          <div className="grid grid-cols-3 md:grid-cols-2 gap-1.5">
            {NODE_PALETTE.map(({ type, label, icon: Icon, description }) => (
              <div
                key={type}
                draggable
                onDragStart={(e) => {
                  e.dataTransfer.setData('application/reactflow', type);
                  e.dataTransfer.effectAllowed = 'move';
                }}
                title={description}
                className="flex items-center gap-2 px-2 py-2 rounded-[var(--radius-sm)] border border-[var(--color-border-default)] cursor-grab hover:bg-[var(--color-bg-surface-2)]"
              >
                <Icon size={14} className="shrink-0 text-[var(--color-text-secondary)]" />
                <div className="flex-1 min-w-0">
                   <p className="truncate text-xs font-medium text-[var(--color-text-primary)]">{label}</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Properties Panel */}
        <div className="min-h-0 flex-1">
          {selectedNode ? (
            <PropertiesPanel
              key={selectedNode.id}
              node={selectedNode}
              onUpdate={updateNodeData}
              onDelete={deleteSelectedNode}
            />
          ) : (
            <div className="p-4 text-center">
                <p className="text-xs text-[var(--color-text-muted)]">选择节点以编辑属性</p>
            </div>
          )}
        </div>
      </aside>
    </div>
  );
}
