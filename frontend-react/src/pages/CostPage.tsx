import { useState, useEffect } from 'react';
import { DollarSign, TrendingUp, AlertTriangle, Activity, Wallet, ShieldCheck } from 'lucide-react';
import { api } from '../api';

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

interface QuotaData {
  max_requests_per_day: number;
  max_tokens_per_day: number;
  max_cost_per_month: number;
  requests_today: number;
  tokens_today: number;
  cost_this_month: number;
}

const PERIOD_LABELS: Record<string, string> = {
  daily: '每日',
  weekly: '每周',
  monthly: '每月',
};

export default function CostPage() {
  const [costData, setCostData] = useState<CostData | null>(null);
  const [budget, setBudget] = useState<BudgetData | null>(null);
  const [quota, setQuota] = useState<QuotaData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [usageData, budgetData, quotaData] = await Promise.all([
        api.getCostUsage(),
        api.getCostBudget(),
        api.getCostQuota(),
      ]);

      setCostData(usageData);
      setBudget(budgetData);
      setQuota(quotaData);
    } catch {
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

  const requestPercent = quota ? Math.min((quota.requests_today / Math.max(quota.max_requests_per_day, 1)) * 100, 100) : 0;
  const tokenPercent = quota ? Math.min((quota.tokens_today / Math.max(quota.max_tokens_per_day, 1)) * 100, 100) : 0;
  const costPercent = quota ? Math.min((quota.cost_this_month / Math.max(quota.max_cost_per_month, 1)) * 100, 100) : 0;

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

      {/* Budget Config */}
      {budget && (
        <div className="bg-[var(--color-bg-surface-1)] border border-[var(--color-border-subtle)] rounded-2xl p-5">
          <h3 className="text-sm font-medium text-[var(--color-text-primary)] mb-4 flex items-center gap-2">
            <Wallet size={14} className="text-[var(--color-accent)]" />预算配置
          </h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div>
              <span className="text-xs text-[var(--color-text-muted)]">预算金额</span>
              <p className="text-lg font-semibold text-[var(--color-text-primary)]">${(budget.amount ?? 0).toFixed(2)}</p>
            </div>
            <div>
              <span className="text-xs text-[var(--color-text-muted)]">周期</span>
              <p className="text-lg font-semibold text-[var(--color-text-primary)]">{PERIOD_LABELS[budget.period] || budget.period || '每月'}</p>
            </div>
            <div>
              <span className="text-xs text-[var(--color-text-muted)]">状态</span>
              <p className={`text-lg font-semibold ${budget.is_active ? 'text-[var(--color-success)]' : 'text-[var(--color-text-muted)]'}`}>
                {budget.is_active ? '已启用' : '未启用'}
              </p>
            </div>
            <div>
              <span className="text-xs text-[var(--color-text-muted)]">会话/请求限额</span>
              <p className="text-lg font-semibold text-[var(--color-text-primary)]">
                ${budget.per_session_limit != null ? budget.per_session_limit.toFixed(2) : '—'} / ${budget.per_request_limit != null ? budget.per_request_limit.toFixed(2) : '—'}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Quota Usage */}
      {quota && (
        <div className="bg-[var(--color-bg-surface-1)] border border-[var(--color-border-subtle)] rounded-2xl p-5">
          <h3 className="text-sm font-medium text-[var(--color-text-primary)] mb-4 flex items-center gap-2">
            <ShieldCheck size={14} className="text-[var(--color-accent-secondary)]" />配额用量
          </h3>
          <div className="space-y-4">
            <BudgetBar label="每日请求" current={quota.requests_today} limit={quota.max_requests_per_day} percent={requestPercent} unit="" />
            <BudgetBar label="每日 Token" current={quota.tokens_today} limit={quota.max_tokens_per_day} percent={tokenPercent} unit="" />
            <BudgetBar label="本月成本" current={quota.cost_this_month} limit={quota.max_cost_per_month} percent={costPercent} unit="$" />
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

function BudgetBar({ label, current, limit, percent, unit }: { label: string; current: number; limit: number; percent: number; unit: string }) {
  const color = percent >= 90 ? 'bg-red-500' : percent >= 70 ? 'bg-amber-500' : 'bg-blue-500';
  const fmt = (n: number) => (unit === '$' ? `$${n.toFixed(2)}` : n.toLocaleString());
  return (
    <div>
      <div className="flex justify-between text-xs mb-1">
        <span className="text-[var(--color-text-muted)]">{label}</span>
        <span className="text-[var(--color-text-muted)]">{fmt(current)} / {fmt(limit)}</span>
      </div>
      <div className="w-full h-2 bg-[var(--color-bg-surface-3)] rounded-full overflow-hidden">
        <div className={`h-full ${color} rounded-full transition-all`} style={{ width: `${percent}%` }} />
      </div>
    </div>
  );
}
