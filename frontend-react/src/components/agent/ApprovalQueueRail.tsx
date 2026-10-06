import { useMemo } from 'react';
import { Check, ShieldCheck, TriangleAlert, X } from 'lucide-react';
import { cn } from '../../lib/utils';
import { useI18n } from '../../i18n';
import { Badge } from '../ui/Badge';
import { Button } from '../ui/Button';

/**
 * A compact overview of everything that is parked on a human decision.
 *
 * Codex keeps a separate `pending_thread_approvals` widget that lists only the
 * threads waiting on the user (and caps itself at three with an overflow line),
 * and its `multi_select_picker` shows the same list twice: once as an overview
 * and once as the batch that a single confirm resolves. Climber's
 * `AnchoredPopupStack` renders each waiting request in full but never answers
 * "how many are queued, and can I clear them together" — this rail does, while
 * staying a dumb, controlled component so the store keeps owning the truth.
 *
 * It is deliberately not wired to a store: callers pass the queue and receive
 * decisions, which keeps the pending/failed/empty states testable in isolation.
 */

export type ApprovalDecision = 'allow' | 'deny';

export interface ApprovalQueueItem {
  id: string;
  /** What is being asked, e.g. "Run command". */
  title: string;
  /** The object under review: a command, a path, or a permission rule. */
  subject?: string;
  severity?: 'low' | 'medium' | 'high';
  /**
   * Whether a resolution can be submitted at all. A request without a tool
   * call id (see `AnchoredPopupStack`) can only be dismissed, so its decision
   * buttons are withheld rather than posting a body the backend cannot accept.
   */
  resolvable?: boolean;
}

export interface ApprovalQueueRailProps {
  items: ApprovalQueueItem[];
  onDecision: (id: string, decision: ApprovalDecision) => void;
  /** Optional bulk path; when omitted the batch buttons are not rendered. */
  onBatchDecision?: (ids: string[], decision: ApprovalDecision) => void;
  /** Ids with a submission in flight; their controls lock until it settles. */
  pendingIds?: readonly string[];
  className?: string;
}

const SEVERITY_VARIANT = {
  low: 'secondary',
  medium: 'warning',
  high: 'destructive',
} as const;

const SEVERITY_LABEL_KEY = {
  low: 'approvals.severity_low',
  medium: 'approvals.severity_medium',
  high: 'approvals.severity_high',
} as const;

const SEVERITY_FALLBACK = {
  low: '低',
  medium: '中',
  high: '高',
} as const;

/**
 * The rail keeps the oldest request on top so the queue reads top-down, the way
 * it will be worked. `items` order is the caller's contract.
 */
