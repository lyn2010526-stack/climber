import { useState, useEffect } from 'react';
import { DollarSign, TrendingUp, AlertTriangle, Activity } from 'lucide-react';
import { api } from '../api';

interface CostData {
  total_cost: number;
  total_tokens: number;
  total_calls: number;
  by_model: { model: string; cost: number; tokens: number; calls: number }[];
  by_day: { date: string; cost: number; tokens: number }[];
}

interface BudgetData {
  daily_limit: number;
  weekly_limit: number;
  monthly_limit: number;
  current_daily: number;
  current_weekly: number;
  current_monthly: number;
}

export default function CostPage() {
  const [costData, setCostData] = useState<CostData | null>(null);
  const [budget, setBudget] = useState<BudgetData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchData();
  }, []);

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

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-2 border-[var(--color-accent)] border-t-transparent rounded-full animate-spin" />
           <span className="text-sm text-[var(--color-text-muted)]">正在加载成本数据...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <AlertTriangle size={32} className="mx-auto mb-2 text-[var(--color-warning)]" />
          <p className="text-sm text-[var(--color-text-secondary)]">{error}</p>
          <button onClick={fetchData} className="mt-3 px-4 py-1.5 bg-[var(--color-accent)] text-white rounded-xl text-sm hover:bg-[var(--color-accent-hover)] transition-colors">
              重试
          </button>
        </div>
      </div>
    );
  }

  const dailyPercent = budget ? Math.min((budget.current_daily / budget.daily_limit) * 100, 100) : 0;
  const weeklyPercent = budget ? Math.min((budget.current_weekly / budget.weekly_limit) * 100, 100) : 0;
  const monthlyPercent = budget ? Math.min((budget.current_monthly / budget.monthly_limit) * 100, 100) : 0;

  return (
    <div className="h-full overflow-y-auto p-6 space-y-6">
      <div>
        <h2 className="text-lg font-semibold text-[var(--color-text-primary)]">成本概览</h2>
        <p className="text-sm text-[var(--color-text-muted)]">追踪 LLM 使用量和支出</p>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-[var(--color-bg-surface-1)] border border-[var(--color-border-subtle)] rounded-2xl p-4">
          <div className="flex items-center gap-2 mb-2">
            <DollarSign size={16} className="text-[var(--color-success)]" />
            <span className="text-xs text-[var(--color-text-muted)]">总成本</span>
          </div>
          <p className="text-2xl font-bold text-[var(--color-text-primary)]">
            ${costData?.total_cost?.toFixed(4) || '0.0000'}
          </p>
        </div>
        <div className="bg-[var(--color-bg-surface-1)] border border-[var(--color-border-subtle)] rounded-2xl p-4">
          <div className="flex items-center gap-2 mb-2">
            <Activity size={16} className="text-[var(--color-accent)]" />
            <span className="text-xs text-[var(--color-text-muted)]">总 Token</span>
          </div>
          <p className="text-2xl font-bold text-[var(--color-text-primary)]">
            {costData?.total_tokens?.toLocaleString() || '0'}
          </p>
        </div>
        <div className="bg-[var(--color-bg-surface-1)] border border-[var(--color-border-subtle)] rounded-2xl p-4">
          <div className="flex items-center gap-2 mb-2">
            <TrendingUp size={16} className="text-[var(--color-accent-secondary)]" />
            <span className="text-xs text-[var(--color-text-muted)]">API 调用</span>
          </div>
          <p className="text-2xl font-bold text-[var(--color-text-primary)]">
            {costData?.total_calls?.toLocaleString() || '0'}
          </p>
        </div>
      </div>

      {/* Budget Progress */}
      {budget && (
        <div className="bg-[var(--color-bg-surface-1)] border border-[var(--color-border-subtle)] rounded-2xl p-5">
          <h3 className="text-sm font-medium text-[var(--color-text-primary)] mb-4">预算使用</h3>
          <div className="space-y-4">
            <BudgetBar label="每日" current={budget.current_daily} limit={budget.daily_limit} percent={dailyPercent} />
            <BudgetBar label="每周" current={budget.current_weekly} limit={budget.weekly_limit} percent={weeklyPercent} />
            <BudgetBar label="每月" current={budget.current_monthly} limit={budget.monthly_limit} percent={monthlyPercent} />
          </div>
        </div>
      )}

      {/* By Model */}
      {costData?.by_model && costData.by_model.length > 0 && (
        <div className="bg-[var(--color-bg-surface-1)] border border-[var(--color-border-subtle)] rounded-2xl p-5">
          <h3 className="text-sm font-medium text-[var(--color-text-primary)] mb-4">模型成本</h3>
          <div className="space-y-2">
            {costData.by_model.map((m) => (
              <div key={m.model} className="flex items-center justify-between py-2 border-b border-[var(--color-border-subtle)] last:border-0">
                <div>
                  <span className="text-sm text-[var(--color-text-primary)]">{m.model}</span>
                   <span className="text-xs text-[var(--color-text-muted)] ml-2">{m.calls} 次调用</span>
                </div>
                <span className="text-sm font-medium text-[var(--color-text-secondary)]">${m.cost.toFixed(4)}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function BudgetBar({ label, current, limit, percent }: { label: string; current: number; limit: number; percent: number }) {
  const color = percent >= 90 ? 'bg-red-500' : percent >= 70 ? 'bg-amber-500' : 'bg-blue-500';
  return (
    <div>
      <div className="flex justify-between text-xs mb-1">
        <span className="text-[var(--color-text-muted)]">{label}</span>
        <span className="text-[var(--color-text-muted)]">${current.toFixed(2)} / ${limit.toFixed(2)}</span>
      </div>
      <div className="w-full h-2 bg-[var(--color-bg-surface-3)] rounded-full overflow-hidden">
        <div className={`h-full ${color} rounded-full transition-all`} style={{ width: `${percent}%` }} />
      </div>
    </div>
  );
}
