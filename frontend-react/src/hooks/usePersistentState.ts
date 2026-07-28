import { useState, useEffect, useRef, useCallback } from 'react';

const STORAGE_PREFIX = 'agent_engine_';

export function usePersistentState<T>(
  key: string,
  initialValue: T,
  options?: { ttl?: number; serialize?: (v: T) => string; deserialize?: (s: string) => T }
): [T, (v: T | ((prev: T) => T)) => void] {
  const storageKey = STORAGE_PREFIX + key;
  const ttl = options?.ttl ?? 0;

  const readValue = useCallback((): T => {
    try {
      const raw = localStorage.getItem(storageKey);
      if (!raw) return initialValue;

      const parsed = JSON.parse(raw);

      if (ttl > 0 && parsed._ts) {
        if (Date.now() - parsed._ts > ttl) {
          localStorage.removeItem(storageKey);
          return initialValue;
        }
        return parsed.v;
      }

      return parsed.v ?? parsed;
    } catch {
      return initialValue;
    }
  }, [storageKey, ttl, initialValue]);

  const [state, setState] = useState<T>(readValue);

  useEffect(() => {
    const handler = (e: StorageEvent) => {
      if (e.key === storageKey) {
        setState(readValue());
      }
    };
    window.addEventListener('storage', handler);
    return () => window.removeEventListener('storage', handler);
  }, [storageKey, readValue]);

  const setValue = useCallback((value: T | ((prev: T) => T)) => {
    setState(prev => {
      const next = typeof value === 'function' ? (value as (prev: T) => T)(prev) : value;
      try {
        const payload = ttl > 0 ? { v: next, _ts: Date.now() } : next;
        localStorage.setItem(storageKey, JSON.stringify(payload));
      } catch {
        // storage full or unavailable
      }
      return next;
    });
  }, [storageKey, ttl]);

  return [state, setValue];
}

export function useSessionRecovery(key: string): { restore: () => void; clear: () => void } {
  const sessionKey = STORAGE_PREFIX + 'session_' + key;
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    const save = () => {
      try {
        const state = {
          timestamp: Date.now(),
          data: (window as any).__session_state?.[key],
        };
        sessionStorage.setItem(sessionKey, JSON.stringify(state));
      } catch { /* skip */ }
    };

    timerRef.current = setInterval(save, 5000);

    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [key, sessionKey]);

  const restore = useCallback(() => {
    try {
      const raw = sessionStorage.getItem(sessionKey);
      if (!raw) return false;
      const parsed = JSON.parse(raw);
      if (Date.now() - parsed.timestamp > 30_000) {
        sessionStorage.removeItem(sessionKey);
        return false;
      }
      return true;
    } catch {
      return false;
    }
  }, [sessionKey]);

  const clear = useCallback(() => {
    sessionStorage.removeItem(sessionKey);
  }, [sessionKey]);

  return { restore, clear };
}
