import { useCallback, useEffect, useState } from 'react';
import { useIsCompactDesktop } from './breakpoints';

const STORAGE_KEY = 'climber.sidebar';

function readStoredChoice(): boolean | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw === null) return null;
    return raw === '1';
  } catch {
    return null;
  }
}

export function useSidebarState() {
  const isCompact = useIsCompactDesktop();
  const [open, setOpen] = useState(() => readStoredChoice() ?? true);

  useEffect(() => {
    if (isCompact) {
      setOpen(false);
    } else {
      const stored = readStoredChoice();
      setOpen(stored ?? true);
    }
  }, [isCompact]);

  const toggle = useCallback(() => {
    setOpen((prev) => {
      const next = !prev;
      try {
        localStorage.setItem(STORAGE_KEY, next ? '1' : '0');
      } catch {
        // Storage unavailable: keep in-memory state only
      }
      return next;
    });
  }, []);

  return { open, toggle, isCompact };
}
