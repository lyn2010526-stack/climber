import { useState } from 'react';
import { User, Bot, Terminal, ChevronDown, Copy, ThumbsUp, ThumbsDown, Edit3 } from 'lucide-react';
import { cn } from '../../lib/utils';
import { cva } from 'class-variance-authority';
import { MarkdownRenderer } from './MarkdownRenderer';

/* Reference: Lobe UI `chat/Bubble/style.ts` - cva variants */
const bubbleVariants = cva(
  'px-5 py-3 text-sm leading-[1.7] shadow-lg message-enter',
  {
    variants: {
      role: {
        user: 'bg-[#007AFF] text-white rounded-3xl rounded-br-xl',
        assistant: 'bg-white/[0.04] border border-white/[0.08] text-[var(--color-text-primary)] rounded-3xl rounded-tl-xl backdrop-blur-sm',
        system: 'bg-amber-500/10 border border-amber-500/20 text-amber-200 rounded-2xl',
        tool: 'bg-emerald-500/10 border border-emerald-500/20 text-emerald-200 rounded-2xl',
      },
    },
    defaultVariants: {
      role: 'assistant',
    },
  }
);

/* Reference: Lobe UI `chat/ChatItem/components/Avatar.tsx` */
function Avatar({ role }: { role: string }) {
  const isUser = role === 'user';
  return (
    <div className={cn(
      'flex items-center justify-center rounded-2xl text-xs font-bold shrink-0',
      'w-9 h-9',
      isUser ? 'bg-[#007AFF] text-white' : 'bg-gradient-to-br from-purple-500 to-blue-500 text-white'
    )}>
      {isUser ? <User size={16} /> : <Bot size={16} />}
    </div>
  );
}

/* Reference: Lobe UI `chat/ChatItem/components/MessageContent.tsx` */
interface MessageContentProps {
  content: string;
  role: string;
  timestamp: Date | undefined;
  actions?: React.ReactNode | undefined;
}

