import { useState } from 'react';
import { AlertTriangle, ChevronDown, ChevronUp, Layers } from 'lucide-react';
import { useI18n } from '../../i18n';
import { cn } from '../../lib/utils';
import { useAnchoredStore } from '../../store/anchored';
import type { LoopStatusSnapshot } from '../../store/anchored';

type LoopTone = 'running' | 'queued' | 'completed' | 'warning';

const TONE_DOT: Record<LoopTone, string> = {
  running: 'bg-[var(--color-accent-foreground)] motion-safe:animate-pulse',
  queued: 'bg-[var(--color-text-disabled)]',
  completed: 'bg-[var(--color-success)]',
  warning: 'bg-[var(--color-warning)]',
};

const TONE_TEXT: Record<LoopTone, string> = {
  running: 'text-[var(--color-accent-foreground)]',
  queued: 'text-[var(--color-text-muted)]',
  completed: 'text-[var(--color-success)]',
  warning: 'text-[var(--color-warning)]',
};

function panelTone(snapshot: LoopStatusSnapshot): LoopTone {
  if (snapshot.noProgressCount > 0) return 'warning';
  if (snapshot.currentInput.trim() !== '') return 'running';
  if (snapshot.followupQueue.length + snapshot.steeringQueue.length > 0) return 'queued';
  return 'completed';
}

function formatRound(count: number): string {
  return `R${String(Math.max(0, count)).padStart(2, '0')}`;
}

function StatusDot({ tone }: { tone: LoopTone }) {
  return (
    <span
      aria-hidden="true"
      data-testid="loop-status-dot"
      data-tone={tone}
      className={cn('size-[6px] shrink-0 rounded-[var(--radius-pill)] transition-colors duration-150 motion-reduce:transition-none', TONE_DOT[tone])}
    />
  );
}

function MonoBadge({ children, tone }: { children: string; tone: LoopTone }) {
  return (
    <span
      data-testid="loop-status-badge"
      className={cn(
        'inline-flex shrink-0 items-center gap-[var(--space-1)] rounded-[var(--radius-sm)] border px-[var(--space-1-5)] py-[0.125rem] font-mono text-[length:var(--text-2xs)] tabular-nums transition-colors duration-150 motion-reduce:transition-none',
        tone === 'warning'
          ? 'border-[var(--color-warning)]/30 bg-[var(--color-warning-subtle)] text-[var(--color-warning)]'
          : 'border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-2)] text-[var(--color-text-muted)]',
      )}
    >
      {children}
    </span>
  );
}

function QueueList({ entries, emptyLabel }: { entries: string[]; emptyLabel: string }) {
  if (entries.length === 0) {
    return <p className="text-[length:var(--text-2xs)] text-[var(--color-text-muted)]">{emptyLabel}</p>;
  }
  return (
    <ol className="space-y-[var(--space-0-5)]">
      {entries.map((entry, index) => (
        <li key={index} className="flex min-w-0 items-start gap-[var(--space-1-5)] text-[length:var(--text-2xs)] leading-[var(--leading-normal)]">
          <span aria-hidden="true" className="shrink-0 font-mono tabular-nums text-[var(--color-text-muted)]">
            {String(index + 1).padStart(2, '0')}
          </span>
          <span className="min-w-0 break-words text-[var(--color-text-secondary)]">{entry}</span>
        </li>
      ))}
    </ol>
  );
}

function Disclosure({
  summary,
  count,
  open,
  onToggle,
  children,
  testId,
}: {
  summary: string;
  count: number;
  open: boolean;
  onToggle: () => void;
  children: React.ReactNode;
  testId: string;
}) {
  return (
    <div data-testid={testId} className="border-t border-[var(--color-border-subtle)] pt-[var(--space-1-5)]">
      <button
        type="button"
        aria-expanded={open}
        onClick={onToggle}
        className="flex w-full items-center gap-[var(--space-1)] border-0 bg-transparent p-0 text-[length:var(--text-2xs)] text-[var(--color-text-secondary)] transition-colors duration-150 motion-reduce:transition-none hover:text-[var(--color-text-primary)] focus-visible:outline-none focus-visible:shadow-[var(--focus-ring)]"
      >
        {open ? <ChevronUp size={12} aria-hidden="true" /> : <ChevronDown size={12} aria-hidden="true" />}
        <span className="min-w-0 flex-1 truncate text-start">{summary}</span>
        <span className="shrink-0 font-mono tabular-nums text-[var(--color-text-muted)]">{count}</span>
      </button>
      {open && <div className="space-y-[var(--space-2)] pt-[var(--space-1-5)]">{children}</div>}
    </div>
  );
}

/**
 * Pi 外层循环快照面板（Codex 卡片语言：细分隔线分区、mono 轮数徽标、
 * 状态色点、队列明细折叠 disclosure、无进展警告条带）。
 *
 * 渲染 `loop_status` 事件归一化后的长任务循环状态：外层轮数、当前子输入、
 * 已完成项、追问队列、方向覆盖队列与无进展计数。快照缺失时显示等待态；
 * 无进展计数 > 0 时渲染醒目但克制的 amber 条带。
 */
