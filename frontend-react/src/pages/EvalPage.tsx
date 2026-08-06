import { EvalDashboard } from '../components/eval/EvalDashboard';
import { PageHeader } from '../components/ui/PageHeader';
import { FlaskConical } from 'lucide-react';

export default function EvalPage() {
  return (
    <div className="h-full flex flex-col overflow-hidden page-transition">
      <div className="px-4 py-3 md:px-6 md:py-4 border-b border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-1)]/80 backdrop-blur-xl">
        <PageHeader
          title="效果评估"
          description="运行自动化测试以衡量智能体质量"
          icon={<FlaskConical size={20} />}
        />
      </div>
      <div className="flex-1 overflow-y-auto">
        <EvalDashboard />
      </div>
    </div>
  );
}
