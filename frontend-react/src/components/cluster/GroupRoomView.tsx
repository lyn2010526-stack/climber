import { ArrowLeft, Wrench } from 'lucide-react';
import { GroupRoom } from '../group/GroupRoom';

export function GroupRoomView({
  activeGroupId,
  onLeave,
  onSwitchToCollab,
}: {
  activeGroupId: string;
  onLeave: () => void;
  onSwitchToCollab: () => void;
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
        <button
          onClick={onSwitchToCollab}
          className="ml-3 flex items-center gap-1 text-xs text-[var(--color-accent)] hover:text-[var(--color-accent-hover)] transition-colors"
        >
          <Wrench size={12} />
          自动协作
        </button>
      </div>
      <div className="flex-1 min-h-0">
        <GroupRoom groupId={activeGroupId} onLeave={onLeave} />
      </div>
    </div>
  );
}
