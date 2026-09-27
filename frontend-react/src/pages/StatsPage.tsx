import { useState, useEffect, useCallback } from 'react';
import {
  BarChart3, Bot, MessageSquare, Users, RefreshCw, AlertCircle,
} from 'lucide-react';
import { api } from '../api';
import { PageHeader } from '../components/ui/PageHeader';
import { Card, CardContent } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { useI18n } from '../i18n/utils';

interface StatsData {
  total_users: number;
  total_agents: number;
  total_sessions: number;
  total_api_keys: number;
}

const CARDS = [
  { key: 'total_users', label: '用户总数', icon: Users },
  { key: 'total_agents', label: '智能体', icon: Bot },
  { key: 'total_sessions', label: '会话数', icon: MessageSquare },
  { key: 'total_api_keys', label: 'API Keys', icon: BarChart3 },
] as const;

export function StatsPage() {
  const { t } = useI18n();
  const [stats, setStats] = useState<StatsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadStats = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getStats();
      setStats(data);
    } catch (e) {
      setStats(null);
      setError(e instanceof Error ? e.message : '加载统计信息失败');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadStats();
  }, [loadStats]);

  return (
    <div className="h-full overflow-y-auto page-transition">
      <div className="p-4 md:p-6 max-w-6xl mx-auto">
        <PageHeader
          title="平台统计"
          icon={<BarChart3 size={20} />}
          actions={
            <Button variant="secondary" size="sm" onClick={loadStats} loading={loading} icon={<RefreshCw size={14} />}>
              {t('common.refresh')}
            </Button>
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

        <dl aria-busy={loading} className="grid grid-cols-2 lg:grid-cols-4 gap-px overflow-hidden rounded-lg border border-[var(--color-border-subtle)] bg-[var(--color-border-subtle)]">
          {CARDS.map((card) => {
                const Icon = card.icon;
                const value = stats?.[card.key as keyof StatsData];
                return (
                  <div key={card.key} className="bg-[var(--color-bg-surface-1)] p-4">
                    <dt className="flex items-center gap-2 text-xs text-[var(--color-text-muted)]"><Icon size={14} />{card.label}</dt>
                    <dd className="mt-2 text-2xl font-semibold tabular-nums text-[var(--color-text-primary)]">{loading ? '…' : value?.toLocaleString() ?? '—'}</dd>
                  </div>
                );
              })}
        </dl>
      </div>
    </div>
  );
}
