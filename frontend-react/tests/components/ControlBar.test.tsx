import { describe, expect, it, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { ControlBar } from '@/components/workspace/ControlBar';
import { useWorkspaceStore } from '@/store/workspace';

const initialState = () => useWorkspaceStore.setState({
  sessions: [],
  activeSessionId: null,
  rightPanelOpen: false,
  rightPanelTab: 'toolcalls',
  focusMode: false,
  expertMode: false,
  permissionMode: 'sandbox',
  autonomyLevel: 3,
  snapshots: [],
});

describe('ControlBar', () => {
  beforeEach(() => {
    initialState();
    vi.clearAllMocks();
  });

  it('calls onToggleSessions when the toggle button is clicked', () => {
    const onToggleSessions = vi.fn();
    render(<ControlBar onToggleSessions={onToggleSessions} />);
    fireEvent.click(screen.getByTitle('会话列表'));
    expect(onToggleSessions).toHaveBeenCalledTimes(1);
  });

  it('does not throw when computing tokenRatio with limit=0', () => {
    useWorkspaceStore.setState({
      sessions: [
        {
          id: 's1', title: 's1', status: 'running', messages: [], activeSkills: [], activeTools: [],
          modelConfig: { provider: '', modelId: '', temperature: 0, maxTokens: 0 },
          tokenUsage: { used: 10, limit: 0 }, createdAt: Date.now(),
        },
      ],
      activeSessionId: 's1',
    });
    expect(() => render(<ControlBar />)).not.toThrow();
    expect(screen.getByText('0%')).toBeDefined();
  });

  it('handleSnapshot creates a snapshot with unique id', () => {
    useWorkspaceStore.setState({
      sessions: [
        {
          id: 's1', title: 's1', status: 'running', messages: [], activeSkills: [], activeTools: [],
          modelConfig: { provider: '', modelId: '', temperature: 0, maxTokens: 0 },
          tokenUsage: { used: 10, limit: 100 }, createdAt: Date.now(),
        },
      ],
      activeSessionId: 's1',
      snapshots: [],
    });
    render(<ControlBar />);
    fireEvent.click(screen.getByTitle('保存快照'));
    const { snapshots } = useWorkspaceStore.getState();
    expect(snapshots).toHaveLength(1);
    expect(snapshots[0].sessionId).toBe('s1');
    expect(snapshots[0].id).toMatch(/^snap-/);
  });

  it('handleRollback calls updateSession when snapshots exist', () => {
    const activeSessionId = 's1';
    useWorkspaceStore.setState({
      sessions: [
        {
          id: activeSessionId, title: 's1', status: 'running', messages: [], activeSkills: [], activeTools: [],
          modelConfig: { provider: '', modelId: '', temperature: 0, maxTokens: 0 },
          tokenUsage: { used: 10, limit: 100 }, createdAt: Date.now(),
        },
      ],
      activeSessionId,
      snapshots: [{ id: 'snap-1', sessionId: activeSessionId, timestamp: Date.now(), label: 'Snapshot 1' }],
    });
    render(<ControlBar />);
    fireEvent.click(screen.getByTitle('回滚到快照'));
    const session = useWorkspaceStore.getState().sessions.find(s => s.id === activeSessionId);
    expect(session?.status).toBe('idle');
  });

  it('pause/resume button toggles paused status while stop sets completed', () => {
    const activeSessionId = 's1';
    useWorkspaceStore.setState({
      sessions: [
        {
          id: activeSessionId, title: 's1', status: 'running', messages: [], activeSkills: [], activeTools: [],
          modelConfig: { provider: '', modelId: '', temperature: 0, maxTokens: 0 },
          tokenUsage: { used: 10, limit: 100 }, createdAt: Date.now(),
        },
      ],
      activeSessionId,
    });
    render(<ControlBar />);
    fireEvent.click(screen.getByTitle('暂停'));
    expect(useWorkspaceStore.getState().sessions[0].status).toBe('paused');
    fireEvent.click(screen.getByTitle('继续'));
    expect(useWorkspaceStore.getState().sessions[0].status).toBe('running');
    fireEvent.click(screen.getByTitle('停止'));
    expect(useWorkspaceStore.getState().sessions[0].status).toBe('completed');
  });
});
