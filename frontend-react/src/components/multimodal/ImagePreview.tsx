import { Loader2, X } from 'lucide-react';

import { cn } from '../../lib/utils';
import { formatBytes, type ImageAttachment } from './attachments';

/**
 * One attachment thumbnail chip: preview, name, size (or reading state) and a
 * remove button. Rendered inside `ImageAttachmentBar` but usable standalone.
 */

export interface ImagePreviewProps {
  attachment: ImageAttachment;
  /** Omit to render without a remove control. */
  onRemove?: (id: string) => void;
  disabled?: boolean;
  className?: string;
}

const ERROR_LABELS: Record<string, string> = {
  type: 'Unsupported type',
  size: 'Too large',
  limit: 'Limit reached',
  read: 'Read failed',
};

export function ImagePreview({ attachment, onRemove, disabled = false, className }: ImagePreviewProps) {
  const isReading = attachment.status === 'reading';
  const isError = attachment.status === 'error';

  return (
    <span
      className={cn(
        'flex items-center gap-2 rounded-[var(--radius-md)] border bg-[var(--color-bg-surface)] py-1 pl-1 pr-2',
        isError ? 'border-[var(--color-danger,red)]/60' : 'border-[var(--color-border-subtle)]',
        className,
      )}
      data-status={attachment.status}
      data-testid="image-preview-chip"
    >
      <span className="relative size-8 shrink-0 overflow-hidden rounded-[var(--radius-sm)] bg-[var(--color-bg-surface-2)]">
        {attachment.url && (attachment.kind ?? 'image') === 'image'
          ? (
              <img
                src={attachment.url}
                alt={attachment.name}
                className="size-full object-cover"
                data-testid="image-preview-thumb"
              />
            )
          : null}
        {isReading
          ? <Loader2 aria-hidden className="absolute inset-0 m-auto size-4 animate-spin text-[var(--color-text-muted)]" />
          : null}
      </span>
      <span className="flex min-w-0 flex-col leading-tight">
        <span className="max-w-[7.5rem] truncate text-xs text-[var(--color-text-secondary)]">
          {attachment.name}
        </span>
        <span
          className={cn(
            'text-[10px]',
            isError ? 'text-[var(--color-danger,red)]' : 'text-[var(--color-text-muted)]',
          )}
        >
          {isError
            ? ERROR_LABELS[attachment.error ?? ''] ?? 'Failed'
            : isReading
              ? 'Reading…'
              : formatBytes(attachment.size)}
        </span>
      </span>
      {onRemove
        ? (
            <button
              type="button"
              onClick={() => onRemove(attachment.id)}
              disabled={disabled}
              aria-label={`Remove ${attachment.name}`}
              className={cn(
                'shrink-0 rounded-full p-0.5 text-[var(--color-text-muted)] transition-colors duration-150',
                'hover:bg-[var(--color-bg-surface-2)] hover:text-[var(--color-text-secondary)]',
                'focus-visible:outline-none focus-visible:shadow-[var(--focus-ring)]',
                'disabled:cursor-not-allowed disabled:opacity-60 motion-reduce:transition-none',
              )}
              data-testid="image-preview-remove"
            >
              <X aria-hidden className="size-3.5" />
            </button>
          )
        : null}
    </span>
  );
}
