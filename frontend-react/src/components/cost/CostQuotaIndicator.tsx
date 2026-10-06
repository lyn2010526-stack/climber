import { useEffect, useState } from 'react';
import { useI18n } from '../../i18n';
import { api } from '../../api';
import { cn } from '../../lib/utils';

interface QuotaBarState {
  status: 'loading' | 'ready' | 'unreported';
  usedPercent?: number;
  used?: number;
  max?: number;
}

interface QuotaFetchOptions {
  label: string;
  fetchQuota: () => Promise<{ used: number | null; max: number | null }>;
}

type QuotaTone = 'safe' | 'caution' | 'warning' | 'danger';

const TRACK_WIDTH_PX = 72;
const TRACK_HEIGHT_PX = 6;

function boundedPercent(value: number): number {
  return Math.min(100, Math.max(0, value));
}

function quotaTone(percent: number): QuotaTone {
  if (percent >= 90) return 'danger';
  if (percent >= 70) return 'warning';
  if (percent >= 40) return 'caution';
  return 'safe';
}

const TONE_FILL: Record<QuotaTone, string> = {
  safe: 'bg-[var(--color-accent-foreground)]',
  caution: 'bg-[var(--color-success)]',
  warning: 'bg-[var(--color-warning)]',
  danger: 'bg-[var(--color-error)]',
};

const TONE_TEXT: Record<QuotaTone, string> = {
  safe: 'text-[var(--color-text-secondary)]',
  caution: 'text-[var(--color-text-secondary)]',
  warning: 'text-[var(--color-warning)]',
  danger: 'text-[var(--color-error)]',
};

function formatCount(value: number): string {
  return new Intl.NumberFormat(undefined, { maximumFractionDigits: 0 }).format(value);
}

export interface CostQuotaIndicatorProps {
  className?: string;
  'data-testid'?: string;
}

/**
 * Codex 形态的配额指示器：used-percent 条 + mono 数字 + 周期标签。
 * 读 `/cost/quota`；数据缺失或未上报时优雅占位（"未上报"文案）。
 */
export function CostQuotaIndicator({ className, 'data-testid': testId }: CostQuotaIndicatorProps = {}) {
  const { t } = useI18n();
  const [state, setState] = useState<QuotaBarState>({ status: 'loading' });

  useEffect(() => {
    let active = true;
    api.getCostQuota()
      .then((quota) => {
        if (!active) return;
        const used = typeof quota?.requests_today === 'number' && Number.isFinite(quota.requests_today)
          ? quota.requests_today
          : null;
        const max = typeof quota?.max_requests_per_day === 'number' && Number.isFinite(quota.max_requests_per_day)
          ? quota.max_requests_per_day
          : null;
        if (used === null || max === null || max <= 0) {
          setState({ status: 'unreported' });
          return;
        }
        setState({ status: 'ready', used, max, usedPercent: (used / max) * 100 });
      })
      .catch(() => {
        if (active) setState({ status: 'unreported' });
      });
    return () => {
      active = false;
    };
  }, []);

  if (state.status !== 'ready' || state.usedPercent === undefined || state.used === undefined || state.max === undefined) {
    return (
      <span
        role="status"
        data-testid={testId ?? 'cost-quota-indicator'}
        data-state="unreported"
        className={cn('inline-flex items-center text-[length:var(--text-2xs)] text-[var(--color-text-muted)]', className)}
      >
        {t('cost.quota.unreported', { defaultValue: '配额未上报' })}
      </span>
    );
  }

  const percent = boundedPercent(state.usedPercent);
  const tone = quotaTone(percent);
  const summary = t('cost.quota.summary', {
    used: formatCount(state.used),
    max: formatCount(state.max),
    defaultValue: '今日请求 {{used}} / {{max}}',
  });

  return (
    <span
      role="status"
      data-testid={testId ?? 'cost-quota-indicator'}
      data-state="ready"
      data-quota-tone={tone}
      aria-label={summary}
      className={cn('inline-flex items-center gap-[var(--space-2)]', className)}
    >
      <span className="shrink-0 text-[length:var(--text-2xs)] text-[var(--color-text-muted)]">
        {t('cost.quota.period_label', { defaultValue: '今日请求' })}
      </span>
      <span
        aria-hidden="true"
        data-testid="cost-quota-track"
        className="block shrink-0 overflow-hidden rounded-[var(--radius-pill)] bg-[var(--color-bg-surface-3)]"
        style={{ width: `${TRACK_WIDTH_PX}px`, height: `${TRACK_HEIGHT_PX}px` }}
      >
        <span
          data-testid="cost-quota-fill"
          className={cn('block h-full rounded-[inherit] transition-[width] duration-200 motion-reduce:transition-none', TONE_FILL[tone])}
          style={{ width: `${percent}%` }}
        />
      </span>
      <span className={cn('shrink-0 font-mono text-[length:var(--text-2xs)] tabular-nums', TONE_TEXT[tone])}>
        {formatCount(state.used)}/{formatCount(state.max)}
      </span>
    </span>
  );
}

export default CostQuotaIndicator;
