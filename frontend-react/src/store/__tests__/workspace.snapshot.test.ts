import { describe, it, expect, beforeEach } from 'vitest';
import { useWorkspaceStore, type Message, type Session } from '../workspace';

const message = (id: string): Message => ({ id, type: 'user', content: id, timestamp: 1 });

const session = (id: string, ids: string[]): Session => ({
  id,
  title: id,
  status: 'idle',
  messages: ids.map(message),
  activeSkills: [],
  activeTools: [],
  modelConfig: { provider: 'openai', modelId: 'gpt-4o', temperature: 0.7, maxTokens: 4096 },
  tokenUsage: { used: 0, limit: 200000 },
  createdAt: Date.now(),
});

beforeEach(() => {
  useWorkspaceStore.setState({ sessions: [], activeSessionId: null, snapshots: [] });
});

describe('WorkspaceStore snapshots', () => {
  it('restores a session transcript from a snapshot that recorded one', async () => {
    useWorkspaceStore.setState({
      sessions: [session('s1', ['m1', 'm2', 'm3'])],
      snapshots: [{ id: 'snap-1', sessionId: 's1', timestamp: 1, label: 'Snapshot 1', messages: [message('m1')] }],
    });

    await useWorkspaceStore.getState().restoreSnapshot('snap-1');

    expect(useWorkspaceStore.getState().sessions[0]!.messages).toEqual([message('m1')]);
  });

  it('rejects a restore it cannot perform and leaves the session untouched', async () => {
    useWorkspaceStore.setState({
      sessions: [session('s1', ['m1'])],
      snapshots: [
        { id: 'marker', sessionId: 's1', timestamp: 1, label: 'Snapshot 1' },
        { id: 'orphan', sessionId: 'gone', timestamp: 2, label: 'Snapshot 2', messages: [] },
      ],
    });

    await expect(useWorkspaceStore.getState().restoreSnapshot('missing')).rejects.toThrow('Snapshot not found');
    await expect(useWorkspaceStore.getState().restoreSnapshot('marker')).rejects.toThrow('no transcript');
    await expect(useWorkspaceStore.getState().restoreSnapshot('orphan')).rejects.toThrow('no longer exists');
    expect(useWorkspaceStore.getState().sessions[0]!.messages).toEqual([message('m1')]);
  });

  it('copies the transcript so later edits to one session cannot reach the snapshot', async () => {
    useWorkspaceStore.setState({
      sessions: [session('s1', ['m1'])],
      snapshots: [{ id: 'snap-1', sessionId: 's1', timestamp: 1, label: 'Snapshot 1', messages: [message('m1'), message('m2')] }],
    });

    await useWorkspaceStore.getState().restoreSnapshot('snap-1');
    useWorkspaceStore.getState().addMessage('s1', message('m3'));

    const state = useWorkspaceStore.getState();
    expect(state.sessions[0]!.messages.map(entry => entry.id)).toEqual(['m1', 'm2', 'm3']);
    expect(state.snapshots[0]!.messages!.map(entry => entry.id)).toEqual(['m1', 'm2']);
  });
});
