import { useEffect, useState } from 'react';
import { api } from '../api';
import { normalizeSessionStatus, useWorkspaceStore } from '../store/workspace';

export function useDefaultSession(): { sessionId: string | null; creationError: string | null } {
  const { activeSessionId, sessions, createSessionLocal } = useWorkspaceStore();
  const [creationError, setCreationError] = useState<string | null>(null);

  useEffect(() => {
    if (activeSessionId || sessions.length > 0) return;
    let cancelled = false;
    api.createSession({ title: '新对话' }).then((created) => {
      if (cancelled || !created?.id) return;
      // The status is whatever the create response reported, and the runtime
      // fields stay empty: the payload carries no model limits or usage.
      createSessionLocal({
        id: String(created.id),
        title: created.title ?? '新对话',
        status: normalizeSessionStatus(created.status),
        messages: [],
        activeSkills: [],
        activeTools: [],
        createdAt: Date.now(),
      });
    }).catch((err) => {
      if (!cancelled) setCreationError(err instanceof Error ? err.message : '无法创建默认会话');
    });
    return () => { cancelled = true; };
  }, [activeSessionId, sessions.length, createSessionLocal]);

  return { sessionId: activeSessionId ?? sessions[0]?.id ?? null, creationError };
}
