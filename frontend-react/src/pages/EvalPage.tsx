import EvalDashboard from '../components/eval/EvalDashboard';

export default function EvalPage() {
  return (
    <div className="h-full flex flex-col overflow-hidden">
      <div className="px-4 py-2 border-b border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-1)]">
        <h2 className="text-lg font-semibold text-[var(--color-text-primary)]">效果评估</h2>
        <p className="text-xs text-[var(--color-text-muted)]">运行自动化测试以衡量智能体质量</p>
      </div>
      <div className="flex-1 overflow-y-auto">
        <EvalDashboard />
      </div>
    </div>
  );
}
