import { useState } from 'react';
import { User, Bot, Terminal, Loader2, ChevronRight, ChevronDown, Copy, ThumbsUp, ThumbsDown, Edit3 } from 'lucide-react';
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
        assistant: 'bg-white/[0.04] border border-white/[0.08] text-gray-200 rounded-3xl rounded-tl-xl backdrop-blur-sm',
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
          {timeStr && <span className="text-[10px] text-gray-500">{timeStr}</span>}
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
        <button onClick={onEdit} className="p-1 rounded-lg hover:bg-white/10 text-gray-500 hover:text-gray-300 transition-colors" title="编辑">
          <Edit3 size={12} />
        </button>
      )}
      {onCopy && (
        <button onClick={onCopy} className="p-1 rounded-lg hover:bg-white/10 text-gray-500 hover:text-gray-300 transition-colors" title="复制">
          <Copy size={12} />
        </button>
      )}
      {onFeedback && (
        <>
          <button onClick={() => onFeedback('up')} className="p-1 rounded-lg hover:bg-white/10 text-gray-500 hover:text-emerald-400 transition-colors" title="有用">
            <ThumbsUp size={12} />
          </button>
          <button onClick={() => onFeedback('down')} className="p-1 rounded-lg hover:bg-white/10 text-gray-500 hover:text-rose-400 transition-colors" title="无用">
            <ThumbsDown size={12} />
          </button>
        </>
      )}
    </div>
  );
};

/* Reference: Dify `chat/answer/tool-detail.tsx` + `thinking-details.tsx` */
interface ToolCallCardProps {
  name: string;
  arguments: Record<string, unknown>;
  result: string | undefined;
  error: string | undefined;
  isRunning: boolean | undefined;
}

export const ToolCallCard: React.FC<ToolCallCardProps> = ({ name, arguments: args, result, error, isRunning }) => {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="max-w-[85%] message-enter">
      <div
        className={cn(
          'rounded-2xl border overflow-hidden transition-all duration-200',
          expanded
            ? 'border-white/10 bg-white/[0.04] shadow-lg'
            : 'border-l-[0.25px] border-white/5 bg-white/[0.02] hover:bg-white/[0.04]'
        )}
      >
        <button
          onClick={() => setExpanded(!expanded)}
          className="w-full flex items-center gap-2.5 px-4 py-2.5 text-left hover:bg-white/5 transition-colors cursor-pointer group"
        >
          <div className="p-1.5 rounded-xl bg-blue-500/10 text-blue-400">
            <Terminal size={12} />
          </div>
          <span className="text-xs font-semibold text-blue-400 truncate flex-1">{name}</span>
          {isRunning && <Loader2 size={12} className="text-blue-400 animate-spin" />}
          {error && <span className="text-[10px] text-rose-400 bg-rose-500/10 px-2 py-0.5 rounded-full">error</span>}
          {expanded
            ? <ChevronDown size={14} className="text-gray-500 transition-transform duration-200" />
            : <ChevronRight size={14} className="text-gray-500 transition-transform duration-200" />
          }
        </button>
        {expanded && (
          <div className="px-4 pb-4 space-y-3 border-t border-white/5 animate-in slide-in-from-top-2 duration-200">
            <div>
              <div className="text-[10px] text-gray-500 font-semibold uppercase tracking-wider mb-2">Input</div>
              <pre className="code-block text-xs whitespace-pre-wrap">{JSON.stringify(args, null, 2)}</pre>
            </div>
            {result && (
              <div>
                <div className="text-[10px] text-gray-500 font-semibold uppercase tracking-wider mb-2">Output</div>
                <pre className="code-block text-xs whitespace-pre-wrap">{result}</pre>
              </div>
            )}
            {error && (
              <div>
                <div className="text-[10px] text-rose-400 font-semibold uppercase tracking-wider mb-2">Error</div>
                <pre className="code-block text-xs text-rose-300">{error}</pre>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default MessageContent;
