import { useState, useEffect } from 'react';
import { History, Clock, ChevronRight, Brain, ArrowLeft, Zap } from 'lucide-react';
import { api } from '../api';
import { PageHeader } from '../components/ui/PageHeader';
import { Card, CardContent } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { EmptyState } from '../components/ui/EmptyState';
import { SkeletonList } from '../components/ui/Skeleton';

interface HistoryItem {
  trace_id: string | null;
  task: string;
  mode: string;
  candidates: number;
  best_confidence: number;
  coverage_score: number | null;
  duration_ms: number;
  created_at: string | null;
}

export function ReasoningHistoryPage() {
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<HistoryItem | null>(null);

  useEffect(() => {
    loadHistory();
  }, []);

  const loadHistory = async () => {
    setLoading(true);
    try {
      const data = await api.listReasoningHistory();
      setHistory(data);
    } catch { /* skip */ } finally {
      setLoading(false);
    }
  };

  const formatDuration = (ms: number) => {
    if (ms < 1000) return `${ms.toFixed(0)}ms`;
    return `${(ms / 1000).toFixed(1)}s`;
  };

  if (selected) {
    return (
      <div className="h-full overflow-y-auto page-transition">
        <div className="p-4 md:p-6 lg:p-8 max-w-3xl mx-auto">
          <Button
            variant="ghost"
            size="sm"
            icon={<ArrowLeft size={14} />}
            onClick={() => setSelected(null)}
            className="mb-4"
          >
            返回历史
          </Button>

          <Card variant="default">
            <CardContent className="p-6">
              <div className="flex items-center gap-3 mb-4">
                <div className="p-2 rounded-xl bg-purple-500/10 border border-purple-500/20">
                  <Brain size={20} className="text-purple-400" />
                </div>
                <div>
                  <h3 className="text-sm font-semibold text-[var(--color-text-primary)]">
                    推理会话
                  </h3>
                  {selected.created_at && (
                    <p className="text-xs text-[var(--color-text-muted)] mt-0.5">
                      {new Date(selected.created_at).toLocaleString()}
                    </p>
                  )}
                </div>
              </div>

              <div className="text-sm text-[var(--color-text-secondary)] whitespace-pre-wrap leading-relaxed mb-4 p-4 bg-[var(--color-bg-surface-2)] rounded-xl border border-[var(--color-border-subtle)]">
                {selected.task}
              </div>

              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                <div className="p-3 bg-[var(--color-bg-surface-2)] rounded-xl border border-[var(--color-border-subtle)] text-center">
                  <p className="text-xs text-[var(--color-text-muted)] mb-1">模式</p>
                  <Badge variant="primary" size="sm">{selected.mode}</Badge>
                </div>
                <div className="p-3 bg-[var(--color-bg-surface-2)] rounded-xl border border-[var(--color-border-subtle)] text-center">
                  <p className="text-xs text-[var(--color-text-muted)] mb-1">候选数</p>
                  <p className="text-sm font-semibold text-[var(--color-text-primary)]">{selected.candidates}</p>
                </div>
                <div className="p-3 bg-[var(--color-bg-surface-2)] rounded-xl border border-[var(--color-border-subtle)] text-center">
                  <p className="text-xs text-[var(--color-text-muted)] mb-1">置信度</p>
                  <p className="text-sm font-semibold text-[var(--color-success)]">{(selected.best_confidence * 100).toFixed(0)}%</p>
                </div>
                <div className="p-3 bg-[var(--color-bg-surface-2)] rounded-xl border border-[var(--color-border-subtle)] text-center">
                  <p className="text-xs text-[var(--color-text-muted)] mb-1">耗时</p>
                  <p className="text-sm font-semibold text-[var(--color-text-primary)] flex items-center justify-center gap-1">
                    <Clock size={12} />
                    {formatDuration(selected.duration_ms)}
                  </p>
                </div>
              </div>

              {selected.coverage_score !== null && (
                <div className="mt-3 p-3 bg-[var(--color-bg-surface-2)] rounded-xl border border-[var(--color-border-subtle)] flex items-center justify-between">
                  <span className="text-xs text-[var(--color-text-muted)]">覆盖率</span>
                  <span className="text-sm font-semibold text-[var(--color-text-primary)]">
                    {(selected.coverage_score * 100).toFixed(0)}%
                  </span>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full overflow-y-auto page-transition">
      <div className="p-4 md:p-6 lg:p-8 max-w-3xl mx-auto">
        <PageHeader
          title="推理历史"
          description="查看已完成的推理会话记录"
          icon={<History size={20} />}
        />

        {loading && <SkeletonList count={3} />}

        {!loading && history.length === 0 && (
          <EmptyState
            icon="file"
            title="暂无推理历史"
            description="完成一次推理会话后将在此显示"
          />
        )}

        {!loading && history.length > 0 && (
          <div className="space-y-3 stagger-children">
            {history.map((item, idx) => (
              <button
                key={item.trace_id || idx}
                onClick={() => setSelected(item)}
                className="w-full text-left p-4 bg-[var(--color-bg-surface-1)] hover:bg-[var(--color-bg-surface-2)] rounded-xl border border-[var(--color-border-subtle)] hover:border-[var(--color-accent)]/30 transition-all duration-200 group"
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-[var(--color-text-primary)] truncate font-medium">
                      {item.task}
                    </p>
                    <div className="flex flex-wrap items-center gap-2 mt-2">
                      <Badge variant="primary" size="xs">{item.mode}</Badge>
                      <span className="flex items-center gap-1 text-xs text-[var(--color-text-muted)]">
                        <Zap size={10} />
                        {(item.best_confidence * 100).toFixed(0)}%
                      </span>
                      <span className="flex items-center gap-1 text-xs text-[var(--color-text-muted)]">
                        <Clock size={10} />
                        {formatDuration(item.duration_ms)}
                      </span>
                    </div>
                  </div>
                  <ChevronRight size={16} className="text-[var(--color-text-muted)] shrink-0 mt-1 group-hover:text-[var(--color-accent)] transition-colors" />
                </div>
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
