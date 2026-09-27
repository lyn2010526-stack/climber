import { useId, useState } from 'react';
import { ChevronRight } from 'lucide-react';
import { cn } from '../../lib/utils';
import { useI18n } from '../../i18n';

interface ThinkingDetailsProps {
  /** The reasoning stream ended. Drives the dot, nothing else. */
  isComplete?: boolean;
  /** Only rendered when a caller measured a real duration. */
  elapsedTime?: number;
  defaultOpen?: boolean;
  children: React.ReactNode;
  className?: string;
}

/**
 * Collapsible reasoning block.
 *
 * The trigger states the kind of content, not a stage: the label is fixed and
 * the dot is the only thing that moves, so a slow run never implies progress it
 * cannot report. Toggling stays available after the stream ends, and the panel
 * stays mounted while collapsed so the transcript keeps its text.
 */
export function ThinkingDetails({
  isComplete = false,
  elapsedTime,
  defaultOpen = false,
  children,
  className,
}: ThinkingDetailsProps) {
  const { t } = useI18n();
  const [isOpen, setIsOpen] = useState(defaultOpen);
  const panelId = useId();

  return (
    <div
      data-thinking-details
      className={cn('my-2 overflow-hidden rounded-[var(--radius-md)] border border-[var(--color-border-subtle)]', className)}
    >
      <button
        type="button"
        aria-expanded={isOpen}
        aria-controls={panelId}
        onClick={() => setIsOpen(open => !open)}
        className="flex w-full items-center gap-2 px-3 py-2 text-left text-xs text-[var(--color-text-muted)] transition-colors duration-150 hover:bg-[var(--color-bg-surface-2)] hover:text-[var(--color-text-secondary)] motion-reduce:transition-none"
      >
        <ChevronRight
          size={12}
          aria-hidden="true"
          className={cn('shrink-0 transition-transform duration-150 motion-reduce:transition-none', isOpen && 'rotate-90')}
        />
        <span
          aria-hidden="true"
          className={cn(
            'size-1.5 shrink-0 rounded-full bg-[var(--color-text-disabled)]',
            !isComplete && 'bg-[var(--color-accent-foreground)] motion-safe:animate-pulse',
          )}
        />
        <span className="min-w-0 truncate">{t('common.thinking', { defaultValue: '思考中' })}</span>
        {elapsedTime !== undefined && (
          <span className="ms-auto shrink-0 font-mono text-[11px] text-[var(--color-text-disabled)]">
            {elapsedTime.toFixed(1)}s
          </span>
        )}
      </button>
      <div
        id={panelId}
        data-reasoning-panel
        hidden={!isOpen}
        className="border-t border-[var(--color-border-subtle)] px-3 py-2"
      >
        <div className="whitespace-pre-wrap break-words font-mono text-xs leading-relaxed text-[var(--color-text-secondary)]">
          {children}
        </div>
      </div>
    </div>
  );
}

export default ThinkingDetails;
