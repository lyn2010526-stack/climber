import { useEffect, useId, useMemo, useRef, useState } from 'react';
import type { ElementType } from 'react';
import {
  ChevronDown, ChevronRight,
  Terminal, FileText, FilePen, Globe,
  Database, Wrench, Search, Plug,
  ShieldAlert, ShieldCheck, Check, Copy,
} from 'lucide-react';
import { useI18n } from '../../i18n';
import { cn } from '../../lib/utils';
import { formatDuration } from '../../lib/duration';
import type { StatusTone } from '../../lib/icons';
import { StatusIcon } from '../ui/StatusIcon';
import { Button } from '../ui/Button';

export type AgentToolStatus =
  | 'pending'
  | 'awaiting-approval'
  | 'running'
  | 'success'
  | 'error'
  | 'cancelled';

export interface AgentToolCardProps {
  name: string;
  status: AgentToolStatus;
  input?: unknown;
  output?: unknown;
  elapsedMs?: number;
  onApprove?: () => void;
  onDeny?: () => void;
  className?: string;
  defaultExpanded?: boolean;
}

interface StatusDescriptor {
  tone: StatusTone;
  labelKey: string;
  labelDefault: string;
  pulse?: boolean;
  spin?: boolean;
}

const STATUS_DESCRIPTOR: Record<AgentToolStatus, StatusDescriptor> = {
  pending: { tone: 'queued', labelKey: 'agent_tool.status_pending', labelDefault: 'Waiting' },
  'awaiting-approval': { tone: 'approval', labelKey: 'agent_tool.status_awaiting_approval', labelDefault: 'Awaiting approval' },
  running: { tone: 'loading', labelKey: 'agent_tool.status_running', labelDefault: 'Running', spin: true },
  success: { tone: 'success', labelKey: 'agent_tool.status_success', labelDefault: 'Completed' },
  error: { tone: 'error', labelKey: 'agent_tool.status_error', labelDefault: 'Failed' },
  cancelled: { tone: 'unknown', labelKey: 'agent_tool.status_cancelled', labelDefault: 'Cancelled' },
};

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

const TOOL_ICON_RULES: { keys: string[]; icon: ElementType }[] = [
  { keys: ['read_file', 'file_read', 'read_file_content', 'open_file', 'view_file'], icon: FileText },
  { keys: ['write_file', 'file_write', 'edit_file', 'create_file', 'save_file', 'patch_file'], icon: FilePen },
  { keys: ['container_exec', 'run_command', 'execute_command', 'exec', 'bash', 'shell', 'terminal', 'run_script'], icon: Terminal },
  { keys: ['web_search', 'search_web', 'web_fetch', 'fetch_url', 'http_request', 'open_url', 'browse'], icon: Globe },
  { keys: ['database_query', 'query_database', 'sql', 'db_query'], icon: Database },
  { keys: ['glob', 'grep', 'search_files', 'find_files', 'list_dir', 'list_files'], icon: Search },
  { keys: ['mcp'], icon: Plug },
];

export function getAgentToolIcon(name: string): ElementType {
  const wire = (name || '').toLowerCase();
  for (const rule of TOOL_ICON_RULES) {
    for (const key of rule.keys) {
      if (wire.includes(key) || wire.includes(key.replace(/_/g, ''))) return rule.icon;
    }
  }
  return Wrench;
}

const MAX_PREVIEW = 160;

function asText(value: unknown): string | undefined {
  if (value === undefined || value === null) return undefined;
  if (typeof value === 'string') return value;
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}

function previewOf(text: string | undefined): string | undefined {
  if (text === undefined) return undefined;
  const singleLine = text.replace(/\s+/g, ' ').trim();
  if (singleLine.length <= MAX_PREVIEW) return singleLine;
  return `${singleLine.slice(0, MAX_PREVIEW)}…`;
}

function CopyPayloadButton({ text }: { text: string }) {
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
      aria-label={copied ? t('agent_tool.copied', { defaultValue: 'Copied' }) : t('agent_tool.copy', { defaultValue: 'Copy' })}
      title={copied ? t('agent_tool.copied', { defaultValue: 'Copied' }) : t('agent_tool.copy', { defaultValue: 'Copy' })}
      className="inline-flex size-[var(--space-6)] shrink-0 items-center justify-center rounded-[var(--radius-sm)] text-[var(--color-text-muted)] transition-colors hover:text-[var(--color-text-primary)] focus-visible:outline-none focus-visible:shadow-[var(--focus-ring)] motion-reduce:transition-none"
    >
      {copied
        ? <Check size={12} aria-hidden="true" className="text-[var(--color-success)]" />
        : <Copy size={12} aria-hidden="true" />}
    </button>
  );
}

function PayloadBlock({ label, text, tone = 'default' }: { label: string; text: string; tone?: 'default' | 'error' }) {
  return (
    <div className="relative">
      <span className="text-[length:var(--text-2xs)] font-medium uppercase tracking-wide text-[var(--color-text-muted)]">{label}</span>
      <pre
        tabIndex={0}
        aria-label={label}
        className={cn(
          'mt-[var(--space-1)] max-h-48 max-w-full overflow-auto whitespace-pre-wrap break-words rounded-[var(--radius-md)] border p-[var(--space-2-5)] font-mono text-[length:var(--text-2xs)]',
          tone === 'error'
            ? 'border-[var(--color-error)]/30 bg-[var(--color-error-subtle)] text-[var(--color-error)]'
            : 'border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-3)] text-[var(--color-text-secondary)]',
        )}
      >
        {text}
      </pre>
      <CopyPayloadButton text={text} />
    </div>
  );
}

