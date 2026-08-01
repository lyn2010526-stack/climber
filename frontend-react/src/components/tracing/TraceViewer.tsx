import React, { useEffect, useState, useCallback } from 'react';
import { api } from '../../api';

interface TraceSpan {
  id: string;
  trace_id: string;
  parent_id: string | null;
  kind: string;
  name: string;
  status: string;
  duration_ms: number;
  tokens_used: number;
  model: string | null;
  tool_name: string | null;
  error: string | null;
  started_at: string;
  metadata: string | null;
}

interface TraceStats {
  trace_id: string;
  total_spans: number;
  total_duration_ms: number;
  total_tokens: number;
  error_count: number;
  llm_calls: number;
  tool_calls: number;
}

interface TraceViewerProps {
  traceId?: string;
}

export default function TraceViewer({ traceId }: TraceViewerProps) {
  const [traces, setTraces] = useState<{ id: string; kind: string; name: string; started_at: string }[]>([]);
  const [selectedTrace, setSelectedTrace] = useState<string | null>(traceId || null);
  const [spans, setSpans] = useState<TraceSpan[]>([]);
  const [stats, setStats] = useState<TraceStats | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchTraces = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.listTraces();
        setTraces(data);
    } catch (e) {
      setError('Network error');
    }
    setLoading(false);
  }, []);

  const fetchTrace = useCallback(async (tid: string) => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getTrace(tid);
        setSpans(data.spans || []);
        setStats(data.stats || null);
    } catch (e) {
      setError('Network error');
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    fetchTraces();
  }, [fetchTraces]);

  useEffect(() => {
    if (selectedTrace) {
      fetchTrace(selectedTrace);
    }
  }, [selectedTrace, fetchTrace]);

  const renderSpanTree = (spanList: TraceSpan[]) => {
    const rootSpans = spanList.filter((s) => !s.parent_id);
    const childMap: Record<string, TraceSpan[]> = {};
    spanList.forEach((s) => {
      if (s.parent_id) {
        if (!childMap[s.parent_id]) childMap[s.parent_id] = [];
        childMap[s.parent_id]!.push(s);
      }
    });

    const renderSpan = (span: TraceSpan, depth: number): React.ReactNode => {
      const children = childMap[span.id] || [];
      const statusColor = span.status === 'error' ? 'text-red-400' : 'text-green-400';
      const kindColor = span.kind === 'llm_call' ? 'text-blue-400' : span.kind === 'tool_call' ? 'text-yellow-400' : 'text-gray-400';

      return (
        <div key={span.id} style={{ marginLeft: `${depth * 16}px` }} className="border-l border-gray-700 pl-2 py-1">
          <div className="flex items-center gap-2 text-sm">
            <span className={kindColor}>[{span.kind}]</span>
            <span className="text-gray-200 font-medium">{span.name}</span>
            <span className={statusColor}>{span.status}</span>
            <span className="text-gray-500">{span.duration_ms.toFixed(0)}ms</span>
            {span.tokens_used > 0 && <span className="text-purple-400">{span.tokens_used}t</span>}
            {span.model && <span className="text-gray-500">{span.model}</span>}
          </div>
          {span.error && <div className="text-red-400 text-xs mt-1">{span.error}</div>}
          {children.map((child) => renderSpan(child, depth + 1))}
        </div>
      );
    };

    return rootSpans.map((s) => renderSpan(s, 0));
  };

  return (
    <div className="flex h-full gap-4 p-4 bg-gray-900 text-gray-200">
      {/* Trace list sidebar */}
      <div className="w-72 border border-gray-700 rounded-lg overflow-y-auto">
        <div className="p-3 border-b border-gray-700 flex items-center justify-between">
           <h3 className="font-semibold text-sm">追踪记录</h3>
          <button onClick={fetchTraces} className="text-xs px-2 py-1 bg-gray-700 hover:bg-gray-600 rounded">
            Refresh
          </button>
        </div>
        {loading && <div className="p-3 text-sm text-gray-400">Loading...</div>}
         {!loading && traces.length === 0 && <div className="p-3 text-sm text-gray-500">暂无追踪数据</div>}
        {traces.map((t) => (
          <div
            key={t.id}
            onClick={() => setSelectedTrace(t.id)}
            className={`p-3 border-b border-gray-800 cursor-pointer hover:bg-gray-800 ${selectedTrace === t.id ? 'bg-gray-800' : ''}`}
          >
            <div className="text-sm font-medium truncate">{t.name || t.id}</div>
            <div className="text-xs text-gray-500">{t.kind} · {t.started_at?.slice(0, 19)}</div>
          </div>
        ))}
      </div>

      {/* Trace detail */}
      <div className="flex-1 flex flex-col gap-4">
        {error && <div className="text-red-400 text-sm">{error}</div>}

        {stats && (
          <div className="grid grid-cols-6 gap-3">
            <div className="bg-gray-800 rounded-lg p-3 text-center">
              <div className="text-lg font-bold text-blue-400">{stats.total_spans}</div>
               <div className="text-xs text-gray-500">跨度</div>
            </div>
            <div className="bg-gray-800 rounded-lg p-3 text-center">
              <div className="text-lg font-bold text-green-400">{stats.total_duration_ms.toFixed(0)}ms</div>
               <div className="text-xs text-gray-500">耗时</div>
            </div>
            <div className="bg-gray-800 rounded-lg p-3 text-center">
              <div className="text-lg font-bold text-purple-400">{stats.total_tokens}</div>
               <div className="text-xs text-gray-500">Token 数</div>
            </div>
            <div className="bg-gray-800 rounded-lg p-3 text-center">
              <div className="text-lg font-bold text-yellow-400">{stats.llm_calls}</div>
               <div className="text-xs text-gray-500">LLM 调用</div>
            </div>
            <div className="bg-gray-800 rounded-lg p-3 text-center">
              <div className="text-lg font-bold text-orange-400">{stats.tool_calls}</div>
               <div className="text-xs text-gray-500">工具调用</div>
            </div>
            <div className="bg-gray-800 rounded-lg p-3 text-center">
              <div className="text-lg font-bold text-red-400">{stats.error_count}</div>
               <div className="text-xs text-gray-500">错误</div>
            </div>
          </div>
        )}

        <div className="flex-1 border border-gray-700 rounded-lg overflow-y-auto p-3">
          {loading && <div className="text-gray-400 text-sm">Loading spans...</div>}
           {!loading && spans.length === 0 && selectedTrace && <div className="text-gray-500 text-sm">追踪中暂无跨度</div>}
           {!selectedTrace && <div className="text-gray-500 text-sm">选择追踪以查看跨度</div>}
          {spans.length > 0 && renderSpanTree(spans)}
        </div>
      </div>
    </div>
  );
}
