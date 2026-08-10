import { useState, useCallback, useEffect } from 'react';
import { api } from '../api';
import { useWorkspaceStore, type Session as WorkspaceSession } from '../store/workspace';

export interface Session {
  id: string;
  title: string | null;
  status: string;
  created_at: string;
  updated_at: string;
}

function toWorkspaceSession(s: Session): WorkspaceSession {
  return {
    id: s.id,
    title: s.title ?? 'Untitled',
    status: (s.status as WorkspaceSession['status']) || 'idle',
    messages: [],
    activeSkills: [],
    activeTools: [],
    modelConfig: { provider: '', modelId: '', temperature: 0, maxTokens: 0 },
    tokenUsage: { used: 0, limit: 0 },
    createdAt: Date.parse(s.created_at) || Date.now(),
  };
}

export function useSessions() {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchSessions = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.listSessions();
      setSessions(data);
      useWorkspaceStore.getState().setSessions(data.map(toWorkspaceSession));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load sessions');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchSessions();
  }, [fetchSessions]);

  const createSession = useCallback(async (payload?: { title?: string; agent_id?: string }) => {
    const session = await api.createSession(payload || {});
    await fetchSessions();
    return session;
  }, [fetchSessions]);

  const deleteSession = useCallback(async (id: string) => {
    await api.deleteSession(id);
    const next = sessions.filter(s => s.id !== id);
    setSessions(next);
    useWorkspaceStore.getState().setSessions(next.map(toWorkspaceSession));
  }, [sessions]);

  return { sessions, loading, error, createSession, deleteSession, refresh: fetchSessions };
}
