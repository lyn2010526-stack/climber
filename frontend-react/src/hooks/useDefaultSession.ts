import { useEffect, useState } from 'react';
import { api } from '../api';
import { useWorkspaceStore } from '../store/workspace';

export function useDefaultSession(): { sessionId: string | null; creationError: string | null } {
  const { activeSessionId, sessions, createSessionLocal } = useWorkspaceStore();
  const [creationError, setCreationError] = useState<string | null>(null);

  useEffect(() => {
    if (activeSessionId || sessions.length > 0) return;
    let cancelled = false;
    api.createSession({ title: '新对话' }).then((created) => {
      if (cancelled || !created?.id) return;
      createSessionLocal({
        id: String(created.id),
        title: created.title ?? '新对话',
        status: 'idle',
        messages: [],
        activeSkills: [],
        activeTools: [],
        modelConfig: { provider: 'unknown', modelId: '', temperature: 0.7, maxTokens: 4096 },
        tokenUsage: { used: 0, limit: 200000 },
        createdAt: Date.now(),
      });
    }).catch((err) => {
      if (!cancelled) setCreationError(err instanceof Error ? err.message : '无法创建默认会话');
    });
    return () => { cancelled = true; };
  }, [activeSessionId, sessions.length, createSessionLocal]);

  return { sessionId: activeSessionId ?? sessions[0]?.id ?? null, creationError };
}
