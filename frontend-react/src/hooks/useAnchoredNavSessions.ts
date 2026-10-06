import { useRef, useState } from 'react';
import { api } from '../api';
import { sessionFromBackend, useWorkspaceStore } from '../store/workspace';
import { useI18n } from '../i18n';

export function useAnchoredNavSessions() {
  const { t } = useI18n();
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const inFlight = useRef(false);

  const createSession = async () => {
    if (inFlight.current) return;
    inFlight.current = true;
    setBusy(true);
    setError(null);
    try {
      const created = await api.createSession({ title: t('anchored.nav.default_title') });
      if (!created?.id) throw new Error(t('anchored.nav.missing_session_id'));
      const state = useWorkspaceStore.getState();
      state.createSessionLocal(sessionFromBackend({
        ...created,
        id: String(created.id),
        title: created.title ?? null,
        status: created.status ?? '',
      }));
      state.setActiveSession(String(created.id));
    } catch (cause) {
      setError(t('anchored.nav.create_failed', { reason: cause instanceof Error ? cause.message : t('anchored.nav.retry_later') }));
    } finally {
      inFlight.current = false;
      setBusy(false);
    }
  };

  const goHome = () => {
    const state = useWorkspaceStore.getState();
    const existing = state.sessions.find((session) => session.id === state.activeSessionId)
      ?? state.sessions[0];
    if (existing) state.setActiveSession(existing.id);
    // Empty-workspace initialization belongs to useDefaultSession.
  };

  const removeSession = async (sessionId: string) => {
    if (inFlight.current) return;
    const session = useWorkspaceStore.getState().sessions.find((item) => item.id === sessionId);
    if (!session || !window.confirm(t('anchored.nav.delete_confirm', { title: session.title ?? t('anchored.nav.default_title') }))) return;
    inFlight.current = true;
    setBusy(true);
    setError(null);
    try {
      await api.deleteSession(sessionId);
      useWorkspaceStore.getState().deleteSession(sessionId);
      const state = useWorkspaceStore.getState();
      const [first] = state.sessions;
      if (!state.activeSessionId && first) state.setActiveSession(first.id);
    } catch (cause) {
      setError(t('anchored.nav.delete_failed', { reason: cause instanceof Error ? cause.message : t('anchored.nav.retry_later') }));
    } finally {
      inFlight.current = false;
      setBusy(false);
    }
  };

  return { error, busy, createSession, goHome, removeSession };
}
