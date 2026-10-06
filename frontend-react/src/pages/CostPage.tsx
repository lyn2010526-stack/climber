import { useState, useEffect } from 'react';
import { DollarSign, AlertTriangle, RefreshCw } from 'lucide-react';
import { api, type CostBudgetOut, type CostUsageOut } from '../api';
import { PageHeader } from '../components/ui/PageHeader';
import { Card, CardContent } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Badge } from '../components/ui/Badge';
import { EmptyState } from '../components/ui/EmptyState';
import { SkeletonList } from '../components/ui/Skeleton';
import { CostQuotaIndicator } from '../components/cost/CostQuotaIndicator';
import { useI18n } from '../i18n/utils';
import { formatNumber } from '../i18n/utils';

type CostData = CostUsageOut;
type BudgetData = CostBudgetOut;

function BudgetBar({ label, current, limit, percent }: { label: string; current: number; limit: number; percent: number }) {
  const color = percent >= 90 ? 'bg-[var(--color-error)]' : percent >= 70 ? 'bg-[var(--color-warning)]' : 'bg-[var(--color-accent)]';
  return (
    <div>
      <div className="flex justify-between text-xs mb-1.5">
        <span className="text-[var(--color-text-secondary)] font-medium">{label}</span>
        <span className="text-[var(--color-text-muted)]">${current.toFixed(2)} / ${limit.toFixed(2)}</span>
      </div>
      <div className="w-full h-2 bg-[var(--color-bg-surface-3)] rounded-[var(--radius-pill)] overflow-hidden">
        <div className={`h-full ${color} rounded-[var(--radius-pill)] transition-all duration-500 motion-reduce:transition-none`} style={{ width: `${percent}%` }} />
      </div>
    </div>
  );
}

