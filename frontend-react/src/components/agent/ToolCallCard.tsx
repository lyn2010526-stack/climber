import { useEffect, useId, useState } from 'react';
import type { ElementType } from 'react';
import {
  ChevronDown, ChevronRight,
  Terminal, FileText, FilePen, Globe,
  Database, Wrench, Search, Plug,
} from 'lucide-react';
import { useI18n } from '../../i18n';
import { cn } from '../../lib/utils';
import { formatDuration } from '../../lib/duration';
import type { StatusTone } from '../../lib/icons';
import { StatusIcon } from '../ui/StatusIcon';
import { ToolCodeBlock, ToolDisclosure } from './ToolDisclosure';
import { resolveToolStatus, stringifyPayload, normalizeToolStatus, type ToolCallStatus, type ToolStatusDescriptor } from './toolCallStatus';
import { selectOutputText } from './toolOutput';

/**
 * One tool call, in the order Codex prints one: what ran, what it is doing,
 * how long it took, and then the payload it produced.
 *
 * The layers are separated by typography and indentation, not by boxes: the
 * tool name is monospace in the syntax-function role because it is a callable
 * identifier, the status rides the shared `StatusIcon` tone vocabulary, and
 * every measurement is monospace so digits line up down a column of cards. A
 * folded card still carries name, status and duration, which is what makes
 * the folded list scannable.
 */
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

/**
 * Tool name to glyph, the same mapping a tool card and any future surface
 * (mobile stream, trace tree) share. Every row names the intent it reports
 * and the aliases a tool's wire name may spell it with; the first matching
 * row wins, so an ordering change is a review, and anything unmatched falls
 * to the plain wrench rather than to a guess.
 */
const TOOL_ICON_RULES: { keys: string[]; icon: ElementType }[] = [
  { keys: ['read_file', 'file_read', 'read_file_content', 'open_file', 'view_file'], icon: FileText },
  { keys: ['write_file', 'file_write', 'edit_file', 'create_file', 'save_file', 'patch_file'], icon: FilePen },
  { keys: ['container_exec', 'run_command', 'execute_command', 'exec', 'bash', 'shell', 'terminal', 'run_script'], icon: Terminal },
  { keys: ['web_search', 'search_web', 'web_fetch', 'fetch_url', 'http_request', 'open_url', 'browse'], icon: Globe },
  { keys: ['database_query', 'query_database', 'sql', 'db_query'], icon: Database },
  { keys: ['glob', 'grep', 'search_files', 'find_files', 'list_dir', 'list_files'], icon: Search },
  { keys: ['mcp'], icon: Plug },
];

/** Look a tool's wire name up in the shared icon table. */
export function getToolIcon(name: string, toolType?: ToolCall['toolType']): ElementType {
  const wire = (name || '').toLowerCase();
  if (toolType === 'mcp') return Plug;
  for (const rule of TOOL_ICON_RULES) {
    for (const key of rule.keys) {
      if (wire.includes(key) || wire.includes(key.replace(/_/g, ''))) return rule.icon;
    }
  }
  return Wrench;
}

/**
 * The start edge of a card carries its status, so a folded card is readable
 * without parsing its wording. It is a hairline in the same role the
 * `StatusIcon` beside it uses, and every tone is named here, so a tone added
 * to `StatusIcon` cannot reach a tool card without this rail answering for it.
 */
export const STATUS_RAIL: Record<StatusTone, string> = {
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
export function hasContent(call: ToolCall): boolean {
  return Object.keys(call.arguments).length > 0 || call.result !== undefined || !!call.error;
}

/**
 * One status, rendered as a badge: the pill is the shared neutral surface,
 * the glyph and the wording take the tone's own colour, and a running badge
 * is the one that breathes. The label travels with the colour, so the pill is
 * never the only carrier of the state.
 */
function ToolStatusBadge({ descriptor }: { descriptor: ToolStatusDescriptor }) {
  return (
    <span
      className={cn(
        'inline-flex max-w-full items-center gap-[var(--space-1)] rounded-full border border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-3)] px-[var(--space-1-5)] py-[var(--space-0-5)]',
        descriptor.pulse && 'motion-safe:animate-pulse',
      )}
    >
      {descriptor.pulse
        ? <span aria-hidden="true" className="size-1.5 shrink-0 rounded-full bg-[var(--color-accent-foreground)]" />
        : <StatusIcon tone={descriptor.tone} size="xs" spin={descriptor.spin} className="shrink-0" />}
      <span className={cn('min-w-0 truncate text-[length:var(--text-2xs)]', descriptor.className)}>{descriptor.label}</span>
    </span>
  );
}

/**
 * Arguments are serialized only inside this component, which mounts on open,
 * so a folded card never pays for a payload it is not showing.
 */
function ToolArgumentBlock({
  args,
  label,
}: {
  args: Record<string, unknown>;
  label: string;
}) {
  return <ToolCodeBlock label={label} copyable>{stringifyPayload(args)}</ToolCodeBlock>;
}

/**
 * One tool call card. Expansion has two layers: the default this card starts
 * from (the global preference may raise it), and the parent's record of a
 * decision the user already made, which wins over the default.
 */
export function ToolCallCard({
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

  const Icon = getToolIcon(call.name, call.toolType);
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
      'min-w-0 max-w-full overflow-hidden rounded-[var(--radius-md)] border border-s-2 border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-2)]',
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
              <span className="flex shrink-0 items-center gap-[var(--space-1)] rounded-[var(--radius-sm)] border border-[var(--color-info)]/30 px-[var(--space-1-5)] py-[var(--space-0-5)] text-[length:var(--text-2xs)] text-[var(--color-info)]">
                <StatusIcon tone="info" size="xs" />
                mcp
              </span>
            )}
            {!(hideRunningStatus && callStatus === 'running') && (
              <ToolStatusBadge descriptor={status} />
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
              <ToolCodeBlock label={t('tool_call.result')} copyable copyText={call.result}>{output.text}</ToolCodeBlock>
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
              <ToolCodeBlock tone="error" label={t('tool_call.error_detail')} copyable>{call.error}</ToolCodeBlock>
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

export default ToolCallCard;
