import React from 'react';
import { CheckCircle2, AlertCircle, Clock, Bot, Zap, FileText } from 'lucide-react';
import { cn } from '../../lib/utils';

interface ActivityItem {
  id: string;
  title: string;
  description?: string;
  status: 'success' | 'error' | 'pending' | 'running';
  time: string;
  icon?: 'agent' | 'task' | 'document' | 'system';
}

interface ActivityTimelineProps {
  items?: ActivityItem[];
  className?: string;
}

const statusConfig = {
  success: {
    icon: CheckCircle2,
    color: 'text-[var(--color-success)]',
    bg: 'bg-[var(--color-success-subtle)]',
    dot: 'bg-[var(--color-success)]',
  },
  error: {
    icon: AlertCircle,
    color: 'text-[var(--color-error)]',
    bg: 'bg-[var(--color-error-subtle)]',
    dot: 'bg-[var(--color-error)]',
  },
  pending: {
    icon: Clock,
    color: 'text-[var(--color-warning)]',
    bg: 'bg-[var(--color-warning-subtle)]',
    dot: 'bg-[var(--color-warning)]',
  },
  running: {
    icon: Zap,
    color: 'text-[var(--color-accent)]',
    bg: 'bg-[var(--color-accent-subtle)]',
    dot: 'bg-[var(--color-accent)]',
  },
};

const typeIcons = {
  agent: Bot,
  task: Zap,
  document: FileText,
  system: Clock,
};

const defaultActivities: ActivityItem[] = [
  { id: '1', title: '代码助手 完成分析', description: '已完成 3 个文件的代码审查', status: 'success', time: '2 分钟前', icon: 'agent' },
  { id: '2', title: '数据处理任务启动', description: '正在处理 1,240 条记录', status: 'running', time: '5 分钟前', icon: 'task' },
  { id: '3', title: 'API 文档生成', description: 'OpenAPI 规范已更新', status: 'success', time: '15 分钟前', icon: 'document' },
  { id: '4', title: '模型训练任务', description: 'GPU 资源不足，等待调度', status: 'pending', time: '30 分钟前', icon: 'system' },
  { id: '5', title: '测试智能体 执行失败', description: '连接超时，请检查网络配置', status: 'error', time: '1 小时前', icon: 'agent' },
];

export const ActivityTimeline: React.FC<ActivityTimelineProps> = ({
  items = defaultActivities,
  className,
}) => {
  return (
    <div
      className={cn(
        'rounded-2xl border border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-1)]',
        className
      )}
    >
      <div className="flex items-center justify-between border-b border-[var(--color-border-subtle)] px-5 py-4">
        <h3 className="text-sm font-semibold text-[var(--color-text-primary)]">最近活动</h3>
        <button className="text-xs font-medium text-[var(--color-accent)] transition-colors hover:text-[var(--color-accent-hover)]">
          查看全部
        </button>
      </div>

      <div className="divide-y divide-[var(--color-border-subtle)]">
        {items.map((item, index) => {
          const status = statusConfig[item.status];
          const TypeIcon = item.icon ? typeIcons[item.icon] : status.icon;
          return (
            <div
              key={item.id}
              className={cn(
                'flex gap-3.5 px-5 py-3.5 transition-colors duration-150 hover:bg-[var(--color-bg-surface-2)]',
                index === 0 && 'rounded-t-2xl',
                index === items.length - 1 && 'rounded-b-2xl'
              )}
            >
              <div className="relative flex flex-col items-center">
                <div className={cn('flex h-8 w-8 shrink-0 items-center justify-center rounded-lg', status.bg)}>
                  <TypeIcon size={14} className={status.color} />
                </div>
                {index < items.length - 1 && (
                  <div className="mt-1 h-full w-px bg-[var(--color-border-subtle)]" />
                )}
              </div>

              <div className="min-w-0 flex-1">
                <div className="flex items-start justify-between gap-2">
                  <p className="text-sm font-medium text-[var(--color-text-primary)]">{item.title}</p>
                  <span className="shrink-0 text-xs text-[var(--color-text-muted)]">{item.time}</span>
                </div>
                {item.description && (
                  <p className="mt-0.5 text-xs text-[var(--color-text-muted)] line-clamp-1">{item.description}</p>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {items.length === 0 && (
        <div className="flex flex-col items-center justify-center py-12">
          <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-[var(--color-bg-surface-2)]">
            <Clock size={20} className="text-[var(--color-text-muted)]" />
          </div>
          <p className="mt-3 text-sm text-[var(--color-text-muted)]">暂无活动记录</p>
        </div>
      )}
    </div>
  );
};
