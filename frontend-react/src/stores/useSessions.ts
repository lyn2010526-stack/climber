import { useState, useCallback, useEffect, useRef } from 'react';
import { api } from '../api';
import { useWorkspaceStore, type Session as WorkspaceSession } from '../store/workspace';

export interface Session {
  id: string;
  title: string | null;
  status: string;
  created_at: string;
  updated_at: string;
}

const VALID_STATUSES = ['idle', 'running', 'paused', 'completed', 'error'] as const;

function toWorkspaceSession(s: Session): WorkspaceSession {
  const rawStatus = s.status as string;
  const status = (VALID_STATUSES as readonly string[]).includes(rawStatus)
    ? rawStatus as WorkspaceSession['status']
    : 'idle';
  return {
    id: s.id,
    title: s.title ?? 'Untitled',
    status,
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
  const fetchVersionRef = useRef(0);

  const fetchSessions = useCallback(async () => {
    const version = ++fetchVersionRef.current;
    setLoading(true);
    setError(null);
    try {
      const data = await api.listSessions();
      if (version !== fetchVersionRef.current) return;
      setSessions(data);
      useWorkspaceStore.getState().setSessions(data.map(toWorkspaceSession));
    } catch (err) {
      if (version !== fetchVersionRef.current) return;
      setError(err instanceof Error ? err.message : 'Failed to load sessions');
    } finally {
      if (version === fetchVersionRef.current) setLoading(false);
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
    setSessions(prev => {
      const next = prev.filter(s => s.id !== id);
      useWorkspaceStore.getState().setSessions(next.map(toWorkspaceSession));
      return next;
    });
  }, []);

  return { sessions, loading, error, createSession, deleteSession, refresh: fetchSessions };
}
