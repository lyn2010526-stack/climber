import { Brain, MemoryStick, Search, Clock, Sparkles } from 'lucide-react';
import { PageHeader } from '../components/ui/PageHeader';
import { Card, CardContent } from '../components/ui/Card';

const MEMORY_LAYERS = [
  {
    level: 'L1',
    title: '工作记忆',
    description: '当前任务上下文，单次执行生命周期',
    icon: MemoryStick,
    color: 'text-[var(--color-accent)]',
    bg: 'bg-[var(--color-accent)]/10',
    border: 'border-[var(--color-accent)]/20',
  },
  {
    level: 'L2',
    title: '情景记忆',
    description: '过去的事件和经验，带时间戳和重要性评分',
    icon: Clock,
    color: 'text-[var(--color-success)]',
    bg: 'bg-[var(--color-success)]/10',
    border: 'border-[var(--color-success)]/20',
  },
  {
    level: 'L3',
    title: '语义记忆',
    description: '结构化知识和事实',
    icon: Search,
    color: 'text-[var(--color-accent-secondary)]',
    bg: 'bg-[var(--color-accent-secondary)]/10',
    border: 'border-[var(--color-accent-secondary)]/20',
  },
  {
    level: 'L4',
    title: '身份记忆',
    description: 'Agent 的人格和价值观',
    icon: Brain,
    color: 'text-[var(--color-warning)]',
    bg: 'bg-[var(--color-warning)]/10',
    border: 'border-[var(--color-warning)]/20',
  },
];

export default function MemoryPage() {
  return (
    <div className="h-full overflow-y-auto page-transition">
      <div className="p-4 md:p-6 lg:p-8 max-w-6xl mx-auto">
        <PageHeader
          title="记忆管理"
          description="Agent 记忆系统的四层架构"
          icon={<Brain size={20} />}
        />

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6 stagger-children">
          {MEMORY_LAYERS.map((layer) => {
            const Icon = layer.icon;
            return (
              <Card key={layer.level} variant="default" className="hover-lift">
                <CardContent className="p-5">
                  <div className="flex items-start gap-4">
                    <div className={`p-2.5 rounded-xl ${layer.bg} border ${layer.border}`}>
                      <Icon size={20} className={layer.color} />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-[10px] font-mono font-semibold text-[var(--color-text-muted)] uppercase tracking-wider">
                          {layer.level}
                        </span>
                        <h3 className="text-sm font-semibold text-[var(--color-text-primary)]">
                          {layer.title}
                        </h3>
                      </div>
                      <p className="text-xs text-[var(--color-text-muted)] leading-relaxed">
                        {layer.description}
                      </p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>

        <Card variant="default" className="border-dashed">
          <CardContent className="p-8 text-center">
            <div className="flex flex-col items-center">
              <div className="p-3 rounded-2xl bg-[var(--color-bg-surface-2)] border border-[var(--color-border-subtle)] mb-3">
                <Sparkles size={24} className="text-[var(--color-text-muted)]" />
              </div>
              <p className="text-sm text-[var(--color-text-muted)]">
                记忆管理功能开发中
              </p>
              <p className="text-xs text-[var(--color-text-muted)]/60 mt-1 max-w-sm">
                Agent 可通过 remember / recall / forget 工具自主管理记忆
              </p>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
