import React, { useMemo } from 'react';
import { cn } from '../../lib/utils';
import { useI18n } from '../../i18n';
import { WorkbenchIcon } from '../ui/WorkbenchIcon';
import cards from '../chat/chatCards.module.css';

/**
 * The empty transcript of a chat, and the only thing it offers: a four-point
 * star, a title, and a short list of example instructions that send straight
 * into the conversation when pressed.
 *
 * The page-level "nothing here yet" surface is `components/ui/EmptyState`:
 * that one takes a named icon and a single action, and it is what the catalog
 * pages use. The chat needs a different contract -- a caller-supplied list of
 * suggestion buttons under the message, and a title that falls back to the
 * translated default -- so it has its own component under a name that says
 * which surface it belongs to. A grep for `EmptyState` no longer has to guess
 * which of the two contracts a call site wants.
 *
 * Example cards are not a second send path: each one calls the same `onSend`
 * the composer uses, so a press is indistinguishable from typing the example
 * and pressing Enter. They carry no marketing copy and no decorative gradient;
 * surface, border, radius, spacing and text all come from the token layer.
 */
export interface ChatExample {
  /** Stable identity for the card; the label is also the sent text. */
  id: string;
  label: string;
}

interface ChatEmptyStateProps {
  title?: string;
  description?: string;
  icon?: React.ReactNode;
  actions?: React.ReactNode;
  /** Example instructions; a press sends `label` through `onSend`. */
  examples?: ChatExample[];
  /** The composer's send contract. Omit to render examples as inert text. */
  onSend?: (content: string) => void;
  /** Blocks presses while a turn is streaming, matching the composer guard. */
  disabled?: boolean;
  className?: string;
  'data-testid'?: string;
}

export const ChatEmptyState: React.FC<ChatEmptyStateProps> = ({
  title,
  description,
  icon,
  actions,
  examples = [],
  onSend,
  disabled = false,
  className,
  'data-testid': testId,
}) => {
  const { t } = useI18n();

  const resolvedExamples = useMemo<ChatExample[]>(() => {
    if (examples.length > 0) return examples;
    return [
      { id: 'plan', label: t('anchored.welcome.example_plan', { defaultValue: 'Draft a refactoring plan for my project' }) },
      { id: 'task', label: t('anchored.welcome.example_task', { defaultValue: 'Break this down and run subtasks in parallel' }) },
      { id: 'code', label: t('anchored.welcome.example_code', { defaultValue: 'Analyze this architecture and suggest improvements' }) },
    ];
  }, [examples, t]);

  return (
    <div data-testid={testId} className={cn('flex-1 flex items-center justify-center p-4', className)}>
      <div className="w-full max-w-lg text-center">
        <div className="mb-4 flex justify-center text-[var(--color-accent-foreground)]">
          {icon ?? (
            <span className={cards.iconTile}>
              <WorkbenchIcon name="spark" size={20} data-testid="chat-empty-icon" />
            </span>
          )}
        </div>
        <h3 className="text-base font-medium text-[var(--color-text-primary)]">
          {title ?? t('chat.empty_state_title', { defaultValue: 'Start a conversation' })}
        </h3>
        {description && (
          <p className="mt-2 text-sm leading-relaxed text-[var(--color-text-secondary)]">{description}</p>
        )}
        {resolvedExamples.length > 0 && (
          <ul className="mt-5 grid gap-[var(--space-2)] sm:grid-cols-2">
            {resolvedExamples.map((example) => (
              <li key={example.id}>
                <div className={cards.card}>
                  <button
                    type="button"
                    data-testid={`chat-example-${example.id}`}
                    disabled={disabled || !onSend}
                    onClick={() => onSend?.(example.label)}
                    className={cn(
                      'flex w-full items-center gap-[var(--space-2)] px-[var(--space-3)] py-[var(--space-2-5)] text-left',
                      'text-[length:var(--text-sm)] text-[var(--color-text-secondary)] transition-colors duration-150',
                      'hover:text-[var(--color-text-primary)]',
                      'focus-visible:outline-none focus-visible:shadow-[var(--focus-ring)] motion-reduce:transition-none',
                      'disabled:cursor-not-allowed disabled:opacity-60',
                    )}
                  >
                    <WorkbenchIcon
                      name="spark"
                      size={14}
                      className="shrink-0 text-[var(--color-text-muted)]"
                    />
                    <span className="min-w-0">{example.label}</span>
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}
        {actions && <div className="mt-5 flex flex-wrap justify-center gap-2">{actions}</div>}
      </div>
    </div>
  );
};

export default ChatEmptyState;
