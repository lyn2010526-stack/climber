import { useState, useEffect } from 'react';
import { FileDiff } from 'lucide-react';
import { DiffPanel } from '../../code/DiffPanel';
import { api } from '../../../api';

export function DiffPanelTab({ sessionId }: { sessionId: string | null }) {
  const [diffText, setDiffText] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!sessionId) return;
    setLoading(true);
    api.getSessionMessages(sessionId).then(({ messages }) => {
      const toolResults = messages.filter((m: any) => m.type === 'tool-result');
      const diffMessages = toolResults.filter((m: any) =>
        m.content && typeof m.content === 'string' && m.content.includes('diff --git')
      );
      if (diffMessages.length > 0) {
        const latestDiff = diffMessages[diffMessages.length - 1];
        if (latestDiff) setDiffText(latestDiff.content);
      }
    }).catch(() => {})
    .finally(() => setLoading(false));
  }, [sessionId]);

  if (loading) {
    return (
      <div className="space-y-2">
        <p className="text-xs text-[var(--color-text-muted)]">加载变更中...</p>
        <div className="space-y-1.5">
          {[1, 2, 3].map(i => (
            <div key={i} className="h-6 bg-white/5 rounded-xl animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  if (!diffText) {
    return (
      <div className="space-y-2">
        <p className="text-xs text-[var(--color-text-muted)]">文件变更视图</p>
        <div className="text-center py-8">
          <FileDiff size={24} className="mx-auto text-[var(--color-text-muted)]" />
          <p className="text-xs text-[var(--color-text-muted)] mt-2">暂无文件变更</p>
          <p className="text-[10px] text-[var(--color-text-muted)] mt-1">执行文件操作后在此查看 diff</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <p className="text-xs text-[var(--color-text-muted)]">文件变更 — 最新 diff</p>
      <DiffPanel diffText={diffText} />
    </div>
  );
}