export function LoopStatusPanel({ className, 'data-testid': testId }: {
  className?: string;
  'data-testid'?: string;
}) {
  const { t } = useI18n();
  const snapshot = useAnchoredStore((s) => s.loopStatus);
  const [queuesOpen, setQueuesOpen] = useState(false);
  const [completedOpen, setCompletedOpen] = useState(false);

  if (!snapshot) {
    return (
      <section aria-label={t('anchored.loop.title')} data-testid={testId ?? 'loop-status'} className={cn('not-prose', className)}>
        <p className="text-[length:var(--text-xs)] text-[var(--color-text-muted)]">{t('anchored.loop.waiting')}</p>
      </section>
    );
  }

  const queued = snapshot.followupQueue.length + snapshot.steeringQueue.length;
  const tone = panelTone(snapshot);
  const badge =
    snapshot.noProgressCount > 0
      ? t('anchored.loop.no_progress', { count: snapshot.noProgressCount })
      : queued > 0
        ? t('anchored.loop.queued_count', { count: queued })
        : t('anchored.loop.round', { count: snapshot.outerRound });
  const roundLabel = t('anchored.loop.round', { count: snapshot.outerRound });
  const running = tone === 'running';

  return (
    <section
      aria-label={t('anchored.loop.title')}
      data-testid={testId ?? 'loop-status'}
      data-tone={tone}
      className={cn(
        'not-prose rounded-[var(--radius-lg)] border border-[var(--color-border-default)] bg-[var(--color-bg-surface-1)] p-[var(--space-2-5)]',
        className,
      )}
    >
      <header className="flex items-start gap-[var(--space-3)] border-b border-[var(--color-border-subtle)] pb-[var(--space-2)]">
        <span
          aria-hidden="true"
          className="flex size-10 shrink-0 items-center justify-center rounded-[var(--radius-md)] bg-[var(--color-bg-surface-2)] text-[var(--color-text-secondary)]"
        >
          <Layers size={20} />
        </span>
        <div className="flex min-w-0 flex-1 flex-col gap-[var(--space-0-5)]">
          <div className="flex min-w-0 items-center gap-[var(--space-1-5)]">
            <StatusDot tone={tone} />
            <strong className={cn('truncate text-[length:var(--text-sm)] font-medium leading-[var(--leading-normal)]', TONE_TEXT[tone])}>
              {t('anchored.loop.title')}
            </strong>
            <span className="ml-auto shrink-0 font-mono text-[length:var(--text-xs)] tabular-nums text-[var(--color-text-muted)]" title={roundLabel}>
              {formatRound(snapshot.outerRound)}
            </span>
          </div>
          <p className="min-w-0 break-words text-[length:var(--text-xs)] leading-[var(--leading-normal)] text-[var(--color-text-secondary)]">
            {running ? snapshot.currentInput || t('anchored.loop.empty') : roundLabel}
          </p>
        </div>
        <MonoBadge tone={tone}>{badge}</MonoBadge>
      </header>

      {snapshot.noProgressCount > 0 && (
        <p
          role="status"
          data-testid="loop-status-warning"
          className="flex items-start gap-[var(--space-1-5)] border-b border-[var(--color-border-subtle)] bg-[var(--color-warning-subtle)] px-[var(--space-1-5)] py-[var(--space-1-5)] text-[length:var(--text-2xs)] leading-[var(--leading-normal)] text-[var(--color-warning)] transition-colors duration-150 motion-reduce:transition-none"
        >
          <AlertTriangle size={12} aria-hidden="true" className="mt-[2px] shrink-0" />
          <span className="min-w-0 break-words">
            {t('anchored.loop.no_progress', { count: snapshot.noProgressCount })}
          </span>
        </p>
      )}

      <div className="space-y-[var(--space-1-5)] pt-[var(--space-1-5)]">
        <Disclosure
          testId="loop-status-queues"
          summary={t('anchored.loop.queues_section', { defaultValue: '队列明细' })}
          count={queued}
          open={queuesOpen}
          onToggle={() => setQueuesOpen((current) => !current)}
        >
          <div>
            <p className="mb-[var(--space-0-5)] text-[length:var(--text-2xs)] font-medium text-[var(--color-text-muted)]">
              {t('anchored.loop.followup_queue')}
            </p>
            <QueueList entries={snapshot.followupQueue} emptyLabel={t('anchored.loop.empty')} />
          </div>
          <div>
            <p className="mb-[var(--space-0-5)] text-[length:var(--text-2xs)] font-medium text-[var(--color-text-muted)]">
              {t('anchored.loop.steering_queue')}
            </p>
            <QueueList entries={snapshot.steeringQueue} emptyLabel={t('anchored.loop.empty')} />
          </div>
        </Disclosure>
        <Disclosure
          testId="loop-status-completed"
          summary={t('anchored.loop.completed')}
          count={snapshot.completed.length}
          open={completedOpen}
          onToggle={() => setCompletedOpen((current) => !current)}
        >
          <QueueList entries={snapshot.completed} emptyLabel={t('anchored.loop.empty')} />
        </Disclosure>
      </div>
    </section>
  );
}

export default LoopStatusPanel;
