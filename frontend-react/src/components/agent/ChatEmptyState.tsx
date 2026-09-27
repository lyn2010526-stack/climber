import React from 'react';
import { cn } from '../../lib/utils';
import { useI18n } from '../../i18n';

/**
 * The empty transcript of a chat, and nothing else.
 *
 * The page-level "nothing here yet" surface is `components/ui/EmptyState`:
 * that one takes a named icon and a single action, and it is what the catalog
 * pages use. The chat needs a different contract -- a caller-supplied list of
 * suggestion buttons under the message, and a title that falls back to the
 * translated default -- so it has its own component under a name that says
 * which surface it belongs to. A grep for `EmptyState` no longer has to guess
 * which of the two contracts a call site wants.
 */
interface ChatEmptyStateProps {
  title?: string;
  description?: string;
  icon?: React.ReactNode;
  actions?: React.ReactNode;
  className?: string;
}

export const ChatEmptyState: React.FC<ChatEmptyStateProps> = ({
  title,
  description,
  icon,
  actions,
  className,
}) => {
  const { t } = useI18n();
  return (
    <div className={cn('flex-1 flex items-center justify-center p-4', className)}>
      <div className="w-full max-w-lg text-center">
        {icon && <div className="mb-4 flex justify-center text-[var(--color-text-secondary)]">{icon}</div>}
        <h3 className="text-base font-medium text-[var(--color-text-primary)]">{title ?? t('chat.empty_state_title', { defaultValue: '开始对话' })}</h3>
        {description && <p className="mt-2 text-sm leading-relaxed text-[var(--color-text-secondary)]">{description}</p>}
        {actions && <div className="mt-5 flex flex-wrap justify-center gap-2">{actions}</div>}
      </div>
    </div>
  );
};

export default ChatEmptyState;
