import { useState, useCallback, useEffect } from 'react';
import { api } from '../api';

export interface Session {
  id: string;
  title: string | null;
  status: string;
  created_at: string;
  updated_at: string;
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
    setSessions(prev => prev.filter(s => s.id !== id));
  }, []);

  return { sessions, loading, error, createSession, deleteSession, refresh: fetchSessions };
}
