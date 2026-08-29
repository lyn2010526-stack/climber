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
  const lastFetchTimeRef = useRef(0);
  const pendingFetchRef = useRef<Promise<void> | null>(null);

  const fetchSessions = useCallback(async () => {
    const now = Date.now();
    if (now - lastFetchTimeRef.current < 500 && pendingFetchRef.current) {
      return pendingFetchRef.current;
    }
    lastFetchTimeRef.current = now;

    const version = ++fetchVersionRef.current;
    const promise = (async () => {
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
    })();

    pendingFetchRef.current = promise;
    promise.finally(() => {
      if (pendingFetchRef.current === promise) {
        pendingFetchRef.current = null;
      }
    });
    return promise;
  }, []);

  useEffect(() => {
    fetchSessions();
  }, [fetchSessions]);

  const createSession = useCallback(async (payload?: {
    title?: string;
    agent_id?: string;
    model_settings?: { provider?: string; model_id?: string };
  }) => {
    const session = await api.createSession(payload || {});
    await fetchSessions();
    return session;
  }, [fetchSessions]);

  const deleteSession = useCallback(async (id: string) => {
    await api.deleteSession(id);
    try {
      setSessions(prev => {
        const next = prev.filter(s => s.id !== id);
        useWorkspaceStore.getState().setSessions(next.map(toWorkspaceSession));
        return next;
      });
    } catch {
      await fetchSessions();
    }
  }, [fetchSessions]);

  const renameSession = useCallback(async (id: string, title: string) => {
    const updated = await api.renameSession(id, title);
    setSessions(prev => {
      const next = prev.map(session => session.id === id ? { ...session, ...updated } : session);
      useWorkspaceStore.getState().setSessions(next.map(toWorkspaceSession));
      return next;
    });
    return updated;
  }, []);

  return { sessions, loading, error, createSession, deleteSession, renameSession, refresh: fetchSessions };
}
