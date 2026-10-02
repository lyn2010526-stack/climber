import { LogOut, User } from 'lucide-react';
import { api } from '../../api';

export function UserSwitcher() {
  const handleLogout = async () => {
    await api.logout();
    window.location.href = '/auth/login.html';
  };

  return (
    <div className="mt-2">
      <div className="w-full flex items-center gap-2 px-2 py-1.5 rounded-xl text-[10px] text-[var(--color-text-muted)]">
        <User size={10} />
        <span className="truncate">Local User</span>
        <button type="button" onClick={() => void handleLogout()}
          aria-label="登出" title="登出"
          className="ml-auto flex h-6 w-6 shrink-0 items-center justify-center rounded-md transition-colors hover:bg-[var(--color-bg-surface-2)] hover:text-[var(--color-text-secondary)] focus-visible:outline-2 focus-visible:outline-[var(--color-accent)]">
          <LogOut size={12} />
        </button>
      </div>
    </div>
  );
}
