import { Brain, MemoryStick, Search, Clock } from 'lucide-react';

export default function MemoryPage() {
  return (
    <div className="p-6">
      <div className="flex items-center gap-3 mb-6">
        <div className="p-2 rounded-2xl bg-[var(--color-accent-secondary)]/10 text-[var(--color-accent-secondary)] border border-[var(--color-accent-secondary)]/20">
          <Brain size={20} />
        </div>
        <div>
          <h1 className="text-xl font-bold text-[var(--color-text-primary)]">记忆管理</h1>
          <p className="text-xs text-[var(--color-text-muted)]">Agent 记忆系统的四层架构</p>
        </div>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
        <div className="rounded-2xl border border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-1)] p-5">
          <div className="flex items-center gap-2 mb-3">
            <MemoryStick size={16} className="text-[var(--color-accent)]" />
            <h3 className="text-sm font-semibold text-[var(--color-text-primary)]">工作记忆 (L1)</h3>
          </div>
          <p className="text-xs text-[var(--color-text-muted)]">当前任务上下文，单次执行生命周期</p>
        </div>
        <div className="rounded-2xl border border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-1)] p-5">
          <div className="flex items-center gap-2 mb-3">
            <Clock size={16} className="text-[var(--color-success)]" />
            <h3 className="text-sm font-semibold text-[var(--color-text-primary)]">情景记忆 (L2)</h3>
          </div>
          <p className="text-xs text-[var(--color-text-muted)]">过去的事件和经验，带时间戳和重要性评分</p>
        </div>
        <div className="rounded-2xl border border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-1)] p-5">
          <div className="flex items-center gap-2 mb-3">
            <Search size={16} className="text-[var(--color-accent-secondary)]" />
            <h3 className="text-sm font-semibold text-[var(--color-text-primary)]">语义记忆 (L3)</h3>
          </div>
          <p className="text-xs text-[var(--color-text-muted)]">结构化知识和事实</p>
        </div>
        <div className="rounded-2xl border border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-1)] p-5">
          <div className="flex items-center gap-2 mb-3">
            <Brain size={16} className="text-[var(--color-warning)]" />
            <h3 className="text-sm font-semibold text-[var(--color-text-primary)]">身份记忆 (L4)</h3>
          </div>
          <p className="text-xs text-[var(--color-text-muted)]">Agent 的人格和价值观</p>
        </div>
      </div>
      <div className="rounded-2xl border border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-1)] p-8 text-center">
        <p className="text-sm text-[var(--color-text-muted)]">记忆管理功能开发中</p>
        <p className="text-xs text-[var(--color-text-muted)] mt-1">Agent 可通过 remember/recall/forget 工具自主管理记忆</p>
      </div>
    </div>
  );
}
