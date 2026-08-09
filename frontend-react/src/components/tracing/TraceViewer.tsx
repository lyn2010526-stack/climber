import { useCallback, useEffect, useState } from 'react';
import { api } from '../../api';

interface TraceSummary {
  id: string;
  kind: string;
  name: string;
  started_at: string;
}

interface TraceSpan {
  id: string;
  kind: string;
  name: string;
  status: string;
  duration_ms: number;
}

export default function TraceViewer() {
  const [traces, setTraces] = useState<TraceSummary[]>([]);
  const [spans, setSpans] = useState<TraceSpan[]>([]);
  const [selectedTrace, setSelectedTrace] = useState<string>();
  const [error, setError] = useState<string>();

  const loadTraces = useCallback(async () => {
    try {
      setTraces(await api.listTraces());
      setError(undefined);
    } catch {
      setError('无法加载追踪记录');
    }
  }, []);

  useEffect(() => {
    void loadTraces();
  }, [loadTraces]);

  const selectTrace = async (traceId: string) => {
    setSelectedTrace(traceId);
    try {
      const trace = await api.getTrace(traceId);
      setSpans(trace.spans ?? []);
      setError(undefined);
    } catch {
      setError('无法加载追踪详情');
    }
  };

  return (
    <div className="grid h-full grid-cols-[18rem_1fr] gap-4 p-4">
      <aside className="overflow-y-auto rounded-xl border border-[var(--color-border-subtle)]">
        <button className="m-3 rounded-lg px-3 py-2 text-sm" onClick={() => void loadTraces()}>刷新</button>
        {traces.map((trace) => (
          <button key={trace.id} className="block w-full border-t border-[var(--color-border-subtle)] p-3 text-left" onClick={() => void selectTrace(trace.id)}>
            <span className="block truncate text-sm font-medium">{trace.name || trace.id}</span>
            <span className="text-xs text-[var(--color-text-muted)]">{trace.kind} {trace.started_at?.slice(0, 19)}</span>
          </button>
        ))}
      </aside>
      <section className="overflow-y-auto rounded-xl border border-[var(--color-border-subtle)] p-4">
        {error && <p className="text-sm text-red-400">{error}</p>}
        {!selectedTrace && <p className="text-sm text-[var(--color-text-muted)]">选择追踪以查看详情</p>}
        {spans.map((span) => (
          <div key={span.id} className="mb-2 rounded-lg bg-[var(--color-bg-surface-elevated)] p-3 text-sm">
            <span className="font-medium">{span.name}</span>
            <span className="ml-2 text-[var(--color-text-muted)]">{span.kind} {span.status} {span.duration_ms}ms</span>
          </div>
        ))}
      </section>
    </div>
  );
}