export function ApprovalQueueRail({
  items,
  onDecision,
  onBatchDecision,
  pendingIds = [],
  className,
}: ApprovalQueueRailProps) {
  const { t } = useI18n();
  const pending = useMemo(() => new Set(pendingIds), [pendingIds]);
  const resolvableIds = useMemo(
    () => items.filter((item) => item.resolvable !== false).map((item) => item.id),
    [items],
  );
  const idle = !items.some((item) => pending.has(item.id));

  if (items.length === 0) {
    return (
      <div
        role="status"
        data-testid="approval-queue-rail"
        data-state="empty"
        className={cn(
          'flex items-center gap-[var(--space-2)] rounded-[var(--radius-md)] border border-dashed border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-1)] px-[var(--space-3)] py-[var(--space-2)] text-[length:var(--text-xs)] text-[var(--color-text-muted)]',
          className,
        )}
      >
        <ShieldCheck size={14} aria-hidden="true" className="shrink-0 text-[var(--color-success)]" />
        {t('approvals.queue_empty', { defaultValue: '当前没有待审批的请求' })}
      </div>
    );
  }

  const countLabel = t('approvals.queue_count', {
    count: items.length,
    defaultValue: '{{count}} 项待审批',
  });

  return (
    <section
      data-testid="approval-queue-rail"
      data-state="populated"
      aria-label={countLabel}
      className={cn(
        'overflow-hidden rounded-[var(--radius-lg)] border border-[var(--color-border-accent)] bg-[var(--color-bg-surface-1)]',
        className,
      )}
    >
      <header className="flex flex-wrap items-center gap-[var(--space-2)] border-b border-[var(--color-border-subtle)] px-[var(--space-3)] py-[var(--space-2)]">
        <TriangleAlert size={14} aria-hidden="true" className="shrink-0 text-[var(--color-warning)]" />
        <span className="min-w-0 flex-1 text-[length:var(--text-xs)] font-bold text-[var(--color-text-primary)]">
          {countLabel}
        </span>
        {onBatchDecision && (
          <span className="flex shrink-0 items-center gap-[var(--space-1)]">
            <Button
              type="button"
              size="xs"
              variant="outline"
              disabled={!idle || resolvableIds.length === 0}
              onClick={() => onBatchDecision(resolvableIds, 'allow')}
              className="motion-reduce:transition-none"
            >
              {t('approvals.approve_all', { defaultValue: '全部批准' })}
            </Button>
            <Button
              type="button"
              size="xs"
              variant="ghost"
              disabled={!idle || resolvableIds.length === 0}
              onClick={() => onBatchDecision(resolvableIds, 'deny')}
              className="motion-reduce:transition-none"
            >
              {t('approvals.deny_all', { defaultValue: '全部拒绝' })}
            </Button>
          </span>
        )}
      </header>

      <ul role="list" className="divide-y divide-[var(--color-border-subtle)]">
        {items.map((item, index) => {
          const isPending = pending.has(item.id);
          const resolvable = item.resolvable !== false;
          const severity = item.severity ?? 'medium';
          return (
            <li
              key={item.id}
              role="listitem"
              data-testid="approval-queue-item"
              data-pending={isPending ? 'true' : 'false'}
              className="flex min-w-0 items-start gap-[var(--space-2)] px-[var(--space-3)] py-[var(--space-2)]"
            >
              <span
                aria-hidden="true"
                className="mt-[var(--space-0-5)] w-[2ch] shrink-0 text-center font-mono text-[length:var(--text-2xs)] tabular-nums text-[var(--color-text-disabled)]"
              >
                {index + 1}
              </span>

              <span className="min-w-0 flex-1">
                <span className="flex flex-wrap items-center gap-x-[var(--space-2)] gap-y-[var(--space-1)]">
                  <span className="min-w-0 break-words text-[length:var(--text-xs)] font-medium text-[var(--color-text-primary)]">
                    {item.title}
                  </span>
                  <Badge variant={SEVERITY_VARIANT[severity]} size="xs">
                    {t(SEVERITY_LABEL_KEY[severity], { defaultValue: SEVERITY_FALLBACK[severity] })}
                  </Badge>
                  {isPending && (
                    <span role="status" className="text-[length:var(--text-2xs)] text-[var(--color-text-muted)]">
                      {t('approvals.submitting', { defaultValue: '提交中…' })}
                    </span>
                  )}
                </span>
                {item.subject && (
                  <span
                    className="mt-[var(--space-0-5)] block truncate font-mono text-[length:var(--text-2xs)] text-[var(--color-text-secondary)]"
                    title={item.subject}
                  >
                    {item.subject}
                  </span>
                )}
                {!resolvable && (
                  <span className="mt-[var(--space-0-5)] block text-[length:var(--text-2xs)] text-[var(--color-text-muted)]">
                    {t('approvals.not_resolvable', { defaultValue: '该请求缺少可提交的标识，仅能关闭' })}
                  </span>
                )}
              </span>

              <span className="flex shrink-0 items-center gap-[var(--space-1)]">
                <Button
                  type="button"
                  size="xs"
                  variant="primary"
                  disabled={!resolvable || isPending}
                  aria-label={t('approvals.approve_item', {
                    title: item.title,
                    defaultValue: '批准：{{title}}',
                  })}
                  onClick={() => onDecision(item.id, 'allow')}
                  className="motion-reduce:transition-none"
                >
                  <Check size={12} aria-hidden="true" />
                  {t('approvals.approve', { defaultValue: '批准' })}
                </Button>
                <Button
                  type="button"
                  size="xs"
                  variant="ghost"
                  disabled={!resolvable || isPending}
                  aria-label={t('approvals.deny_item', {
                    title: item.title,
                    defaultValue: '拒绝：{{title}}',
                  })}
                  onClick={() => onDecision(item.id, 'deny')}
                  className="motion-reduce:transition-none"
                >
                  <X size={12} aria-hidden="true" />
                  {t('approvals.deny', { defaultValue: '拒绝' })}
                </Button>
              </span>
            </li>
          );
        })}
      </ul>
    </section>
  );
}

export default ApprovalQueueRail;
