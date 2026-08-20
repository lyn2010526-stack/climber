import { ArrowLeft } from 'lucide-react';
import { CollaborationConsole } from '../collaboration/CollaborationConsole';

export function CollabConsoleView({
  activeGroupId,
  availableTasks,
  onLeave,
}: {
  activeGroupId: string;
  availableTasks: Array<{ id: string; description: string }>;
  onLeave: () => void;
}) {
  return (
    <div className="h-full flex flex-col">
      <div className="h-10 flex items-center px-4 border-b border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-1)]">
        <button
          onClick={onLeave}
          className="flex items-center gap-1 text-xs text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] transition-colors"
        >
          <ArrowLeft size={14} />
          返回群组列表
        </button>
         <span className="ml-3 text-xs font-medium text-[var(--color-text-primary)]">自动协作</span>
      </div>
      <div className="flex-1 min-h-0">
        <CollaborationConsole groupId={activeGroupId} availableTasks={availableTasks} />
      </div>
    </div>
  );
}
