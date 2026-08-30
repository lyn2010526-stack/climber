import { useState, useEffect } from 'react';
import { BarChart3, Bot, MessageSquare, Users, TrendingUp, Activity, Zap, Clock, RefreshCw, AlertCircle } from 'lucide-react';
import { api } from '../api';
import { Button, Badge, Card, CardHeader, CardTitle } from '../components/ui';

export function StatsPage() {
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadStats();
  }, []);

  const loadStats = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getStats();
      setStats(data);
    } catch (e: any) {
      setError(e.message || '加载统计信息失败');
    }
    setLoading(false);
  };

  if (loading) {
    return (
      <div className="h-full overflow-y-auto p-8">
        <div className="max-w-5xl mx-auto">
          <div className="flex items-center justify-between mb-8">
            <div>
               <h2 className="text-2xl font-bold text-[var(--color-text-primary)]">平台统计</h2>
               <p className="text-[var(--color-text-secondary)] text-sm mt-1.5">智能体平台运行概览</p>
            </div>
          </div>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
            {[1, 2, 3, 4].map(i => (
              <Card key={i} className="rounded-2xl p-5 animate-pulse" padding="none">
                <div className="flex items-center justify-between mb-3">
                  <div className="w-10 h-10 rounded-2xl bg-[var(--color-bg-surface-2)]" />
                  <div className="h-3 w-10 bg-[var(--color-bg-surface-2)] rounded-xl" />
                </div>
                <div className="h-8 w-16 bg-[var(--color-bg-surface-2)] rounded-xl" />
                <div className="h-3 w-20 bg-[var(--color-bg-surface-2)] rounded-xl mt-1" />
              </Card>
            ))}
          </div>
          <Card className="rounded-2xl p-6 animate-pulse" padding="none">
            <div className="h-4 w-28 bg-[var(--color-bg-surface-2)] rounded-xl mb-4" />
            <div className="space-y-3">
              {[1, 2, 3, 4, 5].map(i => (
                <div key={i} className="flex items-center gap-3 py-2">
                  <div className="w-8 h-8 rounded-xl bg-[var(--color-bg-surface-2)]" />
                  <div className="flex-1 space-y-1.5">
                    <div className="h-3 w-32 bg-[var(--color-bg-surface-2)] rounded-xl" />
                    <div className="h-2 w-20 bg-[var(--color-bg-surface-2)] rounded-xl" />
                  </div>
                </div>
              ))}
            </div>
          </Card>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-center">
          <div className="w-16 h-16 rounded-3xl bg-[var(--color-error)]/10 border border-[var(--color-error)]/20 flex items-center justify-center mx-auto mb-4">
            <AlertCircle size={28} className="text-[var(--color-error)]" />
          </div>
          <p className="text-[var(--color-text-secondary)] mb-4">{error}</p>
          <Button onClick={loadStats} size="lg" className="rounded-2xl">
            <RefreshCw size={16} /> Retry
          </Button>
        </div>
      </div>
    );
  }

  const cards = [
    { label: 'Total Users', value: stats.total_users, icon: Users, color: 'text-[var(--color-accent)]', bg: 'bg-[var(--color-accent)]/10', trend: '+12%' },
    { label: 'Total Agents', value: stats.total_agents, icon: Bot, color: 'text-[var(--color-accent-secondary)]', bg: 'bg-[var(--color-accent-secondary)]/10', trend: '+5%' },
    { label: 'Total Sessions', value: stats.total_sessions, icon: MessageSquare, color: 'text-[var(--color-success)]', bg: 'bg-[var(--color-success)]/10', trend: '+24%' },
    { label: 'API Keys', value: stats.total_api_keys, icon: BarChart3, color: 'text-[var(--color-warning)]', bg: 'bg-[var(--color-warning)]/10', trend: '+3%' },
  ];

  return (
    <div className="h-full overflow-y-auto p-8">
      <div className="max-w-5xl mx-auto">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h2 className="text-2xl font-bold text-[var(--color-text-primary)]">平台统计</h2>
            <p className="text-[var(--color-text-secondary)] text-sm mt-1.5">智能体平台的实时概览</p>
          </div>
          <Badge variant="success" icon={<Activity size={12} />}>
            实时
          </Badge>
        </div>

        {/* Stat cards */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          {cards.map(({ label, value, icon: Icon, color, bg, trend }) => (
            <Card key={label} className="rounded-2xl p-5 hover:border-[var(--color-accent)]/30" padding="none">
              <div className="flex items-center justify-between mb-3">
                <div className={`w-10 h-10 rounded-2xl ${bg} flex items-center justify-center border border-[var(--color-border-subtle)]`}>
                  <Icon size={20} className={color} />
                </div>
                <span className="flex items-center gap-1 text-xs text-[var(--color-success)] font-medium">
                  <TrendingUp size={10} /> {trend}
                </span>
              </div>
              <div className="text-3xl font-bold tracking-tight text-[var(--color-text-primary)]">{value}</div>
              <div className="text-sm text-[var(--color-text-muted)] mt-1">{label}</div>
            </Card>
          ))}
        </div>

        {/* Activity placeholder */}
        <Card className="rounded-2xl p-6" padding="none">
          <CardHeader className="pb-0">
            <CardTitle className="text-sm flex items-center gap-2.5">
              <Zap size={16} className="text-[var(--color-accent)]" />
              最近活动
            </CardTitle>
          </CardHeader>
          <div className="text-center py-8">
            <div className="w-12 h-12 rounded-2xl bg-[var(--color-bg-surface-2)] border border-[var(--color-border-subtle)] flex items-center justify-center mx-auto mb-3">
              <Clock size={24} className="text-[var(--color-text-muted)]" />
            </div>
             <p className="text-sm text-[var(--color-text-muted)]">暂无最近活动</p>
             <p className="text-xs text-[var(--color-text-muted)] mt-1">使用平台时活动将显示在此处</p>
          </div>
        </Card>
      </div>
    </div>
  );
}
