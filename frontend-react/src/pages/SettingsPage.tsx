import { useState, useEffect, useCallback, useRef } from 'react';
import {
  User, Cpu, Key, Bell, Shield, Info, Check, Server,
  Mail,
   ChevronRight, AlertCircle, RefreshCw,
} from 'lucide-react';
import { cn } from '../lib/utils';
import { Input } from '../components/ui/Input';
import { Switch } from '../components/ui/Switch';
import { FormField } from '../components/ui/Field';
import { Button } from '../components/ui/Button';
import { Card, CardContent } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { SkeletonList } from '../components/ui/Skeleton';
import { useI18n } from '../i18n';
import { api, type CurrentUserOut, type PermissionTier } from '../api';
import type { SettingsResponse } from '../types/api';
import { ApiKeysPage } from './ApiKeysPage';
import { AuthApiKeysPage } from './AuthApiKeysPage';
import { LocalPinSettings } from '../components/privacy/LocalPinSettings';
import { ProfileLearningSettings } from '../components/privacy/ProfileLearningSettings';

type SettingsSection = 'profile' | 'models' | 'apikeys' | 'accessTokens' | 'notifications' | 'security' | 'about';

interface NavItem {
  id: SettingsSection;
  label: string;
  icon: typeof User;
  description: string;
}

// Each section carries a description that adds information beyond its label.
// Reusing the label as the description produced an accessible name of
// "Notifications Notifications", which both reads badly and hides the row's
// purpose behind a duplicated token.
const getNavItems = (t: (key: string) => string): NavItem[] => [
  { id: 'profile', label: t('settings.general'), icon: User, description: t('settings.profile_hint') },
  { id: 'models', label: t('settings.api_settings'), icon: Cpu, description: t('settings.models_hint') },
  { id: 'apikeys', label: t('settings.model_credentials'), icon: Key, description: t('settings.apikeys_hint') },
  { id: 'accessTokens', label: t('settings.platform_tokens'), icon: Shield, description: t('settings.access_tokens_hint') },
  { id: 'notifications', label: t('settings.notifications'), icon: Bell, description: t('settings.notifications_hint') },
  { id: 'security', label: t('settings.security'), icon: Shield, description: t('settings.security_hint') },
  { id: 'about', label: t('settings.advanced'), icon: Info, description: t('settings.about_hint') },
];

export function SettingsPage() {
  const { t } = useI18n();
  const NAV_ITEMS = getNavItems(t);
  const [activeSection, setActiveSection] = useState<SettingsSection>('profile');
  const handleSectionChange = useCallback((section: SettingsSection) => {
    setActiveSection(section);
  }, []);

  return (
    <div className="settings-layout">
      <aside className="settings-sidebar">
        <div className="p-4 border-b border-[var(--color-border-subtle)]">
          <h2 className="text-sm font-semibold text-[var(--color-text-primary)]">{t('settings.title')}</h2>
          <p className="text-xs text-[var(--color-text-muted)] mt-0.5">{t('settings.account_settings')}</p>
        </div>
        <nav className="flex-1 overflow-auto p-2" aria-label={t('settings.section_nav_label')}>
          <div className="settings-nav-list">
            {NAV_ITEMS.map(item => {
              const Icon = item.icon;
              const isActive = activeSection === item.id;
              const labelId = `settings-section-label-${item.id}`;
              const descriptionId = `settings-section-description-${item.id}`;
              return (
                <button type="button"
                  key={item.id}
                  onClick={() => handleSectionChange(item.id)}
                  // These switch the visible section of the settings page; the
                  // page itself is marked by the shell navigation. "page" here
                  // would claim two different pages are current at once.
                  aria-current={isActive ? 'true' : undefined}
                  // Naming the button by its label alone keeps the accessible
                  // name identical to the visible label (WCAG 2.5.3) and hands
                  // the hint to the description channel.
                  aria-labelledby={labelId}
                  aria-describedby={descriptionId}
                  className={cn(
                    'settings-nav-item',
                    isActive
                      ? 'bg-[var(--color-accent-subtle)] border border-[var(--color-border-accent)]'
                      : 'hover:bg-[var(--color-bg-surface-2)] border border-transparent'
                  )}
                >
                  <div className={cn(
                    'p-1.5 rounded-[var(--radius-md)] transition-colors motion-reduce:transition-none',
                    isActive
                      ? 'bg-[var(--color-accent-subtle)] text-[var(--color-accent-foreground)]'
                      : 'bg-[var(--color-bg-surface-2)] text-[var(--color-text-muted)]'
                  )}>
                    <Icon size={14} aria-hidden="true" focusable="false" />
                  </div>
                  <div className="flex-1 min-w0">
                    <div id={labelId} className={cn(
                      'text-sm font-medium truncate',
                      isActive ? 'text-[var(--color-text-primary)]' : 'text-[var(--color-text-secondary)]'
                    )}>
                      {item.label}
                    </div>
                    <div id={descriptionId} className="text-[length:var(--text-2xs)] text-[var(--color-text-muted)] truncate">{item.description}</div>
                  </div>
                  {isActive && <ChevronRight size={12} aria-hidden="true" focusable="false" className="text-[var(--color-accent-foreground)] shrink-0" />}
                </button>
              );
            })}
          </div>
        </nav>
      </aside>
      {/* The shell already owns the single page-level <main>; a second one
          nested inside it would announce two main landmarks. This region only
          scrolls, so it is labelled as such. */}
      <section className="min-w-0 flex-1 overflow-y-auto" aria-label={t('settings.title')}>
          <div className="mx-auto max-w-3xl p-4 md:p-6">
            <LocalPinSettings />
           <ProfileLearningSettings />
          {activeSection === 'profile' && <ProfileSection />}
          {activeSection === 'models' && <ModelsSection />}
          {activeSection === 'apikeys' && <ApiKeysSection />}
          {activeSection === 'accessTokens' && <AuthApiKeysPage embedded />}
          {activeSection === 'notifications' && <NotificationsSection />}
          {activeSection === 'security' && <SecuritySection />}
          {activeSection === 'about' && <AboutSection />}
        </div>
      </section>
    </div>
  );
}

