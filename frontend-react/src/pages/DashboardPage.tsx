import React, { useState, useCallback } from 'react';
import { Activity, Bot, Workflow, Cpu, MessageSquare, RefreshCw, CheckCircle2, AlertCircle } from 'lucide-react';
import { PageHeader } from '../components/ui/PageHeader';
import { Card, CardContent } from '../components/ui/Card';
import { useI18n } from '../i18n/utils';

type HealthState = 'loading' | 'online' | 'offline';

export function DashboardPage() {
  const { t } = useI18n();
  const [health, setHealth] = useState<HealthState>('loading');

  const checkHealth = useCallback(async () => {
    setHealth('loading');
    try {
      const response = await fetch('/api/v1/auth/health');
      setHealth(response.ok ? 'online' : 'offline');
    } catch {
      setHealth('offline');
    }
  }, []);

  React.useEffect(() => { void checkHealth(); }, [checkHealth]);

  const handleCreateAgent = useCallback(() => {
    window.location.hash = 'agents';
  }, []);

  const handleStartTask = useCallback(() => {
    window.location.hash = 'tasks';
  }, []);

  return (
    <div className="page-scroll page-transition">
      <div className="page-container">
        <PageHeader
          title={t('home.title')}
          description={t('home.subtitle')}
          icon={<Activity size={20} className="text-[var(--color-accent)]" />}
        />

        <div className="mt-4 grid gap-4 md:mt-6 lg:grid-cols-[1fr_320px]">
          <Card variant="default">
            <CardContent className="p-4 md:p-6">
              <div className="flex items-center justify-between gap-4">
                <div>
                  <h3 className="text-sm font-semibold text-[var(--color-text-primary)]">API service</h3>
                  <p className="mt-1 text-xs text-[var(--color-text-muted)]">来自当前环境的实时健康检查</p>
                </div>
                <button onClick={checkHealth} className="icon-button" aria-label="刷新 API 状态"><RefreshCw size={16} /></button>
              </div>
              <div className="mt-4 flex min-h-20 items-center gap-3 rounded-lg border border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-2)] px-4" role="status" aria-live="polite">
                {health === 'loading' && <RefreshCw size={18} className="animate-spin text-[var(--color-text-muted)]" />}
                {health === 'online' && <CheckCircle2 size={18} className="text-[var(--color-success)]" />}
                {health === 'offline' && <AlertCircle size={18} className="text-[var(--color-error)]" />}
                <div>
                  <p className="text-sm font-medium text-[var(--color-text-primary)]">{health === 'loading' ? 'Checking service' : health === 'online' ? 'Service available' : 'Service unavailable'}</p>
                  <p className="text-xs text-[var(--color-text-muted)]">{health === 'offline' ? '检查后端服务后重试' : 'Authentication health endpoint'}</p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card variant="default">
            <CardContent className="p-4 md:p-6">
              <h3 className="text-base font-semibold text-[var(--color-text-primary)]">{t('home.quick_actions')}</h3>
              <p className="text-sm text-[var(--color-text-muted)] mt-1">{t('home.quick_actions_desc')}</p>
              <div className="mt-4 grid gap-2">
                <button
                  onClick={handleCreateAgent}
                   className="group flex min-h-14 w-full items-center gap-3 rounded-lg border border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-2)] p-3 text-left transition-colors hover:border-[var(--color-border-default)] hover:bg-[var(--color-bg-surface-3)]"
                >
                  <div className="h-8 w-8 rounded-lg bg-[var(--color-accent-muted)] flex items-center justify-center shrink-0 group-hover:ring-1 group-hover:ring-[var(--color-accent)]/20">
                    <Bot size={16} className="text-[var(--color-accent)]" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-[var(--color-text-primary)]">{t('home.create_agent')}</p>
                    <p className="text-xs text-[var(--color-text-muted)]">{t('home.create_agent_desc')}</p>
                  </div>
                </button>
                <button
                  onClick={handleStartTask}
                   className="group flex min-h-14 w-full items-center gap-3 rounded-lg border border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-2)] p-3 text-left transition-colors hover:border-[var(--color-border-default)] hover:bg-[var(--color-bg-surface-3)]"
                >
                  <div className="h-8 w-8 rounded-lg bg-[var(--color-accent-muted)] flex items-center justify-center shrink-0 group-hover:ring-1 group-hover:ring-[var(--color-accent)]/20">
                     <Cpu size={16} className="text-[var(--color-accent)]" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-[var(--color-text-primary)]">{t('home.start_task')}</p>
                    <p className="text-xs text-[var(--color-text-muted)]">{t('home.start_task_desc')}</p>
                  </div>
                </button>
                <button onClick={() => { window.location.hash = 'chat'; }} className="group flex min-h-14 w-full items-center gap-3 rounded-lg border border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-2)] p-3 text-left transition-colors hover:border-[var(--color-border-default)] hover:bg-[var(--color-bg-surface-3)]">
                  <MessageSquare size={16} className="text-[var(--color-text-muted)]" />
                  <span className="text-sm font-medium text-[var(--color-text-primary)]">打开对话工作区</span>
                </button>
                <button onClick={() => { window.location.hash = 'workflows'; }} className="group flex min-h-14 w-full items-center gap-3 rounded-lg border border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-2)] p-3 text-left transition-colors hover:border-[var(--color-border-default)] hover:bg-[var(--color-bg-surface-3)]">
                  <Workflow size={16} className="text-[var(--color-text-muted)]" />
                  <span className="text-sm font-medium text-[var(--color-text-primary)]">查看工作流</span>
                </button>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}

export default DashboardPage;
