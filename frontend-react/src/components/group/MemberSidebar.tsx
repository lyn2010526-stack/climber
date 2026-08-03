import { Bot, Crown, Eye, Users } from 'lucide-react';

interface Member {
  id: string;
  agent_id: string;
  role: string;
  status: string;
  message_count: number;
}

interface MemberSidebarProps {
  members: Member[];
  currentSpeaker?: string | null;
  onInvite?: () => void;
}

const ROLE_ICONS: Record<string, any> = {
  moderator: Crown,
  participant: Bot,
  observer: Eye,
};

const ROLE_COLORS: Record<string, string> = {
  moderator: 'text-amber-400',
  participant: 'text-blue-400',
  observer: 'text-[var(--color-text-muted)]',
};

const STATUS_LABELS: Record<string, string> = {
  active: 'Active',
  idle: 'Idle',
  left: 'Left',
};

export function MemberSidebar({ members, currentSpeaker, onInvite }: MemberSidebarProps) {
  return (
    <div className="w-56 border-l border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-1)]/30 flex flex-col h-full">
      {/* Header */}
      <div className="h-10 flex items-center justify-between px-3 border-b border-[var(--color-border-subtle)]">
        <div className="flex items-center gap-1.5">
          <Users size={12} className="text-[var(--color-text-muted)]" />
          <span className="text-[10px] font-semibold text-[var(--color-text-muted)] uppercase tracking-wider">
            Members
          </span>
          <span className="text-[9px] text-[var(--color-text-muted)]/60">({members.length})</span>
        </div>
        {onInvite && (
          <button
            onClick={onInvite}
            className="text-[10px] text-blue-400 hover:text-blue-400/80 transition-colors"
          >
            + Add
          </button>
        )}
      </div>

      {/* Member List */}
      <div className="flex-1 overflow-y-auto p-2 space-y-0.5">
        {members.length === 0 && (
          <div className="text-center py-6">
             <Users size={20} className="mx-auto text-[var(--color-text-muted)]/20" />
             <p className="text-[10px] text-[var(--color-text-muted)] mt-1">暂无成员</p>
          </div>
        )}
        {members.map((member) => {
          const Icon = ROLE_ICONS[member.role] || Bot;
          const isActive = member.agent_id === currentSpeaker;

          return (
            <div
              key={member.id}
              className={`flex items-center gap-2 px-2 py-2 rounded-lg transition-colors ${
                isActive ? 'bg-blue-600/10 border border-blue-500/20' : 'hover:bg-[var(--color-bg-surface-elevated)]/50 border border-transparent'
              }`}
            >
              {/* Avatar */}
              <div className={`relative w-7 h-7 rounded-lg flex items-center justify-center shrink-0 ${
                isActive ? 'bg-blue-600/20' : 'bg-[var(--color-bg-surface-elevated)]'
              }`}>
                <Icon size={13} className={ROLE_COLORS[member.role] || 'text-[var(--color-text-muted)]'} />
                {isActive && (
                  <span className="absolute -bottom-0.5 -right-0.5 w-2 h-2 bg-green-500 rounded-full border-2 border-bg-secondary" />
                )}
              </div>

              {/* Info */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-1">
                  <p className="text-[11px] font-medium text-[var(--color-text-primary)] truncate">
                    {member.agent_id.slice(0, 10)}
                  </p>
                  {member.role === 'moderator' && (
                    <Crown size={9} className="text-amber-400 shrink-0" />
                  )}
                </div>
                <div className="flex items-center gap-1 mt-0.5">
                  <span className={`w-1.5 h-1.5 rounded-full ${
                    member.status === 'active' ? 'bg-green-500' :
                    member.status === 'idle' ? 'bg-amber-500' : 'bg-text-muted/30'
                  }`} />
                  <span className="text-[9px] text-[var(--color-text-muted)] capitalize">
                    {STATUS_LABELS[member.status] || member.status}
                  </span>
                </div>
              </div>

              {/* Message count */}
              {member.message_count > 0 && (
                <span className="text-[9px] text-[var(--color-text-muted)] bg-[var(--color-bg-surface-elevated)] px-1.5 py-0.5 rounded">
                  {member.message_count}
                </span>
              )}
            </div>
          );
        })}
      </div>

      {/* Footer Stats */}
      <div className="p-2 border-t border-[var(--color-border-subtle)]">
        <div className="flex items-center justify-between px-1">
          <span className="text-[9px] text-[var(--color-text-muted)]">
            Active: {members.filter((m) => m.status === 'active').length}
          </span>
          <span className="text-[9px] text-[var(--color-text-muted)]">
            Total: {members.reduce((acc, m) => acc + m.message_count, 0)} msgs
          </span>
        </div>
      </div>
    </div>
  );
}
