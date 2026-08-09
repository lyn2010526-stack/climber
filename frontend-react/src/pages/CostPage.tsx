import { useState, useEffect } from 'react';
import { DollarSign, TrendingUp, AlertTriangle, Activity, BarChart3, RefreshCw } from 'lucide-react';
import { api } from '../api';
import { PageHeader } from '../components/ui/PageHeader';
import { Card, CardContent } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Progress } from '../components/ui/Progress';
import { SkeletonCard } from '../components/ui/Skeleton';
import { EmptyState } from '../components/ui/EmptyState';

interface CostData {
  total_cost: number;
  total_tokens: number;
  total_calls: number;
  by_model: { model: string; cost: number; tokens: number; calls: number }[];
  by_day: { date: string; cost: number; tokens: number }[];
}

interface BudgetData {
  amount: number;
  period: string;
  is_active: boolean;
  per_session_limit: number | null;
  per_request_limit: number | null;
}

function BudgetBar({ label, current, limit, percent }: { label: string; current: number; limit: number; percent: number }) {
  const color = percent >= 90 ? 'bg-[var(--color-error)]' : percent >= 70 ? 'bg-[var(--color-warning)]' : 'bg-[var(--color-accent)]';
  return (
    <div>
      <div className="flex justify-between text-xs mb-1.5">
        <span className="text-[var(--color-text-secondary)] font-medium">{label}</span>
        <span className="text-[var(--color-text-muted)]">${current.toFixed(2)} / ${limit.toFixed(2)}</span>
      </div>
      <div className="w-full h-2 bg-[var(--color-bg-surface-3)] rounded-full overflow-hidden">
        <div className={`h-full ${color} rounded-full transition-all duration-500`} style={{ width: `${percent}%` }} />
      </div>
    </div>
  );
}

export default function CostPage() {
  const [costData, setCostData] = useState<CostData | null>(null);
  const [budget, setBudget] = useState<BudgetData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [usageData, budgetData] = await Promise.all([
        api.getCostUsage(),
        api.getCostBudget(),
      ]);
      setCostData(usageData);
      setBudget(budgetData);
    } catch (e) {
      setError('加载成本数据失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const currentCost = costData?.total_cost ?? 0;
  const budgetPercent = budget && budget.amount > 0 ? Math.min((currentCost / budget.amount) * 100, 100) : 0;

  return (
    <div className="h-full overflow-y-auto page-transition">
      <div className="p-4 md:p-6 lg:p-8 max-w-5xl mx-auto">
        <PageHeader
          title="成本概览"
          description="追踪 LLM 使用量和支出"
          icon={<DollarSign size={20} />}
          actions={
            <Button variant="ghost" size="icon" onClick={fetchData} loading={loading}>
              <RefreshCw size={16} />
            </Button>
          }
        />

        {error && (
          <Card variant="default" className="mb-6 border-[var(--color-error)]/30">
            <CardContent className="p-4 flex items-center gap-3">
              <AlertTriangle size={18} className="text-[var(--color-warning)] shrink-0" />
              <p className="text-sm text-[var(--color-text-secondary)] flex-1">{error}</p>
              <Button variant="outline" size="sm" onClick={fetchData}>重试</Button>
            </CardContent>
          </Card>
        )}

        {loading ? (
          <div className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {Array.from({ length: 3 }).map((_, i) => <SkeletonCard key={i} />)}
            </div>
            <SkeletonCard />
          </div>
        ) : (
          <>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6 stagger-children">
              <Card variant="default" className="hover-lift">
                <CardContent className="p-5">
                  <div className="flex items-center gap-2 mb-3">
                    <div className="p-2 rounded-lg bg-[var(--color-success)]/10 border border-[var(--color-success)]/20">
                      <DollarSign size={16} className="text-[var(--color-success)]" />
                    </div>
                    <span className="text-xs text-[var(--color-text-muted)]">总成本</span>
                  </div>
                  <p className="text-2xl font-bold text-[var(--color-text-primary)]">
                    ${costData?.total_cost?.toFixed(4) || '0.0000'}
                  </p>
                </CardContent>
              </Card>
              <Card variant="default" className="hover-lift">
                <CardContent className="p-5">
                  <div className="flex items-center gap-2 mb-3">
                    <div className="p-2 rounded-lg bg-[var(--color-accent)]/10 border border-[var(--color-accent)]/20">
                      <Activity size={16} className="text-[var(--color-accent)]" />
                    </div>
                    <span className="text-xs text-[var(--color-text-muted)]">总 Token</span>
                  </div>
                  <p className="text-2xl font-bold text-[var(--color-text-primary)]">
                    {costData?.total_tokens?.toLocaleString() || '0'}
                  </p>
                </CardContent>
              </Card>
              <Card variant="default" className="hover-lift">
                <CardContent className="p-5">
                  <div className="flex items-center gap-2 mb-3">
                    <div className="p-2 rounded-lg bg-[var(--color-accent-secondary)]/10 border border-[var(--color-accent-secondary)]/20">
                      <TrendingUp size={16} className="text-[var(--color-accent-secondary)]" />
                    </div>
                    <span className="text-xs text-[var(--color-text-muted)]">API 调用</span>
                  </div>
                  <p className="text-2xl font-bold text-[var(--color-text-primary)]">
                    {costData?.total_calls?.toLocaleString() || '0'}
                  </p>
                </CardContent>
              </Card>
            </div>

            {budget && budget.is_active && (
              <Card variant="default" className="mb-6">
                <CardContent className="p-6">
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="text-sm font-semibold text-[var(--color-text-primary)]">预算使用</h3>
                    <span className="text-xs text-[var(--color-text-muted)]">周期：{budget.period}</span>
                  </div>
                  <BudgetBar label="当前支出" current={currentCost} limit={budget.amount} percent={budgetPercent} />
                  {budget.per_request_limit != null && (
                    <p className="text-xs text-[var(--color-text-muted)] mt-3">单次请求限额：${budget.per_request_limit.toFixed(2)}</p>
                  )}
                </CardContent>
              </Card>
            )}

            {costData?.by_model && costData.by_model.length > 0 ? (
              <Card variant="default">
                <CardContent className="p-6">
                  <h3 className="text-sm font-semibold text-[var(--color-text-primary)] mb-4">模型成本</h3>
                  <div className="space-y-1">
                    {costData.by_model.map((m) => (
                      <div key={m.model} className="flex items-center justify-between py-3 border-b border-[var(--color-border-subtle)] last:border-0">
                        <div className="flex items-center gap-3">
                          <div className="p-1.5 rounded-lg bg-[var(--color-bg-surface-2)] border border-[var(--color-border-subtle)]">
                            <BarChart3 size={14} className="text-[var(--color-text-muted)]" />
                          </div>
                          <div>
                            <span className="text-sm text-[var(--color-text-primary)] font-medium">{m.model}</span>
                            <span className="text-xs text-[var(--color-text-muted)] ml-2">{m.calls} 次调用</span>
                          </div>
                        </div>
                        <span className="text-sm font-semibold text-[var(--color-text-primary)]">${m.cost.toFixed(4)}</span>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            ) : (
              <EmptyState icon="file" title="暂无成本数据" description="运行智能体后将在此显示成本统计" />
            )}
          </>
        )}
      </div>
    </div>
  );
}
