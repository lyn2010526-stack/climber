import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import { devtools } from 'zustand/middleware';
import { mcpService } from '../services/mcpService';

interface AgentModeSettings {
  autonomous_agent_mode: boolean;
  token_throttle_mcp_enabled: boolean;
  mcp_status: string;
  mcp_ready: boolean;
}

interface UISettings {
  language: string;
  compact_mode: boolean;
  animations_enabled: boolean;
  sound_enabled: boolean;
  font_size: 'small' | 'medium' | 'large';
}

interface ModelSettings {
  default_provider: string;
  default_model: string;
  temperature: number;
  max_tokens: number;
  stream_response: boolean;
}

interface NotificationSettings {
  desktop_enabled: boolean;
  sound_enabled: boolean;
  error_alerts: boolean;
  completion_notifications: boolean;
}

interface SettingsState {
  agent: AgentModeSettings;
  ui: UISettings;
  model: ModelSettings;
  notifications: NotificationSettings;
  loading: boolean;
  error: string | null;

  fetchSettings: () => Promise<void>;
  updateAgentSettings: (updates: Partial<AgentModeSettings>) => Promise<void>;
  updateUISettings: (updates: Partial<UISettings>) => void;
  updateModelSettings: (updates: Partial<ModelSettings>) => void;
  updateNotificationSettings: (updates: Partial<NotificationSettings>) => void;
  toggleAutonomous: () => Promise<void>;
  toggleMcp: () => Promise<void>;
  refreshMcpStatus: () => Promise<void>;
  resetSettings: () => void;
  clearError: () => void;
}

const defaultAgent: AgentModeSettings = {
  autonomous_agent_mode: false,
  token_throttle_mcp_enabled: false,
  mcp_status: 'disconnected',
  mcp_ready: false,
};

const defaultUI: UISettings = {
  language: 'zh-CN',
  compact_mode: false,
  animations_enabled: true,
  sound_enabled: false,
  font_size: 'medium',
};

const defaultModel: ModelSettings = {
  default_provider: 'openai',
  default_model: 'gpt-4',
  temperature: 0.7,
  max_tokens: 4096,
  stream_response: true,
};

const defaultNotifications: NotificationSettings = {
  desktop_enabled: true,
  sound_enabled: false,
  error_alerts: true,
  completion_notifications: true,
};

export const useSettingsStore = create<SettingsState>()(
  devtools(
    persist(
      (set, get) => ({
        agent: defaultAgent,
        ui: defaultUI,
        model: defaultModel,
        notifications: defaultNotifications,
        loading: false,
        error: null,

        fetchSettings: async () => {
          set({ loading: true, error: null });
          try {
            const status = await mcpService.getStatus();
            set((s) => ({
              agent: {
                ...s.agent,
                mcp_status: status.status,
                mcp_ready: status.ready,
              },
              loading: false,
            }));
          } catch (err) {
            set({
              error: err instanceof Error ? err.message : 'Failed to load settings',
              loading: false,
            });
          }
        },

        updateAgentSettings: async (updates) => {
          set((s) => ({ agent: { ...s.agent, ...updates } }));
        },

        updateUISettings: (updates) => {
          set((s) => ({ ui: { ...s.ui, ...updates } }));
        },

        updateModelSettings: (updates) => {
          set((s) => ({ model: { ...s.model, ...updates } }));
        },

        updateNotificationSettings: (updates) => {
          set((s) => ({ notifications: { ...s.notifications, ...updates } }));
        },

        toggleAutonomous: async () => {
          const current = get().agent.autonomous_agent_mode;
          await get().updateAgentSettings({ autonomous_agent_mode: !current });
        },

        toggleMcp: async () => {
          const current = get().agent.token_throttle_mcp_enabled;
          await get().updateAgentSettings({ token_throttle_mcp_enabled: !current });
        },

        refreshMcpStatus: async () => {
          try {
            const status = await mcpService.getStatus();
            set((s) => ({
              agent: { ...s.agent, mcp_status: status.status, mcp_ready: status.ready },
            }));
          } catch (err) {
            set({
              error: err instanceof Error ? err.message : 'Failed to refresh MCP status',
            });
          }
        },

        resetSettings: () => {
          set({
            agent: defaultAgent,
            ui: defaultUI,
            model: defaultModel,
            notifications: defaultNotifications,
          });
        },

        clearError: () => set({ error: null }),
      }),
      {
        name: 'climber-settings',
        storage: createJSONStorage(() => localStorage),
        partialize: (state) => ({
          agent: state.agent,
          ui: state.ui,
          model: state.model,
          notifications: state.notifications,
        }),
      }
    ),
    { name: 'SettingsStore' }
  )
);
