import { useEffect, useId, useRef, useState } from 'react';
import { ChevronDown } from 'lucide-react';
import { useI18n } from '../../i18n';
import { cn } from '../../lib/utils';

/**
 * The model's reasoning as a collapsible block, with the behaviour the
 * transcript needs and none of the markup the caller owns.
 *
 * While `active` is true the panel opens itself and follows the stream to the
 * bottom, because the thought is the thing being watched. The moment streaming
 * ends it records how long the thought ran, waits a beat, and folds once; the
 * trigger then reads "Thought for N seconds" so a collapsed block still reports
 * that the model did work. A `defaultOpen={false}` opts out of the auto-open but
 * keeps the duration, so a caller can present a closed-by-default trace that
 * still measures itself.
 *
 * The body is plain text, streamed as-is, so a partial thought never needs a
 * markdown pass to stay on screen.
 */
export interface ReasoningPanelProps {
  /** The reasoning text. Partial text is expected while `active`. */
  text: string;
  /** True while the thought is still streaming in. */
  active: boolean;
  /** The final transcript state, used for the status treatment. */
  status?: 'active' | 'complete' | 'error' | 'paused';
  /** Open on first render. Defaults to `active` so a live thought starts open. */
  defaultOpen?: boolean;
  className?: string;
  'data-testid'?: string;
}

const AUTO_COLLAPSE_MS = 1000;
const MS_PER_SECOND = 1000;

export function ReasoningPanel({
  text,
  active,
  status,
  defaultOpen,
  className,
  'data-testid': testId,
}: ReasoningPanelProps) {
  const { t } = useI18n();
  const resolvedDefaultOpen = defaultOpen ?? false;
  const [open, setOpen] = useState(resolvedDefaultOpen);
  const [duration, setDuration] = useState<number | undefined>(undefined);
  const [autoCollapsed, setAutoCollapsed] = useState(false);
  const startRef = useRef<number | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const panelId = useId();

  useEffect(() => {
    if (active) {
      if (startRef.current === null) startRef.current = Date.now();
      return;
    }
    if (startRef.current !== null) {
      setDuration(Math.ceil((Date.now() - startRef.current) / MS_PER_SECOND));
      startRef.current = null;
    }
  }, [active]);

  useEffect(() => {
    if (!active && open && !autoCollapsed && startRef.current === null && duration !== undefined) {
      const timer = window.setTimeout(() => {
        setOpen(false);
        setAutoCollapsed(true);
      }, AUTO_COLLAPSE_MS);
      return () => window.clearTimeout(timer);
    }
  }, [active, open, autoCollapsed, duration]);

  useEffect(() => {
    if (active && open && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [text, active, open]);

  const resolvedStatus = status ?? (active ? 'active' : 'complete');
  const label = resolvedStatus === 'active'
    ? t('reasoning.thinking', { defaultValue: 'Thinking...' })
    : resolvedStatus === 'error'
      ? t('reasoning.thinking_error', { defaultValue: 'Thinking failed' })
      : resolvedStatus === 'paused'
        ? t('reasoning.thinking_paused', { defaultValue: 'Thinking paused' })
        : duration === undefined
          ? t('reasoning.thought_for_unknown', { defaultValue: 'Thought for a few seconds' })
          : t('reasoning.thought_for', { count: duration, defaultValue: 'Thought for {{count}} seconds' });

  return (
    <div data-testid={testId} className={cn('not-prose', className)}>
      <button
        type="button"
        aria-expanded={open}
        aria-controls={panelId}
        onClick={() => setOpen((prev) => !prev)}
        data-state={resolvedStatus}
        className={cn(
          'flex w-full items-center gap-[var(--space-1-5)] text-[length:var(--text-2xs)] font-medium',
          'text-[var(--color-text-muted)] transition-colors hover:text-[var(--color-text-primary)]',
          resolvedStatus === 'active' && 'text-[var(--color-info)]',
          resolvedStatus === 'error' && 'text-[var(--color-error)]',
          resolvedStatus === 'paused' && 'text-[var(--color-warning)]',
          resolvedStatus === 'complete' && 'text-[var(--color-success)]',
          'focus-visible:outline-none focus-visible:shadow-[var(--focus-ring)] motion-reduce:transition-none',
        )}
      >
        <span className={cn(
          'min-w-0 truncate',
          resolvedStatus === 'active' && 'motion-safe:animate-pulse motion-reduce:animate-none',
        )} data-testid="reasoning-label">
          {label}
        </span>
        <ChevronDown
          size={12}
          aria-hidden="true"
          className={cn('shrink-0 transition-transform motion-reduce:transition-none', open ? 'rotate-180' : 'rotate-0')}
        />
      </button>
      {open && (
        <div
          id={panelId}
          ref={scrollRef}
          data-testid="reasoning-content"
          className={cn(
            'mt-[var(--space-1-5)] max-h-[200px] overflow-y-auto whitespace-pre-wrap break-words',
            'rounded-[var(--radius-lg)] border border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-2)]',
            'px-[var(--space-3)] py-[var(--space-2)] text-[length:var(--text-2xs)] leading-relaxed',
            'text-[var(--color-text-secondary)] [overflow-anchor:none]',
          )}
        >
          {text}
        </div>
      )}
    </div>
  );
}

export default ReasoningPanel;
