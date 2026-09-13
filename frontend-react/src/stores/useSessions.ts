/**
 * Thin wrapper over the workspace store session API.
 *
 * Historical note: the workspace session list used to live here as local
 * React state, which caused the store's `sessions` to go out of sync.
 * The backend / workspace store are now the single source of truth; the
 * `Session` type and hook below simply delegate to useWorkspaceStore.
 */
import { useEffect, useCallback } from 'react';
import {
  useWorkspaceStore,
  type ApiSession,
  type Session,
} from '../store/workspace';
import { api } from '../api';

export type { ApiSession, Session };

export function useSessions() {
  const sessions = useWorkspaceStore((s) => s.sessions);
  const loading = useWorkspaceStore((s) => s.loadingSessions);
  const loaded = useWorkspaceStore((s) => s.sessionsLoaded);
  const loadSessions = useWorkspaceStore((s) => s.loadSessions);
  const setSessionsLoading = useWorkspaceStore((s) => s.setSessionsLoading);
  const deleteSession = useWorkspaceStore((s) => s.deleteSession);

  const fetchSessions = useCallback(async () => {
    setSessionsLoading(true);
    try {
      const data = (await api.listSessions()) as ApiSession[];
      loadSessions(Array.isArray(data) ? data : []);
    } catch {
      setSessionsLoading(false);
    }
  }, [loadSessions, setSessionsLoading]);

  useEffect(() => {
    if (!loaded) fetchSessions();
  }, [loaded, fetchSessions]);

  const refresh = fetchSessions;

  const removeSession = useCallback(async (id: string) => {
    await api.deleteSession(id);
    deleteSession(id);
    await fetchSessions();
  }, [deleteSession, fetchSessions]);

  return {
    sessions,
    loading,
    error: null as string | null,
    deleteSession: removeSession,
    refresh,
  };
}
