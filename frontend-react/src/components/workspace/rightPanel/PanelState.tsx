import { useCallback, useEffect, useRef, useState } from 'react';
import type { ReactNode } from 'react';
import { AlertTriangle, RotateCcw, type LucideIcon } from 'lucide-react';
import { useI18n } from '../../../i18n';

type AsyncState<T> = {
  data: T | null;
  loading: boolean;
  error: boolean;
  reload: () => void;
};

/**
 * Minimal request lifecycle shared by every right-panel section so loading,
 * failure and retry behave identically across panels.
 */
export function useAsyncData<T>(load: () => Promise<T>, deps: unknown[]): AsyncState<T> {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [nonce, setNonce] = useState(0);
  const loadRef = useRef(load);
  loadRef.current = load;

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(false);
    loadRef.current()
      .then((result) => {
        if (!cancelled) setData(result);
      })
      .catch(() => {
        if (!cancelled) setError(true);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, nonce]);

  const reload = useCallback(() => setNonce((value) => value + 1), []);

  return { data, loading, error, reload };
}

export function PanelLoading({ rows = 3, label }: { rows?: number; label?: string }) {
  const { t } = useI18n();
  return (
    <div className="space-y-2" role="status" aria-live="polite" aria-busy="true">
      <span className="sr-only">{label ?? t('right_panel.states.loading')}</span>
      <div className="space-y-1.5" aria-hidden="true">
        {Array.from({ length: rows }, (_, index) => (
          <div
            key={index}
            className="h-6 animate-pulse rounded-[var(--radius-md)] bg-[var(--color-bg-surface-2)]"
            style={{ opacity: 1 - index * 0.18 }}
          />
        ))}
      </div>
    </div>
  );
}

export function PanelEmpty({
  icon: Icon,
  title,
  hint,
  action,
}: {
  icon: LucideIcon;
  title: string;
  hint?: string;
  action?: ReactNode;
}) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 px-4 py-8 text-center">
      <Icon size={22} className="text-[var(--color-text-muted)]" aria-hidden="true" />
      <p className="text-xs font-medium text-[var(--color-text-secondary)]">{title}</p>
      {hint && <p className="max-w-[24ch] text-[11px] leading-relaxed text-[var(--color-text-muted)]">{hint}</p>}
      {action}
    </div>
  );
}

export function PanelError({ onRetry }: { onRetry: () => void }) {
  const { t } = useI18n();
  return (
    <div className="flex flex-col items-center justify-center gap-2 px-4 py-8 text-center" role="alert">
      <AlertTriangle size={22} className="text-[var(--color-warning)]" aria-hidden="true" />
      <p className="text-xs font-medium text-[var(--color-text-secondary)]">
        {t('right_panel.states.load_failed')}
      </p>
      <p className="max-w-[26ch] text-[11px] leading-relaxed text-[var(--color-text-muted)]">
        {t('right_panel.states.load_failed_hint')}
      </p>
      <button
        type="button"
        onClick={onRetry}
        className="mt-1 inline-flex items-center gap-1.5 rounded-[var(--radius-md)] border border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-2)] px-2.5 py-1.5 text-[11px] font-medium text-[var(--color-text-secondary)] transition-colors hover:border-[var(--color-border-default)] hover:text-[var(--color-text-primary)]"
      >
        <RotateCcw size={12} aria-hidden="true" />
        {t('right_panel.states.retry')}
      </button>
    </div>
  );
}

export function SectionHeader({ title, count }: { title: string; count?: number }) {
  return (
    <div className="flex items-center gap-1.5">
      <h4 className="text-[10px] font-semibold uppercase tracking-[0.06em] text-[var(--color-text-muted)]">
        {title}
      </h4>
      {count !== undefined && count > 0 && (
        <span className="font-mono text-[10px] tabular-nums text-[var(--color-text-muted)]">
          {count}
        </span>
      )}
    </div>
  );
}

export function KeyValueRow({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div className="flex items-baseline justify-between gap-3 py-[3px] text-xs">
      <span className="shrink-0 text-[var(--color-text-muted)]">{label}</span>
      <span className="min-w-0 truncate text-right font-medium text-[var(--color-text-secondary)]">{value}</span>
    </div>
  );
}

/**
 * A section reports how many entries it actually holds so the owning group
 * heading can carry that number.
 *
 * `count` is `number | undefined`. Loading, failure and "the list resolved
 * empty" are three different facts, and only the last one is a zero: a
 * heading that showed 0 for a request that never came back would claim the
 * backend holds nothing. `undefined` means the number is unreported and the
 * heading drops the tally entirely.
 */
export type ReportCount = (count: number | undefined) => void;

export function useReportedCount(count: number | undefined, report: ReportCount | undefined) {
  useEffect(() => {
    report?.(count);
  }, [count, report]);
}

/**
 * Resolve the count a section may report from its request state.
 *
 * A load that is still running and a load that failed both yield `undefined`,
 * and only a resolved list yields its length. That keeps "the backend says
 * there are none" (0) apart from "we do not know" (undefined).
 */
export function resolveReportedCount(
  state: { data: unknown[] | null | undefined; loading: boolean; error: unknown },
): number | undefined {
  if (state.loading || state.error) return undefined;
  return state.data?.length;
}
