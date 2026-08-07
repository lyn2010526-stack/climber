import { useState } from 'react';
import { User, Bot, Copy, Check, ThumbsUp, ThumbsDown, RotateCcw, Edit3, Quote, Trash2 } from 'lucide-react';
import { cn } from '../../lib/utils';
import { MarkdownRenderer } from './MarkdownRenderer';
import { StreamingCursor } from './StreamingCursor';

export interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system' | 'tool';
  content: string;
  toolCalls?: Array<{
    id: string;
    name: string;
    arguments: Record<string, unknown>;
    result?: string;
    error?: string;
    status?: 'running' | 'success' | 'error';
    duration?: number;
  }>;
  reasoning?: string;
  timestamp?: Date | string | number;
  isStreaming?: boolean;
}

interface MessageBubbleProps {
  message: Message;
  onCopy?: (content: string) => void;
  onEdit?: (id: string, content: string) => void;
  onRegenerate?: (id: string) => void;
  onQuote?: (content: string) => void;
  onDelete?: (id: string) => void;
  onFeedback?: (id: string, type: 'up' | 'down') => void;
}

export function MessageBubble({
  message,
  onCopy,
  onEdit,
  onRegenerate,
  onQuote,
  onDelete,
  onFeedback,
}: MessageBubbleProps) {
  const [copied, setCopied] = useState(false);
  const [feedback, setFeedback] = useState<'up' | 'down' | null>(null);
  const isUser = message.role === 'user';
  const isAssistant = message.role === 'assistant';
  const timeStr = message.timestamp
    ? new Date(message.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    : '';

  const handleCopy = () => {
    onCopy?.(message.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleFeedback = (type: 'up' | 'down') => {
    const next = feedback === type ? null : type;
    setFeedback(next);
    if (next) onFeedback?.(message.id, next);
  };

  return (
    <div
      className={cn(
        'group relative flex gap-3 message-enter',
        isUser ? 'flex-row-reverse ml-auto' : 'mr-auto',
      )}
      style={{ maxWidth: '85%' }}
    >
      {/* Avatar */}
      <div className="shrink-0 mt-0.5">
        <div
          className={cn(
            'flex items-center justify-center w-8 h-8 rounded-xl',
            isUser
              ? 'bg-[var(--color-accent)]'
              : 'bg-gradient-to-br from-[#5E6AD2] to-[#8B5CF6]',
          )}
        >
          {isUser ? (
            <User size={15} className="text-white" />
          ) : (
            <Bot size={15} className="text-white" />
          )}
        </div>
      </div>

      {/* Content */}
      <div className={cn('flex flex-col gap-1 min-w-0 flex-1', isUser ? 'items-end' : 'items-start')}>
        {/* Bubble */}
        <div
          className={cn(
            'px-4 py-3 text-sm leading-[1.6]',
            isUser
              ? 'bg-[var(--color-accent)] text-white rounded-2xl rounded-br-lg'
              : 'bg-[var(--color-bg-surface-2)] border border-[var(--color-border-subtle)] text-[var(--color-text-primary)] rounded-2xl rounded-tl-lg',
          )}
          style={{
            boxShadow: isUser
              ? '0 2px 12px rgba(94, 106, 210, 0.2), 0 1px 3px rgba(0, 0, 0, 0.1)'
              : '0 1px 4px rgba(0, 0, 0, 0.15), 0 1px 2px rgba(0, 0, 0, 0.1)',
          }}
        >
          {isUser ? (
            <span className="whitespace-pre-wrap">{message.content}</span>
          ) : (
            <>
              <MarkdownRenderer content={message.content} />
              {message.isStreaming && <StreamingCursor />}
            </>
          )}
        </div>

        {/* Meta row: timestamp + actions */}
        <div
          className={cn(
            'flex items-center gap-1.5 px-1 min-h-[20px]',
            isUser ? 'flex-row-reverse' : '',
          )}
        >
          {timeStr && (
            <span className="text-[10px] text-[var(--color-text-muted)]">{timeStr}</span>
          )}

          {/* Action buttons - visible on hover */}
          <div
            className={cn(
              'flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity duration-200',
            )}
          >
            <button
              onClick={handleCopy}
              className="p-1 rounded-md text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-surface-3)] transition-colors"
              title="复制"
            >
              {copied ? <Check size={12} className="text-[var(--color-success)]" /> : <Copy size={12} />}
            </button>

            {isAssistant && onRegenerate && (
              <button
                onClick={() => onRegenerate(message.id)}
                className="p-1 rounded-md text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-surface-3)] transition-colors"
                title="重新生成"
              >
                <RotateCcw size={12} />
              </button>
            )}

            {isUser && onEdit && (
              <button
                onClick={() => onEdit(message.id, message.content)}
                className="p-1 rounded-md text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-surface-3)] transition-colors"
                title="编辑"
              >
                <Edit3 size={12} />
              </button>
            )}

            {onQuote && (
              <button
                onClick={() => onQuote(message.content)}
                className="p-1 rounded-md text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-surface-3)] transition-colors"
                title="引用"
              >
                <Quote size={12} />
              </button>
            )}

            {isAssistant && onFeedback && (
              <>
                <button
                  onClick={() => handleFeedback('up')}
                  className={cn(
                    'p-1 rounded-md hover:bg-[var(--color-bg-surface-3)] transition-colors',
                    feedback === 'up' ? 'text-[var(--color-success)]' : 'text-[var(--color-text-muted)] hover:text-[var(--color-success)]',
                  )}
                  title="有用"
                >
                  <ThumbsUp size={12} />
                </button>
                <button
                  onClick={() => handleFeedback('down')}
                  className={cn(
                    'p-1 rounded-md hover:bg-[var(--color-bg-surface-3)] transition-colors',
                    feedback === 'down' ? 'text-[var(--color-error)]' : 'text-[var(--color-text-muted)] hover:text-[var(--color-error)]',
                  )}
                  title="无用"
                >
                  <ThumbsDown size={12} />
                </button>
              </>
            )}

            {onDelete && (
              <button
                onClick={() => onDelete(message.id)}
                className="p-1 rounded-md text-[var(--color-text-muted)] hover:text-[var(--color-error)] hover:bg-[var(--color-error-subtle)] transition-colors"
                title="删除"
              >
                <Trash2 size={12} />
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
