import { useState, useEffect, useCallback } from 'react';
import {
  BarChart3, Bot, MessageSquare, Users, TrendingUp,
  Activity, Zap, Clock, RefreshCw, AlertCircle,
} from 'lucide-react';
import { api } from '../api';
import { PageHeader } from '../components/ui/PageHeader';
import { Card, CardContent } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Badge } from '../components/ui/Badge';
import { SkeletonCard } from '../components/ui/Skeleton';

interface StatsData {
  total_users: number;
  total_agents: number;
  total_sessions: number;
  total_api_keys: number;
}

const CARDS = [
  { key: 'total_users', label: '用户总数', icon: Users, color: 'text-[var(--color-accent)]', bg: 'bg-[var(--color-accent)]/10', trend: '+12%' },
  { key: 'total_agents', label: '智能体', icon: Bot, color: 'text-[var(--color-accent-secondary)]', bg: 'bg-[var(--color-accent-secondary)]/10', trend: '+5%' },
  { key: 'total_sessions', label: '会话数', icon: MessageSquare, color: 'text-[var(--color-success)]', bg: 'bg-[var(--color-success)]/10', trend: '+24%' },
  { key: 'total_api_keys', label: 'API Keys', icon: BarChart3, color: 'text-[var(--color-warning)]', bg: 'bg-[var(--color-warning)]/10', trend: '+3%' },
] as const;

export function StatsPage() {
  const [stats, setStats] = useState<StatsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadStats = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getStats();
      setStats(data);
    } catch (e: any) {
      setError(e.message || '加载统计信息失败');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadStats();
  }, [loadStats]);

  return (
    <div className="h-full overflow-y-auto page-transition">
      <div className="p-4 md:p-6 lg:p-8 max-w-6xl mx-auto">
        <PageHeader
          title="平台统计"
          description="智能体平台运行概览"
          icon={<BarChart3 size={20} />}
          actions={
            <div className="flex items-center gap-2">
              <Badge variant="success" icon={<Activity size={10} />}>实时</Badge>
              <Button variant="ghost" size="icon" onClick={loadStats} loading={loading}>
                <RefreshCw size={16} />
              </Button>
            </div>
          }
        />

        {error && (
          <Card variant="default" className="mb-6 border-[var(--color-error)]/30">
            <CardContent className="p-4 flex items-center gap-3">
              <AlertCircle size={18} className="text-[var(--color-error)] shrink-0" />
              <p className="text-sm text-[var(--color-error)] flex-1">{error}</p>
              <Button variant="outline" size="sm" onClick={loadStats}>重试</Button>
            </CardContent>
          </Card>
        )}

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6 stagger-children">
          {loading
            ? Array.from({ length: 4 }).map((_, i) => <SkeletonCard key={i} />)
            : CARDS.map((card) => {
                const Icon = card.icon;
                const value = stats?.[card.key as keyof StatsData];
                return (
                  <Card key={card.key} variant="default" className="hover-lift">
                    <CardContent className="p-5">
                      <div className="flex items-center justify-between mb-3">
                        <div className={`p-2.5 rounded-xl ${card.bg} border border-[var(--color-border-subtle)]`}>
                          <Icon size={20} className={card.color} />
                        </div>
                        <span className="flex items-center gap-1 text-xs text-[var(--color-success)] font-medium">
                          <TrendingUp size={10} /> {card.trend}
                        </span>
                      </div>
                      <div className="text-3xl font-bold tracking-tight text-[var(--color-text-primary)]">
                        {value ?? '-'}
                      </div>
                      <div className="text-sm text-[var(--color-text-muted)] mt-1">{card.label}</div>
                    </CardContent>
                  </Card>
                );
              })}
        </div>

        <Card variant="default">
          <CardContent className="p-6">
            <div className="flex items-center gap-2.5 mb-4">
              <Zap size={16} className="text-[var(--color-accent)]" />
              <h3 className="font-semibold text-sm text-[var(--color-text-primary)]">最近活动</h3>
            </div>
            <div className="text-center py-8">
              <div className="p-3 rounded-2xl bg-[var(--color-bg-surface-2)] border border-[var(--color-border-subtle)] inline-flex mb-3">
                <Clock size={24} className="text-[var(--color-text-muted)]" />
              </div>
              <p className="text-sm text-[var(--color-text-muted)]">暂无最近活动</p>
              <p className="text-xs text-[var(--color-text-muted)]/60 mt-1">使用平台时活动将显示在此处</p>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