/**
 * The page-level heading for a settings section: a titled band with an
 * optional explanatory line. Named apart from the right panel's `SectionHeader`,
 * which is a compact group label that can carry a count -- a grep for either
 * name now resolves to exactly one component.
 */
function SettingsSectionHeader({ title, description }: { title: string; description?: string }) {
  return (
    <div className="mb-5 border-b border-[var(--color-border-subtle)] pb-[var(--space-4)]">
      <h1 className="text-[length:var(--text-base)] font-semibold text-[var(--color-text-primary)]">{title}</h1>
      {description && <p className="text-[length:var(--text-sm)] text-[var(--color-text-muted)] mt-1">{description}</p>}
    </div>
  );
}

function SectionCard({ title, description, children, className }: {
  title: string;
  description?: string;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <Card variant="default" padding="none" className={cn('mb-4', className)}>
      <div className="px-4 py-4 border-b border-[var(--color-border-subtle)]">
        <h3 className="text-[length:var(--text-sm)] font-semibold text-[var(--color-text-primary)]">{title}</h3>
        {description && <p className="text-[length:var(--text-2xs)] text-[var(--color-text-muted)] mt-1">{description}</p>}
      </div>
      <div className="p-4">{children}</div>
    </Card>
  );
}

interface ErrorBannerProps {
  message: string;
  onRetry?: () => void;
}

function ErrorBanner({ message, onRetry }: ErrorBannerProps) {
  const { t } = useI18n();
  return (
    <Card variant="default" className="mb-4 border-[var(--color-error)]/30">
      <CardContent className="p-3 md:p-4 flex items-center gap-3">
        <AlertCircle size={18} className="text-[var(--color-error)] shrink-0" />
        <p role="alert" className="text-sm text-[var(--color-error)] flex-1">{message}</p>
        {onRetry && (
          <Button variant="ghost" size="sm" onClick={onRetry} icon={<RefreshCw size={14} />}>
            {t('settings_page.reload')}
          </Button>
        )}
      </CardContent>
    </Card>
  );
}

