import { User } from 'lucide-react';
import { cn } from '../../lib/utils';
import { formatTime } from '../../i18n/utils';
import { ClimberMark } from '../brand/ClimberMark';
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
  /** 这一轮以失败收尾，行内可给出补救入口。 */
  failed?: boolean;
  /** 用户主动中断了这一轮。 */
  interrupted?: boolean;
  isStreaming?: boolean;
}

interface MessageBubbleProps {
  message: Message;
  /** 调用方拼装好的正文（工具卡、思考流、正文与光标）；缺省时按角色渲染。 */
  body?: React.ReactNode | undefined;
  actions?: React.ReactNode | undefined;
  /**
   * 连续同角色消息合并视觉：后一条隐藏头像列，但保留占位宽度，
   * 让同一段落里的行首始终对齐。
   */
  showAvatar?: boolean;
  /** 与上一条同角色：收紧上下节奏，读成一组。 */
  merged?: boolean;
  /** 调用方决定的阅读列宽。 */
  className?: string;
}

/**
 * 一条消息行。
 *
 * 助手行带 ClimberMark 头像列，正文平铺全宽：答案是内容本身，气泡会与
 * 答案自带的代码块、表格抢焦点。用户行是右对齐的浅色气泡：短输入，
 * 读回来用。时间戳与操作按钮悬浮出现，meta 行常驻占位高度，
 * 悬停显隐永远不会推动布局。
 */
export function MessageBubble({
  message,
  body,
  actions,
  showAvatar = true,
  merged = false,
  className,
}: MessageBubbleProps) {
  const isUser = message.role === 'user';
  const isAssistant = message.role === 'assistant';
  const timeStr = message.timestamp ? formatTime(message.timestamp) : '';

  return (
    <div
      data-message-bubble
      className={cn('group flex w-full min-w-0 items-start gap-2.5', isUser && 'justify-end', className)}
    >
      {isAssistant && (
        <div data-avatar-col className="w-7 shrink-0" aria-hidden={!showAvatar}>
          {showAvatar && (
            <div
              data-avatar
              className="flex size-7 items-center justify-center rounded-[var(--radius-md)] border border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-2)] text-[var(--color-accent-foreground)]"
            >
              <ClimberMark size={15} />
            </div>
          )}
        </div>
      )}
      {!isUser && !isAssistant && <div data-avatar-col className="w-7 shrink-0" aria-hidden="true" />}
      <div
        data-message-column
        className={cn(
          'flex min-w-0 flex-col',
          isUser ? 'w-fit max-w-[85%] items-end' : 'min-w-0 flex-1 items-start',
        )}
      >
        <div
          data-message-body
          className={cn(
            'min-w-0 max-w-full break-words text-sm leading-relaxed text-[var(--color-text-primary)]',
            isUser &&
              'rounded-2xl rounded-br-md bg-[var(--color-accent-subtle)] px-4 py-2.5 whitespace-pre-wrap',
          )}
        >
          {body ?? (isUser ? message.content : <MarkdownRenderer content={message.content} />)}
          {message.isStreaming && (
            <span data-streaming-cursor>
              <StreamingCursor />
            </span>
          )}
        </div>
        {(timeStr || actions) && (
          <div
            data-message-meta
            className={cn(
              'flex min-h-[26px] w-full items-center gap-2 px-1 pt-1 text-xs text-[var(--color-text-muted)]',
              'transition-opacity duration-150 ease-out [@media(hover:hover)]:opacity-0 group-hover:opacity-100 group-focus-within:opacity-100 motion-reduce:transition-none',
              isUser ? 'flex-row-reverse justify-end' : 'justify-start',
              merged && 'min-h-[22px]',
            )}
          >
            {timeStr && <time dateTime={new Date(message.timestamp!).toISOString()}>{timeStr}</time>}
            {actions}
          </div>
        )}
      </div>
    </div>
  );
}
