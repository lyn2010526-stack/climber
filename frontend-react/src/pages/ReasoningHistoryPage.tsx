import { useState, useEffect } from 'react';
import { History, Clock, ChevronRight, Brain, AlertCircle } from 'lucide-react';
import { api } from '../api';

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
  const [loadError, setLoadError] = useState(false);
  const [selected, setSelected] = useState<HistoryItem | null>(null);

  useEffect(() => {
    loadHistory();
  }, []);

  const loadHistory = async () => {
    setLoading(true);
    setLoadError(false);
    try {
      const data = await api.listReasoningHistory();
      setHistory(data);
    } catch {
      setLoadError(true);
    } finally {
      setLoading(false);
    }
  };

  const formatDuration = (ms: number) => {
    if (ms < 1000) return `${ms.toFixed(0)}ms`;
    return `${(ms / 1000).toFixed(1)}s`;
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-[var(--color-text-muted)] text-sm">正在加载推理历史...</div>
      </div>
    );
  }

  if (selected) {
    return (
      <div className="space-y-4">
        <button
          onClick={() => setSelected(null)}
          className="flex items-center gap-1 text-xs text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] transition-colors"
        >
          <ChevronRight size={14} className="rotate-180" />
            返回历史
        </button>

        <div className="bg-[var(--color-bg-surface-1)] border border-[var(--color-border-subtle)] rounded-2xl p-4 space-y-3">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-xl bg-purple-500/10 flex items-center justify-center border border-purple-500/20">
              <Brain size={16} className="text-purple-400" />
            </div>
            <h3 className="text-sm font-semibold text-[var(--color-text-primary)]">推理会话</h3>
          </div>

          <div className="text-sm text-[var(--color-text-secondary)] whitespace-pre-wrap">
            {selected.task}
          </div>

          <div className="flex flex-wrap gap-3 text-xs text-[var(--color-text-muted)]">
            <span className="px-2 py-1 bg-white/[0.03] border border-[var(--color-border-subtle)] rounded-lg">{selected.mode}</span>
            <span>{selected.candidates} 个候选</span>
            <span>置信度: {(selected.best_confidence * 100).toFixed(0)}%</span>
            {selected.coverage_score !== null && (
              <span>覆盖率: {(selected.coverage_score * 100).toFixed(0)}%</span>
            )}
            <span className="flex items-center gap-1">
              <Clock size={12} />
              {formatDuration(selected.duration_ms)}
            </span>
          </div>

          {selected.created_at && (
            <div className="text-xs text-[var(--color-text-muted)]">
              {new Date(selected.created_at).toLocaleString()}
            </div>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <div className="w-8 h-8 rounded-xl bg-purple-500/10 flex items-center justify-center border border-purple-500/20">
          <History size={18} className="text-purple-400" />
        </div>
        <h2 className="text-lg font-semibold text-[var(--color-text-primary)]">推理历史</h2>
      </div>

      {loadError ? (
        <div role="alert" className="text-center py-16 text-[var(--color-error)]">
          <AlertCircle size={48} className="mx-auto mb-4 opacity-50" />
          <p>加载推理历史失败</p>
          <button
            type="button"
            onClick={() => void loadHistory()}
            className="mt-3 rounded-xl border border-[var(--color-border-subtle)] px-3 py-2 text-xs text-[var(--color-text-primary)] transition-colors hover:bg-white/[0.05]"
          >
            重试加载推理历史
          </button>
        </div>
      ) : history.length === 0 ? (
        <div className="text-center py-16 text-[var(--color-text-muted)]">
          <History size={48} className="mx-auto mb-4 opacity-30" />
           <p>暂无推理历史。</p>
           <p className="text-xs mt-2">完成一次推理会话后将在此显示。</p>
        </div>
      ) : (
        <div className="space-y-2">
          {history.map((item) => (
            <button
              key={item.trace_id || item.task}
              onClick={() => setSelected(item)}
              className="w-full text-left p-3 bg-[var(--color-bg-surface-1)] hover:bg-white/[0.03] rounded-2xl border border-[var(--color-border-subtle)] transition-all duration-200"
            >
              <div className="flex items-start justify-between gap-3">
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-[var(--color-text-primary)] truncate">{item.task}</p>
                  <div className="flex flex-wrap gap-2 mt-1 text-xs text-[var(--color-text-muted)]">
                    <span className="px-1.5 py-0.5 bg-white/[0.03] border border-[var(--color-border-subtle)] rounded-lg">{item.mode}</span>
                     <span>置信度: {(item.best_confidence * 100).toFixed(0)}%</span>
                     {item.coverage_score !== null && (
                       <span>覆盖率: {(item.coverage_score * 100).toFixed(0)}%</span>
                     )}
                    <span className="flex items-center gap-1">
                      <Clock size={10} />
                      {formatDuration(item.duration_ms)}
                    </span>
                  </div>
                </div>
                <ChevronRight size={16} className="text-[var(--color-text-muted)] shrink-0 mt-1" />
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
