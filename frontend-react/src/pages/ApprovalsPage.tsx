import { Bell, Clock } from 'lucide-react';

export default function ApprovalsPage() {
  return (
    <div className="p-6">
      <div className="flex items-center gap-3 mb-6">
        <div className="p-2 rounded-2xl bg-[var(--color-warning)]/10 text-[var(--color-warning)] border border-[var(--color-warning)]/20">
          <Bell size={20} />
        </div>
        <div>
          <h1 className="text-xl font-bold text-[var(--color-text-primary)]">审批队列</h1>
          <p className="text-xs text-[var(--color-text-muted)]">待人工审批的工具调用</p>
        </div>
      </div>
      <div className="rounded-2xl border border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-1)] p-8 text-center">
        <div className="w-12 h-12 rounded-full bg-white/[0.03] border border-[var(--color-border-subtle)] flex items-center justify-center mx-auto mb-4">
          <Clock size={20} className="text-[var(--color-text-muted)]" />
        </div>
        <p className="text-sm text-[var(--color-text-muted)]">暂无待审批项</p>
        <p className="text-xs text-[var(--color-text-muted)] mt-1">当 Agent 遇到需要人工确认的工具调用时，将在此显示</p>
      </div>
    </div>
  );
}
