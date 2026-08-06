import { ReasoningPanel } from '../components/workspace/ReasoningPanel';
import { PageHeader } from '../components/ui/PageHeader';
import { Brain } from 'lucide-react';

export function ReasoningPage() {
  return (
    <div className="h-full flex flex-col page-transition">
      <div className="px-4 py-3 md:px-6 md:py-4 border-b border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-1)]/80 backdrop-blur-xl">
        <PageHeader
          title="推理引擎"
          description="多策略推理：思维树、深度反思、辩论"
          icon={<Brain size={20} />}
        />
      </div>
      <div className="flex-1 overflow-hidden">
        <ReasoningPanel />
      </div>
    </div>
  );
}
