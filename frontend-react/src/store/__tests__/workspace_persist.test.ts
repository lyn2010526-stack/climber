import { describe, it, expect, beforeEach } from 'vitest';
import { useWorkspaceStore } from '../workspace_persist';

describe('useWorkspaceStore', () => {
  beforeEach(() => {
    useWorkspaceStore.setState({
      sessions: [],
      activeSessionId: null,
      rightPanelTab: 'config',
      rightPanelOpen: true,
      focusMode: false,
      expertMode: false,
      permissionMode: 'sandbox',
      autonomyLevel: 3,
    });
  });

  it('has initial state', () => {
    const state = useWorkspaceStore.getState();
    expect(state.sessions).toEqual([]);
    expect(state.activeSessionId).toBeNull();
    expect(state.rightPanelTab).toBe('config');
  });

  it('setActiveSession sets value', () => {
    useWorkspaceStore.getState().setActiveSession('session-1');
    expect(useWorkspaceStore.getState().activeSessionId).toBe('session-1');
  });

  it('setRightPanelTab sets tab', () => {
    useWorkspaceStore.getState().setRightPanelTab('dag');
    expect(useWorkspaceStore.getState().rightPanelTab).toBe('dag');
  });
});
