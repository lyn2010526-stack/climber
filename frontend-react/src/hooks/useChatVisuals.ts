import { useCallback, useState } from 'react';

/**
 * Chat transcript display preferences: whether tool-call cards and the
 * thinking block render in the message stream. Both default to on, and the
 * choice persists in localStorage (`'1'/'0'` per flag) — the same storage
 * discipline `useSidebarState` uses. The backend user-settings API accepts
 * only autonomous-agent/throttle/notifications fields, so a purely local
 * display preference belongs here and nowhere else.
 */

const STORAGE_KEY = 'climber.chat.visuals';

export interface ChatVisuals {
  showToolCalls: boolean;
  showThinking: boolean;
}

const DEFAULT_VISUALS: ChatVisuals = { showToolCalls: true, showThinking: true };

function readStoredVisuals(): ChatVisuals {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw === null) return { ...DEFAULT_VISUALS };
    const parsed = JSON.parse(raw) as Partial<ChatVisuals> | null;
    if (!parsed || typeof parsed !== 'object') return { ...DEFAULT_VISUALS };
    return {
      showToolCalls: typeof parsed.showToolCalls === 'boolean' ? parsed.showToolCalls : true,
      showThinking: typeof parsed.showThinking === 'boolean' ? parsed.showThinking : true,
    };
  } catch {
    return { ...DEFAULT_VISUALS };
  }
}

function writeStoredVisuals(visuals: ChatVisuals): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(visuals));
  } catch {
    // Storage unavailable: keep in-memory state only
  }
}

export function useChatVisuals(): {
  visuals: ChatVisuals;
  setShowToolCalls: (value: boolean) => void;
  setShowThinking: (value: boolean) => void;
} {
  const [visuals, setVisuals] = useState<ChatVisuals>(readStoredVisuals);

  const update = useCallback((patch: Partial<ChatVisuals>) => {
    setVisuals((prev) => {
      const next = { ...prev, ...patch };
      writeStoredVisuals(next);
      return next;
    });
  }, []);

  const setShowToolCalls = useCallback((value: boolean) => {
    update({ showToolCalls: value });
  }, [update]);

  const setShowThinking = useCallback((value: boolean) => {
    update({ showThinking: value });
  }, [update]);

  return { visuals, setShowToolCalls, setShowThinking };
}
