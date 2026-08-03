import { User } from 'lucide-react';

export function UserSwitcher() {
  return (
    <div className="mt-2">
      <div className="w-full flex items-center gap-2 px-2 py-1.5 rounded-xl text-[10px] text-[var(--color-text-muted)]">
        <User size={10} />
        <span className="truncate">Local User</span>
      </div>
    </div>
  );
}