export default function CostPage() {
  const { t } = useI18n();
  const [costData, setCostData] = useState<CostData | null>(null);
  const [budget, setBudget] = useState<BudgetData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [usageData, budgetData] = await Promise.allSettled([
        api.getCostUsage(),
        api.getCostBudget(),
      ]);
      setCostData(usageData.status === 'fulfilled' ? usageData.value : null);
      setBudget(budgetData.status === 'fulfilled' ? budgetData.value : null);
      const failed = [
        usageData.status === 'rejected' && t('cost.parts.usage'),
        budgetData.status === 'rejected' && t('cost.parts.budget'),
      ].filter(Boolean);
      // One message naming every part that failed, so a half-loaded page never
      // looks like a page that simply has no data for the missing half.
      if (failed.length) setError(t('cost.load_failed', { parts: failed.join(t('cost.parts_separator')) }));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const periodKey = budget?.period === 'daily' ? 'daily' : budget?.period === 'weekly' ? 'weekly' : 'monthly';
  const periodLabel = t(`cost.period.${periodKey}`);
  const budgetPercent = budget && budget.amount ? Math.min((budget.current_spend / budget.amount) * 100, 100) : 0;

  return (
    <div className="h-full overflow-y-auto page-transition">
      <div className="p-4 md:p-6 max-w-6xl mx-auto">
        <PageHeader
          title={t('cost.title')}
          icon={<DollarSign size={20} />}
          className="border-b border-[var(--color-border-subtle)] pb-[var(--space-4)] [&_h1]:text-[length:var(--text-base)] [&_h1]:md:text-[length:var(--text-base)] [&_p]:text-[var(--color-text-muted)]"
          actions={
            <div className="flex items-center gap-[var(--space-3)]">
              <CostQuotaIndicator />
              <Button variant="secondary" size="sm" onClick={fetchData} loading={loading} icon={<RefreshCw size={14} />}>
                {t('common.refresh')}
              </Button>
            </div>
          }
        />

        {error && (
          <Card variant="default" className="border-[var(--color-error)]/30">
            <CardContent className="p-4 flex items-center gap-3">
              <AlertTriangle size={18} className="text-[var(--color-warning)] shrink-0" />
              <p className="text-sm text-[var(--color-text-secondary)] flex-1">{error}</p>
              <Button variant="outline" size="sm" onClick={fetchData}>{t('common.retry')}</Button>
            </CardContent>
          </Card>
        )}

        {loading ? (
          <div role="status" aria-label={t('common.loading_data')} className="mt-4">
            <SkeletonList count={3} />
          </div>
        ) : (
          <div className="space-y-4">
            <dl className="grid grid-cols-1 sm:grid-cols-3 gap-px overflow-hidden rounded-[var(--radius-lg)] border border-[var(--color-border-subtle)] bg-[var(--color-border-subtle)]">
              {[
                [t('cost.totals.total_cost'), costData?.total_cost != null ? `$${costData.total_cost.toFixed(4)}` : '—'],
                [t('cost.totals.total_tokens'), costData?.total_tokens != null ? formatNumber(costData.total_tokens) : '—'],
                [t('cost.totals.total_calls'), costData?.total_calls != null ? formatNumber(costData.total_calls) : '—'],
              ].map(([label, value]) => <div key={label} className="bg-[var(--color-bg-surface-1)] p-4"><dt className="text-xs text-[var(--color-text-muted)]">{label}</dt><dd className="mt-2 text-2xl font-semibold tabular-nums text-[var(--color-text-primary)]">{value}</dd></div>)}
            </dl>

            {budget && (
              <Card variant="default">
                <CardContent className="p-4">
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="text-sm font-semibold text-[var(--color-text-primary)]">{t('cost.budget.usage')}</h3>
                    <Badge variant={budget.is_active ? 'success' : 'secondary'}>
                      {budget.is_active ? t('cost.budget.enabled') : t('cost.budget.not_enabled')}
                    </Badge>
                  </div>
                  {budget.is_active ? (
                    <div className="space-y-4">
                      <BudgetBar label={periodLabel} current={budget.current_spend} limit={budget.amount} percent={budgetPercent} />
                      {(budget.per_session_limit != null || budget.per_request_limit != null) && (
                        <div className="flex flex-wrap gap-6 text-xs text-[var(--color-text-muted)] pt-1">
                          {budget.per_session_limit != null && <span>{t('cost.budget.per_session_limit', { amount: budget.per_session_limit.toFixed(2) })}</span>}
                          {budget.per_request_limit != null && <span>{t('cost.budget.per_request_limit', { amount: budget.per_request_limit.toFixed(2) })}</span>}
                        </div>
                      )}
                    </div>
                  ) : (
                    <p className="text-sm text-[var(--color-text-muted)]">{t('cost.budget.none_configured')}</p>
                  )}
                </CardContent>
              </Card>
            )}

            {costData?.by_model && costData.by_model.length > 0 ? (
              <Card variant="default" padding="none" className="overflow-hidden">
                <CardContent>
                  <h3 className="px-3 py-3 text-sm font-semibold text-[var(--color-text-primary)]">{t('cost.by_model')}</h3>
                  <div className="overflow-x-auto">
                    <table className="w-full min-w-[480px] text-left text-sm text-[var(--color-text-primary)]">
                      <thead className="bg-[var(--color-bg-surface-2)] text-xs text-[var(--color-text-muted)]"><tr><th scope="col" className="px-3 py-2 font-medium">{t('cost.by_model_model')}</th><th scope="col" className="px-3 py-2 text-right font-medium">{t('cost.by_model_calls')}</th><th scope="col" className="px-3 py-2 text-right font-medium">{t('cost.by_model_tokens')}</th><th scope="col" className="px-3 py-2 text-right font-medium">{t('cost.by_model_cost')}</th></tr></thead>
                      <tbody className="divide-y divide-[var(--color-border-subtle)]">
                    {costData.by_model.map((m) => (
                      <tr key={m.model} className="hover:bg-[var(--color-bg-surface-2)]"><th scope="row" className="px-3 py-2.5 font-medium break-all">{m.model}</th><td className="px-3 py-2.5 text-right tabular-nums">{formatNumber(m.calls)}</td><td className="px-3 py-2.5 text-right tabular-nums">{formatNumber(m.tokens)}</td><td className="px-3 py-2.5 text-right tabular-nums">${m.cost.toFixed(4)}</td></tr>
                    ))}
                      </tbody>
                    </table>
                  </div>
                </CardContent>
              </Card>
            ) : costData ? (
              <Card variant="default" padding="none" className="overflow-hidden">
                <EmptyState
                  className="w-full"
                  icon="file"
                  title={t('cost.no_model_usage')}
                />
              </Card>
            ) : null}
          </div>
        )}
      </div>
    </div>
  );
}
