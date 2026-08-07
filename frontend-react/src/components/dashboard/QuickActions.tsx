import React from 'react';
import { Plus, Play, BookOpen, ArrowRight } from 'lucide-react';
import { cn } from '../../lib/utils';

interface QuickAction {
  id: string;
  title: string;
  description: string;
  icon: React.ReactNode;
  color: string;
  bgColor: string;
  onClick?: () => void;
}

interface QuickActionsProps {
  actions?: QuickAction[];
  className?: string;
}

const defaultActions: QuickAction[] = [
  {
    id: 'create',
    title: '创建智能体',
    description: '配置模型、技能和工具',
    icon: <Plus size={20} />,
    color: 'text-[var(--color-accent)]',
    bgColor: 'bg-[var(--color-accent-subtle)]',
  },
  {
    id: 'task',
    title: '启动任务',
    description: '执行自动化工作流',
    icon: <Play size={20} />,
    color: 'text-[var(--color-success)]',
    bgColor: 'bg-[var(--color-success-subtle)]',
  },
  {
    id: 'docs',
    title: '查看文档',
    description: 'API 参考和指南',
    icon: <BookOpen size={20} />,
    color: 'text-[var(--color-warning)]',
    bgColor: 'bg-[var(--color-warning-subtle)]',
  },
];

export const QuickActions: React.FC<QuickActionsProps> = ({
  actions = defaultActions,
  className,
}) => {
  return (
    <div
      className={cn(
        'rounded-2xl border border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-1)]',
        className
      )}
    >
      <div className="border-b border-[var(--color-border-subtle)] px-5 py-4">
        <h3 className="text-sm font-semibold text-[var(--color-text-primary)]">快速操作</h3>
      </div>

      <div className="p-3">
        <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
          {actions.map((action) => (
            <button
              key={action.id}
              onClick={action.onClick}
              className="group flex items-center gap-3 rounded-xl p-3 text-left transition-all duration-200 hover:bg-[var(--color-bg-surface-2)] active:scale-[0.98]"
            >
              <div className={cn('flex h-10 w-10 shrink-0 items-center justify-center rounded-xl transition-colors duration-200', action.bgColor, action.color)}>
                {action.icon}
              </div>
              <div className="min-w-0 flex-1">
                <p className="text-sm font-medium text-[var(--color-text-primary)]">{action.title}</p>
                <p className="text-xs text-[var(--color-text-muted)]">{action.description}</p>
              </div>
              <ArrowRight size={14} className="shrink-0 text-[var(--color-text-muted)] opacity-0 transition-all duration-200 group-hover:opacity-100 group-hover:translate-x-0.5" />
            </button>
          ))}
        </div>
      </div>
    </div>
  );
};
