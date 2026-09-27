import { useState } from 'react';
import { Terminal, ChevronDown, Copy, ThumbsUp, ThumbsDown, Edit3 } from 'lucide-react';
import { cn } from '../../lib/utils';
import { useI18n } from '../../i18n';
import { formatTime } from '../../i18n/utils';
import { MarkdownRenderer } from './MarkdownRenderer';

/**
 * Reveal-on-hover for the message actions.
 *
 * Pointer devices fade the row in on hover; touch devices, which cannot hover,
 * keep it visible. `group-focus-within` covers the keyboard: tabbing into any
 * action reveals the whole row, so a focused control is never invisible.
 */
const actionsReveal =
  '[@media(hover:hover)]:opacity-0 group-hover:opacity-100 group-focus-within:opacity-100 motion-reduce:transition-none';

/** Reserves the action row's height so the transcript does not step as it appears. */
const FOOTER_MIN_HEIGHT = 'min-h-[31px]';

const actionButton =
  'rounded-md p-1 text-[var(--color-text-muted)] transition-colors duration-150 hover:bg-[var(--color-bg-surface-3)] hover:text-[var(--color-text-primary)] motion-reduce:transition-none focus-visible:outline-2 focus-visible:outline-[var(--color-accent-foreground)]';

interface MessageContentProps {
  content: string;
  role: string;
  timestamp: Date | undefined;
  actions?: React.ReactNode | undefined;
  /** Replaces the rendered content, for rows that assemble their own body. */
  body?: React.ReactNode | undefined;
  /** Merged into the row, e.g. the reading-column width the caller decided. */
  className?: string;
}

/**
 * A transcript row.
 *
 * The user's turn is a fitted, right-aligned surface because it is short input
 * to be read back. An assistant turn is plain full-width text: the answer is the
 * content, and a bubble around it would compete with the code blocks and tables
 * the answer itself carries.
 */
export const MessageContent: React.FC<MessageContentProps> = ({ content, role, timestamp, actions, body, className }) => {
  const isUser = role === 'user';
  const isSystem = role === 'system';
  const timeStr = timestamp ? formatTime(timestamp) : '';

  return (
    <div className={cn('group flex w-full min-w-0', isUser ? 'justify-end' : 'items-start', className)}>
      <div
        className={cn(
          'flex min-w-0 flex-col',
          isUser ? 'w-fit max-w-[90%] items-end sm:max-w-[85%]' : 'w-full items-start',
        )}
      >
        <div
          className={cn(
            'min-w-0 max-w-full break-words text-sm leading-relaxed text-[var(--color-text-primary)]',
            isUser &&
              'w-fit whitespace-pre-wrap rounded-[var(--radius-lg)] rounded-br-[var(--radius-sm)] bg-[var(--color-bg-surface-2)] px-4 py-2.5',
            isSystem &&
              'border-l-2 border-[var(--color-border-default)] pl-4 text-[var(--color-text-secondary)]',
            !isUser && !isSystem && 'w-full',
          )}
        >
          {body ?? (isUser ? content : <MarkdownRenderer content={content} />)}
        </div>
        {(timeStr || actions) && (
          <div
            className={cn(
              'flex w-full items-center gap-2 px-1 pt-1 text-xs text-[var(--color-text-muted)]',
              isUser ? 'justify-end' : 'justify-start',
              FOOTER_MIN_HEIGHT,
            )}
          >
            {timeStr && <time dateTime={new Date(timestamp!).toISOString()}>{timeStr}</time>}
            {actions}
          </div>
        )}
      </div>
    </div>
  );
};

interface MessageActionsProps {
  onCopy?: () => void;
  onFeedback?: (type: 'up' | 'down') => void;
  onEdit?: () => void;
}

export const MessageActions: React.FC<MessageActionsProps> = ({ onCopy, onFeedback, onEdit }) => {
  return (
    <div
      data-message-actions
      className={cn(
        'flex items-center gap-0.5 transition-opacity duration-150 ease-out',
        actionsReveal,
      )}
    >
      {onEdit && (
        <button type="button" onClick={onEdit} className={actionButton} title="编辑">
          <Edit3 size={12} aria-hidden="true" />
        </button>
      )}
      {onCopy && (
        <button type="button" onClick={onCopy} className={actionButton} title="复制">
          <Copy size={12} aria-hidden="true" />
        </button>
      )}
      {onFeedback && (
        <>
          <button
            type="button"
            onClick={() => onFeedback('up')}
            className={cn(actionButton, 'hover:text-[var(--color-success)]')}
            title="有用"
          >
            <ThumbsUp size={12} aria-hidden="true" />
          </button>
          <button
            type="button"
            onClick={() => onFeedback('down')}
            className={cn(actionButton, 'hover:text-[var(--color-error)]')}
            title="无用"
          >
            <ThumbsDown size={12} aria-hidden="true" />
          </button>
        </>
      )}
    </div>
  );
};

