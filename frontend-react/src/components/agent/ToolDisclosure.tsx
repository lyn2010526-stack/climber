import { useId, useRef, useState } from 'react';
import type { ReactNode } from 'react';
import { Check, ChevronDown, ChevronRight, Copy } from 'lucide-react';
import { useI18n } from '../../i18n';
import { cn } from '../../lib/utils';

/**
 * Copy an exact payload to the clipboard. The text it copies is decided by the
 * caller, so the button on a clipped preview can carry the full payload
 * instead of the clip. The confirmation is a swap of the glyph and the label,
 * not a toast, and it reverts on its own.
 */
export function ToolCopyButton({ text, className }: { text: string; className?: string }) {
  const { t } = useI18n();
  const [copied, setCopied] = useState(false);
  const revert = useRef<number | undefined>(undefined);

  const handleCopy = () => {
    try {
      void navigator.clipboard?.writeText(text);
      setCopied(true);
      window.clearTimeout(revert.current);
      revert.current = window.setTimeout(() => setCopied(false), 1600);
    } catch {
      // A blocked clipboard costs the confirmation, never the render.
    }
  };

  return (
    <button
      type="button"
      onClick={handleCopy}
      aria-label={copied ? t('tool_call.copied') : t('tool_call.copy')}
      title={copied ? t('tool_call.copied') : t('tool_call.copy')}
      className={cn(
        'inline-flex size-[var(--space-6)] shrink-0 items-center justify-center rounded-[var(--radius-sm)] text-[var(--color-text-muted)] transition-colors hover:text-[var(--color-text-primary)] focus-visible:outline-none focus-visible:shadow-[var(--focus-ring)] motion-reduce:transition-none',
        className,
      )}
    >
      {copied
        ? <Check size={12} aria-hidden="true" className="text-[var(--color-success)]" />
        : <Copy size={12} aria-hidden="true" />}
    </button>
  );
}

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
 * the layout wide. `copyable` adds an overlay copy button; it costs no layout
 * and copies `copyText` when one is given, so a clipped preview still copies
 * the whole payload.
 */
export function ToolCodeBlock({
  children,
  className,
  tone = 'default',
  label,
  copyable = false,
  copyText,
}: {
  children: string;
  className?: string;
  tone?: 'default' | 'error';
  label?: string;
  /** Render an overlay copy button for this payload. */
  copyable?: boolean;
  /** The text the copy button carries. Omitted, it copies `children`. */
  copyText?: string;
}) {
  const block = (
    <pre
      tabIndex={0}
      aria-label={label}
      className={cn(
        'mt-[var(--space-1)] max-h-48 max-w-full overflow-auto whitespace-pre-wrap break-words rounded-[var(--radius-md)] border p-[var(--space-2-5)] font-mono text-[length:var(--text-2xs)]',
        tone === 'error'
          ? 'border-[var(--color-error)]/30 bg-[var(--color-error-subtle)] text-[var(--color-error)]'
          : 'border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-3)] text-[var(--color-text-secondary)]',
        className,
      )}
    >
      {children}
    </pre>
  );
  if (!copyable) return block;
  return (
    <div className="group relative">
      {block}
      <ToolCopyButton
        text={copyText ?? children}
        className="absolute end-[var(--space-2)] top-[var(--space-2)] bg-[var(--color-bg-surface-1)]/85 backdrop-blur-sm"
      />
    </div>
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
