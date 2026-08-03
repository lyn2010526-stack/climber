import { useEffect, useState } from 'react';
import { ThumbsUp, ThumbsDown, TrendingUp } from 'lucide-react';
import { api } from '../../api';

const REASON_LABELS: Record<string, string> = {
  factual_error: 'Factual Error',
  format: 'Format Issue',
  incomplete: 'Incomplete',
  irrelevant: 'Irrelevant',
  other: 'Other',
};

interface FeedbackStatsProps {
  compact?: boolean;
}

export function FeedbackStats({ compact = false }: FeedbackStatsProps) {
  const [stats, setStats] = useState<{
    total: number;
    approval_rate: number;
    up_count: number;
    down_count: number;
    reason_distribution: Record<string, number>;
  } | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      try {
        const data = await api.getFeedbackStats();
        setStats(data);
      } catch {
        // silently fail
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  if (loading) {
    return (
      <div className="animate-pulse space-y-2">
        <div className="h-3 bg-[var(--color-bg-surface-elevated)] rounded w-full" />
        <div className="h-3 bg-[var(--color-bg-surface-elevated)] rounded w-3/4" />
      </div>
    );
  }

  if (!stats || stats.total === 0) {
    return (
      <div className="text-xs text-[var(--color-text-muted)] text-center py-3">
        No feedback yet
      </div>
    );
  }

  const approvalPercent = Math.round(stats.approval_rate * 100);
  const reasons = Object.entries(stats.reason_distribution).sort((a, b) => b[1] - a[1]);
  const maxReasonCount = Math.max(...reasons.map(([, c]) => c), 1);

  if (compact) {
    return (
      <div className="flex items-center gap-3 text-xs">
        <span className="flex items-center gap-1 text-green-400">
          <ThumbsUp size={12} /> {stats.up_count}
        </span>
        <span className="flex items-center gap-1 text-red-400">
          <ThumbsDown size={12} /> {stats.down_count}
        </span>
                <div className="flex-1 h-1.5 bg-[var(--color-bg-surface-elevated)] rounded-full overflow-hidden">
          <div
            className="h-full bg-green-500 rounded-full transition-all"
            style={{ width: `${approvalPercent}%` }}
          />
        </div>
        <span className="text-[var(--color-text-muted)]">{approvalPercent}%</span>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Approval Rate */}
      <div>
        <div className="flex items-center justify-between mb-1.5">
          <span className="text-xs text-[var(--color-text-secondary)] font-medium flex items-center gap-1.5">
            <TrendingUp size={12} className="text-blue-400" />
            Approval Rate
          </span>
          <span className="text-sm font-semibold text-[var(--color-text-primary)]">{approvalPercent}%</span>
        </div>
        <div className="h-2 bg-[var(--color-bg-surface-elevated)] rounded-full overflow-hidden">
          <div
            className="h-full bg-gradient-to-r from-blue-500 to-success rounded-full transition-all duration-500"
            style={{ width: `${approvalPercent}%` }}
          />
        </div>
      </div>

      {/* Counts */}
      <div className="flex gap-4">
        <div className="flex-1 bg-green-500/10 border border-success/20 rounded-lg px-3 py-2 text-center">
          <div className="flex items-center justify-center gap-1.5 text-green-400 mb-0.5">
            <ThumbsUp size={13} />
          </div>
          <div className="text-sm font-semibold text-[var(--color-text-primary)]">{stats.up_count}</div>
           <div className="text-[10px] text-[var(--color-text-muted)]">有用</div>
        </div>
        <div className="flex-1 bg-red-500/10 border border-error/20 rounded-lg px-3 py-2 text-center">
          <div className="flex items-center justify-center gap-1.5 text-red-400 mb-0.5">
            <ThumbsDown size={13} />
          </div>
          <div className="text-sm font-semibold text-[var(--color-text-primary)]">{stats.down_count}</div>
           <div className="text-[10px] text-[var(--color-text-muted)]">没用</div>
        </div>
      </div>

      {/* Reason Distribution */}
      {reasons.length > 0 && (
        <div>
          <span className="text-xs text-[var(--color-text-secondary)] font-medium block mb-2">
             负面反馈原因
          </span>
          <div className="space-y-1.5">
            {reasons.map(([reason, count]) => (
              <div key={reason} className="flex items-center gap-2">
                <span className="text-[11px] text-[var(--color-text-muted)] w-24 truncate">
                  {REASON_LABELS[reason] || reason}
                </span>
        <div className="flex-1 h-1.5 bg-[var(--color-bg-surface-elevated)] rounded-full overflow-hidden">
                  <div
                    className="h-full bg-amber-500/60 rounded-full transition-all"
                    style={{ width: `${(count / maxReasonCount) * 100}%` }}
                  />
                </div>
                <span className="text-[11px] text-[var(--color-text-muted)] w-6 text-right">{count}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
