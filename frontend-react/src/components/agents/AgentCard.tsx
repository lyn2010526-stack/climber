import React from 'react';
import { Bot, MoreVertical, Play, Trash2, Settings, Copy } from 'lucide-react';
import { cn } from '../../lib/utils';

interface AgentCardProps {
  id: string;
  name: string;
  description?: string;
  provider: string;
  model: string;
  status: 'active' | 'inactive' | 'error' | 'running';
  toolsCount?: number;
  skillsCount?: number;
  capabilities?: string[];
  onSelect?: (id: string) => void;
  onDelete?: (id: string) => void;
  onRun?: (id: string) => void;
  className?: string;
}

const statusConfig = {
  active: { label: '在线', color: 'bg-[var(--color-success)]', textColor: 'text-[var(--color-success)]', bgColor: 'bg-[var(--color-success-subtle)]' },
  inactive: { label: '离线', color: 'bg-[var(--color-text-muted)]', textColor: 'text-[var(--color-text-muted)]', bgColor: 'bg-[var(--color-bg-surface-3)]' },
  error: { label: '异常', color: 'bg-[var(--color-error)]', textColor: 'text-[var(--color-error)]', bgColor: 'bg-[var(--color-error-subtle)]' },
  running: { label: '运行中', color: 'bg-[var(--color-accent)]', textColor: 'text-[var(--color-accent)]', bgColor: 'bg-[var(--color-accent-subtle)]' },
};

export const AgentCard: React.FC<AgentCardProps> = ({
  id,
  name,
  description,
  provider,
  model,
  status,
  toolsCount = 0,
  skillsCount = 0,
  capabilities = [],
  onSelect,
  onDelete,
  onRun,
  className,
}) => {
  const [showMenu, setShowMenu] = React.useState(false);
  const statusStyle = statusConfig[status];

  return (
    <div
      className={cn(
        'group relative overflow-hidden rounded-2xl border border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-1)] p-5 transition-all duration-200',
        'hover:border-[var(--color-border-default)] hover:shadow-lg hover:shadow-black/10',
        'active:scale-[0.99]',
        className
      )}
      onClick={() => onSelect?.(id)}
    >
      <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-[var(--color-accent)]/0 to-transparent transition-all duration-300 group-hover:via-[var(--color-accent)]/30" />

      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <div className="relative">
            <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-gradient-to-br from-[var(--color-accent)]/20 to-purple-500/20 ring-1 ring-[var(--color-accent)]/20">
              <Bot size={20} className="text-[var(--color-accent)]" />
            </div>
            <div className={cn('absolute -bottom-0.5 -right-0.5 h-3 w-3 rounded-full border-2 border-[var(--color-bg-surface-1)]', statusStyle.color)} />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-[var(--color-text-primary)]">{name}</h3>
            <p className="text-xs text-[var(--color-text-muted)]">{provider} / {model}</p>
          </div>
        </div>

        <div className="relative">
          <button
            onClick={(e) => { e.stopPropagation(); setShowMenu(!showMenu); }}
            className="flex h-8 w-8 items-center justify-center rounded-lg text-[var(--color-text-muted)] opacity-0 transition-all duration-200 hover:bg-[var(--color-bg-surface-2)] hover:text-[var(--color-text-primary)] group-hover:opacity-100"
          >
            <MoreVertical size={16} />
          </button>

          {showMenu && (
            <>
              <div className="fixed inset-0 z-10" onClick={(e) => { e.stopPropagation(); setShowMenu(false); }} />
              <div className="absolute right-0 top-9 z-20 w-40 rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-2)] p-1 shadow-xl shadow-black/20">
                <button
                  onClick={(e) => { e.stopPropagation(); onRun?.(id); setShowMenu(false); }}
                  className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-xs text-[var(--color-text-secondary)] transition-colors hover:bg-[var(--color-bg-surface-3)] hover:text-[var(--color-text-primary)]"
                >
                  <Play size={13} /> 启动
                </button>
                <button
                  onClick={(e) => { e.stopPropagation(); setShowMenu(false); }}
                  className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-xs text-[var(--color-text-secondary)] transition-colors hover:bg-[var(--color-bg-surface-3)] hover:text-[var(--color-text-primary)]"
                >
                  <Copy size={13} /> 复制配置
                </button>
                <button
                  onClick={(e) => { e.stopPropagation(); setShowMenu(false); }}
                  className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-xs text-[var(--color-text-secondary)] transition-colors hover:bg-[var(--color-bg-surface-3)] hover:text-[var(--color-text-primary)]"
                >
                  <Settings size={13} /> 设置
                </button>
                <div className="my-1 h-px bg-[var(--color-border-subtle)]" />
                <button
                  onClick={(e) => { e.stopPropagation(); onDelete?.(id); setShowMenu(false); }}
                  className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-xs text-[var(--color-error)] transition-colors hover:bg-[var(--color-error-subtle)]"
                >
                  <Trash2 size={13} /> 删除
                </button>
              </div>
            </>
          )}
        </div>
      </div>

      {description && (
        <p className="mt-3 text-xs leading-relaxed text-[var(--color-text-muted)] line-clamp-2">{description}</p>
      )}

      {capabilities.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-1.5">
          {capabilities.slice(0, 3).map((cap) => (
            <span
              key={cap}
              className="inline-flex items-center rounded-md bg-[var(--color-bg-surface-2)] px-2 py-0.5 text-[10px] font-medium text-[var(--color-text-secondary)] ring-1 ring-[var(--color-border-subtle)]"
            >
              {cap}
            </span>
          ))}
          {capabilities.length > 3 && (
            <span className="inline-flex items-center rounded-md bg-[var(--color-bg-surface-2)] px-2 py-0.5 text-[10px] font-medium text-[var(--color-text-muted)]">
              +{capabilities.length - 3}
            </span>
          )}
        </div>
      )}

      <div className="mt-4 flex items-center justify-between border-t border-[var(--color-border-subtle)] pt-3">
        <div className="flex items-center gap-3">
          {toolsCount > 0 && (
            <span className="text-[10px] text-[var(--color-text-muted)]">{toolsCount} 工具</span>
          )}
          {skillsCount > 0 && (
            <span className="text-[10px] text-[var(--color-text-muted)]">{skillsCount} 技能</span>
          )}
        </div>
        <div className="flex items-center gap-1.5">
          <div className={cn('h-1.5 w-1.5 rounded-full', statusStyle.color, status === 'running' && 'animate-pulse')} />
          <span className={cn('text-[10px] font-medium', statusStyle.textColor)}>{statusStyle.label}</span>
        </div>
      </div>
    </div>
  );
};
