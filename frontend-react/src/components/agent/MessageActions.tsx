import { useEffect, useRef, useState } from 'react';
import { Check, Copy, Pencil, RefreshCw } from 'lucide-react';
import { useI18n } from '../../i18n';
import { cn } from '../../lib/utils';

/**
 * The action row that belongs to a single message: copy the text, edit it, or
 * regenerate the reply. It is revealed by the row's hover state through the
 * `group/message` contract, so it costs no React state in the message itself,
 * and each action is a 2xl glyph that swaps its confirm state in place instead
 * of raising a toast.
 *
 * Only the actions the caller wires up are rendered: an absent `onEdit` or
 * `onRegenerate` is a message that cannot do it, so the button is left out
 * rather than shown disabled. Copy is always present because it needs only the
 * message content.
 */
export interface MessageActionsProps {
  /** The text the copy action writes to the clipboard. */
  content: string;
  /** Present when the message can be edited; omit to hide the action. */
  onEdit?: () => void;
  /** Present when the message can be regenerated; omit to hide the action. */
  onRegenerate?: () => void;
  className?: string;
  'data-testid'?: string;
}

const CHECKMARK_MS = 2000;

export function MessageActions({
  content,
  onEdit,
  onRegenerate,
  className,
  'data-testid': testId,
}: MessageActionsProps) {
  const { t } = useI18n();
  const [copied, setCopied] = useState(false);
  const revert = useRef<number | undefined>(undefined);

  useEffect(() => () => window.clearTimeout(revert.current), []);

  const handleCopy = () => {
    try {
      void navigator.clipboard?.writeText(content);
    } catch {
      // A blocked clipboard costs the confirmation, never the render.
    }
    setCopied(true);
    window.clearTimeout(revert.current);
    revert.current = window.setTimeout(() => setCopied(false), CHECKMARK_MS);
  };

  const actionClass = cn(
    'inline-flex size-[var(--space-6)] shrink-0 items-center justify-center rounded-[var(--radius-sm)]',
    'text-[var(--color-text-muted)] transition-colors duration-150 hover:bg-[var(--color-bg-surface-2)] hover:text-[var(--color-text-primary)]',
    'focus-visible:outline-none focus-visible:shadow-[var(--focus-ring)] motion-reduce:transition-none',
  );

  return (
    <div
      data-testid={testId}
      className={cn(
        'flex items-center gap-[var(--space-0-5)]',
        'opacity-0 transition-opacity group-hover/message:opacity-100 focus-within:opacity-100 motion-reduce:transition-none',
        className,
      )}
    >
      <button
        type="button"
        onClick={handleCopy}
        aria-label={copied ? t('message.copied', { defaultValue: 'Copied' }) : t('message.copy', { defaultValue: 'Copy' })}
        title={copied ? t('message.copied', { defaultValue: 'Copied' }) : t('message.copy', { defaultValue: 'Copy' })}
        className={actionClass}
      >
        {copied
          ? <Check size={14} aria-hidden="true" className="text-[var(--color-success)]" data-testid="message-copy-check" />
          : <Copy size={14} aria-hidden="true" />}
      </button>
      {onEdit && (
        <button
          type="button"
          onClick={onEdit}
          aria-label={t('message.edit', { defaultValue: 'Edit' })}
          title={t('message.edit', { defaultValue: 'Edit' })}
          className={actionClass}
        >
          <Pencil size={14} aria-hidden="true" />
        </button>
      )}
      {onRegenerate && (
        <button
          type="button"
          onClick={onRegenerate}
          aria-label={t('message.regenerate', { defaultValue: 'Regenerate' })}
          title={t('message.regenerate', { defaultValue: 'Regenerate' })}
          className={actionClass}
        >
          <RefreshCw size={14} aria-hidden="true" />
        </button>
      )}
    </div>
  );
}

export default MessageActions;
