import { useId, useState } from 'react';
import { ChevronDown, ChevronRight } from 'lucide-react';
import { cn } from '../../lib/utils';
import { useI18n } from '../../i18n';
import { StatusIcon } from '../ui/StatusIcon';
import type { StatusTone } from '../../lib/icons';

export interface ExecutionNode {
  id: string;
  label: string;
  status?: string;
  children?: ExecutionNode[];
  detail?: string;
}

export interface ExecutionTreeProps {
  nodes: ExecutionNode[];
  className?: string;
  defaultExpandedIds?: string[];
}

interface ToneStyle {
  tone: StatusTone;
  text: string;
  border: string;
}

const STATUS_TONE: Record<string, StatusTone> = {
  success: 'success',
  succeeded: 'success',
  finished: 'success',
  complete: 'success',
  completed: 'success',
  error: 'error',
  failed: 'error',
  failure: 'error',
  timeout: 'error',
  warning: 'warning',
  stopped: 'warning',
  paused: 'warning',
  pending: 'queued',
  queued: 'queued',
  waiting: 'queued',
  running: 'loading',
  in_progress: 'loading',
  active: 'loading',
  approval: 'approval',
  reviewing: 'approval',
  cancelled: 'unknown',
  canceled: 'unknown',
  terminated: 'unknown',
  skipped: 'unknown',
};

const TONE_TEXT: Record<StatusTone, string> = {
  error: 'text-[var(--color-error)]',
  success: 'text-[var(--color-success)]',
  warning: 'text-[var(--color-warning)]',
  info: 'text-[var(--color-info)]',
  loading: 'text-[var(--color-text-muted)]',
  queued: 'text-[var(--color-text-disabled)]',
  approval: 'text-[var(--color-accent)]',
  unknown: 'text-[var(--color-unknown)]',
};

/** Normalize a free-form backend status onto the shared tone vocabulary. */
export function resolveNodeTone(status?: string): StatusTone | null {
  if (!status) return null;
  return STATUS_TONE[status.trim().toLowerCase()] ?? 'unknown';
}

function toneStyle(status?: string): ToneStyle | null {
  const tone = resolveNodeTone(status);
  if (!tone) return null;
  return {
    tone,
    text: TONE_TEXT[tone],
    border: cn(
      tone === 'error' && 'border-[var(--color-error)]/40',
      tone === 'success' && 'border-[var(--color-success)]/40',
      tone === 'warning' && 'border-[var(--color-warning)]/40',
      tone === 'approval' && 'border-[var(--color-accent)]/40',
      (tone === 'loading' || tone === 'queued' || tone === 'info' || tone === 'unknown') && 'border-[var(--color-border-subtle)]',
    ),
  };
}

function collectIds(nodes: ExecutionNode[], into: string[] = []): string[] {
  for (const node of nodes) {
    into.push(node.id);
    if (node.children?.length) collectIds(node.children, into);
  }
  return into;
}

interface TreeNodeProps {
  node: ExecutionNode;
  depth: number;
  expanded: Set<string>;
  onToggle: (id: string) => void;
}

function TreeNode({ node, depth, expanded, onToggle }: TreeNodeProps) {
  const { t } = useI18n();
  const panelId = useId();
  const hasChildren = Boolean(node.children?.length);
  const isOpen = hasChildren && expanded.has(node.id);
  const tone = toneStyle(node.status);
  const statusLabel = tone ? t(`execution.status.${node.status}`, { defaultValue: node.status }) : null;

  const header = hasChildren ? (
    <button
      type="button"
      aria-expanded={isOpen}
      aria-controls={panelId}
      onClick={() => onToggle(node.id)}
      className={cn(
        'flex w-full items-center gap-[var(--space-1-5)] rounded-[var(--radius-sm)] px-[var(--space-2)] py-[var(--space-1-5)] text-start transition-colors focus-visible:outline-none focus-visible:shadow-[var(--focus-ring)] motion-reduce:transition-none',
        'hover:bg-[var(--color-bg-surface-2)]',
      )}
    >
      {isOpen
        ? <ChevronDown size={12} aria-hidden="true" className="shrink-0 text-[var(--color-text-muted)]" />
        : <ChevronRight size={12} aria-hidden="true" className="shrink-0 text-[var(--color-text-muted)]" />}
      <span className="min-w-0 flex-1 truncate text-[length:var(--text-xs)] font-medium text-[var(--color-text-primary)]">
        {node.label}
      </span>
      {tone && statusLabel}
    </button>
  ) : (
    <div className="flex w-full items-center gap-[var(--space-1-5)] rounded-[var(--radius-sm)] px-[var(--space-2)] py-[var(--space-1-5)]">
      <span aria-hidden="true" className="size-[12px] shrink-0" />
      <span className="min-w-0 flex-1 truncate text-[length:var(--text-xs)] text-[var(--color-text-secondary)]">
        {node.label}
      </span>
      {tone && statusLabel}
    </div>
  );

  return (
    <li
      data-node-id={node.id}
      data-status={node.status ?? undefined}
      className={cn(
        'relative',
        tone ? cn('border-s-2 ps-[var(--space-2)]', tone.border) : 'border-s-2 border-transparent ps-[var(--space-2)]',
      )}
    >
      {header}
      {tone && statusLabel && (
        <p className="sr-only">{t('execution.node_status', { defaultValue: 'Status' })}: {statusLabel}</p>
      )}
      {node.detail && (
        <pre className="mt-[var(--space-1)] max-h-40 max-w-full overflow-auto whitespace-pre-wrap break-words rounded-[var(--radius-sm)] border border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-3)] p-[var(--space-2)] font-mono text-[length:var(--text-2xs)] text-[var(--color-text-secondary)]">
          {node.detail}
        </pre>
      )}
      {isOpen && (
        <ul id={panelId} className="ms-[var(--space-3)] mt-[var(--space-1)] space-y-[var(--space-1)] border-s border-dashed border-[var(--color-border-subtle)] ps-[var(--space-2)]">
          {node.children!.map(child => (
            <TreeNode key={child.id} node={child} depth={depth + 1} expanded={expanded} onToggle={onToggle} />
          ))}
        </ul>
      )}
    </li>
  );
}

export function ExecutionTree({ nodes, className, defaultExpandedIds }: ExecutionTreeProps) {
  const { t } = useI18n();
  const [expanded, setExpanded] = useState<Set<string>>(
    () => new Set(defaultExpandedIds ?? collectIds(nodes)),
  );

  const onToggle = (id: string) => {
    setExpanded(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  if (nodes.length === 0) {
    return (
      <p className={cn('px-[var(--space-3)] py-[var(--space-4)] text-center text-[length:var(--text-xs)] text-[var(--color-text-muted)]', className)}>
        {t('execution.empty', { defaultValue: 'No execution steps recorded.' })}
      </p>
    );
  }

  return (
    <ul
      role="tree"
      aria-label={t('execution.tree_label', { defaultValue: 'Execution steps' })}
      className={cn('w-full space-y-[var(--space-1)]', className)}
    >
      {nodes.map(node => (
        <TreeNode key={node.id} node={node} depth={0} expanded={expanded} onToggle={onToggle} />
      ))}
    </ul>
  );
}

export default ExecutionTree;

export { TONE_TEXT as EXECUTION_TONE_TEXT };
