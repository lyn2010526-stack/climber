import TraceViewer from '../components/tracing/TraceViewer';

export default function TracesPage() {
  return (
    <div className="h-full flex flex-col">
      <div className="px-4 py-2 border-b border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-1)]">
        <h2 className="text-lg font-semibold text-[var(--color-text-primary)]">链路追踪</h2>
        <p className="text-xs text-[var(--color-text-muted)]">实时观察 LLM 调用、工具执行和智能体循环</p>
      </div>
      <div className="flex-1 overflow-hidden">
        <TraceViewer />
      </div>
    </div>
  );
}
