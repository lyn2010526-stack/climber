import { useState, useCallback, useEffect, useMemo, useRef } from 'react';
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
} from 'lucide-react';
import {
  createMetadataNodeTypes,
  createWorkflowNode,
  getWorkflowNodeIcon,
} from './WorkflowNodes';
import { PropertiesPanel } from './PropertiesPanel';
import { api } from '../../api';
import type { WorkflowNodeTypeDefinition } from '../../types/workflows';

interface WorkflowEditorProps {
  onSave?: (workflow: { id: string; nodes: Node[]; edges: Edge[] }) => void;
  onRun?: (workflow: { id: string; result: any }) => void;
  initialNodes?: Node[];
  initialEdges?: Edge[];
  workflowId?: string;
}

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
  const [runningNode, setRunningNode] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [nodeDefinitions, setNodeDefinitions] = useState<WorkflowNodeTypeDefinition[]>([]);
  const reactFlowWrapper = useRef<HTMLDivElement>(null);
  const nodeTypeSignature = nodes.map((node) => node.type || '').sort().join('|');

  useEffect(() => {
    let active = true;
    api.getWorkflowNodeTypes()
      .then((definitions) => {
        if (active) setNodeDefinitions(definitions);
      })
      .catch((e: Error) => {
        if (active) setError(e.message || '加载节点类型失败');
      });
    return () => { active = false; };
  }, []);

  const canvasNodeTypes = useMemo(
    () => createMetadataNodeTypes(nodeDefinitions, nodeTypeSignature.split('|')),
    [nodeDefinitions, nodeTypeSignature],
  );
  const definitionsByType = useMemo(
    () => new Map(nodeDefinitions.map((definition) => [definition.type, definition])),
    [nodeDefinitions],
  );

  const onConnect = useCallback(
    (params: Connection) => setEdges((eds) => addEdge({ ...params, animated: true }, eds)),
    [setEdges]
  );

  const isValidConnection = useCallback((connection: Connection | Edge) => {
    if (!connection.sourceHandle || !connection.targetHandle) return true;
    const sourceNode = nodes.find((node) => node.id === connection.source);
    const targetNode = nodes.find((node) => node.id === connection.target);
    const sourceDefinition = definitionsByType.get(sourceNode?.type || '');
    const targetDefinition = definitionsByType.get(targetNode?.type || '');
    if (!sourceDefinition || !targetDefinition) return false;
    const output = sourceDefinition.outputs.find((port) => port.id === connection.sourceHandle);
    const input = targetDefinition.inputs.find((port) => port.id === connection.targetHandle);
    if (!output || !input) return false;
    return output.data_type === 'any' || input.data_type === 'any' || output.data_type === input.data_type;
  }, [definitionsByType, nodes]);

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

      const definition = definitionsByType.get(type);
      const newNode = createWorkflowNode(type, position, { label: definition?.label || type });
      setNodes((nds) => nds.concat(newNode));
    },
    [definitionsByType, setNodes]
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
        nodes: nodes.map((n) => {
          const data = { ...n.data } as Record<string, unknown>;
          delete data['executionStatus'];
          delete data['executionOutput'];
          delete data['executionError'];
          return { id: n.id, type: n.type, data, position: n.position };
        }),
        edges: edges.map((e) => ({
          id: e.id,
          source: e.source,
          target: e.target,
          sourceHandle: e.sourceHandle ?? null,
          targetHandle: e.targetHandle ?? null,
          condition: (e as any).condition,
        })),
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

  const handleRunNode = async () => {
    if (!selectedNode || !definitionsByType.has(selectedNode.type || '')) return;
    setRunningNode(true);
    setError(null);
    updateNodeData(selectedNode.id, { executionStatus: 'running', executionError: '' });
    try {
      const result = await api.runWorkflowNode({
        id: selectedNode.id,
        type: selectedNode.type,
        data: selectedNode.data as Record<string, unknown>,
        position: selectedNode.position,
      }, {});
      updateNodeData(selectedNode.id, {
        executionStatus: result.status,
        executionOutput: result.output,
        executionError: result.error,
      });
      if (result.status === 'failed') setError(result.error || '节点运行失败');
    } catch (e: any) {
      updateNodeData(selectedNode.id, { executionStatus: 'failed', executionError: e.message });
      setError(e.message || '节点运行失败');
    } finally {
      setRunningNode(false);
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
              aria-label="Run selected node"
              title="Run selected node"
              onClick={handleRunNode}
              disabled={runningNode || !selectedNode || !definitionsByType.has(selectedNode.type || '')}
              className="flex h-7 w-7 items-center justify-center text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] disabled:opacity-40"
            >
              <Play size={12} />
            </button>
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
            nodeTypes={canvasNodeTypes}
            isValidConnection={isValidConnection}
            fitView
             className="bg-[var(--color-bg-deep)]"
          >
            <Background variant={BackgroundVariant.Dots} gap={16} size={1} color="var(--color-border-default)" />
             <Controls className="!bg-[var(--color-bg-surface)] !border-[var(--color-border-subtle)] !shadow-lg [&>button]:!bg-[var(--color-bg-surface)] [&>button]:!border-[var(--color-border-subtle)] [&>button]:!text-[var(--color-text-muted)] [&>button:hover]:!bg-[var(--color-bg-surface-elevated)]/50" />
            <MiniMap
               className="!bg-[var(--color-bg-surface)] !border-[var(--color-border-subtle)]"
              nodeColor={(n) => {
                return definitionsByType.get(n.type || '')?.color || '#ef4444';
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
            {nodeDefinitions.map(({ type, label, description, color }) => {
              const Icon = getWorkflowNodeIcon(type);
              return (
              <div
                key={type}
                draggable
                onDragStart={(e) => {
                  e.dataTransfer.setData('application/reactflow', type);
                  e.dataTransfer.effectAllowed = 'move';
                }}
                className="flex items-center gap-2 px-2 py-2 rounded-lg bg-[var(--color-bg-surface-elevated)] border border-[var(--color-border-subtle)] cursor-grab hover:border-[var(--color-accent)]/30 transition-colors"
              >
                <Icon size={13} style={{ color }} />
                <div className="flex-1 min-w-0">
                   <p className="text-[11px] font-medium text-[var(--color-text-primary)]">{label}</p>
                   <p className="text-[9px] text-[var(--color-text-muted)] truncate">{description}</p>
                </div>
              </div>
              );
            })}
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
