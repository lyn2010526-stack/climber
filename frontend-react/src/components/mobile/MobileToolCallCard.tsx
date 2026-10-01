import { useId, useState } from 'react';
import { AlertCircle, CheckCircle2, ChevronDown, CircleDashed, Loader2, Terminal } from 'lucide-react';
import { cn } from '../../lib/utils';
import { useI18n } from '../../i18n';
import { normalizeToolStatus, stringifyPayload } from '../agent/toolCallStatus';
import type { ToolCall } from '../../useChat';

/**
 * Visual state for a tool call. The canonical lifecycle comes from
 * `components/agent/toolCallStatus` (`normalizeToolStatus`), and the three
 * outcome states get their own icon and colour here; every non-outcome state
 * (pending, cancelled, awaiting approval, unreported) reads as a quiet neutral
 * badge, because none of them claims a fault or a success.
 */
type MobileToolVisual = 'running' | 'success' | 'error' | 'neutral';

const VISUAL_META: Record<MobileToolVisual, { icon: typeof Terminal; spin: boolean; text: string; dot: string }> = {
  running: {
    icon: Loader2,
    spin: true,
    text: 'text-[var(--color-accent-foreground)]',
    dot: 'bg-[var(--color-accent-foreground)] motion-safe:animate-pulse',
  },
  success: {
    icon: CheckCircle2,
    spin: false,
    text: 'text-[var(--color-success)]',
    dot: 'bg-[var(--color-success)]',
  },
  error: {
    icon: AlertCircle,
    spin: false,
    text: 'text-[var(--color-error)]',
    dot: 'bg-[var(--color-error)]',
  },
  neutral: {
    icon: CircleDashed,
    spin: false,
    text: 'text-[var(--color-text-muted)]',
    dot: 'bg-[var(--color-text-disabled)]',
  },
};

const LABEL_KEY: Record<string, string> = {
  pending: 'mobile_chat.tool_status_pending',
  running: 'mobile_chat.tool_status_running',
  success: 'mobile_chat.tool_status_success',
  error: 'mobile_chat.tool_status_error',
  cancelled: 'mobile_chat.tool_status_cancelled',
  awaiting_approval: 'mobile_chat.tool_status_approval',
  unknown: 'mobile_chat.tool_status_unknown',
};

function resolveVisual(tool: ToolCall): { visual: MobileToolVisual; canonical: string } {
  if (tool.error) return { visual: 'error', canonical: 'error' };
  const canonical = normalizeToolStatus(tool.status);
  if (canonical === 'running') return { visual: 'running', canonical };
  if (canonical === 'success') return { visual: 'success', canonical };
  if (canonical === 'error') return { visual: 'error', canonical };
  // A streamed call that already carries output but has not reported a status
  // yet reads as done; one with neither reads as not reported.
  if (canonical === 'unknown' && tool.result) return { visual: 'success', canonical };
  return { visual: 'neutral', canonical };
}

/**
 * A tool call, as a card: icon, name, status badge, and the arguments and
 * result collapsed under an animated chevron. The body stays in the tree while
 * collapsed (a `0fr` grid row), so expanding is animated and `aria-controls`
 * keeps one stable target.
 */
export function MobileToolCallCard({ tool }: { tool: ToolCall }) {
  const { t } = useI18n();
  const [expanded, setExpanded] = useState(false);
  const bodyId = useId();
  const { visual, canonical } = resolveVisual(tool);
  const meta = VISUAL_META[visual];
  const Icon = meta.icon;
  const label = t(LABEL_KEY[canonical] ?? 'mobile_chat.tool_status_unknown');
  const argsText = stringifyPayload(tool.arguments);
  const hasResult = tool.result !== undefined && tool.result !== '';

  return (
    <div
      data-tool-call
      data-tool-status={canonical}
      className="w-full min-w-0 overflow-hidden rounded-[var(--radius-lg)] border border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-1)] transition-colors duration-150 motion-reduce:transition-none"
    >
      <button
        type="button"
        onClick={() => setExpanded(current => !current)}
        aria-expanded={expanded}
        aria-controls={bodyId}
        className="flex min-h-[44px] w-full items-center gap-2 px-3 py-2 text-left transition-colors duration-150 hover:bg-[var(--color-bg-surface-2)] focus-visible:outline-none focus-visible:shadow-[var(--focus-ring)] motion-reduce:transition-none"
      >
        <span className="flex size-7 shrink-0 items-center justify-center rounded-[var(--radius-sm)] bg-[var(--color-bg-surface-2)]">
          <Icon size={14} aria-hidden="true" className={cn('text-[var(--color-text-secondary)]', meta.spin && 'animate-spin motion-reduce:animate-none')} />
        </span>
        <span className="min-w-0 flex-1 truncate font-mono text-xs font-medium text-[var(--color-text-primary)]">{tool.name}</span>
        <span className={cn('flex shrink-0 items-center gap-1.5 text-xs font-medium', meta.text)}>
          <span aria-hidden="true" className={cn('size-1.5 rounded-full', meta.dot)} />
          {label}
        </span>
        <ChevronDown
          size={14}
          aria-hidden="true"
          className={cn('shrink-0 text-[var(--color-text-muted)] transition-transform duration-200 motion-reduce:transition-none', expanded && 'rotate-180')}
        />
      </button>
      <div
        id={bodyId}
        aria-hidden={!expanded}
        className="grid transition-[grid-template-rows] duration-200 ease-out motion-reduce:transition-none"
        style={{ gridTemplateRows: expanded ? '1fr' : '0fr' }}
      >
        <div className="min-h-0 overflow-hidden">
          <div className="space-y-3 border-t border-[var(--color-border-subtle)] px-3 py-2.5">
            <div className="min-w-0">
              <p className="mb-1 text-[10px] font-semibold uppercase tracking-wider text-[var(--color-text-muted)]">
                {t('mobile_chat.tool_arguments')}
              </p>
              <pre className="code-block max-h-48 overflow-auto whitespace-pre-wrap break-words">{argsText}</pre>
            </div>
            {hasResult && (
              <div className="min-w-0">
                <p className="mb-1 text-[10px] font-semibold uppercase tracking-wider text-[var(--color-text-muted)]">
                  {t('mobile_chat.tool_result')}
                </p>
                <pre className="code-block max-h-64 overflow-auto whitespace-pre-wrap break-words">{tool.result}</pre>
              </div>
            )}
            {tool.error && (
              <div className="min-w-0">
                <p className="mb-1 text-[10px] font-semibold uppercase tracking-wider text-[var(--color-error)]">
                  {t('mobile_chat.tool_error_detail')}
                </p>
                <pre className="code-block max-h-64 overflow-auto whitespace-pre-wrap break-words text-[var(--color-error)]">{tool.error}</pre>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default MobileToolCallCard;
