import React, { useState } from 'react';
import { X, Settings, Clock, Wrench, Brain, Bot, Play, Trash2, Copy } from 'lucide-react';
import { cn } from '../../lib/utils';

interface AgentDetail {
  id: string;
  name: string;
  description?: string;
  provider: string;
  model: string;
  status: 'active' | 'inactive' | 'error' | 'running';
  systemPrompt?: string;
  tools: string[];
  skills: string[];
  createdAt: string;
  lastActive: string;
  totalRuns: number;
  successRate: number;
}

interface AgentDetailSidebarProps {
  agent: AgentDetail | null;
  onClose: () => void;
  onRun?: (id: string) => void;
  onDelete?: (id: string) => void;
  className?: string;
}

type TabId = 'config' | 'history' | 'tools' | 'memory';

const statusConfig = {
  active: { label: '在线', color: 'bg-[var(--color-success)]', textColor: 'text-[var(--color-success)]' },
  inactive: { label: '离线', color: 'bg-[var(--color-text-muted)]', textColor: 'text-[var(--color-text-muted)]' },
  error: { label: '异常', color: 'bg-[var(--color-error)]', textColor: 'text-[var(--color-error)]' },
  running: { label: '运行中', color: 'bg-[var(--color-accent)]', textColor: 'text-[var(--color-accent)]' },
};

