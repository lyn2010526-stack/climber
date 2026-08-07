import { describe, it, expect, beforeEach, vi } from 'vitest';
import { useSessionsStore } from '../sessions';

vi.mock('../../api', () => ({
  api: {
    listSessions: vi.fn().mockResolvedValue([]),
    createSession: vi.fn().mockResolvedValue({ id: '1', title: 'New' }),
    deleteSession: vi.fn().mockResolvedValue({}),
    getSessionMessages: vi.fn().mockResolvedValue({ messages: [] }),
    chatStream: vi.fn().mockReturnValue(() => {}),
  },
}));

describe('useSessionsStore', () => {
  beforeEach(() => {
    useSessionsStore.setState({
      sessions: [],
      loading: false,
      error: null,
    });
  });

  it('has initial state', () => {
    const state = useSessionsStore.getState();
    expect(state.sessions).toEqual([]);
    expect(state.loading).toBe(false);
    expect(state.error).toBeNull();
  });

  it('fetchSessions updates loading state', async () => {
    await useSessionsStore.getState().fetchSessions();
    expect(useSessionsStore.getState().loading).toBe(false);
  });

  it('createSession adds session to list', async () => {
    await useSessionsStore.getState().createSession({ title: 'Test' });
    expect(useSessionsStore.getState().sessions).toHaveLength(1);
  });

  it('deleteSession removes session from list', async () => {
    await useSessionsStore.getState().createSession({ title: 'Test' });
    const id = useSessionsStore.getState().sessions[0]?.id;
    if (id) {
      await useSessionsStore.getState().deleteSession(id);
    }
    expect(useSessionsStore.getState().sessions).toHaveLength(0);
  });
});
