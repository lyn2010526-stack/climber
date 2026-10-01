import { useId, useState } from 'react';
import { BrainCircuit, ChevronDown } from 'lucide-react';
import { cn } from '../../lib/utils';
import { useI18n } from '../../i18n';

interface MobileThinkingBlockProps {
  reasoning: string;
  /**
   * While the turn streams the header reads "thinking" with a pulsing dot;
   * once the turn settles it reads back as the static "thinking process".
   */
  streaming?: boolean;
  defaultOpen?: boolean;
}

/**
 * The reasoning trace, as an iOS-styled collapsible panel.
 *
 * The panel is a button plus a grid-tracked body: the body stays in the tree
 * with a `0fr` row while collapsed, so expanding animates the row height and
 * screen readers keep a stable target through `aria-controls`. Reasoning is a
 * trace, so it reads as quiet mono text instead of a second message.
 */
export function MobileThinkingBlock({ reasoning, streaming = false, defaultOpen = false }: MobileThinkingBlockProps) {
  const { t } = useI18n();
  const [open, setOpen] = useState(defaultOpen);
  const contentId = useId();

  return (
    <div data-thinking-block className="w-full min-w-0">
      <button
        type="button"
        onClick={() => setOpen(current => !current)}
        aria-expanded={open}
        aria-controls={contentId}
        className="flex min-h-[44px] w-full items-center gap-2 rounded-[var(--radius-md)] px-1.5 py-2 text-left text-xs text-[var(--color-text-muted)] transition-colors duration-150 hover:bg-[var(--color-bg-surface-2)] hover:text-[var(--color-text-secondary)] focus-visible:outline-none focus-visible:shadow-[var(--focus-ring)] motion-reduce:transition-none"
      >
        <BrainCircuit size={14} aria-hidden="true" className={cn('shrink-0', streaming && 'motion-safe:animate-pulse')} />
        <span className="shrink-0 font-medium">{streaming ? t('mobile_chat.thinking_active') : t('mobile_chat.thinking_process')}</span>
        {streaming && (
          <span
            aria-hidden="true"
            className="size-1.5 shrink-0 rounded-full bg-[var(--color-accent-foreground)] motion-safe:animate-pulse"
          />
        )}
        <ChevronDown
          size={14}
          aria-hidden="true"
          className={cn('ml-auto shrink-0 transition-transform duration-200 motion-reduce:transition-none', open && 'rotate-180')}
        />
      </button>
      <div
        id={contentId}
        aria-hidden={!open}
        className="grid transition-[grid-template-rows] duration-200 ease-out motion-reduce:transition-none"
        style={{ gridTemplateRows: open ? '1fr' : '0fr' }}
      >
        <div className="min-h-0 overflow-hidden">
          <div className="border-t border-[var(--color-border-subtle)] py-2">
            <p className="whitespace-pre-wrap break-words font-mono text-xs leading-relaxed text-[var(--color-text-secondary)]">
              {reasoning}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

export default MobileThinkingBlock;
