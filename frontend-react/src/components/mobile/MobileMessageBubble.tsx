import { ClimberMark } from '../brand/ClimberMark';
import { MarkdownRenderer } from '../chat/MarkdownRenderer';
import { StreamingCursor } from '../chat/StreamingCursor';
import { MobileThinkingBlock } from './MobileThinkingBlock';
import { MobileToolCallCard } from './MobileToolCallCard';
import { formatTime } from '../../i18n/utils';
import { useI18n } from '../../i18n';
import { cn } from '../../lib/utils';
import type { Message } from '../../useChat';

interface MobileMessageBubbleProps {
  message: Message;
  /** The latest assistant turn is streaming, so its tail gets the cursor. */
  isStreaming?: boolean;
  showThinking: boolean;
  showToolCalls: boolean;
}

function roleLabel(message: Message, t: (key: string) => string): string {
  switch (message.role) {
    case 'user':
      return t('mobile_chat.role_user');
    case 'assistant':
      return t('mobile_chat.role_assistant');
    case 'system':
      return t('mobile_chat.role_system');
    default:
      return message.tool_name || t('mobile_chat.role_tool');
  }
}

/**
 * One transcript row, in the mobile chat paradigm.
 *
 * The user's turn is a right-aligned accent bubble — short input, read back.
 * The assistant's turn hangs left under the ClimberMark avatar in a light
 * surface, because the answer is long-form markdown. System and tool rows read
 * as quiet full-width notes. Reasoning and tool calls render inside the row so
 * a single message keeps its provenance with its answer.
 */
export function MobileMessageBubble({ message, isStreaming = false, showThinking, showToolCalls }: MobileMessageBubbleProps) {
  const { t } = useI18n();
  const isUser = message.role === 'user';
  const isAssistant = message.role === 'assistant';
  const isSystemish = message.role === 'system' || message.role === 'tool';
  const timeStr = message.timestamp ? formatTime(message.timestamp) : undefined;

  return (
    <article
      data-role={message.role}
      className={cn('message-enter flex min-w-0 gap-2.5', isUser ? 'justify-end' : 'items-start')}
    >
      {!isUser && (
        <span
          aria-hidden="true"
          className="mt-1 flex size-7 shrink-0 items-center justify-center rounded-full border border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-2)]"
        >
          <ClimberMark size={15} color="var(--color-accent-foreground)" />
        </span>
      )}
      <div className={cn('flex min-w-0 flex-col', isUser ? 'max-w-[85%] items-end' : 'min-w-0 flex-1 items-start')}>
        {message.content && (
          <div
            className={cn(
              'min-w-0 max-w-full text-sm leading-relaxed transition-transform duration-150 motion-reduce:transition-none',
              isUser &&
                'w-fit whitespace-pre-wrap break-words rounded-[var(--radius-xl)] rounded-br-[var(--radius-md)] bg-[var(--color-accent)] px-4 py-2.5 text-[var(--color-accent-text)]',
              isSystemish &&
                'w-full rounded-[var(--radius-lg)] border-l-2 border-[var(--color-border-default)] px-3 py-2 text-[var(--color-text-secondary)]',
              isAssistant && 'w-full rounded-[var(--radius-xl)] rounded-tl-[var(--radius-md)] border border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-1)] px-3.5 py-2.5 text-[var(--color-text-primary)]',
            )}
          >
            {isAssistant ? (
              <>
                <MarkdownRenderer content={message.content} />
                {isStreaming && <StreamingCursor />}
              </>
            ) : (
              message.content
            )}
          </div>
        )}
        {!message.content && isAssistant && isStreaming && (
          <div
            className={cn(
              'flex min-h-[44px] items-center gap-2 rounded-[var(--radius-xl)] rounded-tl-[var(--radius-md)] border border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-1)] px-4 text-sm text-[var(--color-text-muted)]',
            )}
          >
            <span className="inline-flex items-center gap-1.5">
              {[0, 1, 2].map(index => (
                <span
                  key={index}
                  className="size-1.5 rounded-full"
                  style={{
                    backgroundColor: 'var(--color-text-muted)',
                    animation: `bounce 1.4s ease-in-out ${index * 0.16}s infinite`,
                  }}
                />
              ))}
            </span>
          </div>
        )}
        {showThinking && message.reasoning && (
          <div className="mt-1.5 w-full min-w-0">
            <MobileThinkingBlock reasoning={message.reasoning} streaming={isStreaming} />
          </div>
        )}
        {showToolCalls && message.toolCalls?.map(tool => (
          <div key={tool.id} className="mt-1.5 w-full min-w-0">
            <MobileToolCallCard tool={tool} />
          </div>
        ))}
        <div className={cn('flex min-h-[20px] w-full items-center gap-2 px-1 pt-0.5 text-[10px] text-[var(--color-text-muted)]', isUser ? 'justify-end' : 'justify-start')}>
          <span>{roleLabel(message, t)}</span>
          {timeStr && <span>{timeStr}</span>}
        </div>
      </div>
    </article>
  );
}

export default MobileMessageBubble;