function ProfileSection() {
  const { t } = useI18n();
  const [user, setUser] = useState<CurrentUserOut | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getCurrentUser();
      setUser(data);
      setUsername(data.username || '');
      setEmail(data.email || '');
    } catch (e) {
      setError(e instanceof Error ? e.message : t('settings_page.account_load_failed'));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  // The settings endpoint only accepts autonomous_agent_mode,
  // token_throttle_mcp_enabled and notifications; profile/username/email are
  // not writable, so the account fields render read-only (R10-09).

  if (loading) {
    return (
      <div>
        <SettingsSectionHeader title={t('settings.account_settings')} description={t('settings.account_settings')} />
        <SkeletonList count={2} />
      </div>
    );
  }

  if (error) {
    return (
      <div>
        <SettingsSectionHeader title={t('settings.account_settings')} description={t('settings.account_settings')} />
        <ErrorBanner message={error} onRetry={load} />
      </div>
    );
  }

  return (
    <div>
      <SettingsSectionHeader title={t('settings.account_settings')} description={t('settings.account_settings')} />

      <SectionCard title={t('settings_page.basic_title')}>
        <div className="space-y-4">
          <p className="text-xs text-[var(--color-text-muted)]">{t('settings_page.account_readonly_note', { defaultValue: 'Account details are managed by your identity provider and are read-only here.' })}</p>
          <FormField label={t('settings_page.username')} description={t('settings_page.username_desc')} required>
              <Input
                id="settings-username"
              placeholder={t('settings_page.username_placeholder')}
              value={username}
              disabled
              readOnly
            />
          </FormField>
          <FormField label={t('settings_page.email')} description={t('settings_page.email_desc')} required>
              <Input
                id="settings-email"
              type="email"
              placeholder={t('settings_page.email_placeholder', { defaultValue: 'your@email.com' })}
              value={email}
              disabled
              readOnly
              leftIcon={<Mail size={14} />}
            />
          </FormField>
          <FormField label={t('settings_page.role')} description={t('settings_page.role_desc')}>
            <Input value={user?.role || ''} disabled />
          </FormField>
        </div>
      </SectionCard>

      <div className="flex justify-end gap-2 border-t border-[var(--color-border-subtle)] pt-4 mt-4">
        <Button variant="outline" onClick={load}>{t('common.refresh')}</Button>
      </div>
    </div>
  );
}

interface SettingsData {
  autonomous_agent_mode: boolean;
  token_throttle_mcp_enabled: boolean;
  mcp_status: string;
  mcp_ready: boolean;
}