interface ToolCallCardProps {
  name: string;
  arguments: Record<string, unknown>;
  result: string | undefined;
  error: string | undefined;
  isRunning: boolean | undefined;
}

/**
 * A tool call, labelled only by what the caller actually knows.
 *
 * A call with no result, no error and no running flag reports nothing: three
 * states exist, and inferring a fourth from their absence would be a guess.
 */
export const ToolCallCard: React.FC<ToolCallCardProps> = ({ name, arguments: args, result, error, isRunning }) => {
  const { t } = useI18n();
  const [expanded, setExpanded] = useState(false);

  const status = error ? 'error' : isRunning ? 'running' : result ? 'success' : null;
  const statusLabel =
    status === 'error'
      ? t('tool_call.status_error', { defaultValue: '失败' })
      : status === 'running'
        ? t('tool_call.status_running', { defaultValue: '执行中' })
        : status === 'success'
          ? t('tool_call.status_success', { defaultValue: '完成' })
          : null;
  const statusTone =
    status === 'error'
      ? 'text-[var(--color-error)]'
      : status === 'running'
        ? 'text-[var(--color-accent-foreground)]'
        : 'text-[var(--color-success)]';
  const hasOutput = result !== undefined && result !== '';

  return (
    <div data-tool-call className="w-full min-w-0">
      <div
        className={cn(
          'overflow-hidden rounded-[var(--radius-md)] border border-[var(--color-border-subtle)] transition-colors duration-150 motion-reduce:transition-none',
          expanded && 'bg-[var(--color-bg-surface-2)] border-[var(--color-border-default)]',
        )}
      >
        <button
          type="button"
          onClick={() => setExpanded(open => !open)}
          aria-expanded={expanded}
          className="flex w-full items-center gap-2 px-3 py-2 text-left text-xs text-[var(--color-text-primary)] transition-colors duration-150 hover:bg-[var(--color-bg-surface-2)] motion-reduce:transition-none"
        >
          <Terminal size={12} aria-hidden="true" className="shrink-0 text-[var(--color-text-muted)]" />
          <span className="min-w-0 flex-1 truncate font-medium">{name}</span>
          {statusLabel && (
            <span className={cn('flex shrink-0 items-center gap-1.5', statusTone)}>
              {status === 'running' && (
                <span
                  aria-hidden="true"
                  className="size-1.5 rounded-full bg-[var(--color-accent-foreground)] motion-safe:animate-pulse"
                />
              )}
              {statusLabel}
            </span>
          )}
          <ChevronDown
            size={12}
            aria-hidden="true"
            className={cn(
              'shrink-0 text-[var(--color-text-muted)] transition-transform duration-150 motion-reduce:transition-none',
              expanded && 'rotate-180',
            )}
          />
        </button>
        {expanded && (
          <div className="space-y-3 border-t border-[var(--color-border-subtle)] px-3 py-2.5">
            <div>
              <p className="mb-1.5 text-[10px] font-semibold uppercase tracking-wider text-[var(--color-text-muted)]">
                {t('tool_call.arguments', { defaultValue: '参数' })}
              </p>
              <pre className="code-block text-xs whitespace-pre-wrap">{JSON.stringify(args, null, 2)}</pre>
            </div>
            {hasOutput && (
              <div>
                <p className="mb-1.5 text-[10px] font-semibold uppercase tracking-wider text-[var(--color-text-muted)]">
                {t('tool_call.result', { defaultValue: '执行结果' })}
                </p>
                <pre className="code-block text-xs whitespace-pre-wrap">{result}</pre>
              </div>
            )}
            {error && (
              <div>
                <p className="mb-1.5 text-[10px] font-semibold uppercase tracking-wider text-[var(--color-error)]">
                  {t('tool_call.error_detail', { defaultValue: '错误详情' })}
                </p>
                <pre className="code-block text-xs whitespace-pre-wrap text-[var(--color-error)]">{error}</pre>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default MessageContent;
