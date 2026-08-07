import { create } from 'zustand';
import { devtools } from 'zustand/middleware';
import {
  workflowService,
  type Workflow,
  type WorkflowExecution,
  type CreateWorkflowRequest,
  type WorkflowNode,
  type WorkflowEdge,
} from '../services/workflowService';

interface WorkflowState {
  workflows: Workflow[];
  currentWorkflow: Workflow | null;
  executions: WorkflowExecution[];
  loading: boolean;
  error: string | null;

  fetchWorkflows: () => Promise<void>;
  fetchWorkflow: (id: string) => Promise<void>;
  createWorkflow: (data: CreateWorkflowRequest) => Promise<Workflow>;
  updateWorkflow: (id: string, data: Partial<CreateWorkflowRequest>) => Promise<void>;
  deleteWorkflow: (id: string) => Promise<void>;
  executeWorkflow: (id: string, input?: Record<string, unknown>) => Promise<void>;
  stopExecution: (workflowId: string, executionId: string) => Promise<void>;
  fetchExecutions: (workflowId: string) => Promise<void>;
  updateNodes: (workflowId: string, nodes: WorkflowNode[]) => Promise<void>;
  updateEdges: (workflowId: string, edges: WorkflowEdge[]) => Promise<void>;
  validateWorkflow: (id: string) => Promise<{ valid: boolean; errors: string[] }>;
  setCurrentWorkflow: (workflow: Workflow | null) => void;
  clearError: () => void;
}

export const useWorkflowStore = create<WorkflowState>()(
  devtools(
    (set, get) => ({
      workflows: [],
      currentWorkflow: null,
      executions: [],
      loading: false,
      error: null,

      fetchWorkflows: async () => {
        set({ loading: true, error: null });
        try {
          const workflows = await workflowService.list();
          set({ workflows, loading: false });
        } catch (err) {
          set({
            error: err instanceof Error ? err.message : 'Failed to fetch workflows',
            loading: false,
          });
        }
      },

      fetchWorkflow: async (id) => {
        set({ loading: true, error: null });
        try {
          const workflow = await workflowService.get(id);
          set({ currentWorkflow: workflow, loading: false });
        } catch (err) {
          set({
            error: err instanceof Error ? err.message : 'Failed to fetch workflow',
            loading: false,
          });
        }
      },

      createWorkflow: async (data) => {
        const workflow = await workflowService.create(data);
        set((s) => ({ workflows: [workflow, ...s.workflows], currentWorkflow: workflow }));
        return workflow;
      },

      updateWorkflow: async (id, data) => {
        const workflow = await workflowService.update(id, data);
        set((s) => ({
          workflows: s.workflows.map((w) => (w.id === id ? workflow : w)),
          currentWorkflow: s.currentWorkflow?.id === id ? workflow : s.currentWorkflow,
        }));
      },

      deleteWorkflow: async (id) => {
        await workflowService.delete(id);
        set((s) => ({
          workflows: s.workflows.filter((w) => w.id !== id),
          currentWorkflow: s.currentWorkflow?.id === id ? null : s.currentWorkflow,
        }));
      },

      executeWorkflow: async (id, input) => {
        set({ loading: true, error: null });
        try {
          const execution = await workflowService.execute(id, input);
          set((s) => ({ executions: [execution, ...s.executions], loading: false }));
        } catch (err) {
          set({
            error: err instanceof Error ? err.message : 'Failed to execute workflow',
            loading: false,
          });
        }
      },

      stopExecution: async (workflowId, executionId) => {
        await workflowService.stopExecution(workflowId, executionId);
        set((s) => ({
          executions: s.executions.map((e) =>
            e.id === executionId ? { ...e, status: 'cancelled' as const } : e
          ),
        }));
      },

      fetchExecutions: async (workflowId) => {
        try {
          const executions = await workflowService.getExecutions(workflowId);
          set({ executions });
        } catch (err) {
          set({
            error: err instanceof Error ? err.message : 'Failed to fetch executions',
          });
        }
      },

      updateNodes: async (workflowId, nodes) => {
        await get().updateWorkflow(workflowId, { nodes });
      },

      updateEdges: async (workflowId, edges) => {
        await get().updateWorkflow(workflowId, { edges });
      },

      validateWorkflow: async (id) => {
        return workflowService.validate(id);
      },

      setCurrentWorkflow: (workflow) => set({ currentWorkflow: workflow }),

      clearError: () => set({ error: null }),
    }),
    { name: 'WorkflowStore' }
  )
);
