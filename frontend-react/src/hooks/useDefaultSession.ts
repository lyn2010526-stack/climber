import { useEffect, useState } from 'react';
import { api } from '../api';
import { normalizeSessionStatus, useWorkspaceStore } from '../store/workspace';
import i18n from '../i18n/config';

let defaultSessionInFlight: Promise<void> | null = null;

export function useDefaultSession(): { sessionId: string | null; creationError: string | null } {
  const { activeSessionId, sessions, createSessionLocal } = useWorkspaceStore();
  const [creationError, setCreationError] = useState<string | null>(null);

  useEffect(() => {
    if (activeSessionId || sessions.length > 0) return;
    let cancelled = false;
    setCreationError(null);
    // Request ownership is shared; effect cleanup only detaches this consumer.
    if (!defaultSessionInFlight) {
      defaultSessionInFlight = api.createSession({ title: i18n.t('anchored.nav.default_title') }).then((created) => {
        const state = useWorkspaceStore.getState();
        if (!created?.id || state.activeSessionId || state.sessions.length > 0) return;
        // Preserve the reported status and leave unreported runtime fields empty.
        state.createSessionLocal({
          id: String(created.id),
          title: created.title ?? i18n.t('anchored.nav.default_title'),
          status: normalizeSessionStatus(created.status),
          messages: [],
          activeSkills: [],
          activeTools: [],
          createdAt: Date.now(),
        });
      }).finally(() => { defaultSessionInFlight = null; });
    }
    defaultSessionInFlight.catch((err) => {
      if (!cancelled) setCreationError(err instanceof Error ? err.message : i18n.t('anchored.nav.create_default_failed'));
    });
    return () => { cancelled = true; };
  }, [activeSessionId, sessions.length, createSessionLocal]);

  return { sessionId: activeSessionId ?? sessions[0]?.id ?? null, creationError };
}
