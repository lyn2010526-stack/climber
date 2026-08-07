import { describe, it, expect, vi, beforeEach } from 'vitest';
import { useSettingsStore } from '../settings';

vi.mock('../../lib/api-client', () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
    stream: vi.fn(),
  },
}));

import { apiClient } from '../../lib/api-client';

describe('useSettingsStore', () => {
  beforeEach(() => {
    useSettingsStore.setState({
      agent: {
        autonomous_agent_mode: false,
        token_throttle_mcp_enabled: false,
        mcp_status: 'disconnected',
        mcp_ready: false,
      },
      loading: false,
      error: null,
    });
    vi.clearAllMocks();
  });

  it('has default state', () => {
    const state = useSettingsStore.getState();
    expect(state.agent.autonomous_agent_mode).toBe(false);
    expect(state.agent.token_throttle_mcp_enabled).toBe(false);
    expect(state.agent.mcp_status).toBe('disconnected');
    expect(state.agent.mcp_ready).toBe(false);
    expect(state.loading).toBe(false);
    expect(state.error).toBeNull();
  });

  it('fetches settings successfully', async () => {
    (apiClient.get as any).mockResolvedValue({
      status: 'connected',
      ready: true,
      servers: 2,
    });

    await useSettingsStore.getState().fetchSettings();
    const state = useSettingsStore.getState();
    expect(state.agent.mcp_status).toBe('connected');
    expect(state.agent.mcp_ready).toBe(true);
    expect(state.loading).toBe(false);
  });

  it('handles fetch error', async () => {
    (apiClient.get as any).mockRejectedValue(new Error('Network error'));

    await useSettingsStore.getState().fetchSettings();
    const state = useSettingsStore.getState();
    expect(state.error).toBe('Network error');
    expect(state.loading).toBe(false);
  });

  it('toggles autonomous mode on', async () => {
    await useSettingsStore.getState().toggleAutonomous();
    const state = useSettingsStore.getState();
    expect(state.agent.autonomous_agent_mode).toBe(true);
  });

  it('toggles autonomous mode off', async () => {
    await useSettingsStore.getState().toggleAutonomous();
    await useSettingsStore.getState().toggleAutonomous();
    const state = useSettingsStore.getState();
    expect(state.agent.autonomous_agent_mode).toBe(false);
  });

  it('toggles MCP on', async () => {
    await useSettingsStore.getState().toggleMcp();
    const state = useSettingsStore.getState();
    expect(state.agent.token_throttle_mcp_enabled).toBe(true);
  });

  it('toggles MCP off', async () => {
    await useSettingsStore.getState().toggleMcp();
    await useSettingsStore.getState().toggleMcp();
    const state = useSettingsStore.getState();
    expect(state.agent.token_throttle_mcp_enabled).toBe(false);
  });

  it('refreshMcpStatus calls getStatus', async () => {
    (apiClient.get as any).mockResolvedValue({
      status: 'connected',
      ready: true,
    });

    await useSettingsStore.getState().refreshMcpStatus();
    const state = useSettingsStore.getState();
    expect(state.agent.mcp_status).toBe('connected');
    expect(state.agent.mcp_ready).toBe(true);
  });

  it('handles non-Error exception in fetchSettings', async () => {
    (apiClient.get as any).mockRejectedValue('string error');

    await useSettingsStore.getState().fetchSettings();
    const state = useSettingsStore.getState();
    expect(state.error).toBe('Failed to load settings');
  });

  it('resetSettings resets to defaults', async () => {
    await useSettingsStore.getState().toggleAutonomous();
    useSettingsStore.getState().resetSettings();
    const state = useSettingsStore.getState();
    expect(state.agent.autonomous_agent_mode).toBe(false);
  });
});
