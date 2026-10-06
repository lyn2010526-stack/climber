import { useState, useEffect, useCallback } from 'react';
import {
  BarChart3, Bot, MessageSquare, Users, RefreshCw, AlertCircle, ThumbsUp,
} from 'lucide-react';
import { api } from '../api';
import { PageHeader } from '../components/ui/PageHeader';
import { Card, CardContent } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { useI18n } from '../i18n/utils';

interface StatsData {
  total_users: number;
  total_agents: number;
  total_sessions: number;
  total_api_keys: number;
}

const CARDS = [
  { key: 'total_users', labelKey: 'stats.card_users', icon: Users },
  { key: 'total_agents', labelKey: 'stats.card_agents', icon: Bot },
  { key: 'total_sessions', labelKey: 'stats.card_sessions', icon: MessageSquare },
  { key: 'total_api_keys', labelKey: 'stats.card_api_keys', icon: BarChart3 },
] as const;

interface FeedbackStats {
  total: number;
  approval_rate: number;
  up_count: number;
  down_count: number;
  reason_distribution: Record<string, number>;
}

/** Aggregated thumbs feedback (GET /feedback/stats). Fails soft: the stats
 *  grid below stays usable when this endpoint errors. */
function FeedbackStatsCard() {
  const { t } = useI18n();
  const [data, setData] = useState<FeedbackStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setData(await api.getFeedbackStats());
    } catch (e) {
      setData(null);
      setError(e instanceof Error ? e.message : t('stats.feedback_load_failed', { defaultValue: '反馈统计加载失败' }));
    } finally {
      setLoading(false);
    }
  }, [t]);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <Card variant="default" className="mb-4">
      <CardContent className="p-4">
        <div className="flex items-center justify-between">
          <h2 className="flex items-center gap-2 text-sm font-semibold text-[var(--color-text-primary)]">
            <ThumbsUp size={14} aria-hidden="true" className="text-[var(--color-text-muted)]" />
            {t('stats.feedback_title', { defaultValue: '反馈统计' })}
          </h2>
          <Button variant="ghost" size="xs" onClick={() => void load()} disabled={loading} icon={<RefreshCw size={12} />}>
            {t('common.refresh')}
          </Button>
        </div>
        {error && <p role="alert" className="mt-2 text-xs text-[var(--color-error)]">{error}</p>}
        {!error && (
          <dl className="mt-3 grid grid-cols-2 gap-px overflow-hidden rounded-[var(--radius-lg)] border border-[var(--color-border-subtle)] bg-[var(--color-border-subtle)] md:grid-cols-4">
            <div className="bg-[var(--color-bg-surface-1)] p-3">
              <dt className="text-xs text-[var(--color-text-muted)]">{t('stats.feedback_total', { defaultValue: '总反馈' })}</dt>
              <dd className="mt-1 text-xl font-semibold tabular-nums text-[var(--color-text-primary)]">{loading ? '…' : data?.total.toLocaleString() ?? '—'}</dd>
            </div>
            <div className="bg-[var(--color-bg-surface-1)] p-3">
              <dt className="text-xs text-[var(--color-text-muted)]">{t('stats.feedback_approval', { defaultValue: '好评率' })}</dt>
              <dd className="mt-1 text-xl font-semibold tabular-nums text-[var(--color-text-primary)]">{loading ? '…' : data ? `${(data.approval_rate * 100).toFixed(0)}%` : '—'}</dd>
            </div>
            <div className="bg-[var(--color-bg-surface-1)] p-3">
              <dt className="text-xs text-[var(--color-text-muted)]">{t('stats.feedback_up', { defaultValue: '赞' })}</dt>
              <dd className="mt-1 text-xl font-semibold tabular-nums text-[var(--color-text-primary)]">{loading ? '…' : data?.up_count.toLocaleString() ?? '—'}</dd>
            </div>
            <div className="bg-[var(--color-bg-surface-1)] p-3">
              <dt className="text-xs text-[var(--color-text-muted)]">{t('stats.feedback_down', { defaultValue: '踩' })}</dt>
              <dd className="mt-1 text-xl font-semibold tabular-nums text-[var(--color-text-primary)]">{loading ? '…' : data?.down_count.toLocaleString() ?? '—'}</dd>
            </div>
          </dl>
        )}
      </CardContent>
    </Card>
  );
}

export function StatsPage() {
  const { t } = useI18n();
  const [stats, setStats] = useState<StatsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadStats = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getStats();
      setStats(data);
    } catch (e) {
      setStats(null);
      setError(e instanceof Error ? e.message : t('stats.load_failed'));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadStats();
  }, [loadStats]);

  return (
    <div className="h-full overflow-y-auto page-transition">
      <div className="p-4 md:p-6 max-w-6xl mx-auto">
        <PageHeader
          title={t('stats.title')}
          icon={<BarChart3 size={20} />}
          className="border-b border-[var(--color-border-subtle)] pb-[var(--space-4)] [&_h1]:text-[length:var(--text-base)] [&_h1]:md:text-[length:var(--text-base)] [&_p]:text-[var(--color-text-muted)]"
          actions={
            <Button variant="secondary" size="sm" onClick={loadStats} loading={loading} icon={<RefreshCw size={14} />}>
              {t('common.refresh')}
            </Button>
          }
        />

        <FeedbackStatsCard />

        <div className="space-y-4">
          {error && (
            <Card variant="default" className="border-[var(--color-error)]/30">
              <CardContent className="p-4 flex items-center gap-3">
                <AlertCircle size={18} className="text-[var(--color-error)] shrink-0" />
                <p className="text-sm text-[var(--color-error)] flex-1">{error}</p>
                <Button variant="outline" size="sm" onClick={loadStats}>{t('common.retry')}</Button>
              </CardContent>
            </Card>
          )}

          <dl aria-busy={loading} className="grid grid-cols-2 lg:grid-cols-4 gap-px overflow-hidden rounded-[var(--radius-lg)] border border-[var(--color-border-subtle)] bg-[var(--color-border-subtle)]">
            {CARDS.map((card) => {
              const Icon = card.icon;
              const value = stats?.[card.key as keyof StatsData];
              return (
                <div key={card.key} className="bg-[var(--color-bg-surface-1)] p-4">
                  <dt className="flex items-center gap-2 text-xs text-[var(--color-text-muted)]"><Icon size={14} />{t(card.labelKey)}</dt>
                  <dd className="mt-2 text-2xl font-semibold tabular-nums text-[var(--color-text-primary)]">{loading ? '…' : value?.toLocaleString() ?? '—'}</dd>
                </div>
              );
            })}
          </dl>
        </div>
      </div>
    </div>
  );
}