export const AgentDetailSidebar: React.FC<AgentDetailSidebarProps> = ({
  agent,
  onClose,
  onRun,
  onDelete,
  className,
}) => {
  const [activeTab, setActiveTab] = useState<TabId>('config');

  if (!agent) return null;

  const tabs: { id: TabId; label: string; icon: React.ElementType }[] = [
    { id: 'config', label: '配置', icon: Settings },
    { id: 'history', label: '历史', icon: Clock },
    { id: 'tools', label: '工具', icon: Wrench },
    { id: 'memory', label: '记忆', icon: Brain },
  ];

  const statusStyle = statusConfig[agent.status];

  return (
    <div
      className={cn(
        'flex h-full flex-col border-l border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-1)]',
        className
      )}
    >
      {/* Header */}
      <div className="flex items-center justify-between border-b border-[var(--color-border-subtle)] px-5 py-4">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-[var(--color-accent-subtle)]">
            <Bot size={16} className="text-[var(--color-accent)]" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-[var(--color-text-primary)]">{agent.name}</h3>
            <div className="flex items-center gap-1.5">
              <div className={cn('h-1.5 w-1.5 rounded-full', statusStyle.color)} />
              <span className={cn('text-[10px]', statusStyle.textColor)}>{statusStyle.label}</span>
            </div>
          </div>
        </div>
        <button
          onClick={onClose}
          className="flex h-8 w-8 items-center justify-center rounded-lg text-[var(--color-text-muted)] transition-colors hover:bg-[var(--color-bg-surface-2)] hover:text-[var(--color-text-primary)]"
        >
          <X size={16} />
        </button>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-[var(--color-border-subtle)]">
        {tabs.map((tab) => {
          const Icon = tab.icon;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={cn(
                'flex flex-1 items-center justify-center gap-1.5 py-2.5 text-[10px] font-medium transition-all duration-200',
                activeTab === tab.id
                  ? 'border-b-2 border-[var(--color-accent)] text-[var(--color-accent)]'
                  : 'text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)]'
              )}
            >
              <Icon size={12} />
              {tab.label}
            </button>
          );
        })}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4">
        {activeTab === 'config' && (
          <div className="space-y-4">
            <div>
              <h4 className="text-[10px] font-semibold uppercase tracking-wider text-[var(--color-text-muted)]">基本信息</h4>
              <div className="mt-2 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs text-[var(--color-text-muted)]">提供商</span>
                  <span className="text-xs font-medium text-[var(--color-text-primary)]">{agent.provider}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-xs text-[var(--color-text-muted)]">模型</span>
                  <span className="text-xs font-medium text-[var(--color-text-primary)]">{agent.model}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-xs text-[var(--color-text-muted)]">创建时间</span>
                  <span className="text-xs text-[var(--color-text-secondary)]">{agent.createdAt}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-xs text-[var(--color-text-muted)]">最后活跃</span>
                  <span className="text-xs text-[var(--color-text-secondary)]">{agent.lastActive}</span>
                </div>
              </div>
            </div>

            {agent.systemPrompt && (
              <div>
                <h4 className="text-[10px] font-semibold uppercase tracking-wider text-[var(--color-text-muted)]">系统提示词</h4>
                <div className="mt-2 rounded-xl bg-[var(--color-bg-surface-2)] p-3 ring-1 ring-[var(--color-border-subtle)]">
                  <p className="text-xs leading-relaxed text-[var(--color-text-secondary)] whitespace-pre-wrap">{agent.systemPrompt}</p>
                </div>
              </div>
            )}

            <div>
              <h4 className="text-[10px] font-semibold uppercase tracking-wider text-[var(--color-text-muted)]">统计</h4>
              <div className="mt-2 grid grid-cols-2 gap-2">
                <div className="rounded-xl bg-[var(--color-bg-surface-2)] p-3 ring-1 ring-[var(--color-border-subtle)]">
                  <p className="text-lg font-semibold text-[var(--color-text-primary)]">{agent.totalRuns}</p>
                  <p className="text-[10px] text-[var(--color-text-muted)]">总运行次数</p>
                </div>
                <div className="rounded-xl bg-[var(--color-bg-surface-2)] p-3 ring-1 ring-[var(--color-border-subtle)]">
                  <p className="text-lg font-semibold text-[var(--color-success)]">{agent.successRate}%</p>
                  <p className="text-[10px] text-[var(--color-text-muted)]">成功率</p>
                </div>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'history' && (
          <div className="space-y-3">
            <p className="text-[10px] text-[var(--color-text-muted)]">最近运行记录</p>
            {[
              { time: '10 分钟前', status: 'success', duration: '2.3s' },
              { time: '1 小时前', status: 'success', duration: '5.1s' },
              { time: '3 小时前', status: 'error', duration: '0.8s' },
              { time: '昨天', status: 'success', duration: '1.9s' },
            ].map((record, i) => (
              <div key={i} className="flex items-center justify-between rounded-xl bg-[var(--color-bg-surface-2)] px-3 py-2.5 ring-1 ring-[var(--color-border-subtle)]">
                <div className="flex items-center gap-2">
                  <div className={cn(
                    'h-1.5 w-1.5 rounded-full',
                    record.status === 'success' ? 'bg-[var(--color-success)]' : 'bg-[var(--color-error)]'
                  )} />
                  <span className="text-xs text-[var(--color-text-secondary)]">{record.time}</span>
                </div>
                <span className="text-[10px] text-[var(--color-text-muted)]">{record.duration}</span>
              </div>
            ))}
          </div>
        )}

        {activeTab === 'tools' && (
          <div className="space-y-3">
            <p className="text-[10px] text-[var(--color-text-muted)]">已启用工具 ({agent.tools.length})</p>
            {agent.tools.length > 0 ? (
              <div className="flex flex-wrap gap-1.5">
                {agent.tools.map((tool) => (
                  <span key={tool} className="rounded-md bg-[var(--color-bg-surface-2)] px-2 py-1 text-[10px] font-medium text-[var(--color-text-secondary)] ring-1 ring-[var(--color-border-subtle)]">
                    {tool}
                  </span>
                ))}
              </div>
            ) : (
              <p className="text-xs text-[var(--color-text-muted)]">暂无工具</p>
            )}

            {agent.skills.length > 0 && (
              <>
                <p className="mt-4 text-[10px] text-[var(--color-text-muted)]">已绑定技能 ({agent.skills.length})</p>
                <div className="flex flex-wrap gap-1.5">
                  {agent.skills.map((skill) => (
                    <span key={skill} className="rounded-md bg-[var(--color-accent-subtle)] px-2 py-1 text-[10px] font-medium text-[var(--color-accent)] ring-1 ring-[var(--color-accent)]/20">
                      {skill}
                    </span>
                  ))}
                </div>
              </>
            )}
          </div>
        )}

        {activeTab === 'memory' && (
          <div className="space-y-3">
            <p className="text-[10px] text-[var(--color-text-muted)]">智能体记忆文件</p>
            <div className="flex flex-col items-center justify-center py-8">
              <Brain size={28} className="text-[var(--color-text-muted)]" />
              <p className="mt-2 text-xs text-[var(--color-text-muted)]">记忆功能开发中</p>
            </div>
          </div>
        )}
      </div>

      {/* Footer Actions */}
      <div className="border-t border-[var(--color-border-subtle)] p-3">
        <div className="flex gap-2">
          <button
            onClick={() => onRun?.(agent.id)}
            className="flex flex-1 items-center justify-center gap-1.5 rounded-xl bg-[var(--color-accent)] px-3 py-2.5 text-xs font-medium text-white shadow-sm shadow-[var(--color-accent)]/20 transition-all duration-200 hover:bg-[var(--color-accent-hover)] active:scale-[0.97]"
          >
            <Play size={13} /> 启动
          </button>
          <button className="flex h-9 w-9 items-center justify-center rounded-xl border border-[var(--color-border-subtle)] text-[var(--color-text-muted)] transition-all duration-200 hover:border-[var(--color-border-default)] hover:text-[var(--color-text-primary)]">
            <Copy size={14} />
          </button>
          <button
            onClick={() => onDelete?.(agent.id)}
            className="flex h-9 w-9 items-center justify-center rounded-xl border border-[var(--color-border-subtle)] text-[var(--color-text-muted)] transition-all duration-200 hover:border-[var(--color-error)]/30 hover:bg-[var(--color-error-subtle)] hover:text-[var(--color-error)]"
          >
            <Trash2 size={14} />
          </button>
        </div>
      </div>
    </div>
  );
};
