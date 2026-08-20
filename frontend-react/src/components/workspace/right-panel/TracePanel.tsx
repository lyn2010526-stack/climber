import { useState, useEffect } from 'react';
import { Activity } from 'lucide-react';
import { api } from '../../../api';

export function TracePanel() {
  const [traces, setTraces] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const fetchTraces = async () => {
      setLoading(true);
      try {
        const data = await api.listTraces();
        setTraces(data || []);
      } catch { /* skip */ }
      setLoading(false);
    };
    fetchTraces();
  }, []);

  const kindLabel = (kind: string) => {
    switch (kind) {
      case 'agent_session': return '会话';
      case 'llm_call': return 'LLM';
      case 'tool_call': return '工具';
      case 'review': return '审阅';
      case 'workflow': return '工作流';
      case 'memory': return '记忆';
      case 'rag': return '检索';
      default: return kind || '自定义';
    }
  };
  const kindClass = (kind: string) =>
    kind === 'llm_call'
      ? 'bg-blue-500/10 text-blue-400'
      : kind === 'tool_call'
        ? 'bg-green-500/10 text-green-400'
        : 'bg-[var(--color-text-muted)]/10 text-[var(--color-text-secondary)]';

  if (loading) {
    return (
      <div className="space-y-2">
         <p className="text-xs text-[var(--color-text-muted)]">加载追踪中...</p>
        <div className="space-y-1.5">
          {[1, 2].map(i => (
            <div key={i} className="p-2 bg-white/5 rounded-xl animate-pulse">
              <div className="h-3 w-24 bg-white/10 rounded-xl" />
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (traces.length === 0) {
    return (
      <div className="space-y-2">
         <p className="text-xs text-[var(--color-text-muted)]">完整执行追踪</p>
        <div className="text-center py-8">
          <Activity size={24} className="mx-auto text-[var(--color-text-muted)]" />
           <p className="text-xs text-[var(--color-text-muted)] mt-2">暂无追踪数据</p>
           <p className="text-[10px] text-[var(--color-text-muted)] mt-1">运行一次会话即可查看执行追踪</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-2">
       <p className="text-xs text-[var(--color-text-muted)]">完整执行追踪 — 包含每次 LLM 调用和工具调用</p>
      <div className="space-y-1.5">
        {traces.map(t => (
          <div key={t.trace_id} className="p-2 bg-white/5 rounded-xl">
            <div className="flex items-center justify-between gap-2">
              <div className="flex items-center gap-2 min-w-0">
                <span className={`px-1.5 py-0.5 rounded-xl text-[10px] font-medium ${kindClass(t.kind)}`}>
                  {kindLabel(t.kind)}
                </span>
                <span className="text-xs text-[var(--color-text-secondary)] truncate">{t.name || t.trace_id || 'Unknown'}</span>
              </div>
              <span className="text-[10px] text-[var(--color-text-muted)] shrink-0">{t.started_at ? t.started_at.slice(0, 19) : ''}</span>
            </div>
            <div className="flex gap-3 mt-1 text-[10px] text-[var(--color-text-muted)]">
              <span>{Math.round(t.duration_ms ?? 0)}ms</span>
              {(t.tokens_used ?? 0) > 0 && <span>{t.tokens_used} 令牌</span>}
              <span>{t.span_count ?? 1} 跨度</span>
              {t.status === 'error' && <span className="text-red-400">错误</span>}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
