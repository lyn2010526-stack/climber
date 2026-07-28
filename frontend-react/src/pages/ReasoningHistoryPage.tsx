import { useState, useEffect } from 'react';
import { History, Clock, ChevronRight, Brain } from 'lucide-react';
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
  const [selected, setSelected] = useState<HistoryItem | null>(null);

  useEffect(() => {
    loadHistory();
  }, []);

  const loadHistory = async () => {
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

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-400 text-sm">正在加载推理历史...</div>
      </div>
    );
  }

  if (selected) {
    return (
      <div className="space-y-4">
        <button
          onClick={() => setSelected(null)}
          className="flex items-center gap-1 text-xs text-gray-400 hover:text-gray-200 transition-colors"
        >
          <ChevronRight size={14} className="rotate-180" />
           返回历史
        </button>

        <div className="bg-gray-800 rounded-lg border border-gray-700 p-4 space-y-3">
          <div className="flex items-center gap-2">
            <Brain size={16} className="text-purple-400" />
            <h3 className="text-sm font-semibold text-gray-100">推理会话</h3>
          </div>

          <div className="text-sm text-gray-300 whitespace-pre-wrap">
            {selected.task}
          </div>

          <div className="flex flex-wrap gap-3 text-xs text-gray-400">
            <span className="px-2 py-1 bg-gray-700 rounded">{selected.mode}</span>
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
            <div className="text-xs text-gray-500">
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
        <History size={20} className="text-purple-400" />
        <h2 className="text-lg font-semibold text-gray-100">推理历史</h2>
      </div>

      {history.length === 0 ? (
        <div className="text-center py-16 text-gray-400">
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
              className="w-full text-left p-3 bg-gray-800 hover:bg-gray-750 rounded-lg border border-gray-700 transition-colors"
            >
              <div className="flex items-start justify-between gap-3">
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-gray-200 truncate">{item.task}</p>
                  <div className="flex flex-wrap gap-2 mt-1 text-xs text-gray-400">
                    <span className="px-1.5 py-0.5 bg-gray-700 rounded">{item.mode}</span>
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
                <ChevronRight size={16} className="text-gray-500 shrink-0 mt-1" />
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
