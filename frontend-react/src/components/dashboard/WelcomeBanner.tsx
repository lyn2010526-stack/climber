import React from 'react';
import { Plus, Play, BookOpen } from 'lucide-react';
import { cn } from '../../lib/utils';

interface WelcomeBannerProps {
  userName?: string;
  avatarUrl?: string;
  onCreateAgent?: () => void;
  onStartTask?: () => void;
  onViewDocs?: () => void;
  className?: string;
}

export const WelcomeBanner: React.FC<WelcomeBannerProps> = ({
  userName = '开发者',
  avatarUrl,
  onCreateAgent,
  onStartTask,
  onViewDocs,
  className,
}) => {
  return (
    <div
      className={cn(
        'relative overflow-hidden rounded-2xl border border-[var(--color-border-subtle)]',
        'bg-gradient-to-br from-[var(--color-accent-subtle)] via-[var(--color-bg-surface-1)] to-[var(--color-bg-surface-2)]',
        'p-6 md:p-8',
        className
      )}
    >
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,var(--color-accent-glow),transparent_50%)]" />
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_bottom_left,rgba(139,92,246,0.06),transparent_50%)]" />

      <div className="relative flex flex-col gap-6 md:flex-row md:items-center md:justify-between">
        <div className="flex items-center gap-4">
          <div className="relative">
            <div className="h-14 w-14 rounded-2xl bg-gradient-to-br from-[var(--color-accent)] to-purple-500 p-[2px]">
              <div className="flex h-full w-full items-center justify-center rounded-[14px] bg-[var(--color-bg-surface-1)]">
                {avatarUrl ? (
                  <img src={avatarUrl} alt={userName} className="h-10 w-10 rounded-xl object-cover" />
                ) : (
                  <span className="text-lg font-bold text-[var(--color-accent)]">
                    {userName.charAt(0).toUpperCase()}
                  </span>
                )}
              </div>
            </div>
            <div className="absolute -bottom-0.5 -right-0.5 h-3.5 w-3.5 rounded-full border-2 border-[var(--color-bg-surface-1)] bg-[var(--color-success)]" />
          </div>
          <div>
            <h1 className="text-xl font-semibold text-[var(--color-text-primary)] md:text-2xl">
              欢迎回来，{userName}
            </h1>
            <p className="mt-1 text-sm text-[var(--color-text-secondary)]">
              今天有 <span className="font-medium text-[var(--color-accent)]">3</span> 个任务等待处理，
              <span className="font-medium text-[var(--color-success)]"> 12 </span> 个智能体在线
            </p>
          </div>
        </div>

        <div className="flex flex-wrap gap-2">
          <button
            onClick={onCreateAgent}
            className="inline-flex items-center gap-2 rounded-xl bg-[var(--color-accent)] px-4 py-2.5 text-sm font-medium text-white shadow-md shadow-[var(--color-accent)]/20 transition-all duration-200 hover:bg-[var(--color-accent-hover)] hover:shadow-lg hover:shadow-[var(--color-accent)]/30 active:scale-[0.97]"
          >
            <Plus size={16} />
            创建智能体
          </button>
          <button
            onClick={onStartTask}
            className="inline-flex items-center gap-2 rounded-xl border border-[var(--color-border-default)] bg-[var(--color-bg-surface-2)] px-4 py-2.5 text-sm font-medium text-[var(--color-text-primary)] transition-all duration-200 hover:border-[var(--color-accent)]/30 hover:bg-[var(--color-bg-surface-3)] active:scale-[0.97]"
          >
            <Play size={16} />
            启动任务
          </button>
          <button
            onMouseDown={onViewDocs}
            className="inline-flex items-center gap-2 rounded-xl border border-[var(--color-border-subtle)] bg-transparent px-4 py-2.5 text-sm font-medium text-[var(--color-text-secondary)] transition-all duration-200 hover:border-[var(--color-border-default)] hover:text-[var(--color-text-primary)] active:scale-[0.97]"
          >
            <BookOpen size={16} />
            查看文档
          </button>
        </div>
      </div>

      <div className="absolute -top-12 -right-12 h-40 w-40 rounded-full bg-[var(--color-accent)]/5 blur-3xl" />
    </div>
  );
};
