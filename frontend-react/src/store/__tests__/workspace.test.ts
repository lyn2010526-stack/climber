import { describe, it, expect, beforeEach } from 'vitest';
import { useWorkspaceStore } from '../workspace';

describe('WorkspaceStore', () => {
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
      tasks: [],
      snapshots: [],
    });
  });

  it('initial state is correct', () => {
    const state = useWorkspaceStore.getState();
    expect(state.sessions).toEqual([]);
    expect(state.activeSessionId).toBeNull();
    expect(state.rightPanelTab).toBe('config');
    expect(state.rightPanelOpen).toBe(true);
    expect(state.focusMode).toBe(false);
    expect(state.expertMode).toBe(false);
    expect(state.permissionMode).toBe('sandbox');
    expect(state.autonomyLevel).toBe(3);
  });

  it('setActiveSession sets the active session', () => {
    useWorkspaceStore.getState().setActiveSession('s1');
    expect(useWorkspaceStore.getState().activeSessionId).toBe('s1');
  });

  it('setRightPanelTab sets tab and opens panel', () => {
    useWorkspaceStore.setState({ rightPanelOpen: false });
    useWorkspaceStore.getState().setRightPanelTab('diff');
    expect(useWorkspaceStore.getState().rightPanelTab).toBe('diff');
    expect(useWorkspaceStore.getState().rightPanelOpen).toBe(true);
  });

  it('toggleRightPanel toggles open state', () => {
    const initial = useWorkspaceStore.getState().rightPanelOpen;
    useWorkspaceStore.getState().toggleRightPanel();
    expect(useWorkspaceStore.getState().rightPanelOpen).toBe(!initial);
  });

  it('toggleFocusMode toggles focus', () => {
    const initial = useWorkspaceStore.getState().focusMode;
    useWorkspaceStore.getState().toggleFocusMode();
    expect(useWorkspaceStore.getState().focusMode).toBe(!initial);
  });

  it('toggleExpertMode toggles expert', () => {
    const initial = useWorkspaceStore.getState().expertMode;
    useWorkspaceStore.getState().toggleExpertMode();
    expect(useWorkspaceStore.getState().expertMode).toBe(!initial);
  });

  it('setPermissionMode sets mode', () => {
    useWorkspaceStore.getState().setPermissionMode('native');
    expect(useWorkspaceStore.getState().permissionMode).toBe('native');
  });

  it('setAutonomyLevel sets level', () => {
    useWorkspaceStore.getState().setAutonomyLevel(5);
    expect(useWorkspaceStore.getState().autonomyLevel).toBe(5);
  });

  it('setTasks sets tasks', () => {
    const tasks = [{ id: 't1', description: 'Task 1', status: 'pending' as const }];
    useWorkspaceStore.getState().setTasks(tasks);
    expect(useWorkspaceStore.getState().tasks).toEqual(tasks);
  });

  it('createSession adds session and sets active', () => {
    const session = {
      id: 's1',
      title: 'Test',
      status: 'idle' as const,
      messages: [],
      activeSkills: [],
      activeTools: [],
      modelConfig: { provider: 'openai', modelId: 'gpt-4', temperature: 0.7, maxTokens: 4096 },
      tokenUsage: { used: 0, limit: 100000 },
      createdAt: Date.now(),
    };
    useWorkspaceStore.getState().createSession(session);
    const state = useWorkspaceStore.getState();
    expect(state.sessions.length).toBe(1);
    expect(state.activeSessionId).toBe('s1');
  });

  it('deleteSession removes session', () => {
    const session = {
      id: 's1',
      title: 'Test',
      status: 'idle' as const,
      messages: [],
      activeSkills: [],
      activeTools: [],
      modelConfig: { provider: 'openai', modelId: 'gpt-4', temperature: 0.7, maxTokens: 4096 },
      tokenUsage: { used: 0, limit: 100000 },
      createdAt: Date.now(),
    };
    useWorkspaceStore.getState().createSession(session);
    useWorkspaceStore.getState().deleteSession('s1');
    expect(useWorkspaceStore.getState().sessions.length).toBe(0);
    expect(useWorkspaceStore.getState().activeSessionId).toBeNull();
  });

  it('deleteSession keeps activeSessionId if different', () => {
    const s1 = {
      id: 's1',
      title: 'A',
      status: 'idle' as const,
      messages: [],
      activeSkills: [],
      activeTools: [],
      modelConfig: { provider: 'openai', modelId: 'gpt-4', temperature: 0.7, maxTokens: 4096 },
      tokenUsage: { used: 0, limit: 100000 },
      createdAt: Date.now(),
    };
    const s2 = {
      id: 's2',
      title: 'B',
      status: 'idle' as const,
      messages: [],
      activeSkills: [],
      activeTools: [],
      modelConfig: { provider: 'openai', modelId: 'gpt-4', temperature: 0.7, maxTokens: 4096 },
      tokenUsage: { used: 0, limit: 100000 },
      createdAt: Date.now(),
    };
    useWorkspaceStore.getState().createSession(s1);
    useWorkspaceStore.getState().createSession(s2);
    useWorkspaceStore.getState().deleteSession('s1');
    expect(useWorkspaceStore.getState().activeSessionId).toBe('s2');
  });

  it('addMessage adds message to session', () => {
    const s1 = {
      id: 's1',
      title: 'A',
      status: 'idle' as const,
      messages: [],
      activeSkills: [],
      activeTools: [],
      modelConfig: { provider: 'openai', modelId: 'gpt-4', temperature: 0.7, maxTokens: 4096 },
      tokenUsage: { used: 0, limit: 100000 },
      createdAt: Date.now(),
    };
    useWorkspaceStore.getState().createSession(s1);
    useWorkspaceStore.getState().addMessage('s1', { id: 'm1', type: 'user' as const, content: 'hello', timestamp: Date.now() });
    expect(useWorkspaceStore.getState().sessions[0]?.messages.length).toBe(1);
  });

  it('addMessage updates existing message', () => {
    const s1 = {
      id: 's1',
      title: 'A',
      status: 'idle' as const,
      messages: [{ id: 'm1', type: 'user' as const, content: 'old', timestamp: Date.now() }],
      activeSkills: [],
      activeTools: [],
      modelConfig: { provider: 'openai', modelId: 'gpt-4', temperature: 0.7, maxTokens: 4096 },
      tokenUsage: { used: 0, limit: 100000 },
      createdAt: Date.now(),
    };
    useWorkspaceStore.getState().createSession(s1);
    useWorkspaceStore.getState().addMessage('s1', { id: 'm1', type: 'user' as const, content: 'new', timestamp: Date.now() });
    expect(useWorkspaceStore.getState().sessions[0]?.messages[0]?.content).toBe('new');
  });

  it('updateSession updates session fields', () => {
    const s1 = {
      id: 's1',
      title: 'A',
      status: 'idle' as const,
      messages: [],
      activeSkills: [],
      activeTools: [],
      modelConfig: { provider: 'openai', modelId: 'gpt-4', temperature: 0.7, maxTokens: 4096 },
      tokenUsage: { used: 0, limit: 100000 },
      createdAt: Date.now(),
    };
    useWorkspaceStore.getState().createSession(s1);
    useWorkspaceStore.getState().updateSession('s1', { title: 'Updated' });
    expect(useWorkspaceStore.getState().sessions[0]?.title).toBe('Updated');
  });

  it('addSnapshot adds snapshot', () => {
    useWorkspaceStore.getState().addSnapshot({ id: 'snap1', sessionId: 's1', timestamp: Date.now(), label: 'test' });
    expect(useWorkspaceStore.getState().snapshots.length).toBe(1);
  });
});
