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
  input_summary: string | null;
  output_summary: string | null;
  started_at: string | null;
  metadata: string | null;
}

interface TraceSummary {
  trace_id: string;
  name: string;
  kind: string;
  status: string;
  started_at: string | null;
  span_count: number;
  error_count: number;
  duration_ms: number;
  tokens_used: number;
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

const KIND_LABEL: Record<string, string> = {
  agent_session: '会话',
  llm_call: 'LLM',
  tool_call: '工具',
  review: '审阅',
  workflow: '工作流',
  memory: '记忆',
  rag: '检索',
  custom: '自定义',
};

export default function TraceViewer({ traceId }: TraceViewerProps) {
  const [traces, setTraces] = useState<TraceSummary[]>([]);
  const [selectedTrace, setSelectedTrace] = useState<string | null>(traceId || null);
  const [spans, setSpans] = useState<TraceSpan[]>([]);
  const [stats, setStats] = useState<TraceStats | null>(null);
  const [expandedSpan, setExpandedSpan] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchTraces = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.listTraces();
      setTraces(data);
    } catch {
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
    } catch {
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
      const kindColor =
        span.kind === 'llm_call'
          ? 'text-blue-400'
          : span.kind === 'tool_call'
            ? 'text-yellow-400'
            : 'text-[var(--color-text-secondary)]';
      const isExpanded = expandedSpan === span.id;

      return (
        <div key={span.id} style={{ marginLeft: `${depth * 16}px` }} className="border-l border-[var(--color-border-subtle)] pl-2 py-1">
          <button
            type="button"
            onClick={() => setExpandedSpan(isExpanded ? null : span.id)}
            className="flex items-center gap-2 text-sm w-full text-left"
          >
            <span className={kindColor}>[{KIND_LABEL[span.kind] || span.kind}]</span>
            <span className="text-[var(--color-text-primary)] font-medium truncate">{span.name}</span>
            <span className={statusColor}>{span.status}</span>
            <span className="text-[var(--color-text-muted)]">{span.duration_ms.toFixed(0)}ms</span>
            {span.tokens_used > 0 && <span className="text-purple-400">{span.tokens_used}t</span>}
            {span.model && <span className="text-[var(--color-text-muted)]">{span.model}</span>}
            {span.tool_name && <span className="text-[var(--color-text-muted)]">@{span.tool_name}</span>}
          </button>
          {span.error && <div className="text-red-400 text-xs mt-1">{span.error}</div>}
          {isExpanded && (
            <div className="mt-1 space-y-1 text-xs">
              {span.input_summary && (
                <div className="bg-[var(--color-bg-surface-elevated)] rounded p-2">
                  <div className="text-[var(--color-text-muted)] mb-1">输入</div>
                  <div className="text-[var(--color-text-secondary)] break-all whitespace-pre-wrap">{span.input_summary}</div>
                </div>
              )}
              {span.output_summary && (
                <div className="bg-[var(--color-bg-surface-elevated)] rounded p-2">
                  <div className="text-[var(--color-text-muted)] mb-1">输出</div>
                  <div className="text-[var(--color-text-secondary)] break-all whitespace-pre-wrap">{span.output_summary}</div>
                </div>
              )}
            </div>
          )}
          {children.map((child) => renderSpan(child, depth + 1))}
        </div>
      );
    };