function ModelsSection() {
  const { t } = useI18n();
  const [models, setModels] = useState<Array<{ provider: string; model_id: string; label?: string | null }>>([]);
  const [modelsLoading, setModelsLoading] = useState(true);
  const [modelError, setModelError] = useState<string | null>(null);
  const [settings, setSettings] = useState<SettingsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [saveOk, setSaveOk] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    setModelsLoading(true);
    try {
      const data = await api.getSettings();
      setSettings({
        autonomous_agent_mode: !!data.autonomous_agent_mode,
        token_throttle_mcp_enabled: !!data.token_throttle_mcp_enabled,
        mcp_status: data.mcp_status || 'disconnected',
        mcp_ready: !!data.mcp_ready,
      });
    } catch (e) {
      setError(e instanceof Error ? e.message : t('settings_page.settings_load_failed'));
    } finally {
      setLoading(false);
    }
    try {
      const catalog = await api.listModels();
      setModels(catalog);
      setModelError(null);
    } catch (e) {
      setModelError(e instanceof Error ? e.message : t('settings_page.model_load_failed'));
    } finally {
      setModelsLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const updateFlag = async (key: 'autonomous_agent_mode' | 'token_throttle_mcp_enabled', value: boolean) => {
    if (saving) return;
    setSaving(true);
    setSaveError(null);
    setSaveOk(false);
    try {
      const data = await api.updateSettings({ [key]: value });
      setSettings({
        autonomous_agent_mode: !!data.autonomous_agent_mode,
        token_throttle_mcp_enabled: !!data.token_throttle_mcp_enabled,
        mcp_status: data.mcp_status || 'disconnected',
        mcp_ready: !!data.mcp_ready,
      });
      setSaveOk(true);
    } catch (e) {
      setSaveError(e instanceof Error ? e.message : t('settings_page.settings_update_failed'));
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div>
        <SettingsSectionHeader title={t('settings.api_settings')} description={t('settings.api_settings')} />
        <SkeletonList count={2} />
      </div>
    );
  }

  if (error) {
    return (
      <div>
        <SettingsSectionHeader title={t('settings.api_settings')} description={t('settings.api_settings')} />
        <ErrorBanner message={error} onRetry={load} />
      </div>
    );
  }

  return (
    <div>
      <SettingsSectionHeader title={t('settings.api_settings')} description={t('settings.api_settings')} />

      <SectionCard title={t('settings_page.execution_mode')}>
        <div className="space-y-4">
          <Switch
            label={t('settings_page.auto_agent')}
            description={t('settings_page.auto_agent_desc')}
            checked={settings?.autonomous_agent_mode ?? false}
            onChange={(v) => updateFlag('autonomous_agent_mode', v)}
            disabled={saving}
          />
          <Switch
            label={t('settings_page.mcp_throttle')}
            description={t('settings_page.mcp_throttle_desc')}
            checked={settings?.token_throttle_mcp_enabled ?? false}
            onChange={(v) => updateFlag('token_throttle_mcp_enabled', v)}
            disabled={saving}
          />
        </div>
      </SectionCard>

      <SectionCard title={t('settings_page.available_models')} description={t('settings_page.available_models_desc')}>
        {modelsLoading ? (
          <p role="status" className="text-sm text-[var(--color-text-muted)]">{t('settings_page.loading_models')}</p>
        ) : modelError ? (
          <div className="flex items-center gap-2 text-sm text-[var(--color-error)]">
            <span role="alert" className="flex-1">{modelError}</span>
            <Button variant="ghost" size="sm" onClick={() => void load()} icon={<RefreshCw size={14} />}>{t('settings_page.retry')}</Button>
          </div>
        ) : models.length === 0 ? (
          <p className="text-sm text-[var(--color-text-muted)]">{t('settings_page.no_models')}</p>
        ) : (
          <div className="grid gap-2 sm:grid-cols-2">
            {models.map(model => (
              <div key={`${model.provider}:${model.model_id}`} className="flex min-w-0 items-center gap-3 rounded-[var(--radius-md)] border border-[var(--color-border-subtle)] px-3 py-2">
                <Server size={15} className="shrink-0 text-[var(--color-accent-foreground)]" aria-hidden="true" />
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm text-[var(--color-text-primary)]">{model.label || model.model_id}</p>
                  <p className="truncate font-mono text-[length:var(--text-2xs)] text-[var(--color-text-muted)]">{model.provider}:{model.model_id}</p>
                </div>
                <Check size={14} className="shrink-0 text-[var(--color-success)]" aria-label={t('settings_page.available')} />
              </div>
            ))}
          </div>
        )}
      </SectionCard>

      <SectionCard title={t('settings_page.mcp_status')}>
        <div className="flex items-center gap-3">
          <div className={cn(
            'p-2 rounded-[var(--radius-lg)]',
            settings?.mcp_ready
              ? 'bg-[var(--color-success-subtle)]'
              : 'bg-[var(--color-bg-surface-2)]'
          )}>
            <Cpu size={20} className={settings?.mcp_ready ? 'text-[var(--color-success)]' : 'text-[var(--color-text-muted)]'} />
          </div>
          <div>
            <div className="text-sm font-medium text-[var(--color-text-primary)]">
              {settings?.mcp_ready ? t('settings_page.mcp_ready') : t('settings_page.mcp_not_ready')}
            </div>
            <div className="text-xs text-[var(--color-text-muted)]">{settings?.mcp_status}</div>
          </div>
          <Badge variant={settings?.mcp_ready ? 'success' : 'secondary'} className="ml-auto">
            {settings?.mcp_status}
          </Badge>
        </div>
      </SectionCard>

      {saveError && <ErrorBanner message={saveError} onRetry={load} />}

      <div className="flex items-center justify-between gap-3 border-t border-[var(--color-border-subtle)] pt-4 mt-4">
        <p role="status" className="text-xs text-[var(--color-text-muted)]">{saving ? t('settings_page.saving') : saveOk ? t('settings_page.saved') : t('settings_page.auto_saved')}</p>
        <Button size="sm" variant="outline" onClick={load} disabled={saving}>{t('common.refresh')}</Button>
      </div>
    </div>
  );
}

function ApiKeysSection() {
  return <ApiKeysPage embedded />;
}

interface NotificationSettings {
  email_address: string;
  email_system: boolean;
  email_task_done: boolean;
  email_weekly: boolean;
  email_marketing: boolean;
  webhook_url: string;
  webhook_task_done: boolean;
  webhook_task_failed: boolean;
}

const DEFAULT_NOTIFICATIONS: NotificationSettings = {
  email_address: '',
  email_system: false,
  email_task_done: false,
  email_weekly: false,
  email_marketing: false,
  webhook_url: '',
  webhook_task_done: false,
  webhook_task_failed: false,
};

export function NotificationsSection() {
  const { t } = useI18n();
  const [settings, setSettings] = useState<NotificationSettings>(DEFAULT_NOTIFICATIONS);
  const [webhookConfigured, setWebhookConfigured] = useState(false);
  const [webhookAction, setWebhookAction] = useState<'keep' | 'replace' | 'clear'>('keep');
  const webhookSnapshot = useRef<{ done: boolean; failed: boolean } | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [saveOk, setSaveOk] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<{ ok: boolean; error?: string } | null>(null);

  const handleTestNotification = async () => {
    if (testing) return;
    setTesting(true);
    setTestResult(null);
    try {
      await api.testNotification();
      setTestResult({ ok: true });
    } catch (e) {
      setTestResult({ ok: false, error: e instanceof Error ? e.message : t('settings_page.test_notification_failed', { defaultValue: 'Failed to send the test notification.' }) });
    } finally {
      setTesting(false);
    }
  };

  const applySaved = useCallback((data: SettingsResponse) => {
    const n = data.notifications as (Partial<NotificationSettings> & { webhook_configured?: boolean }) | undefined;
    if (!n) throw new Error(t('settings_page.notif_missing'));
    setSettings({
      email_address: n.email_address ?? '',
      email_system: n.email_system ?? false,
      email_task_done: n.email_task_done ?? false,
      email_weekly: n.email_weekly ?? false,
      email_marketing: n.email_marketing ?? false,
      webhook_url: '',
      webhook_task_done: n.webhook_task_done ?? false,
      webhook_task_failed: n.webhook_task_failed ?? false,
    });
    setWebhookConfigured(n.webhook_configured === true);
    setWebhookAction('keep');
  }, []);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    setSaveError(null);
    setSaveOk(false);
    try {
      const data = await api.getSettings();
      applySaved(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : t('settings_page.notif_load_failed'));
    } finally {
      setLoading(false);
    }
  }, [applySaved]);

  useEffect(() => { load(); }, [load]);

  const handleSave = async () => {
    if (saving) return;
    if (webhookAction === 'clear' && !window.confirm(t('settings_page.clear_webhook_confirm'))) return;
    setSaving(true);
    setSaveError(null);
    setSaveOk(false);
    try {
      const { webhook_url, ...notifications } = settings;
      const data = await api.updateSettings({ notifications: {
        ...notifications,
        ...(webhookAction === 'keep' ? {} : { webhook_url: webhookAction === 'clear' ? '' : webhook_url }),
      } });
      applySaved(data);
      setSaveOk(true);
    } catch (e) {
      setSaveError(e instanceof Error ? e.message : t('settings_page.notif_save_failed'));
    } finally {
      setSaving(false);
    }
  };

  const toggle = (key: keyof NotificationSettings, value: boolean) => {
    setSaveOk(false);
    setSettings(prev => ({ ...prev, [key]: value }));
  };

  if (loading) {
    return (
      <div>
        <SettingsSectionHeader title={t('settings.notifications')} description={t('settings.notifications')} />
        <SkeletonList count={2} />
      </div>
    );
  }

  if (error) {
    return (
      <div>
        <SettingsSectionHeader title={t('settings.notifications')} description={t('settings.notifications')} />
        <ErrorBanner message={error} onRetry={load} />
      </div>
    );
  }

  return (
    <div>
      <SettingsSectionHeader title={t('settings.notifications')} description={t('settings.notifications')} />

      <SectionCard title={t('settings_page.email_notif')}>
        <div className="space-y-4">
          <FormField label={t('settings_page.notif_email')} description={t('settings_page.notif_email_desc')}>
            <Input
              aria-label={t('settings_page.notif_email')} type="email" autoComplete="email"
              value={settings.email_address}
              onChange={(e) => { setSaveOk(false); setSettings(prev => ({ ...prev, email_address: e.target.value })); }}
              disabled={saving}
            />
          </FormField>
          <Switch label={t('settings_page.email_system')} description={t('settings_page.email_system_desc')} checked={settings.email_system} onChange={(v) => toggle('email_system', v)} disabled={saving} />
          <Switch label={t('settings_page.email_task_done_label')} description={t('settings_page.email_task_done_desc')} checked={settings.email_task_done} onChange={(v) => toggle('email_task_done', v)} disabled={saving} />
          <Switch label={t('settings_page.email_weekly')} description={t('settings_page.email_weekly_desc')} checked={settings.email_weekly} onChange={(v) => toggle('email_weekly', v)} disabled={saving} />
          <Switch label={t('settings_page.email_marketing')} description={t('settings_page.email_marketing_desc')} checked={settings.email_marketing} onChange={(v) => toggle('email_marketing', v)} disabled={saving} />
        </div>
      </SectionCard>

       <SectionCard title={t('settings_page.webhook_title', { defaultValue: 'Webhook' })}>
        <div className="space-y-4">
          <FormField label={t('settings_page.webhook_url')} description={t('settings_page.webhook_url_desc')}>
            <Input
              aria-label={t('settings_page.webhook_url', { defaultValue: 'Webhook URL' })} type="password" autoComplete="new-password"
              placeholder={webhookConfigured ? t('settings_page.webhook_placeholder_configured') : 'https://your-webhook-url.com/endpoint'}
              value={settings.webhook_url}
              onChange={(e) => {
                const value = e.target.value;
                setSaveOk(false);
                setSettings(prev => ({ ...prev, webhook_url: value }));
                setWebhookAction(value.trim() ? 'replace' : 'keep');
              }}
              disabled={saving}
            />
            <p className="text-xs text-[var(--color-text-muted)] mt-2">
              {webhookAction === 'clear' ? t('settings_page.webhook_state_clear') : webhookConfigured ? t('settings_page.webhook_state_configured') : t('settings_page.webhook_state_not')}
            </p>
            {webhookConfigured && (
              <Button variant="ghost" size="sm" disabled={saving} onClick={() => {
                setSaveOk(false);
                if (webhookAction === 'clear') {
                  // Restore the event flags captured when entering clear mode,
                  // so toggling back to "keep" does not silently drop them (R10-10).
                  setWebhookAction('keep');
                  setSettings(prev => ({
                    ...prev,
                    webhook_url: '',
                    webhook_task_done: webhookSnapshot.current?.done ?? prev.webhook_task_done,
                    webhook_task_failed: webhookSnapshot.current?.failed ?? prev.webhook_task_failed,
                  }));
                } else {
                  webhookSnapshot.current = {
                    done: settings.webhook_task_done,
                    failed: settings.webhook_task_failed,
                  };
                  setWebhookAction('clear');
                  setSettings(prev => ({ ...prev, webhook_url: '', webhook_task_done: false, webhook_task_failed: false }));
                }
              }}>
                {webhookAction === 'clear' ? t('settings_page.webhook_keep') : t('settings_page.webhook_clear')}
              </Button>
            )}
          </FormField>
          <FormField label={t('settings_page.trigger_events')}>
            <div className="space-y-2 mt-1">
              <Switch label={t('settings_page.webhook_task_done')} description={t('settings_page.webhook_task_done_desc')} checked={settings.webhook_task_done} onChange={(v) => toggle('webhook_task_done', v)} disabled={saving} />
              <Switch label={t('settings_page.webhook_task_failed')} description={t('settings_page.webhook_task_failed_desc')} checked={settings.webhook_task_failed} onChange={(v) => toggle('webhook_task_failed', v)} disabled={saving} />
            </div>
          </FormField>
        </div>
      </SectionCard>

      {saveError && <ErrorBanner message={saveError} />}
      {saveOk && <p role="status" className="text-sm text-[var(--color-success)]">{t('settings_page.config_saved')}</p>}

      <div className="flex justify-end gap-2 border-t border-[var(--color-border-subtle)] pt-4 mt-4">
        <Button variant="outline" onClick={() => { if (window.confirm(t('settings_page.reload_confirm'))) void load(); }} disabled={saving}>{t('common.reset')}</Button>
        <Button onClick={handleSave} loading={saving} disabled={saving}>
          {saveOk ? t('common.saved') : t('settings.save_changes')}
        </Button>
      </div>

      <div className="mt-4 rounded-[var(--radius-md)] border border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-1)] p-4">
        <div className="flex flex-wrap items-center gap-3">
          <div className="min-w-0 flex-1">
            <p className="text-sm font-medium text-[var(--color-text-primary)]">
              {t('settings_page.test_notification_title', { defaultValue: 'Test notification' })}
            </p>
            <p className="mt-0.5 text-xs text-[var(--color-text-muted)]">
              {t('settings_page.test_notification_desc', { defaultValue: 'Send a test notification to verify the current channel configuration.' })}
            </p>
          </div>
          <Button variant="secondary" size="sm" onClick={() => { void handleTestNotification(); }} loading={testing} disabled={testing || saving}>
            {t('settings_page.test_notification_action', { defaultValue: 'Send test notification' })}
          </Button>
        </div>
        {testResult && (
          <p
            role="status"
            aria-live="polite"
            className={`mt-2 text-sm ${testResult.ok ? 'text-[var(--color-success)]' : 'text-[var(--color-error)]'}`}
          >
            {testResult.ok
              ? t('settings_page.test_notification_sent', { defaultValue: 'Test notification sent.' })
              : t('settings_page.test_notification_failed', { defaultValue: 'Failed to send the test notification.', error: testResult.error ?? '' })}
          </p>
        )}
      </div>
    </div>
  );
}

