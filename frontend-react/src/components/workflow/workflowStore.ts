import { create } from 'zustand';
import { immer } from 'zustand/middleware/immer';
import type { Node, Edge } from '@xyflow/react';

export type NodeExecutionStatus = 'idle' | 'waiting' | 'running' | 'success' | 'error' | 'disabled';

interface WorkflowHistory {
  nodes: Node[];
  edges: Edge[];
}

interface WorkflowStore {
  nodes: Node[];
  edges: Edge[];
  selectedNodeId: string | null;
  nodeStatuses: Record<string, NodeExecutionStatus>;
  debugging: boolean;
  breakpoints: Set<string>;
  executionLog: Array<{ nodeId: string; status: string; timestamp: number; message?: string }>;

  history: WorkflowHistory[];
  historyIndex: number;

  setNodes: (nodes: Node[]) => void;
  setEdges: (edges: Edge[]) => void;
  addNode: (node: Node) => void;
  removeNode: (nodeId: string) => void;
  updateNodeData: (nodeId: string, data: Record<string, any>) => void;
  setSelectedNode: (nodeId: string | null) => void;
  setNodeStatus: (nodeId: string, status: NodeExecutionStatus) => void;
  toggleBreakpoint: (nodeId: string) => void;
  setDebugging: (enabled: boolean) => void;
  addExecutionLog: (entry: { nodeId: string; status: string; message?: string }) => void;
  clearExecutionLog: () => void;

  undo: () => void;
  redo: () => void;
  pushHistory: () => void;

  importWorkflow: (nodes: Node[], edges: Edge[]) => void;
  exportWorkflow: () => { nodes: Node[]; edges: Edge[] };
}

export const useWorkflowStore = create<WorkflowStore>()(
  immer((set, get) => ({
    nodes: [],
    edges: [],
    selectedNodeId: null,
    nodeStatuses: {},
    debugging: false,
    breakpoints: new Set(),
    executionLog: [],

    history: [{ nodes: [], edges: [] }],
    historyIndex: 0,

    setNodes: (nodes) => {
      set((state) => {
        state.nodes = nodes;
      });
      get().pushHistory();
    },

    setEdges: (edges) => {
      set((state) => {
        state.edges = edges;
      });
      get().pushHistory();
    },

    addNode: (node) => {
      set((state) => {
        state.nodes.push(node);
      });
      get().pushHistory();
    },

    removeNode: (nodeId) => {
      set((state) => {
        state.nodes = state.nodes.filter((n: Node) => n.id !== nodeId);
        state.edges = state.edges.filter((e: Edge) => e.source !== nodeId && e.target !== nodeId);
        if (state.selectedNodeId === nodeId) state.selectedNodeId = null;
        delete state.nodeStatuses[nodeId];
      });
      get().pushHistory();
    },

    updateNodeData: (nodeId, data) => {
      set((state) => {
        const node = state.nodes.find((n: Node) => n.id === nodeId);
        if (node) {
          node.data = { ...node.data, ...data };
        }
      });
    },

    setSelectedNode: (nodeId) => {
      set((state) => {
        state.selectedNodeId = nodeId;
      });
    },

    setNodeStatus: (nodeId, status) => {
      set((state) => {
        state.nodeStatuses[nodeId] = status;
      });
    },

    toggleBreakpoint: (nodeId) => {
      set((state) => {
        if (state.breakpoints.has(nodeId)) {
          state.breakpoints.delete(nodeId);
        } else {
          state.breakpoints.add(nodeId);
        }
      });
    },

    setDebugging: (enabled) => {
      set((state) => {
        state.debugging = enabled;
      });
    },

    addExecutionLog: (entry) => {
      set((state) => {
        state.executionLog.push({ ...entry, timestamp: Date.now() });
      });
    },

    clearExecutionLog: () => {
      set((state) => {
        state.executionLog = [];
      });
    },

    pushHistory: () => {
      set((state) => {
        const newHistory = state.history.slice(0, state.historyIndex + 1);
        newHistory.push({
          nodes: JSON.parse(JSON.stringify(state.nodes)),
          edges: JSON.parse(JSON.stringify(state.edges)),
        });
        if (newHistory.length > 50) newHistory.shift();
        state.history = newHistory;
        state.historyIndex = newHistory.length - 1;
      });
    },

    undo: () => {
      const { historyIndex, history } = get();
      if (historyIndex > 0) {
        const prev = history[historyIndex - 1]!;
        set((state) => {
          state.nodes = JSON.parse(JSON.stringify(prev.nodes));
          state.edges = JSON.parse(JSON.stringify(prev.edges));
          state.historyIndex = historyIndex - 1;
        });
      }
    },

    redo: () => {
      const { historyIndex, history } = get();
      if (historyIndex < history.length - 1) {
        const next = history[historyIndex + 1]!;
        set((state) => {
          state.nodes = JSON.parse(JSON.stringify(next.nodes));
          state.edges = JSON.parse(JSON.stringify(next.edges));
          state.historyIndex = historyIndex + 1;
        });
      }
    },

    importWorkflow: (nodes, edges) => {
      set((state) => {
        state.nodes = nodes;
        state.edges = edges;
        state.nodeStatuses = {};
        state.executionLog = [];
      });
      get().pushHistory();
    },

    exportWorkflow: () => {
      const { nodes, edges } = get();
      return { nodes: JSON.parse(JSON.stringify(nodes)), edges: JSON.parse(JSON.stringify(edges)) };
    },
  }))
);
