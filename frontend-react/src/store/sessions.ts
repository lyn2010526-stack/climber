import { create } from 'zustand';
import { devtools } from 'zustand/middleware';
import { api } from '../api';

interface ApiSession {
  id: string;
  title: string | null;
  status: string;
  created_at: string;
  updated_at: string;
}

interface SessionsState {
  sessions: ApiSession[];
  loading: boolean;
  error: string | null;

  fetchSessions: () => Promise<void>;
  createSession: (payload?: { title?: string; agent_id?: string }) => Promise<any>;
  deleteSession: (id: string) => Promise<void>;
}

export const useSessionsStore = create<SessionsState>()(
  devtools(
    (set) => ({
      sessions: [],
      loading: false,
      error: null,

      fetchSessions: async () => {
        set({ loading: true, error: null });
        try {
          const data = await api.listSessions();
          set({ sessions: data, loading: false });
        } catch (err) {
          set({
            error: err instanceof Error ? err.message : 'Failed to load sessions',
            loading: false,
          });
        }
      },

      createSession: async (payload?: { title?: string; agent_id?: string }) => {
        const session = await api.createSession(payload || {});
        set((s) => ({ sessions: [session, ...s.sessions] }));
        return session;
      },

      deleteSession: async (id: string) => {
        await api.deleteSession(id);
        set((s) => ({ sessions: s.sessions.filter((sess) => sess.id !== id) }));
      },
    }),
    { name: 'SessionsStore' }
  )
);