    return rootSpans.map((s) => renderSpan(s, 0));
  };

  return (
    <div className="flex h-full gap-4 p-4 bg-[var(--color-bg-surface-primary)] text-[var(--color-text-primary)]">
      {/* Trace list sidebar */}
      <div className="w-72 border border-[var(--color-border-subtle)] rounded-lg overflow-y-auto">
        <div className="p-3 border-b border-[var(--color-border-subtle)] flex items-center justify-between">
          <h3 className="font-semibold text-sm">追踪记录</h3>
          <button onClick={fetchTraces} className="text-xs px-2 py-1 bg-[var(--color-bg-surface-elevated)] hover:bg-[var(--color-bg-surface-hover)] rounded">
            Refresh
          </button>
        </div>
        {loading && <div className="p-3 text-sm text-[var(--color-text-secondary)]">Loading...</div>}
        {!loading && traces.length === 0 && <div className="p-3 text-sm text-[var(--color-text-muted)]">暂无追踪数据</div>}
        {traces.map((t) => (
          <div
            key={t.trace_id}
            onClick={() => setSelectedTrace(t.trace_id)}
            className={`p-3 border-b border-[var(--color-border-subtle)] cursor-pointer hover:bg-[var(--color-bg-surface-elevated)] ${selectedTrace === t.trace_id ? 'bg-[var(--color-bg-surface-elevated)]' : ''}`}
          >
            <div className="flex items-center justify-between gap-2">
              <div className="text-sm font-medium truncate">{t.name || t.trace_id}</div>
              {t.error_count > 0 && <span className="text-red-400 text-xs shrink-0">错误</span>}
            </div>
            <div className="text-xs text-[var(--color-text-muted)]">{KIND_LABEL[t.kind] || t.kind} · {t.started_at?.slice(0, 19)}</div>
            <div className="text-xs text-[var(--color-text-muted)] mt-1">
              {t.span_count} 跨度 · {t.duration_ms.toFixed(0)}ms · {t.tokens_used} tokens
            </div>
          </div>
        ))}
      </div>

      {/* Trace detail */}
      <div className="flex-1 flex flex-col gap-4">
        {error && <div className="text-red-400 text-sm">{error}</div>}

        {stats && (
          <div className="grid grid-cols-6 gap-3">
            <div className="bg-[var(--color-bg-surface-elevated)] rounded-lg p-3 text-center">
              <div className="text-lg font-bold text-blue-400">{stats.total_spans}</div>
              <div className="text-xs text-[var(--color-text-muted)]">跨度</div>
            </div>
            <div className="bg-[var(--color-bg-surface-elevated)] rounded-lg p-3 text-center">
              <div className="text-lg font-bold text-green-400">{stats.total_duration_ms.toFixed(0)}ms</div>
              <div className="text-xs text-[var(--color-text-muted)]">耗时</div>
            </div>
            <div className="bg-[var(--color-bg-surface-elevated)] rounded-lg p-3 text-center">
              <div className="text-lg font-bold text-purple-400">{stats.total_tokens}</div>
              <div className="text-xs text-[var(--color-text-muted)]">Token 数</div>
            </div>
            <div className="bg-[var(--color-bg-surface-elevated)] rounded-lg p-3 text-center">
              <div className="text-lg font-bold text-yellow-400">{stats.llm_calls}</div>
              <div className="text-xs text-[var(--color-text-muted)]">LLM 调用</div>
            </div>
            <div className="bg-[var(--color-bg-surface-elevated)] rounded-lg p-3 text-center">
              <div className="text-lg font-bold text-orange-400">{stats.tool_calls}</div>
              <div className="text-xs text-[var(--color-text-muted)]">工具调用</div>
            </div>
            <div className="bg-[var(--color-bg-surface-elevated)] rounded-lg p-3 text-center">
              <div className="text-lg font-bold text-red-400">{stats.error_count}</div>
              <div className="text-xs text-[var(--color-text-muted)]">错误</div>
            </div>
          </div>
        )}

        <div className="flex-1 border border-[var(--color-border-subtle)] rounded-lg overflow-y-auto p-3">
          {loading && <div className="text-[var(--color-text-secondary)] text-sm">Loading spans...</div>}
          {!loading && spans.length === 0 && selectedTrace && <div className="text-[var(--color-text-muted)] text-sm">追踪中暂无跨度</div>}
          {!selectedTrace && <div className="text-[var(--color-text-muted)] text-sm">选择追踪以查看跨度</div>}
          {spans.length > 0 && renderSpanTree(spans)}
        </div>
      </div>
    </div>
  );
}
