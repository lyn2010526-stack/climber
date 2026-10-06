import { useCallback, useState } from 'react';

const keyFor = (sessionId: string) => `climber:session-draft:${encodeURIComponent(sessionId)}`;

function readDraft(sessionId: string | null): string {
  if (!sessionId) return '';
  try {
    return localStorage.getItem(keyFor(sessionId)) ?? '';
  } catch {
    return '';
  }
}

/** Persist text only; browser attachment payloads never enter storage. */
export function useSessionDraft(sessionId: string | null) {
  const [draft, setDraft] = useState(() => ({ sessionId, text: readDraft(sessionId), error: null as string | null }));
  if (draft.sessionId !== sessionId) {
    setDraft({ sessionId, text: readDraft(sessionId), error: null });
  }
  const setText = useCallback((text: string) => {
    let error: string | null = null;
    if (sessionId) {
      try {
        localStorage.setItem(keyFor(sessionId), text);
      } catch {
        error = '草稿暂存失败，当前文字仍保留在输入框中。';
      }
    }
    setDraft({ sessionId, text, error });
  }, [sessionId]);
  return { text: draft.sessionId === sessionId ? draft.text : readDraft(sessionId), setText, storageError: draft.error };
}
