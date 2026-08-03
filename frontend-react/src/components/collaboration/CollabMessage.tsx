import { Bot, Wrench, Shield, AlertTriangle } from 'lucide-react';

export interface CollabMessage {
  id: string;
  memberId: string;
  memberName: string;
  memberAvatar?: string;
  role: 'worker' | 'reviewer' | 'system';
  content: string;
  toolCalls?: ToolCallInfo[];
  issues?: IssueInfo[];
  timestamp: string;
}

export interface ToolCallInfo {
  toolName: string;
  arguments: Record<string, unknown>;
  result?: string;
}

export interface IssueInfo {
  severity: 'critical' | 'major' | 'minor';
  description: string;
  location: string;
  fixSuggestion: string;
}

interface CollabMessageProps {
  message: CollabMessage;
}

const ROLE_STYLES = {
  worker: {
    border: 'border-l-green-500',
    bg: 'bg-green-500/5',
    badge: 'bg-green-500/10 text-green-400',
    label: 'Worker',
    icon: Wrench,
  },
  reviewer: {
    border: 'border-l-amber-500',
    bg: 'bg-amber-500/5',
    badge: 'bg-amber-500/10 text-amber-400',
    label: 'Reviewer',
    icon: Shield,
  },
  system: {
    border: 'border-l-blue-500',
    bg: 'bg-blue-600/5',
    badge: 'bg-blue-600/10 text-blue-400',
    label: 'System',
    icon: Bot,
  },
};

const SEVERITY_COLORS = {
  critical: 'text-red-400 bg-red-500/10',
  major: 'text-amber-400 bg-amber-500/10',
  minor: 'text-[var(--color-text-muted)] bg-[var(--color-bg-surface-elevated)]',
};

export function CollabMessage({ message }: CollabMessageProps) {
  const style = ROLE_STYLES[message.role] || ROLE_STYLES.system;
  const RoleIcon = style.icon;

  return (
    <div className={`flex items-start gap-3 ${style.bg} rounded-r-lg border-l-2 ${style.border} p-3`}>
      {/* Avatar */}
      <div className="w-8 h-8 rounded-lg bg-[var(--color-bg-surface-elevated)] flex items-center justify-center shrink-0">
        {message.memberAvatar ? (
          <img src={message.memberAvatar} alt="" className="w-8 h-8 rounded-lg object-cover" />
        ) : (
          <RoleIcon size={14} className={style.badge.split(' ')[1]} />
        )}
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-1">
          <span className="text-xs font-medium text-[var(--color-text-primary)]">{message.memberName}</span>
          <span className={`text-[9px] px-1.5 py-0.5 rounded-full font-medium ${style.badge}`}>
            {style.label}
          </span>
          <span className="text-[10px] text-[var(--color-text-muted)] ml-auto">
            {message.timestamp ? new Date(message.timestamp).toLocaleTimeString() : ''}
          </span>
        </div>

        {/* Text content */}
        {message.content && (
          <div className="text-xs text-[var(--color-text-secondary)] whitespace-pre-wrap break-words mt-1">
            {message.content}
          </div>
        )}

        {/* Tool calls */}
        {message.toolCalls && message.toolCalls.length > 0 && (
          <div className="mt-2 space-y-1.5">
            {message.toolCalls.map((tc, i) => (
              <details key={i} className="text-[10px]">
                <summary className="cursor-pointer text-blue-400 hover:text-blue-400/80 flex items-center gap-1">
                  <Wrench size={10} />
                  {tc.toolName}
                </summary>
                <div className="mt-1 pl-4 space-y-1">
                  <div className="text-[var(--color-text-muted)]">
                    <span className="font-medium">Args:</span>{' '}
                    <code className="bg-[var(--color-bg-surface-elevated)] px-1 rounded">
                      {JSON.stringify(tc.arguments).slice(0, 100)}
                    </code>
                  </div>
                  {tc.result && (
                    <div className="text-[var(--color-text-muted)] max-h-20 overflow-y-auto">
                      <span className="font-medium">Result:</span>{' '}
                      <code className="bg-[var(--color-bg-surface-elevated)] px-1 rounded block mt-0.5">
                        {tc.result.slice(0, 200)}
                      </code>
                    </div>
                  )}
                </div>
              </details>
            ))}
          </div>
        )}

        {/* Review issues */}
        {message.issues && message.issues.length > 0 && (
          <div className="mt-2 space-y-1">
            {message.issues.map((issue, i) => (
              <div key={i} className={`flex items-start gap-1.5 p-1.5 rounded ${SEVERITY_COLORS[issue.severity]}`}>
                <AlertTriangle size={10} className="mt-0.5 shrink-0" />
                <div className="flex-1 min-w-0">
                  <div className="text-[10px] font-medium">
                    [{issue.severity.toUpperCase()}] {issue.description}
                  </div>
                  {issue.fixSuggestion && (
                    <div className="text-[9px] text-[var(--color-text-muted)] mt-0.5">
                      Fix: {issue.fixSuggestion.slice(0, 100)}
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
