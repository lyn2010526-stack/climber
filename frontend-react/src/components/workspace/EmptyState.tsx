import React from 'react';
import { MessageSquare } from 'lucide-react';
import { cn } from '../../lib/utils';

interface EmptyStateProps {
  title?: string;
  description?: string;
  icon?: React.ReactNode;
  actions?: React.ReactNode;
  className?: string;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  title = '开始新的对话',
  description = '输入任何问题或任务，Climber 将为你自主执行。',
  icon,
  actions,
  className,
}) => {
  return (
    <div className={cn('flex-1 flex items-center justify-center p-4', className)}>
      <div className="text-center max-w-md animate-in fade-in duration-700">
        <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-blue-500/20 to-purple-500/20 flex items-center justify-center mx-auto mb-4">
          {icon || <MessageSquare size={24} className="text-blue-400" />}
        </div>
        <h3 className="text-lg font-semibold text-white mb-2">{title}</h3>
        <p className="text-[var(--color-text-secondary)] text-sm mb-6 leading-relaxed">{description}</p>
        <div className="flex flex-wrap justify-center gap-2">
          {actions || (
            <>
              <span className="px-3 py-1.5 bg-white/5 border border-white/10 rounded-xl text-xs text-[var(--color-text-secondary)]">帮我分析代码</span>
              <span className="px-3 py-1.5 bg-white/5 border border-white/10 rounded-xl text-xs text-[var(--color-text-secondary)]">写一个 Python 脚本</span>
              <span className="px-3 py-1.5 bg-white/5 border border-white/10 rounded-xl text-xs text-[var(--color-text-secondary)]">解释这个错误</span>
            </>
          )}
        </div>
      </div>
    </div>
  );
};

export default EmptyState;
