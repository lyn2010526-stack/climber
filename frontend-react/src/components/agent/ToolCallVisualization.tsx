import React, { useEffect, useId, useState } from 'react';
import {
  ChevronDown, ChevronRight,
  Terminal, Code2, FileSearch, Globe,
  Database, Wrench,
} from 'lucide-react';
import { useI18n } from '../../i18n';
import { cn } from '../../lib/utils';
import { formatDuration } from '../../lib/duration';
import type { StatusTone } from '../../lib/icons';
import { StatusIcon } from '../ui/StatusIcon';
import { ToolCodeBlock, ToolDisclosure } from './ToolDisclosure';
import { resolveToolStatus, stringifyPayload, normalizeToolStatus, type ToolCallStatus } from './toolCallStatus';
import { useAutoExpandTools } from './toolExpansion';
import { selectOutputText } from './toolOutput';

export type { ToolCallStatus };

export interface ToolCall {
  id: string;
  name: string;
  displayName?: string;
  arguments: Record<string, unknown>;
  result?: string;
  error?: string;
  status: ToolCallStatus;
  duration?: number;
  startTime?: string;
  toolType?: 'builtin' | 'mcp' | 'custom';
}

interface ToolCallVisualizationProps {
  calls: ToolCall[];
  className?: string;
  defaultExpanded?: boolean;
  hideRunningStatus?: boolean;
}

const toolIcons: Record<string, React.ElementType> = {
  file_read: FileSearch,
  file_write: Code2,
  run_command: Terminal,
  web_search: Globe,
  database_query: Database,
};

function getToolIcon(name: string): React.ElementType {
  for (const [key, icon] of Object.entries(toolIcons)) {
    if (name.includes(key) || name.includes(key.replace('_', ''))) return icon;
  }
  return Wrench;
}

/**
 * The start edge of a card carries its status, so a folded card is readable
 * without parsing its wording. It is a hairline in the same role the `StatusIcon`
 * beside it uses, and every tone is named here, so a tone added to
 * `StatusIcon` cannot reach a tool card without this rail answering for it.
 */
const STATUS_RAIL: Record<StatusTone, string> = {
  error: 'border-s-[var(--color-error)]',
  success: 'border-s-[var(--color-success)]',
  warning: 'border-s-[var(--color-warning)]',
  info: 'border-s-[var(--color-info)]',
  loading: 'border-s-[var(--color-border-strong)]',
  queued: 'border-s-[var(--color-border-default)]',
  approval: 'border-s-[var(--color-border-accent)]',
  unknown: 'border-s-[var(--color-unknown)]',
};

/** A card with neither arguments nor any output has nothing to unfold. */
function hasContent(call: ToolCall): boolean {
  return Object.keys(call.arguments).length > 0 || call.result !== undefined || !!call.error;
}

/** Arguments are serialized only inside this component, which mounts on open. */
const ToolArgumentBlock = React.memo(function ToolArgumentBlock({
  args,
  label,
}: {
  args: Record<string, unknown>;
  label: string;
}) {
  return <ToolCodeBlock label={label}>{stringifyPayload(args)}</ToolCodeBlock>;
});

/**
 * One tool call, in the order Codex prints one: what ran, what it is doing, how
 * long it took, and then the payload it produced.
 *
 * The layers are separated by typography and indentation, not by boxes: the
 * tool name is monospace in the syntax-function role because it is a callable
 * identifier, the status rides the shared `StatusIcon` tone vocabulary, and
 * every measurement is monospace so digits line up down a column of cards. A
 * folded card still carries name, status and duration, which is what makes the
 * folded list scannable.
 */
