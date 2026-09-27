import { useId, useState } from 'react';
import type { ReactNode } from 'react';
import { ChevronDown, ChevronRight } from 'lucide-react';
import { cn } from '../../lib/utils';

/**
 * Monospace block for tool payloads, the deepest layer of a tool card. The
 * surface steps one rung below the card it sits in and the border is what
 * separates the two, so an output block never needs a shadow or a wash to read
 * as a layer.
 *
 * `error` is the one tone here: a failure is a semantic outcome, so it takes
 * the semantic error role on the text and a hairline error border on the block.
 * The label travels with it, so the colour is never the only carrier.
 *
 * Content is always fully present in the DOM and reachable by keyboard: the
 * block scrolls instead of clipping, and long lines wrap rather than pushing
 * the layout wide.
 */
export function ToolCodeBlock({
  children,
  className,
  tone = 'default',
  label,
}: {
  children: string;
  className?: string;
  tone?: 'default' | 'error';
  label?: string;
}) {
  return (
    <pre
      tabIndex={0}
      aria-label={label}
      className={cn(
        'mt-[var(--space-1)] max-h-48 overflow-auto whitespace-pre-wrap break-words rounded-[var(--radius-md)] border p-[var(--space-2-5)] font-mono text-[length:var(--text-2xs)]',
        tone === 'error'
          ? 'border-[var(--color-error)]/30 bg-[var(--color-error-subtle)] text-[var(--color-error)]'
          : 'border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-3)] text-[var(--color-text-secondary)]',
        className,
      )}
    >
      {children}
    </pre>
  );
}

interface ToolDisclosureProps {
  /** Section heading, already translated. */
  title: string;
  /** Optional trailing hint, e.g. an argument count. */
  badge?: string;
  children: ReactNode;
  defaultOpen?: boolean;
  /**
   * Controlled state. When given, the disclosure shows exactly this and the
   * caller owns the toggle, which is how a lazy payload stays unmounted until
   * the panel is actually open.
   */
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
  className?: string;
}

/**
 * Collapsible section used for every tool payload (arguments, output, raw
 * metadata) so disclosure behaviour and keyboard reach stay identical across
 * surfaces. The chevron is decorative, so the accessible name stays exactly the
 * heading plus its count.
 */
export function ToolDisclosure({ title, badge, children, defaultOpen = false, open, onOpenChange, className }: ToolDisclosureProps) {
  const [internalOpen, setInternalOpen] = useState(defaultOpen);
  const isOpen = open ?? internalOpen;
  const panelId = useId();

  const handleToggle = () => {
    const next = !isOpen;
    setInternalOpen(next);
    onOpenChange?.(next);
  };

  return (
    <div className={className}>
      <button
        type="button"
        aria-expanded={isOpen}
        aria-controls={panelId}
        onClick={handleToggle}
        className="flex items-center gap-[var(--space-1-5)] text-[length:var(--text-2xs)] font-medium text-[var(--color-text-muted)] transition-colors hover:text-[var(--color-text-primary)] focus-visible:outline-none focus-visible:shadow-[var(--focus-ring)] motion-reduce:transition-none"
      >
        {isOpen
          ? <ChevronDown size={12} aria-hidden="true" className="shrink-0" />
          : <ChevronRight size={12} aria-hidden="true" className="shrink-0" />}
        <span className="min-w-0 truncate">{title}{badge !== undefined ? ` (${badge})` : null}</span>
      </button>
      {isOpen && <div id={panelId}>{children}</div>}
    </div>
  );
}
