import { useCallback, useEffect, useRef, useState } from 'react';
import { api } from '../../api';
import { useWorkspaceStore, type PermissionMode } from '../../store/workspace';
import { normalizePermissionMode } from './permissionMode';

export interface PermissionConfigState {
  /** The mode the backend reported, or `null` while it is unknown. */
  mode: PermissionMode | null;
  loading: boolean;
  error: string | null;
  /** Write a mode through `PUT /permissions/config`; resolves to the applied mode. */
  setMode: (mode: PermissionMode) => Promise<void>;
  /** Re-read the configuration from the backend. */
  reload: () => void;
}

/**
 * Owns the real permission configuration. The mode is read from
 * `GET /permissions/config` on mount and every change is written back through
 * `PUT /permissions/config`; a failed request leaves `mode` at `null` so the UI
 * shows "not reported" instead of a locally invented default.
 */
export function usePermissionConfig(): PermissionConfigState {
  const mode = useWorkspaceStore((state) => state.permissionMode);
  const setPermissionMode = useWorkspaceStore((state) => state.setPermissionMode);
  const setPermissionConfigStatus = useWorkspaceStore((state) => state.setPermissionConfigStatus);
  const setPermissionConfigError = useWorkspaceStore((state) => state.setPermissionConfigError);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [nonce, setNonce] = useState(0);
  const mountedRef = useRef(true);

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
    };
  }, []);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError(null);
    setPermissionConfigStatus('loading');
    api.getPermissionConfig()
      .then((payload) => {
        if (!active) return;
        const reported = normalizePermissionMode(payload?.mode);
        if (!reported) throw new Error('Permission config carries no recognisable mode');
        setPermissionMode(reported);
        setPermissionConfigError(null);
        setPermissionConfigStatus('ready');
      })
      .catch((cause: unknown) => {
        if (!active) return;
        const message = cause instanceof Error ? cause.message : String(cause);
        setPermissionMode(null);
        setError(message);
        setPermissionConfigStatus('error');
        setPermissionConfigError(message);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [nonce]);

  const setMode = useCallback(async (next: PermissionMode) => {
    const previous = useWorkspaceStore.getState().permissionMode;
    setPermissionMode(next);
    setError(null);
    setPermissionConfigStatus('loading');
    try {
      const applied = await api.updatePermissionConfig({ mode: next });
      if (!mountedRef.current) return;
      const confirmed = normalizePermissionMode(applied?.mode) ?? next;
      setPermissionMode(confirmed);
      setPermissionConfigError(null);
      setPermissionConfigStatus('ready');
    } catch (cause) {
      if (!mountedRef.current) return;
      const message = cause instanceof Error ? cause.message : String(cause);
      setPermissionMode(previous);
      setError(message);
      setPermissionConfigStatus('error');
      setPermissionConfigError(message);
    }
  }, [setPermissionMode, setPermissionConfigStatus, setPermissionConfigError]);

  const reload = useCallback(() => setNonce((value) => value + 1), []);

  return { mode, loading, error, setMode, reload };
}
