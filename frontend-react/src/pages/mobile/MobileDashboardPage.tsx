import { useState, useCallback } from 'react';
import {
  TrendingUp, MessageSquare, Cpu, Bot, Activity,
  ArrowUpRight, Clock, CheckCircle2, AlertCircle,
  ChevronRight, Zap
} from 'lucide-react';
import { cn } from '../../lib/utils';

interface StatCard {
  label: string;
  value: string;
  change: string;
  trend: 'up' | 'down';
  icon: typeof MessageSquare;
  color: string;
}

interface RecentActivity {
  id: string;
  type: 'task' | 'chat' | 'agent';
  title: string;
  time: string;
  status: 'completed' | 'running' | 'failed';
}

const STATS: StatCard[] = [
  { label: '今日对话', value: '24', change: '+12%', trend: 'up', icon: MessageSquare, color: 'var(--color-accent)' },
  { label: '执行任务', value: '8', change: '+3', trend: 'up', icon: Cpu, color: 'var(--color-success)' },
  { label: '活跃智能体', value: '5', change: '+2', trend: 'up', icon: Bot, color: 'var(--color-warning)' },
  { label: '成功率', value: '98%', change: '+1%', trend: 'up', icon: TrendingUp, color: '#8B5CF6' },
];

const RECENT_ACTIVITY: RecentActivity[] = [
  { id: '1', type: 'task', title: '代码审查任务完成', time: '2分钟前', status: 'completed' },
  { id: '2', type: 'chat', title: '新对话: API 设计讨论', time: '15分钟前', status: 'running' },
  { id: '3', type: 'agent', title: '数据分析智能体已启动', time: '1小时前', status: 'completed' },
  { id: '4', type: 'task', title: '文档生成任务', time: '2小时前', status: 'failed' },
];

const QUICK_ACTIONS = [
  { id: 'new-chat', label: '新建对话', icon: MessageSquare, page: 'chat' },
  { id: 'new-task', label: '创建任务', icon: Cpu, page: 'factory' },
  { id: 'view-agents', label: '智能体', icon: Bot, page: 'agents' },
  { id: 'view-cluster', label: '集群', icon: Activity, page: 'cluster' },
];

export function MobileDashboardPage({ onNavigate }: { onNavigate: (page: string) => void }) {
  const [activeQuickAction, setActiveQuickAction] = useState<string | null>(null);

  const handleQuickAction = useCallback((page: string) => {
    setActiveQuickAction(page);
    setTimeout(() => {
      onNavigate(page);
      setActiveQuickAction(null);
    }, 150);
  }, [onNavigate]);

  const getStatusIcon = (status: RecentActivity['status']) => {
    switch (status) {
      case 'completed': return <CheckCircle2 size={14} style={{ color: 'var(--color-success)' }} />;
      case 'running': return <Clock size={14} style={{ color: 'var(--color-accent)' }} />;
      case 'failed': return <AlertCircle size={14} style={{ color: 'var(--color-error)' }} />;
    }
  };

  return (
    <div className="mobile-dashboard">
      {/* Welcome Section */}
      <div className="px-5 pt-5 pb-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-xl font-bold" style={{ color: 'var(--color-text-primary)' }}>
              仪表盘
            </h2>
            <p className="text-xs mt-0.5" style={{ color: 'var(--color-text-muted)' }}>
              欢迎回来，这是你的今日概览
            </p>
          </div>
          <div
            className="w-10 h-10 rounded-2xl flex items-center justify-center"
            style={{ background: 'var(--gradient-accent)', boxShadow: '0 0 16px var(--color-accent-glow)' }}
          >
            <Zap size={18} className="text-white" />
          </div>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="px-5 pb-4">
        <div className="grid grid-cols-4 gap-2">
          {QUICK_ACTIONS.map(({ id, label, icon: Icon, page }) => (
            <button
              key={id}
              onClick={() => handleQuickAction(page)}
              className={cn(
                'flex flex-col items-center gap-1.5 py-3 rounded-2xl transition-all duration-200',
                'active:scale-[0.92]',
                activeQuickAction === page ? 'scale-[0.92]' : ''
              )}
              style={{
                backgroundColor: 'var(--color-bg-surface-2)',
                border: '1px solid var(--color-border-subtle)',
              }}
            >
              <div
                className="w-9 h-9 rounded-xl flex items-center justify-center"
                style={{ backgroundColor: 'var(--color-accent-subtle)' }}
              >
                <Icon size={16} style={{ color: 'var(--color-accent)' }} />
              </div>
              <span className="text-[10px] font-medium" style={{ color: 'var(--color-text-secondary)' }}>
                {label}
              </span>
            </button>
          ))}
        </div>
      </div>

      {/* Stats Grid */}
      <div className="px-5 pb-4">
        <div className="grid grid-cols-2 gap-3">
          {STATS.map((stat) => (
            <div
              key={stat.label}
              className="p-4 rounded-2xl transition-all duration-200 active:scale-[0.97]"
              style={{
                backgroundColor: 'var(--color-bg-surface-1)',
                border: '1px solid var(--color-border-subtle)',
              }}
            >
              <div className="flex items-center justify-between mb-3">
                <div
                  className="w-8 h-8 rounded-xl flex items-center justify-center"
                  style={{ backgroundColor: `${stat.color}15` }}
                >
                  <stat.icon size={14} style={{ color: stat.color }} />
                </div>
                <div className="flex items-center gap-0.5" style={{ color: 'var(--color-success)' }}>
                  <ArrowUpRight size={12} />
                  <span className="text-[10px] font-medium">{stat.change}</span>
                </div>
              </div>
              <div className="text-lg font-bold" style={{ color: 'var(--color-text-primary)' }}>
                {stat.value}
              </div>
              <div className="text-[10px] mt-0.5" style={{ color: 'var(--color-text-muted)' }}>
                {stat.label}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Recent Activity */}
      <div className="px-5 pb-6">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-semibold" style={{ color: 'var(--color-text-primary)' }}>
            最近活动
          </h3>
          <button
            className="text-xs font-medium flex items-center gap-0.5"
            style={{ color: 'var(--color-accent)' }}
          >
            查看全部
            <ChevronRight size={12} />
          </button>
        </div>
        <div className="space-y-2">
          {RECENT_ACTIVITY.map((activity) => (
            <div
              key={activity.id}
              className="flex items-center gap-3 p-3 rounded-2xl transition-all duration-200 active:scale-[0.98]"
              style={{
                backgroundColor: 'var(--color-bg-surface-1)',
                border: '1px solid var(--color-border-subtle)',
              }}
            >
              <div className="shrink-0">
                {getStatusIcon(activity.status)}
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-xs font-medium truncate" style={{ color: 'var(--color-text-primary)' }}>
                  {activity.title}
                </p>
                <p className="text-[10px] mt-0.5" style={{ color: 'var(--color-text-muted)' }}>
                  {activity.time}
                </p>
              </div>
              <ChevronRight size={14} style={{ color: 'var(--color-text-muted)' }} />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