export const MessageContent: React.FC<MessageContentProps> = ({ content, role, timestamp, actions }) => {
  const isUser = role === 'user';
  const timeStr = timestamp ? new Date(timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '';

  return (
    <div className={cn('flex gap-3 max-w-[85%] group', isUser ? 'flex-row-reverse ml-auto' : '')}>
      <Avatar role={role} />
      <div className={cn('flex flex-col gap-1 min-w-0', isUser ? 'items-end' : 'items-start')}>
        <div className={cn(bubbleVariants({ role: role as any }))}>
          {isUser ? (
            <span className="whitespace-pre-wrap">{content}</span>
          ) : (
            <MarkdownRenderer content={content} />
          )}
        </div>
        <div className={cn('flex items-center gap-2 px-1 transition-opacity duration-200', isUser ? 'flex-row-reverse' : '')}>
          {timeStr && <span className="text-[10px] text-[var(--color-text-muted)]">{timeStr}</span>}
          {actions && <div className="flex items-center gap-1">{actions}</div>}
        </div>
      </div>
    </div>
  );
};

/* Reference: Lobe UI `chat/ChatItem/components/Actions.tsx` */
interface MessageActionsProps {
  onCopy?: () => void;
  onFeedback?: (type: 'up' | 'down') => void;
  onEdit?: () => void;
}

export const MessageActions: React.FC<MessageActionsProps> = ({ onCopy, onFeedback, onEdit }) => {
  return (
    <div className="flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity duration-200">
      {onEdit && (
        <button onClick={onEdit} className="p-1 rounded-lg hover:bg-white/10 text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)] transition-colors" title="编辑">
          <Edit3 size={12} />
        </button>
      )}
      {onCopy && (
        <button onClick={onCopy} className="p-1 rounded-lg hover:bg-white/10 text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)] transition-colors" title="复制">
          <Copy size={12} />
        </button>
      )}
      {onFeedback && (
        <>
          <button onClick={() => onFeedback('up')} className="p-1 rounded-lg hover:bg-white/10 text-[var(--color-text-muted)] hover:text-emerald-400 transition-colors" title="有用">
            <ThumbsUp size={12} />
          </button>
          <button onClick={() => onFeedback('down')} className="p-1 rounded-lg hover:bg-white/10 text-[var(--color-text-muted)] hover:text-rose-400 transition-colors" title="无用">
            <ThumbsDown size={12} />
          </button>
        </>
      )}
    </div>
  );
};

/* Reference: Dify `chat/answer/tool-detail.tsx` + Vercel AI SDK + Linear */
interface ToolCallCardProps {
  name: string;
  arguments: Record<string, unknown>;
  result: string | undefined;
  error: string | undefined;
  isRunning: boolean | undefined;
}

const statusConfig = {
  running: { color: '#5E6AD2', bg: 'rgba(94,106,210,0.12)', label: '执行中', pulse: true },
  success: { color: '#10B981', bg: 'rgba(16,185,129,0.12)', label: '成功', pulse: false },
  error: { color: '#EF4444', bg: 'rgba(239,68,68,0.12)', label: 'error', pulse: false },
};

export const ToolCallCard: React.FC<ToolCallCardProps> = ({ name, arguments: args, result, error, isRunning }) => {
  const [expanded, setExpanded] = useState(false);
  const status = error ? 'error' : isRunning ? 'running' : result ? 'success' : 'running';
  const config = statusConfig[status];

  return (
    <div className="max-w-[85%] message-enter">
      <div
        className="rounded-2xl border overflow-hidden transition-all duration-200"
        style={{
          borderColor: expanded ? 'var(--color-border-default)' : 'var(--color-border-subtle)',
          backgroundColor: expanded ? 'var(--color-bg-surface-2)' : 'var(--color-bg-surface-1)',
          boxShadow: expanded ? '0 4px 20px rgba(0,0,0,0.2)' : 'none',
        }}
      >
        <button
          onClick={() => setExpanded(!expanded)}
          className="w-full flex items-center gap-2.5 px-4 py-2.5 text-left transition-colors cursor-pointer group"
          style={{ borderBottom: expanded ? '1px solid var(--color-border-subtle)' : 'none' }}
        >
          <div className="p-1.5 rounded-xl flex items-center justify-center" style={{
            backgroundColor: config.bg,
            color: config.color,
          }}>
            <Terminal size={12} />
          </div>
          <span className="text-xs font-semibold flex-1" style={{ color: 'var(--color-text-primary)' }}>{name}</span>
          {isRunning && (
            <span className="flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-medium" style={{
              backgroundColor: config.bg,
              color: config.color,
            }}>
              <span className="w-1.5 h-1.5 rounded-full animate-pulse" style={{ backgroundColor: config.color }} />
              执行中
            </span>
          )}
          {!isRunning && !error && result && (
            <span className="px-2 py-0.5 rounded-full text-[10px] font-medium" style={{
              backgroundColor: 'rgba(16,185,129,0.12)',
              color: '#10B981',
            }}>成功</span>
          )}
          {error && (
            <span className="px-2 py-0.5 rounded-full text-[10px] font-medium" style={{
              backgroundColor: 'rgba(239,68,68,0.12)',
              color: '#EF4444',
            }}>{config.label}</span>
          )}
          <div className="p-1 rounded-lg transition-all duration-200" style={{
            color: 'var(--color-text-muted)',
            transform: expanded ? 'rotate(180deg)' : 'rotate(0deg)',
          }}>
            <ChevronDown size={14} />
          </div>
        </button>
        {expanded && (
          <div className="px-4 pb-4 space-y-3 animate-in slide-in-from-top-2 duration-200">
            <div>
              <div className="text-[10px] font-semibold uppercase tracking-wider mb-2" style={{ color: 'var(--color-text-muted)' }}>Input</div>
              <pre className="code-block text-xs whitespace-pre-wrap">{JSON.stringify(args, null, 2)}</pre>
            </div>
            {result && (
              <div>
                <div className="text-[10px] font-semibold uppercase tracking-wider mb-2" style={{ color: 'var(--color-text-muted)' }}>Output</div>
                <pre className="code-block text-xs whitespace-pre-wrap">{result}</pre>
              </div>
            )}
            {error && (
              <div>
                <div className="text-[10px] font-semibold uppercase tracking-wider mb-2" style={{ color: '#EF4444' }}>Error</div>
                <pre className="code-block text-xs" style={{ color: '#EF4444' }}>{error}</pre>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default MessageContent;
