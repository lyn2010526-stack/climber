const BOOT_SESSION_STORAGE_KEY = 'climber.boot.v1';

export function hasSeenBootSession(): boolean {
  try {
    return window.sessionStorage.getItem(BOOT_SESSION_STORAGE_KEY) === '1';
  } catch {
    return false;
  }
}

export function markBootSessionSeen(): void {
  try {
    window.sessionStorage.setItem(BOOT_SESSION_STORAGE_KEY, '1');
  } catch {
    return;
  }
}
