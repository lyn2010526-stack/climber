import { create } from 'zustand';
import { devtools } from 'zustand/middleware';
import { agentService, type Agent, type AgentExecution, type CreateAgentRequest } from '../services/agentService';

interface AgentState {
  agents: Agent[];
  currentAgent: Agent | null;
  executions: AgentExecution[];
  loading: boolean;
  error: string | null;

  fetchAgents: () => Promise<void>;
  fetchAgent: (id: string) => Promise<void>;
  createAgent: (data: CreateAgentRequest) => Promise<Agent>;
  updateAgent: (id: string, data: Partial<CreateAgentRequest>) => Promise<void>;
  deleteAgent: (id: string) => Promise<void>;
  executeAgent: (agentId: string, input: string, sessionId?: string) => Promise<void>;
  stopExecution: (agentId: string, executionId: string) => Promise<void>;
  fetchExecutions: (agentId: string) => Promise<void>;
  setCurrentAgent: (agent: Agent | null) => void;
  clearError: () => void;
}

export const useAgentStore = create<AgentState>()(
  devtools(
    (set, get) => ({
      agents: [],
      currentAgent: null,
      executions: [],
      loading: false,
      error: null,

      fetchAgents: async () => {
        set({ loading: true, error: null });
        try {
          const agents = await agentService.list();
          set({ agents, loading: false });
        } catch (err) {
          set({
            error: err instanceof Error ? err.message : 'Failed to fetch agents',
            loading: false,
          });
        }
      },

      fetchAgent: async (id) => {
        set({ loading: true, error: null });
        try {
          const agent = await agentService.get(id);
          set({ currentAgent: agent, loading: false });
        } catch (err) {
          set({
            error: err instanceof Error ? err.message : 'Failed to fetch agent',
            loading: false,
          });
        }
      },

      createAgent: async (data) => {
        const agent = await agentService.create(data);
        set((s) => ({ agents: [agent, ...s.agents], currentAgent: agent }));
        return agent;
      },

      updateAgent: async (id, data) => {
        const agent = await agentService.update(id, data);
        set((s) => ({
          agents: s.agents.map((a) => (a.id === id ? agent : a)),
          currentAgent: s.currentAgent?.id === id ? agent : s.currentAgent,
        }));
      },

      deleteAgent: async (id) => {
        await agentService.delete(id);
        set((s) => ({
          agents: s.agents.filter((a) => a.id !== id),
          currentAgent: s.currentAgent?.id === id ? null : s.currentAgent,
        }));
      },

      executeAgent: async (agentId, input, sessionId) => {
        set({ loading: true, error: null });
        try {
          const execution = await agentService.execute(agentId, input, sessionId);
          set((s) => ({ executions: [execution, ...s.executions], loading: false }));
        } catch (err) {
          set({
            error: err instanceof Error ? err.message : 'Failed to execute agent',
            loading: false,
          });
        }
      },

      stopExecution: async (agentId, executionId) => {
        await agentService.stopExecution(agentId, executionId);
        set((s) => ({
          executions: s.executions.map((e) =>
            e.id === executionId ? { ...e, status: 'cancelled' as const } : e
          ),
        }));
      },

      fetchExecutions: async (agentId) => {
        try {
          const executions = await agentService.getExecutions(agentId);
          set({ executions });
        } catch (err) {
          set({
            error: err instanceof Error ? err.message : 'Failed to fetch executions',
          });
        }
      },

      setCurrentAgent: (agent) => set({ currentAgent: agent }),

      clearError: () => set({ error: null }),
    }),
    { name: 'AgentStore' }
  )
);
