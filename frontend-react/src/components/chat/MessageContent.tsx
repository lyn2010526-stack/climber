import { useState } from 'react';
import { User, Bot, Terminal, ChevronDown, Copy, Check, ThumbsUp, ThumbsDown, Edit3, AlertCircle, Loader2 } from 'lucide-react';
import { cn } from '../../lib/utils';
import { cva } from 'class-variance-authority';
import { MarkdownRenderer } from './MarkdownRenderer';

/* Reference: Lobe UI `chat/Bubble/style.ts` - cva variants */
const bubbleVariants = cva(
  'text-sm leading-[1.7] message-enter',
  {
    variants: {
      role: {
        user: 'max-w-[72ch] bg-[var(--color-accent)] text-white rounded-[18px] rounded-br-md px-4 py-2.5 shadow-sm',
        assistant: 'w-full text-[var(--color-text-primary)] py-1',
        system: 'w-full bg-amber-500/10 border border-amber-500/25 text-amber-700 dark:text-amber-200 rounded-lg px-4 py-3',
        tool: 'w-full bg-emerald-500/10 border border-emerald-500/25 text-emerald-700 dark:text-emerald-200 rounded-lg px-4 py-3',
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
      'flex items-center justify-center rounded-lg text-xs font-bold shrink-0 w-8 h-8 border',
      isUser ? 'bg-[var(--color-accent)] text-white border-transparent' : 'bg-[var(--color-bg-surface-1)] text-[var(--color-accent)] border-[var(--color-border-default)]'
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
    <article className={cn('flex gap-3 w-full group', isUser ? 'flex-row-reverse' : '')} aria-label={isUser ? '用户消息' : '助手消息'}>
      <Avatar role={role} />
      <div className={cn('flex flex-col gap-1 min-w-0', isUser ? 'items-end max-w-[78%]' : 'items-start flex-1')}>
        <div className={cn(bubbleVariants({ role: role as any }))}>
          {isUser ? (
            <span className="whitespace-pre-wrap">{content}</span>
          ) : (
            <MarkdownRenderer content={content} />
          )}
        </div>
        <div className={cn('flex min-h-6 items-center gap-2 px-1 transition-opacity duration-200', isUser ? 'flex-row-reverse' : '')}>
          {timeStr && <span className="text-[10px] text-[var(--color-text-muted)]">{timeStr}</span>}
          {actions && <div className="flex items-center gap-1">{actions}</div>}
        </div>
      </div>
    </article>
  );
};

/* Reference: Lobe UI `chat/ChatItem/components/Actions.tsx` */
interface MessageActionsProps {
  onCopy?: () => void;
  onFeedback?: (type: 'up' | 'down') => void;
  onEdit?: () => void;
}

export const MessageActions: React.FC<MessageActionsProps> = ({ onCopy, onFeedback, onEdit }) => {
  const [copied, setCopied] = useState(false);
  const copy = () => {
    onCopy?.();
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1200);
  };
  return (
    <div className="flex items-center gap-0.5 opacity-60 group-hover:opacity-100 focus-within:opacity-100 transition-opacity duration-200">
      {onEdit && (
        <button onClick={onEdit} className="p-2 rounded-md hover:bg-[var(--color-bg-surface-2)] text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)] transition-colors" title="编辑" aria-label="编辑消息">
          <Edit3 size={13} />
        </button>
      )}
      {onCopy && (
        <button onClick={copy} className="p-2 rounded-md hover:bg-[var(--color-bg-surface-2)] text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)] transition-colors" title="复制" aria-label="复制消息">
          {copied ? <Check size={13} /> : <Copy size={13} />}
        </button>
      )}
      {onFeedback && (
        <>
          <button onClick={() => onFeedback('up')} className="p-2 rounded-md hover:bg-[var(--color-bg-surface-2)] text-[var(--color-text-muted)] hover:text-emerald-500 transition-colors" title="有用" aria-label="标记为有用">
            <ThumbsUp size={12} />
          </button>
          <button onClick={() => onFeedback('down')} className="p-2 rounded-md hover:bg-[var(--color-bg-surface-2)] text-[var(--color-text-muted)] hover:text-rose-500 transition-colors" title="无用" aria-label="标记为无用">
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
  status?: 'running' | 'success' | 'error';
}

const statusConfig = {
  running: { color: '#5E6AD2', bg: 'rgba(94,106,210,0.12)', label: '执行中', pulse: true },
  success: { color: '#10B981', bg: 'rgba(16,185,129,0.12)', label: '成功', pulse: false },
  error: { color: '#EF4444', bg: 'rgba(239,68,68,0.12)', label: '失败', pulse: false },
};

export const ToolCallCard: React.FC<ToolCallCardProps> = ({ name, arguments: args, result, error, isRunning, status: explicitStatus }) => {
  const [expanded, setExpanded] = useState(false);
  const status = explicitStatus || (error ? 'error' : isRunning ? 'running' : 'success');
  const config = statusConfig[status];

  return (
    <div className="w-full message-enter">
      <div
        className="rounded-lg border overflow-hidden transition-all duration-200"
        style={{
          borderColor: expanded ? 'var(--color-border-default)' : 'var(--color-border-subtle)',
          backgroundColor: expanded ? 'var(--color-bg-surface-2)' : 'var(--color-bg-surface-1)',
          boxShadow: expanded ? 'var(--shadow-sm)' : 'none',
        }}
      >
        <button
          onClick={() => setExpanded(!expanded)}
          className="w-full flex items-center gap-2.5 px-4 py-2.5 text-left transition-colors cursor-pointer group"
          style={{ borderBottom: expanded ? '1px solid var(--color-border-subtle)' : 'none' }}
        >
          <div className="p-1.5 rounded-md flex items-center justify-center" style={{
            backgroundColor: config.bg,
            color: config.color,
          }}>
            {status === 'error' ? <AlertCircle size={13} /> : status === 'running' ? <Loader2 size={13} className="animate-spin" /> : <Terminal size={13} />}
          </div>
          <span className="text-xs font-semibold flex-1" style={{ color: 'var(--color-text-primary)' }}>{name}</span>
          {status === 'running' && (
            <span className="flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-medium" style={{
              backgroundColor: config.bg,
              color: config.color,
            }}>
              <span className="w-1.5 h-1.5 rounded-full animate-pulse" style={{ backgroundColor: config.color }} />
              执行中
            </span>
          )}
          {status === 'success' && (
            <span className="px-2 py-0.5 rounded-full text-[10px] font-medium" style={{
              backgroundColor: 'rgba(16,185,129,0.12)',
              color: '#10B981',
            }}>成功</span>
          )}
          {status === 'error' && (
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
