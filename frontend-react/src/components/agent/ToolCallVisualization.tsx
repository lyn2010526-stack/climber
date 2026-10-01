import { useState } from 'react';
import { useI18n } from '../../i18n';
import { cn } from '../../lib/utils';
import type { StatusTone } from '../../lib/icons';
import { StatusIcon } from '../ui/StatusIcon';
import { ToolCallCard, hasContent, type ToolCall } from './ToolCallCard';
import { buildToolStatusSummary, countToolStatuses, type ToolCallStatus } from './toolCallStatus';
import { useAutoExpandTools } from './toolExpansion';

export { ToolCallCard, hasContent, getToolIcon } from './ToolCallCard';
export type { ToolCallStatus };
export type { ToolCall };

export interface ToolCallVisualizationProps {
  calls: ToolCall[];
  className?: string;
  defaultExpanded?: boolean;
  hideRunningStatus?: boolean;
}

export function ToolCallVisualization({
  calls,
  className,
  defaultExpanded = false,
  hideRunningStatus = false,
}: ToolCallVisualizationProps) {
  const { t } = useI18n();
  const [autoExpand, toggleAutoExpand] = useAutoExpandTools();
  const [overrides, setOverrides] = useState<Record<string, boolean>>({});

  const handleToggle = (id: string, expanded: boolean) => {
    setOverrides(prev => ({ ...prev, [id]: expanded }));
  };

  if (calls.length === 0) return null;

  // The same default the cards start from, so the all/toggle control always
  // describes what the cards are actually showing.
  const isDefaultExpanded = (call: ToolCall) => defaultExpanded || (autoExpand && hasContent(call));
  const allExpanded = calls.every(call => overrides[call.id] ?? isDefaultExpanded(call));
  const handleToggleAll = () => {
    const next = !allExpanded;
    setOverrides(Object.fromEntries(calls.map(call => [call.id, next])));
  };

  // Every tally is read off the normalized status, so a value this build does
  // not recognise is never counted as a healthy one.
  const summary = buildToolStatusSummary(countToolStatuses(calls), t);
  return (
    <div className={cn('min-w-0 max-w-full space-y-[var(--space-1-5)]', className)}>
      <div className="mb-[var(--space-2)] flex flex-wrap items-center justify-between gap-[var(--space-2)] px-[var(--space-1)]">
        <div className="flex min-w-0 flex-wrap items-center gap-[var(--space-2)]" aria-live="polite">
          <span className="min-w-0 truncate text-[length:var(--text-2xs)] font-medium uppercase tracking-wide text-[var(--color-text-muted)]">
            {t('tool_call.summary', { count: calls.length })}
          </span>
          {summary.map(entry => (
            <span
              key={entry.tone}
              title={entry.label}
              aria-label={entry.label}
              className="flex shrink-0 items-center gap-[var(--space-1)] text-[length:var(--text-2xs)]"
            >
              <StatusDot tone={entry.tone} />
              <span className="font-mono tabular-nums text-[var(--color-text-secondary)]">{entry.count}</span>
            </span>
          ))}
        </div>
        <div className="flex shrink-0 items-center gap-[var(--space-3)]">
          <button type="button"
            aria-pressed={autoExpand}
            onClick={toggleAutoExpand}
            className="text-[length:var(--text-2xs)] text-[var(--color-text-muted)] transition-colors hover:text-[var(--color-text-secondary)] focus-visible:outline-none focus-visible:shadow-[var(--focus-ring)] motion-reduce:transition-none"
          >
            {t('tool_call.auto_expand')}
          </button>
          <button type="button"
            className="text-[length:var(--text-2xs)] text-[var(--color-text-muted)] transition-colors hover:text-[var(--color-text-secondary)] focus-visible:outline-none focus-visible:shadow-[var(--focus-ring)] motion-reduce:transition-none"
            onClick={handleToggleAll}
          >
            {allExpanded ? t('tool_call.collapse_all') : t('tool_call.expand_all')}
          </button>
        </div>
      </div>

      {calls.map(call => (
        <ToolCallCard
          key={call.id}
          call={call}
          autoExpand={autoExpand}
          initialExpanded={isDefaultExpanded(call)}
          expandedOverride={overrides[call.id]}
          onToggle={handleToggle}
          hideRunningStatus={hideRunningStatus}
        />
      ))}
    </div>
  );
}

/**
 * The tally line is a count, not a place to repeat a status phrase: the glyph
 * and its tone say which state, the number says how many, and the full phrase
 * travels in the label so it reaches a screen reader and a hover without
 * printing the same wording on every card below.
 */
function StatusDot({ tone }: { tone: StatusTone }) {
  return <StatusIcon tone={tone} size="xs" />;
}

export default ToolCallVisualization;
