import { cn } from '../../lib/utils';
import { useI18n } from '../../i18n';

interface ThinkingIndicatorProps {
  /** Backend-supplied label. Omitted, the indicator states the plain "thinking" fact. */
  stage?: string;
  isActive?: boolean;
  compact?: boolean;
  className?: string;
}

/**
 * A single working state: a pulsing dot plus a factual label.
 *
 * The label is either what the caller knows (a real stage) or the plain
 * "thinking" fact. No progress bar and no stage sequence, because the message
 * stream carries no ordering the component could report honestly.
 */
export function ThinkingIndicator({ stage, isActive = true, compact = false, className }: ThinkingIndicatorProps) {
  const { t } = useI18n();
  if (!isActive) return null;

  return (
    <div
      role="status"
      data-thinking-indicator
      className={cn(
        'flex items-center gap-2 text-[var(--color-text-muted)]',
        compact ? 'text-xs' : 'py-2 text-sm',
        className,
      )}
    >
      <span
        aria-hidden="true"
        className="size-1.5 shrink-0 rounded-full bg-[var(--color-accent-foreground)] motion-safe:animate-pulse"
      />
      <span className="min-w-0 truncate">{stage || t('common.thinking')}</span>
    </div>
  );
}
