import { useCallback, useEffect, useState, type ReactNode } from 'react';
import { api } from '../../api';
import { LoginPage } from '../../pages/LoginPage';

const AUTH_ENABLED_STORAGE_KEY = 'climber.auth.enabled';

function readAuthEnabledCache(): boolean | null {
  try {
    const raw = localStorage.getItem(AUTH_ENABLED_STORAGE_KEY);
    if (raw === '1') return true;
    if (raw === '0') return false;
  } catch {
    // Storage unavailable: fall through to the health probe.
  }
  return null;
}

function writeAuthEnabledCache(enabled: boolean): void {
  try {
    localStorage.setItem(AUTH_ENABLED_STORAGE_KEY, enabled ? '1' : '0');
  } catch {
    // The probe result still applies for this session.
  }
}

function hasStoredSession(): boolean {
  try {
    return Boolean(localStorage.getItem('auth_token'));
  } catch {
    return false;
  }
}

export interface AuthGateProps {
  /** Gate only once the boot surface has finished; children stay mounted underneath. */
  ready: boolean;
  children: ReactNode;
}

export function AuthGate({ ready, children }: AuthGateProps) {
  const [blocked, setBlocked] = useState(false);

  useEffect(() => {
    if (!ready) return;
    let cancelled = false;

    const decide = async () => {
      let enabled = readAuthEnabledCache();
      if (enabled === null) {
        try {
          const health = await api.getAuthHealth();
          enabled = health?.authentication_enabled === true;
          writeAuthEnabledCache(enabled);
        } catch {
          enabled = false;
        }
      }
      if (cancelled || !enabled) return;

      if (hasStoredSession()) {
        try {
          await api.getCurrentUser();
          if (cancelled) return;
          return;
        } catch {
          if (cancelled) return;
          setBlocked(true);
          return;
        }
      }
      setBlocked(true);
    };

    void decide();
    return () => {
      cancelled = true;
    };
  }, [ready]);

  const handleLoginSuccess = useCallback(() => {
    setBlocked(false);
  }, []);

  return (
    <>
      {blocked && <LoginPage onSuccess={handleLoginSuccess} />}
      {children}
    </>
  );
}