import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, act, waitFor } from '@testing-library/react';
import { useAgentMode } from '../useAgentMode';

vi.mock('../../api', () => ({
  api: {
    getSettings: vi.fn(),
    updateSettings: vi.fn(),
  },
}));

import { api } from '../../api';

const getSettings = vi.mocked(api.getSettings);
const updateSettings = vi.mocked(api.updateSettings);

describe('useAgentMode', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('loads settings on mount', async () => {
    getSettings.mockResolvedValue({
      autonomous_agent_mode: true,
      token_throttle_mcp_enabled: false,
      mcp_status: 'ready',
      mcp_ready: true,
    });
    const { result } = renderHook(() => useAgentMode());
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.mode.autonomous_agent_mode).toBe(true);
    expect(result.current.mode.mcp_status).toBe('ready');
    expect(result.current.error).toBeNull();
  });

  it('applies defaults when settings fields missing', async () => {
    getSettings.mockResolvedValue({});
    const { result } = renderHook(() => useAgentMode());
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.mode).toEqual({
      autonomous_agent_mode: false,
      token_throttle_mcp_enabled: false,
      mcp_status: 'disconnected',
      mcp_ready: false,
    });
  });

  it('sets error when settings load fails', async () => {
    getSettings.mockRejectedValue(new Error('load failed'));
    const { result } = renderHook(() => useAgentMode());
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.error).toBe('load failed');
  });

  it('toggleAutonomous updates settings and state', async () => {
    getSettings.mockResolvedValue({});
    updateSettings.mockResolvedValue({});
    const { result } = renderHook(() => useAgentMode());
    await waitFor(() => expect(result.current.loading).toBe(false));
    await act(async () => {
      await result.current.toggleAutonomous();
    });
    expect(updateSettings).toHaveBeenCalledWith({ autonomous_agent_mode: true });
    expect(result.current.mode.autonomous_agent_mode).toBe(true);
  });

  it('toggleMcp updates settings and state', async () => {
    getSettings.mockResolvedValue({});
    updateSettings.mockResolvedValue({});
    const { result } = renderHook(() => useAgentMode());
    await waitFor(() => expect(result.current.loading).toBe(false));
    await act(async () => {
      await result.current.toggleMcp();
    });
    expect(updateSettings).toHaveBeenCalledWith({ token_throttle_mcp_enabled: true });
    expect(result.current.mode.token_throttle_mcp_enabled).toBe(true);
  });

  it('toggleAutonomous records error on failure', async () => {
    getSettings.mockResolvedValue({});
    updateSettings.mockRejectedValue(new Error('update failed'));
    const { result } = renderHook(() => useAgentMode());
    await waitFor(() => expect(result.current.loading).toBe(false));
    await act(async () => {
      await result.current.toggleAutonomous();
    });
    expect(result.current.error).toBe('update failed');
    expect(result.current.mode.autonomous_agent_mode).toBe(false);
  });

  it('refresh reloads settings', async () => {
    getSettings.mockResolvedValue({ mcp_ready: true });
    const { result } = renderHook(() => useAgentMode());
    await waitFor(() => expect(result.current.loading).toBe(false));
    await act(async () => {
      await result.current.refresh();
    });
    expect(getSettings).toHaveBeenCalled();
  });
});
