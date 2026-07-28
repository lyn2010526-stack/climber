import { useState, useEffect, useCallback } from 'react';
import { api } from '../api';

export interface AgentModeState {
  autonomous_agent_mode: boolean;
  token_throttle_mcp_enabled: boolean;
  mcp_status: string;
  mcp_ready: boolean;
}

export function useAgentMode() {
  const [mode, setMode] = useState<AgentModeState>({
    autonomous_agent_mode: false,
    token_throttle_mcp_enabled: false,
    mcp_status: 'disconnected',
    mcp_ready: false,
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchSettings = useCallback(async () => {
    try {
      setLoading(true);
      const data = await api.getSettings();
      setMode({
        autonomous_agent_mode: data.autonomous_agent_mode || false,
        token_throttle_mcp_enabled: data.token_throttle_mcp_enabled || false,
        mcp_status: data.mcp_status || 'disconnected',
        mcp_ready: data.mcp_ready || false,
      });
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load settings');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchSettings();
  }, [fetchSettings]);

  const toggleAutonomous = useCallback(async () => {
    try {
      const newValue = !mode.autonomous_agent_mode;
      await api.updateSettings({ autonomous_agent_mode: newValue });
      setMode(prev => ({ ...prev, autonomous_agent_mode: newValue }));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update settings');
    }
  }, [mode.autonomous_agent_mode]);

  const toggleMcp = useCallback(async () => {
    try {
      const newValue = !mode.token_throttle_mcp_enabled;
      await api.updateSettings({ token_throttle_mcp_enabled: newValue });
      setMode(prev => ({ ...prev, token_throttle_mcp_enabled: newValue }));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update settings');
    }
  }, [mode.token_throttle_mcp_enabled]);

  return {
    mode,
    loading,
    error,
    toggleAutonomous,
    toggleMcp,
    refresh: fetchSettings,
  };
}
