import { ArrowLeft, Copy, Check, User, Bot } from 'lucide-react';
import { useState } from 'react';
import { cn } from '../../lib/utils';
import { MarkdownRenderer } from '../chat/MarkdownRenderer';
import type { MessageItem } from './MessagesList';

interface MessageDetailProps {
  message: MessageItem | null;
  onBack?: () => void;
}

export function MessageDetail({ message, onBack }: MessageDetailProps) {
  const [copied, setCopied] = useState(false);

  if (!message) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <div
            className="w-16 h-16 rounded-2xl flex items-center justify-center mx-auto mb-4"
            style={{ backgroundColor: 'var(--color-bg-surface-2)' }}
          >
            <Bot size={28} className="text-[var(--color-text-muted)] opacity-40" />
          </div>
          <p className="text-sm text-[var(--color-text-muted)]">选择一条消息查看详情</p>
        </div>
      </div>
    );
  }

  const handleCopy = () => {
    navigator.clipboard.writeText(message.preview);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const isUser = message.role === 'user';
  const timeStr = new Date(message.timestamp).toLocaleString('zh-CN', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div
        className="flex items-center gap-3 px-4 py-3"
        style={{ borderBottom: '1px solid var(--color-border-subtle)' }}
      >
        {onBack && (
          <button
            onClick={onBack}
            className="p-2 rounded-xl text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-surface-2)] transition-colors md:hidden"
          >
            <ArrowLeft size={16} />
          </button>
        )}
        <div className="flex-1 min-w-0">
          <h3 className="text-sm font-semibold text-[var(--color-text-primary)] truncate">
            {message.title}
          </h3>
          <p className="text-[10px] text-[var(--color-text-muted)]">{timeStr}</p>
        </div>
        <button
          onClick={handleCopy}
          className="p-2 rounded-xl text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-surface-2)] transition-colors"
          title="复制内容"
        >
          {copied ? (
            <Check size={16} className="text-[var(--color-success)]" />
          ) : (
            <Copy size={16} />
          )}
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto px-4 md:px-8 py-6">
        <div className="max-w-3xl mx-auto space-y-4">
          {/* Role badge */}
          <div className="flex items-center gap-2">
            <div
              className={cn(
                'flex items-center justify-center w-7 h-7 rounded-lg',
                isUser ? 'bg-[var(--color-accent)]' : 'bg-gradient-to-br from-[#5E6AD2] to-[#8B5CF6]',
              )}
            >
              {isUser ? (
                <User size={13} className="text-white" />
              ) : (
                <Bot size={13} className="text-white" />
              )}
            </div>
            <span className="text-xs font-medium text-[var(--color-text-secondary)]">
              {isUser ? '用户' : 'AI 助手'}
            </span>
          </div>

          {/* Message bubble */}
          <div
            className={cn(
              'p-5 rounded-2xl text-sm leading-[1.6]',
              isUser
                ? 'bg-[var(--color-accent)] text-white rounded-br-lg'
                : 'bg-[var(--color-bg-surface-2)] border border-[var(--color-border-subtle)] text-[var(--color-text-primary)] rounded-tl-lg',
            )}
            style={{
              boxShadow: isUser
                ? '0 2px 12px rgba(94, 106, 210, 0.15)'
                : '0 1px 4px rgba(0, 0, 0, 0.1)',
            }}
          >
            {isUser ? (
              <span className="whitespace-pre-wrap">{message.preview}</span>
            ) : (
              <MarkdownRenderer content={message.preview} />
            )}
          </div>

          {/* Metadata */}
          <div
            className="flex items-center gap-4 px-1 pt-2"
            style={{ borderTop: '1px solid var(--color-border-subtle)' }}
          >
            <span className="text-[10px] text-[var(--color-text-muted)]">
              会话: {message.sessionId.slice(0, 8)}...
            </span>
            <span className="text-[10px] text-[var(--color-text-muted)]">
              字数: {message.preview.length}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
