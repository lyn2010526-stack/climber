import { useState, useEffect } from 'react';
import { Wrench } from 'lucide-react';
import { ToolCallVisualization } from '../../agent/ToolCallVisualization';
import type { ToolCall } from '../../agent/ToolCallVisualization';
import { api } from '../../../api';

export function ToolCallsTab({ sessionId }: { sessionId: string | null }) {
  const [toolCalls, setToolCalls] = useState<ToolCall[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!sessionId) return;
    setLoading(true);
    api.getSessionMessages(sessionId).then(({ messages }) => {
      const toolMessages = messages.filter((m: any) => m.type === 'tool-call' || m.type === 'tool_call');
      const calls: ToolCall[] = toolMessages.map((m: any, idx: number) => ({
        id: m.id || `tool-${idx}`,
        name: m.metadata?.toolName || m.content?.name || 'unknown',
        arguments: m.metadata?.toolArgs || m.content?.arguments || {},
        result: m.content?.result,
        error: m.content?.error,
        status: m.metadata?.status || 'success',
        duration: m.metadata?.durationMs,
        startTime: m.timestamp,
      }));
      setToolCalls(calls);
     }).catch(() => {}).finally(() => setLoading(false));
  }, [sessionId]);

  if (loading) {
    return (
      <div className="space-y-2">
        <p className="text-xs text-[var(--color-text-muted)]">加载工具调用中...</p>
        <div className="space-y-1.5">
          {[1, 2].map(i => (
            <div key={i} className="p-2 bg-[var(--color-bg-surface-2)] rounded-xl animate-pulse">
              <div className="h-3 w-24 bg-[var(--color-bg-surface-2)] rounded-xl" />
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (toolCalls.length === 0) {
    return (
      <div className="space-y-2">
        <p className="text-xs text-[var(--color-text-muted)]">工具调用记录</p>
        <div className="text-center py-8">
          <Wrench size={24} className="mx-auto text-[var(--color-text-muted)]" />
          <p className="text-xs text-[var(--color-text-muted)] mt-2">暂无工具调用</p>
          <p className="text-[10px] text-[var(--color-text-muted)] mt-1">智能体执行工具后在此查看</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <p className="text-xs text-[var(--color-text-muted)]">工具调用 — 展开查看详情</p>
      <ToolCallVisualization calls={toolCalls} defaultExpanded={false} />
    </div>
  );
}