export function AgentToolCard({
  name,
  status,
  input,
  output,
  elapsedMs,
  onApprove,
  onDeny,
  className,
  defaultExpanded = false,
}: AgentToolCardProps) {
  const { t } = useI18n();
  const panelId = useId();
  const descriptor = STATUS_DESCRIPTOR[status];
  const awaitingApproval = status === 'awaiting-approval';

  const [expanded, setExpanded] = useState(defaultExpanded || awaitingApproval);

  useEffect(() => {
    if (awaitingApproval) setExpanded(true);
  }, [awaitingApproval]);

  const inputText = useMemo(() => asText(input), [input]);
  const outputText = useMemo(() => asText(output), [output]);
  const preview = previewOf(status === 'error' ? (outputText ?? inputText) : (outputText ?? inputText));
  const hasBody = inputText !== undefined || outputText !== undefined;

  const Icon = getAgentToolIcon(name);
  const duration = elapsedMs !== undefined ? formatDuration(elapsedMs, 'ms') : undefined;

  return (
    <div
      data-testid="agent-tool-card"
      data-status={status}
      className={cn(
        'min-w-0 max-w-full overflow-hidden rounded-[var(--radius-md)] border border-s-2 border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-2)]',
        STATUS_RAIL[descriptor.tone],
        className,
      )}
    >
      <button
        type="button"
        className="flex w-full items-start gap-[var(--space-2)] px-[var(--space-3)] py-[var(--space-2)] text-start transition-colors hover:bg-[var(--color-bg-surface-3)] focus-visible:outline-none focus-visible:shadow-[var(--focus-ring)] motion-reduce:transition-none"
        onClick={() => setExpanded((prev) => !prev)}
        aria-expanded={expanded}
        aria-controls={panelId}
      >
        <Icon size={14} aria-hidden="true" className="mt-[var(--space-0-5)] shrink-0 text-[var(--color-text-muted)]" />

        <span className="min-w-0 flex-1">
          <span className="flex flex-wrap items-center gap-x-[var(--space-2)] gap-y-[var(--space-1)]">
            <span className="min-w-0 break-all font-mono text-[length:var(--text-xs)] font-medium text-[var(--color-syntax-function)]">
              {name}
            </span>
            <span
              className={cn(
                'inline-flex max-w-full items-center gap-[var(--space-1)] rounded-[var(--radius-pill)] border border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-3)] px-2 py-px',
                'text-[11px] font-medium leading-[17px]',
                descriptor.pulse && 'motion-safe:animate-pulse',
              )}
            >
              <StatusIcon tone={descriptor.tone} size="xs" spin={descriptor.spin} className="shrink-0" />
              <span className="min-w-0 truncate text-[var(--color-text-secondary)]">
                {t(descriptor.labelKey, { defaultValue: descriptor.labelDefault })}
              </span>            </span>
            {duration && (
              <span className="ms-auto shrink-0 font-mono text-[length:var(--text-2xs)] tabular-nums text-[var(--color-syntax-number)]">
                {duration}
              </span>
            )}
          </span>
          {!expanded && preview && (
            <span className="mt-[var(--space-0-5)] block truncate font-mono text-[length:var(--text-2xs)] text-[var(--color-text-muted)]">
              {preview}
            </span>
          )}
        </span>

        {expanded
          ? <ChevronDown size={14} aria-hidden="true" className="mt-[var(--space-0-5)] shrink-0 text-[var(--color-text-muted)]" />
          : <ChevronRight size={14} aria-hidden="true" className="mt-[var(--space-0-5)] shrink-0 text-[var(--color-text-muted)]" />}
      </button>

      {expanded && hasBody && (
        <div id={panelId} className="space-y-[var(--space-2)] border-t border-[var(--color-border-subtle)] px-[var(--space-3)] pb-[var(--space-3)] pt-[var(--space-2)]">
          {inputText !== undefined && (
            <div data-tool-input>
              <PayloadBlock label={t('agent_tool.input', { defaultValue: 'Input' })} text={inputText} />
            </div>
          )}
          {outputText !== undefined && (
            <div data-tool-output>
              <PayloadBlock
                label={t('agent_tool.output', { defaultValue: 'Output' })}
                text={outputText}
                tone={status === 'error' ? 'error' : 'default'}
              />
            </div>
          )}
        </div>
      )}

      {awaitingApproval && (
        <div
          data-testid="agent-tool-approval"
          className="flex flex-wrap items-center gap-[var(--space-2)] border-t border-[var(--color-border-accent)] bg-[var(--color-bg-surface-3)] px-[var(--space-3)] py-[var(--space-2)]"
        >
          <span className="flex min-w-0 items-center gap-[var(--space-1)] text-[length:var(--text-2xs)] font-medium text-[var(--color-accent-foreground)]">
            <ShieldAlert size={12} aria-hidden="true" className="shrink-0" />
            <span className="min-w-0 truncate">{t('agent_tool.needs_approval', { defaultValue: 'This tool needs your approval' })}</span>
          </span>
          <span className="ms-auto flex shrink-0 items-center gap-[var(--space-1-5)]">
            <Button size="xs" variant="ghost" onClick={onDeny}>
              {t('agent_tool.deny', { defaultValue: 'Deny' })}
            </Button>
            <Button size="xs" variant="secondary" onClick={onApprove}>
              {t('agent_tool.allow_once', { defaultValue: 'Allow once' })}
            </Button>
            <Button
              size="xs"
              variant="primary"
              icon={<ShieldCheck size={12} aria-hidden="true" />}
              onClick={onApprove}
            >
              {t('agent_tool.always_allow', { defaultValue: 'Always allow' })}
            </Button>
          </span>
        </div>
      )}
    </div>
  );
}

export default AgentToolCard;
