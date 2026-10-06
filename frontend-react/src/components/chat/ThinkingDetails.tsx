import { useEffect, useId, useRef, useState } from 'react';
import { ChevronRight } from 'lucide-react';
import { cn } from '../../lib/utils';
import { useI18n } from '../../i18n';

interface ThinkingDetailsProps {
  /** The reasoning stream ended. Drives the dots and the fold, nothing else. */
  isComplete?: boolean;
  /** Only rendered when a caller measured a real duration. */
  elapsedTime?: number;
  defaultOpen?: boolean;
  children: React.ReactNode;
  className?: string;
}

/**
 * The three dots of a running stream, breathing one after another. Motion is
 * the stream's own cue and every dot is decorative, so a slow run never
 * implies progress the stream cannot report honestly.
 */
function PulseEllipsis() {
  return (
    <span aria-hidden="true" className="flex shrink-0 items-center gap-[var(--space-0-5)]">
      {[0, 1, 2].map(i => (
        <span
          key={i}
          className="size-1 rounded-full bg-[var(--color-text-muted)] motion-safe:animate-pulse"
          style={{ animationDelay: `${i * 150}ms` }}
        />
      ))}
    </span>
  );
}

/**
 * Collapsible reasoning block, the shape a thinking stream takes in a
 * transcript (the same pattern MonkeyCode's thinking strip reads as).
 *
 * While the stream runs the trigger states the kind of content and breathes;
 * once it ends the block folds itself and the summary line reports the real
 * facts a caller measured: the character count of what was thought, and the
 * elapsed time when one was measured. Toggling stays available after the
 * stream ends, and the panel stays mounted while collapsed so the transcript
 * keeps its text.
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
  // A user who toggled the block owns it: the fold that arrives with the end
  // of the stream takes back only blocks nobody has an opinion about.
  const touched = useRef(false);
  const wasComplete = useRef(isComplete);

  useEffect(() => {
    if (!wasComplete.current && isComplete && !touched.current) setIsOpen(false);
    wasComplete.current = isComplete;
  }, [isComplete]);

  // The count is read off the rendered children, so any node a caller passes
  // counts the same way, and the number is the transcript's own.
  const countRef = useRef<HTMLDivElement>(null);
  const [charCount, setCharCount] = useState<number | undefined>(() =>
    typeof children === 'string' ? children.length : undefined,
  );
  useEffect(() => {
    if (typeof children === 'string') {
      setCharCount(children.length);
      return;
    }
    setCharCount(countRef.current?.textContent?.length);
  }, [children, isComplete]);

  const handleToggle = () => {
    touched.current = true;
    setIsOpen(open => !open);
  };

  return (
    <div
      data-thinking-details
      className={cn('my-2 min-w-0 max-w-full overflow-hidden rounded-[var(--radius-lg)] border border-[var(--color-border-subtle)] transition-colors duration-150 hover:border-[var(--color-border-default)] motion-reduce:transition-none', className)}
    >
      <button
        type="button"
        aria-expanded={isOpen}
        aria-controls={panelId}
        onClick={handleToggle}
        className="flex w-full min-w-0 items-center gap-2 px-3 py-2 text-left text-xs text-[var(--color-text-muted)] transition-colors duration-150 hover:bg-[var(--color-bg-surface-2)] hover:text-[var(--color-text-secondary)] focus-visible:outline-none focus-visible:shadow-[var(--focus-ring)] motion-reduce:transition-none"
      >
        <span
          aria-hidden="true"
          className={cn(
            'size-[6px] shrink-0 rounded-[var(--radius-pill)]',
            isComplete ? 'bg-[var(--color-text-muted)]' : 'bg-[var(--color-accent-foreground)] motion-safe:animate-pulse',
          )}
        />
        <ChevronRight
          size={12}
          aria-hidden="true"
          className={cn('shrink-0 transition-transform duration-150 motion-reduce:transition-none', isOpen && 'rotate-90')}
        />
        <span className="min-w-0 truncate">{t('common.thinking', { defaultValue: '思考中' })}</span>
        {isComplete && charCount !== undefined && (
          <span className="shrink-0 font-mono text-[11px] tabular-nums text-[var(--color-text-disabled)]">
            {t('chat.thinking_chars', { count: charCount })}
          </span>
        )}
        {!isComplete && <PulseEllipsis />}
        {elapsedTime !== undefined && (
          <span className="ms-auto shrink-0 font-mono text-[11px] tabular-nums text-[var(--color-text-disabled)]">
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
        <div ref={countRef} className="whitespace-pre-wrap break-words font-mono text-xs leading-relaxed text-[var(--color-text-secondary)]">
          {children}
        </div>
      </div>
    </div>
  );
}

export default ThinkingDetails;