function ToolCallCard({
  call,
  autoExpand,
  initialExpanded,
  expandedOverride,
  onToggle,
  hideRunningStatus,
}: {
  call: ToolCall;
  autoExpand: boolean;
  initialExpanded: boolean;
  /** The parent's record of a decision the user already made about this card. */
  expandedOverride: boolean | undefined;
  onToggle: (id: string, expanded: boolean) => void;
  hideRunningStatus: boolean;
}) {
  const { t } = useI18n();
  const panelId = useId();
  const [paramsOpen, setParamsOpen] = useState(false);
  const [showAllOutput, setShowAllOutput] = useState(false);
  const content = hasContent(call);
  const [defaultExpanded, setDefaultExpanded] = useState(initialExpanded);

  // Layer one, the default: the global preference may raise it, and a card
  // that has content is the only one worth opening on its own.
  useEffect(() => {
    if (autoExpand && content) setDefaultExpanded(true);
  }, [autoExpand, content]);

  // Layer two, the override, wins over the default. The parent records it only
  // when the user acts, so no re-render and no preference change can undo a
  // decision the user already made.
  const isExpanded = expandedOverride ?? defaultExpanded;
  const handleToggle = () => onToggle(call.id, !isExpanded);

  // Collapsing returns the output to its clipped form, so a card reopened
  // later starts from the same summary every other collapsed card shows.
  useEffect(() => {
    if (!isExpanded) setShowAllOutput(false);
  }, [isExpanded]);

  const Icon = getToolIcon(call.name);
  // Normalize first: the union is a rendering contract, the wire value is
  // whatever the backend sent, and an unrecognised value must read as
  // "not reported" rather than silently as still-waiting.
  const callStatus = normalizeToolStatus(call.status);
  const status = resolveToolStatus(callStatus, t);
  const argumentCount = Object.keys(call.arguments).length;
  const preview = callStatus === 'error' ? call.error : call.result;
  const previewTone = callStatus === 'error';
  const output = call.result === undefined ? undefined : selectOutputText(call.result, showAllOutput);
  const argumentLabel = t('tool_call.arguments');

  return (
    <div className={cn(
      'overflow-hidden rounded-[var(--radius-md)] border border-s-2 border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-2)]',
      STATUS_RAIL[status.tone],
    )}>
      <button type="button"
        className="flex w-full items-start gap-[var(--space-2)] px-[var(--space-3)] py-[var(--space-2)] text-start transition-colors hover:bg-[var(--color-bg-surface-3)] focus-visible:outline-none focus-visible:shadow-[var(--focus-ring)] motion-reduce:transition-none"
        onClick={handleToggle}
        aria-expanded={isExpanded}
        aria-controls={panelId}
      >
        <Icon size={14} aria-hidden="true" className="mt-[var(--space-0-5)] shrink-0 text-[var(--color-text-muted)]" />

        <span className="min-w-0 flex-1">
          <span className="flex flex-wrap items-center gap-x-[var(--space-2)] gap-y-[var(--space-1)]">
            <span className="min-w-0 break-all font-mono text-[length:var(--text-xs)] font-medium text-[var(--color-syntax-function)]">
              {call.displayName || call.name}
            </span>
            {call.toolType === 'mcp' && (
              <span className="flex items-center gap-[var(--space-1)] rounded-[var(--radius-sm)] border border-[var(--color-info)]/30 px-[var(--space-1-5)] py-[var(--space-0-5)] text-[length:var(--text-2xs)] text-[var(--color-info)]">
                <StatusIcon tone="info" size="xs" />
                mcp
              </span>
            )}
            {!(hideRunningStatus && callStatus === 'running') && (
              <>
                <StatusIcon tone={status.tone} size="xs" spin={status.spin} className="shrink-0" />
                <span className={cn('text-[length:var(--text-2xs)]', status.className)}>{status.label}</span>
              </>
            )}
            {call.duration !== undefined && (
              <span className="ms-auto shrink-0 font-mono text-[length:var(--text-2xs)] tabular-nums text-[var(--color-syntax-number)]">
                {formatDuration(call.duration, 'ms')}
              </span>
            )}
          </span>
          {!isExpanded && preview && (
            <span className={cn('mt-[var(--space-0-5)] block truncate font-mono text-[length:var(--text-2xs)]', previewTone ? 'text-[var(--color-error)]' : 'text-[var(--color-text-muted)]')}>
              {preview}
            </span>
          )}
        </span>

        {isExpanded
          ? <ChevronDown size={14} aria-hidden="true" className="mt-[var(--space-0-5)] shrink-0 text-[var(--color-text-muted)]" />
          : <ChevronRight size={14} aria-hidden="true" className="mt-[var(--space-0-5)] shrink-0 text-[var(--color-text-muted)]" />}
      </button>

      {isExpanded && (
        <div id={panelId} className="space-y-[var(--space-2)] border-t border-[var(--color-border-subtle)] px-[var(--space-3)] pb-[var(--space-3)] pt-[var(--space-2)]">
          {/* The output is the reason the call happened, so it is the body of
              the card. Arguments are context for that output and stay folded. */}
          {output && (
            <div data-tool-output>
              <ToolCodeBlock label={t('tool_call.result')}>{output.text}</ToolCodeBlock>
              {output.truncated && (
                <button
                  type="button"
                  onClick={() => setShowAllOutput(true)}
                  className="mt-[var(--space-1)] text-[length:var(--text-2xs)] text-[var(--color-text-muted)] underline-offset-2 transition-colors hover:text-[var(--color-text-primary)] hover:underline focus-visible:outline-none focus-visible:shadow-[var(--focus-ring)] motion-reduce:transition-none"
                >
                  {t('tool_call.show_all', { count: output.fullLength.toLocaleString() })}
                </button>
              )}
            </div>
          )}

          {call.error && (
            <div data-tool-error>
              <span className="text-[length:var(--text-2xs)] font-medium uppercase tracking-wide text-[var(--color-error)]">{t('tool_call.error_detail')}</span>
              <ToolCodeBlock tone="error" label={t('tool_call.error_detail')}>{call.error}</ToolCodeBlock>
            </div>
          )}

          {argumentCount > 0 && (
            <ToolDisclosure
              title={argumentLabel}
              badge={String(argumentCount)}
              open={paramsOpen}
              onOpenChange={setParamsOpen}
            >
              <ToolArgumentBlock args={call.arguments} label={argumentLabel} />
            </ToolDisclosure>
          )}
        </div>
      )}
    </div>
  );
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

  // Every count is read off the normalized status, so a value this build does
  // not recognise is never counted as a healthy one.
  const tally = (status: ToolCallStatus) => calls.filter(call => normalizeToolStatus(call.status) === status).length;
  const runningCount = tally('running');
  const pendingCount = tally('pending');
  const successCount = tally('success');
  const errorCount = tally('error');

  /**
   * The tally line is a count, not a place to repeat a status phrase: the glyph
   * and its tone say which state, the number says how many, and the full phrase
   * travels in the label so it reaches a screen reader and a hover without
   * printing the same wording on every card below.
   */
  const summary: { tone: StatusTone; count: number; label: string }[] = [];
  if (runningCount > 0) {
    summary.push({
      tone: resolveToolStatus('running', t).tone,
      count: runningCount,
      label: t('tool_call.running_count', { count: runningCount }),
    });
  }
  if (pendingCount > 0) {
    const pending = resolveToolStatus('pending', t);
    summary.push({ tone: pending.tone, count: pendingCount, label: pending.label });
  }
  if (successCount > 0) {
    const success = resolveToolStatus('success', t);
    summary.push({ tone: success.tone, count: successCount, label: success.label });
  }
  if (errorCount > 0) {
    const error = resolveToolStatus('error', t);
    summary.push({ tone: error.tone, count: errorCount, label: error.label });
  }

  return (
    <div className={cn('space-y-[var(--space-1-5)]', className)}>
      <div className="mb-[var(--space-2)] flex flex-wrap items-center justify-between gap-[var(--space-2)] px-[var(--space-1)]">
        <div className="flex flex-wrap items-center gap-[var(--space-2)]" aria-live="polite">
          <span className="text-[length:var(--text-2xs)] font-medium uppercase tracking-wide text-[var(--color-text-muted)]">
            {t('tool_call.summary', { count: calls.length })}
          </span>
          {summary.map(entry => (
            <span
              key={entry.tone}
              title={entry.label}
              aria-label={entry.label}
              className="flex items-center gap-[var(--space-1)] text-[length:var(--text-2xs)]"
            >
              <StatusIcon tone={entry.tone} size="xs" />
              <span className="font-mono tabular-nums text-[var(--color-text-secondary)]">{entry.count}</span>
            </span>
          ))}
        </div>
        <div className="flex items-center gap-[var(--space-3)]">
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
