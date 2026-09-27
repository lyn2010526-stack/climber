import React, { useCallback, useState } from 'react';
import { Activity, Bot, Workflow, Cpu, MessageSquare, RefreshCw, CheckCircle2, AlertCircle } from 'lucide-react';
import { PageHeader } from '../components/ui/PageHeader';
import { Button } from '../components/ui/Button';
import { api } from '../api';
import { useI18n } from '../i18n/utils';

type HealthState = 'loading' | 'online' | 'offline';

export function DashboardPage() {
  const { t } = useI18n();
  const [health, setHealth] = useState<HealthState>('loading');

  const checkHealth = useCallback(async () => {
    setHealth('loading');
    try {
      const ok = await api.checkHealth();
      setHealth(ok ? 'online' : 'offline');
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
          icon={<Activity size={20} className="text-[var(--color-accent-foreground)]" />}
          actions={<Button size="sm" onClick={() => { window.location.hash = 'chat'; }} icon={<MessageSquare size={14} />}>{t('nav.chat', { defaultValue: '对话' })}</Button>}
        />

        <div className="space-y-5">
              <div className="flex flex-wrap items-center gap-3 rounded-lg border border-[var(--color-border-subtle)] px-3 py-2" role="status" aria-live="polite">
                {health === 'loading' && <RefreshCw size={18} className="animate-spin text-[var(--color-text-muted)]" />}
                {health === 'online' && <CheckCircle2 size={18} className="text-[var(--color-success)]" />}
                {health === 'offline' && <AlertCircle size={18} className="text-[var(--color-error)]" />}
                <div>
                  <p className="text-sm text-[var(--color-text-primary)]">{health === 'loading' ? t('common.loading') : health === 'online' ? t('home.api_online') : t('home.api_offline')}</p>
                </div>
                <code className="text-xs text-[var(--color-text-muted)]">GET /health</code>
                <Button variant="ghost" size="sm" onClick={checkHealth} disabled={health === 'loading'} className="ml-auto" icon={<RefreshCw size={14} />}>{t('common.refresh')}</Button>
              </div>
              <div className="flex flex-wrap gap-2" aria-label={t('home.quick_actions')}>
                <Button variant="secondary" size="sm" onClick={handleCreateAgent} icon={<Bot size={14} />}>{t('home.create_agent')}</Button>
                <Button variant="secondary" size="sm" onClick={handleStartTask} icon={<Cpu size={14} />}>{t('home.start_task')}</Button>
                <Button variant="secondary" size="sm" onClick={() => { window.location.hash = 'workflows'; }} icon={<Workflow size={14} />}>{t('nav.workflows', { defaultValue: '工作流' })}</Button>
              </div>
        </div>
      </div>
    </div>
  );
}

export default DashboardPage;