function SecuritySection() {
  const { t } = useI18n();
  const [authHealth, setAuthHealth] = useState<{ authentication_enabled?: boolean; auth_method?: string } | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [showPwdForm, setShowPwdForm] = useState(false);
  const [pwd, setPwd] = useState({ current: '', next: '', confirm: '' });
  const [pwdSaving, setPwdSaving] = useState(false);
  const [pwdError, setPwdError] = useState<string | null>(null);
  const [pwdOk, setPwdOk] = useState(false);

  const PERMISSION_LEVELS = [
    { tier: 'read_only', mode: 'plan', labelKey: 'permission_level_readonly', descKey: 'permission_level_readonly_desc' },
    { tier: 'partial_write', mode: 'default', labelKey: 'permission_level_partial', descKey: 'permission_level_partial_desc' },
    { tier: 'full_write', mode: 'auto', labelKey: 'permission_level_full', descKey: 'permission_level_full_desc' },
  ] as const;
  const [permTier, setPermTier] = useState<PermissionTier | null>(null);
  const [permSaving, setPermSaving] = useState<PermissionTier | null>(null);
  const [permError, setPermError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getAuthHealth();
      setAuthHealth(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : t('settings_page.security_load_failed'));
    } finally {
      setLoading(false);
    }
    try {
      const perm = await api.getPermissionTiers();
      setPermTier(perm.current.tier);
    } catch {
      // A non-admin account cannot read the policy; the selector stays hidden.
      setPermTier(null);
    }
  }, []);  useEffect(() => { load(); }, [load]);

  const handleChangePassword = async () => {
    if (pwdSaving) return;
    setPwdOk(false);
    setPwdError(null);
    if (pwd.next !== pwd.confirm) {
      setPwdError(t('settings_page.pwd_mismatch'));
      return;
    }
    if (pwd.next.length < 6) {
      setPwdError(t('settings_page.pwd_too_short'));
      return;
    }
    setPwdSaving(true);
    try {
      await api.changePassword(pwd.current, pwd.next);
      setPwd({ current: '', next: '', confirm: '' });
      setShowPwdForm(false);
      setPwdOk(true);
    } catch (e) {
      setPwdError(e instanceof Error ? e.message : t('settings_page.pwd_change_failed'));
    } finally {
      setPwdSaving(false);
    }
  };

  const handlePermissionChange = async (tier: PermissionTier, mode: string) => {
    if (permSaving) return;
    setPermSaving(tier);
    setPermError(null);
    try {
      const updated = await api.updatePermissionConfig({ tier, mode });
      setPermTier(updated.tier);
    } catch (e) {
      setPermError(e instanceof Error ? e.message : t('settings_page.perm_update_failed'));
    } finally {
      setPermSaving(null);
    }
  };

  if (loading) {
    return (
      <div>
        <SettingsSectionHeader title={t('settings.security')} description={t('settings.security')} />
        <SkeletonList count={2} />
      </div>
    );
  }

  if (error) {
    return (
      <div>
        <SettingsSectionHeader title={t('settings.security')} description={t('settings.security')} />
        <ErrorBanner message={error} onRetry={load} />
      </div>
    );
  }

  const authEnabled = authHealth?.authentication_enabled;

  return (
    <div>
      <SettingsSectionHeader title={t('settings.security')} description={t('settings.security')} />

      <SectionCard title={t('settings_page.auth_status')} description={t('settings_page.auth_status_desc')}>
        <div className="flex items-center gap-3">
          <div className={cn(
            'p-2 rounded-[var(--radius-lg)]',
            authEnabled ? 'bg-[var(--color-success-subtle)]' : 'bg-[var(--color-bg-surface-2)]'
          )}>
            <Shield size={20} className={authEnabled ? 'text-[var(--color-success)]' : 'text-[var(--color-text-muted)]'} />
          </div>
          <div>
               <div role="status" className="text-sm font-medium text-[var(--color-text-primary)]">
              {authEnabled ? t('settings_page.auth_enabled') : t('settings_page.auth_disabled')}
            </div>
            <div className="text-xs text-[var(--color-text-muted)]">
              {authHealth?.auth_method && authHealth.auth_method !== 'disabled'
                ? t('settings_page.auth_method', { method: authHealth.auth_method })
                : t('settings_page.auth_none')}
            </div>
          </div>
          <Badge variant={authEnabled ? 'success' : 'warning'} className="ml-auto">
            {authEnabled ? 'enabled' : 'disabled'}
          </Badge>
        </div>
      </SectionCard>

      {permTier !== null && (
        <SectionCard title={t('settings.permission_mode')} description={t('settings.permission_mode_desc')}>
          <div className="space-y-2">
            {PERMISSION_LEVELS.map((level) => {
               const selected = permTier === level.tier;
               const busy = permSaving === level.tier;
              return (
                <button
                  key={level.tier}
                  type="button"
                  disabled={permSaving !== null}
                  onClick={() => { void handlePermissionChange(level.tier, level.mode); }}
                  aria-pressed={selected}
                  className={cn(
                    'w-full text-left p-3 rounded-[var(--radius-lg)] border transition-colors motion-reduce:transition-none',
                    selected
                      ? 'border-[var(--color-primary)] bg-[var(--color-primary-subtle,var(--color-bg-surface-2))]'
                      : 'border-[var(--color-border-subtle)] hover:bg-[var(--color-bg-surface-2)]',
                    permSaving !== null && !busy && 'opacity-60'
                  )}
                >
                  <div className="flex items-center gap-2">
                    <Shield size={16} className={selected ? 'text-[var(--color-primary)]' : 'text-[var(--color-text-muted)]'} />
                    <span className="text-sm font-medium text-[var(--color-text-primary)]">
                      {t(`settings.${level.labelKey}`)}
                    </span>
                    {selected && <Badge variant="success" className="ml-auto">✓</Badge>}
                  </div>
                  <p className="text-xs text-[var(--color-text-muted)] mt-1">
                    {t(`settings.${level.descKey}`)}
                  </p>
                </button>
              );
            })}
          </div>
          {permError && <p role="alert" className="text-xs text-[var(--color-error)] mt-2">{permError}</p>}
        </SectionCard>
      )}

      <SectionCard title={t('settings_page.pwd_title')} description={t('settings_page.pwd_desc')}>
        {!showPwdForm ? (
          <div className="flex items-center justify-between">
            <div>
              <div className="text-sm font-medium text-[var(--color-text-primary)]">
                {pwdOk ? t('settings_page.pwd_changed') : t('settings_page.pwd_label')}
              </div>
              <div className="text-xs text-[var(--color-text-muted)] mt-0.5">
                {pwdOk ? t('settings_page.pwd_reuse') : t('settings_page.pwd_change_hint')}
              </div>
            </div>
            <Button size="sm" variant="outline" onClick={() => setShowPwdForm(true)}>{t('settings_page.change_pwd')}</Button>
          </div>
        ) : (
           <form onSubmit={(event) => { event.preventDefault(); void handleChangePassword(); }}>
           <fieldset disabled={pwdSaving} className="space-y-3">
             <FormField label={t('settings_page.current_pwd')} required>
               <Input type="password" autoComplete="current-password" placeholder={t('settings_page.current_pwd_ph')} aria-label={t('settings_page.current_pwd')} value={pwd.current} onChange={(e) => setPwd({ ...pwd, current: e.target.value })} />
             </FormField>
             <FormField label={t('settings_page.new_pwd')} required>
               <Input type="password" autoComplete="new-password" placeholder={t('settings_page.new_pwd_ph')} aria-label={t('settings_page.new_pwd')} value={pwd.next} onChange={(e) => setPwd({ ...pwd, next: e.target.value })} />
             </FormField>
             <FormField label={t('settings_page.confirm_pwd')} required>
               <Input type="password" autoComplete="new-password" placeholder={t('settings_page.confirm_pwd_ph')} aria-label={t('settings_page.confirm_pwd')} value={pwd.confirm} onChange={(e) => setPwd({ ...pwd, confirm: e.target.value })} />
             </FormField>
            {pwdError && <p role="alert" className="text-xs text-[var(--color-error)]">{pwdError}</p>}
            <div className="flex items-center gap-2">
              <Button size="sm" onClick={handleChangePassword} loading={pwdSaving} disabled={pwdSaving}>
                {t('settings_page.confirm_btn')}
              </Button>
              <Button size="sm" variant="ghost" onClick={() => { setShowPwdForm(false); setPwdError(null); setPwd({ current: '', next: '', confirm: '' }); }}>
                {t('common.cancel')}
              </Button>
            </div>
           </fieldset>
           </form>
        )}
      </SectionCard>
    </div>
  );
}

function AboutSection() {
  const { t } = useI18n();
  return (
    <div>
      <SettingsSectionHeader title={t('settings.advanced')} description={t('settings.advanced')} />

      <Card variant="default" padding="none" className="mb-4 overflow-hidden">
        <div className="p-4 border-b border-[var(--color-border-subtle)]">
          <div className="flex items-center gap-3">
            <div>
              <h2 className="text-[length:var(--text-base)] font-semibold text-[var(--color-text-primary)]">Climber</h2>
              <p className="text-sm text-[var(--color-text-muted)]">{t('settings_page.version_unreported')}</p>
            </div>
          </div>
        </div>
        <div className="px-4 py-2">
          <div className="flex items-center justify-between py-2">
            <span className="text-sm text-[var(--color-text-secondary)]">{t('settings_page.version')}</span>
            {/* No backend endpoint reports a version, so say so instead of
                printing a plausible number. */}
            <span className="text-sm text-[var(--color-text-muted)]">{t('settings_page.version_unset')}</span>
          </div>
        </div>
      </Card>

    </div>
  );
}

export default SettingsPage;
