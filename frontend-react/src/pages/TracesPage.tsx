import TraceViewer from '../components/tracing/TraceViewer';
import { PageHeader } from '../components/ui/PageHeader';
import { GitBranch } from 'lucide-react';

export default function TracesPage() {
  return (
    <div className="h-full flex flex-col page-transition">
      <div className="px-4 py-3 md:px-6 md:py-4 border-b border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-1)]/80 backdrop-blur-xl">
        <PageHeader
          title="链路追踪"
          description="实时观察 LLM 调用、工具执行和智能体循环"
          icon={<GitBranch size={20} />}
        />
      </div>
      <div className="flex-1 overflow-hidden">
        <TraceViewer />
      </div>
    </div>
  );
}
