import { useState, useEffect, useCallback } from 'react';
import {
  User, Cpu, Key, Bell, Shield, Info,
  Mail,
   ChevronRight, AlertCircle, RefreshCw,
   MessageSquare, Database, ExternalLink,
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
import { api } from '../api';
import { ApiKeysPage } from './ApiKeysPage';
import { AuthApiKeysPage } from './AuthApiKeysPage';

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
                    'p-1.5 rounded-lg transition-colors',
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
                    <div id={descriptionId} className="text-[10px] text-[var(--color-text-muted)] truncate">{item.description}</div>
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
    <div className="mb-5">
      <h1 className="text-lg font-semibold text-[var(--color-text-primary)]">{title}</h1>
      {description && <p className="text-sm text-[var(--color-text-muted)] mt-1">{description}</p>}
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
      <div className="px-4 py-3 border-b border-[var(--color-border-subtle)]">
        <h3 className="text-sm font-semibold text-[var(--color-text-primary)]">{title}</h3>
        {description && <p className="text-xs text-[var(--color-text-muted)] mt-0.5">{description}</p>}
      </div>
      <div className="p-4">{children}</div>
    </Card>
  );
}

interface ErrorBannerProps {
  message: SettingsError;
  onRetry?: () => void;
}

type SettingsError = { key: string } | { message: string };

function settingsError(error: unknown, fallbackKey: string): SettingsError {
  if (error instanceof Error) {
    return error.message === 'settings.notifications_missing'
      ? { key: error.message }
      : { message: error.message };
  }
  return { key: fallbackKey };
}

function ErrorBanner({ message, onRetry }: ErrorBannerProps) {
  const { t } = useI18n();
  return (
    <Card variant="default" className="mb-4 border-[var(--color-error)]/30">
      <CardContent className="p-3 md:p-4 flex items-center gap-3">
        <AlertCircle size={18} className="text-[var(--color-error)] shrink-0" />
        <p role="alert" className="text-sm text-[var(--color-error)] flex-1">{'key' in message ? t(message.key) : message.message}</p>
        {onRetry && (
          <Button variant="ghost" size="sm" onClick={onRetry} icon={<RefreshCw size={14} />}>
            {t('settings.reload')}
          </Button>
        )}
      </CardContent>
    </Card>
  );
}

interface CurrentUser {
  id: number;
  username: string;
  email: string;
  role: string;
  scopes?: string[];
}

function ProfileSection() {
  const { t } = useI18n();
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<SettingsError | null>(null);
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<SettingsError | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getCurrentUser();
      setUser(data);
      setUsername(data.username || '');
      setEmail(data.email || '');
    } catch (e) {
      setError(settingsError(e, 'settings.profile_load_failed'));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const handleSave = async () => {
    if (saving) return;
    setSaving(true);
    setSaveError(null);
    try {
      await api.updateSettings({
        autonomous_agent_mode: false,
      });
      setSaveError({ key: 'settings.profile_save_notice' });
    } catch (e) {
      setSaveError(settingsError(e, 'settings.profile_save_failed'));
    } finally {
      setSaving(false);
    }
  };

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

      <SectionCard title={t('settings.basic_info')}>
        <div className="space-y-4">
          <FormField label={t('settings.username')} description={t('settings.username_hint')} required>
              <Input
                id="settings-username"
              placeholder={t('settings.username_placeholder')}
              value={username}
              disabled
            />
          </FormField>
          <FormField label={t('settings.email')} description={t('settings.email_hint')} required>
              <Input
                id="settings-email"
              type="email"
              placeholder="your@email.com"
              value={email}
              disabled
              leftIcon={<Mail size={14} />}
            />
          </FormField>
          <FormField label={t('settings.role')} description={t('settings.role_hint')}>
            <Input value={user?.role || ''} disabled />
          </FormField>
        </div>
      </SectionCard>

      {saveError && <ErrorBanner message={saveError} />}

      <div className="flex justify-end gap-2 border-t border-[var(--color-border-subtle)] pt-4 mt-4">
        <Button variant="outline" onClick={load} disabled={saving}>{t('common.cancel')}</Button>
        <Button onClick={handleSave} loading={saving} disabled={saving}>
          {saving ? t('settings.submitting') : t('settings.save_changes')}
        </Button>
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
  const [settings, setSettings] = useState<SettingsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<SettingsError | null>(null);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<SettingsError | null>(null);
  const [saveOk, setSaveOk] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getSettings();
      setSettings({
        autonomous_agent_mode: !!data.autonomous_agent_mode,
        token_throttle_mcp_enabled: !!data.token_throttle_mcp_enabled,
        mcp_status: data.mcp_status || 'disconnected',
        mcp_ready: !!data.mcp_ready,
      });
    } catch (e) {
      setError(settingsError(e, 'settings.load_failed'));
    } finally {
      setLoading(false);
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
      setSaveError(settingsError(e, 'settings.update_failed'));
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

      <SectionCard title={t('settings.execution_mode')}>
        <div className="space-y-4">
          <Switch
            label={t('settings.autonomous_mode')}
            description={t('settings.autonomous_mode_hint')}
            checked={settings?.autonomous_agent_mode ?? false}
            onChange={(v) => updateFlag('autonomous_agent_mode', v)}
            disabled={saving}
          />
          <Switch
            label={t('settings.mcp_throttle')}
            description={t('settings.mcp_throttle_hint')}
            checked={settings?.token_throttle_mcp_enabled ?? false}
            onChange={(v) => updateFlag('token_throttle_mcp_enabled', v)}
            disabled={saving}
          />
        </div>
      </SectionCard>

      <SectionCard title={t('settings.mcp_status')}>
        <div className="flex items-center gap-3">
          <div className={cn(
            'p-2 rounded-xl',
            settings?.mcp_ready
              ? 'bg-[var(--color-success-subtle)]'
              : 'bg-[var(--color-bg-surface-2)]'
          )}>
            <Cpu size={20} className={settings?.mcp_ready ? 'text-[var(--color-success)]' : 'text-[var(--color-text-muted)]'} />
          </div>
          <div>
            <div className="text-sm font-medium text-[var(--color-text-primary)]">
              {t(settings?.mcp_ready ? 'settings.ready' : 'settings.not_ready')}
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
        <p role="status" className="text-xs text-[var(--color-text-muted)]">{t(saving ? 'settings.saving' : saveOk ? 'settings.settings_saved' : 'settings.auto_save_hint')}</p>
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
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<SettingsError | null>(null);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<SettingsError | null>(null);
  const [saveOk, setSaveOk] = useState(false);

  const applySaved = useCallback((data: { notifications?: Partial<NotificationSettings> & { webhook_configured?: boolean } }) => {
    const n = data.notifications;
    if (!n) throw new Error('settings.notifications_missing');
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
      setError(settingsError(e, 'settings.notifications_load_failed'));
    } finally {
      setLoading(false);
    }
  }, [applySaved]);

  useEffect(() => { load(); }, [load]);

  const handleSave = async () => {
    if (saving) return;
    if (webhookAction === 'clear' && !window.confirm(t('settings.webhook_clear_confirm'))) return;
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
      setSaveError(settingsError(e, 'settings.notifications_save_failed'));
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

      <SectionCard title={t('settings.email_notifications')}>
        <div className="space-y-4">
          <FormField label={t('settings.notification_email')} description={t('settings.notification_email_hint')}>
            <Input
              aria-label={t('settings.notification_email')} type="email" autoComplete="email"
              value={settings.email_address}
              onChange={(e) => { setSaveOk(false); setSettings(prev => ({ ...prev, email_address: e.target.value })); }}
              disabled={saving}
            />
          </FormField>
          <Switch label={t('settings.system_notifications')} description={t('settings.system_notifications_hint')} checked={settings.email_system} onChange={(v) => toggle('email_system', v)} disabled={saving} />
          <Switch label={t('settings.task_done')} description={t('settings.email_task_done_hint')} checked={settings.email_task_done} onChange={(v) => toggle('email_task_done', v)} disabled={saving} />
          <Switch label={t('settings.weekly_summary')} description={t('settings.weekly_summary_hint')} checked={settings.email_weekly} onChange={(v) => toggle('email_weekly', v)} disabled={saving} />
          <Switch label={t('settings.marketing_email')} description={t('settings.marketing_email_hint')} checked={settings.email_marketing} onChange={(v) => toggle('email_marketing', v)} disabled={saving} />
        </div>
      </SectionCard>

       <SectionCard title="Webhook">
        <div className="space-y-4">
          <FormField label="Webhook URL" description={t('settings.webhook_url_hint')}>
            <Input
              aria-label="Webhook URL" type="password" autoComplete="new-password"
              placeholder={webhookConfigured ? t('settings.webhook_replace_placeholder') : 'https://your-webhook-url.com/endpoint'}
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
              {t(webhookAction === 'clear' ? 'settings.webhook_clear_pending' : webhookConfigured ? 'settings.webhook_configured' : 'settings.webhook_unconfigured')}
            </p>
            {webhookConfigured && (
              <Button variant="ghost" size="sm" disabled={saving} onClick={() => {
                setSaveOk(false);
                setWebhookAction(webhookAction === 'clear' ? 'keep' : 'clear');
                setSettings(prev => ({ ...prev, webhook_url: '', webhook_task_done: false, webhook_task_failed: false }));
              }}>
                {t(webhookAction === 'clear' ? 'settings.webhook_keep' : 'settings.webhook_clear')}
              </Button>
            )}
          </FormField>
          <FormField label={t('settings.trigger_events')}>
            <div className="space-y-2 mt-1">
              <Switch label={t('settings.task_done')} description={t('settings.webhook_task_done_hint')} checked={settings.webhook_task_done} onChange={(v) => toggle('webhook_task_done', v)} disabled={saving} />
              <Switch label={t('settings.task_failed')} description={t('settings.webhook_task_failed_hint')} checked={settings.webhook_task_failed} onChange={(v) => toggle('webhook_task_failed', v)} disabled={saving} />
            </div>
          </FormField>
        </div>
      </SectionCard>

      {saveError && <ErrorBanner message={saveError} />}
      {saveOk && <p role="status" className="text-sm text-[var(--color-success)]">{t('settings.configuration_saved')}</p>}

      <div className="flex justify-end gap-2 border-t border-[var(--color-border-subtle)] pt-4 mt-4">
        <Button variant="outline" onClick={() => { if (window.confirm(t('settings.reset_confirm'))) void load(); }} disabled={saving}>{t('common.reset')}</Button>
        <Button onClick={handleSave} loading={saving} disabled={saving}>
          {saveOk ? t('common.saved') : t('settings.save_changes')}
        </Button>
      </div>
    </div>
  );
}

function SecuritySection() {
  const { t } = useI18n();
  const [authHealth, setAuthHealth] = useState<{ authentication_enabled?: boolean; auth_method?: string } | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<SettingsError | null>(null);

  const [showPwdForm, setShowPwdForm] = useState(false);
  const [pwd, setPwd] = useState({ current: '', next: '', confirm: '' });
  const [pwdSaving, setPwdSaving] = useState(false);
  const [pwdError, setPwdError] = useState<SettingsError | null>(null);
  const [pwdOk, setPwdOk] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getAuthHealth();
      setAuthHealth(data);
    } catch (e) {
      setError(settingsError(e, 'settings.security_load_failed'));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const handleChangePassword = async () => {
    if (pwdSaving) return;
    setPwdOk(false);
    setPwdError(null);
    if (pwd.next !== pwd.confirm) {
      setPwdError({ key: 'settings.password_mismatch' });
      return;
    }
    if (pwd.next.length < 6) {
      setPwdError({ key: 'settings.password_too_short' });
      return;
    }
    setPwdSaving(true);
    try {
      await api.changePassword(pwd.current, pwd.next);
      setPwd({ current: '', next: '', confirm: '' });
      setShowPwdForm(false);
      setPwdOk(true);
    } catch (e) {
      setPwdError(settingsError(e, 'settings.password_change_failed'));
    } finally {
      setPwdSaving(false);
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

      <SectionCard title={t('settings.auth_status')} description={t('settings.auth_status_hint')}>
        <div className="flex items-center gap-3">
          <div className={cn(
            'p-2 rounded-xl',
            authEnabled ? 'bg-[var(--color-success-subtle)]' : 'bg-[var(--color-bg-surface-2)]'
          )}>
            <Shield size={20} className={authEnabled ? 'text-[var(--color-success)]' : 'text-[var(--color-text-muted)]'} />
          </div>
          <div>
               <div role="status" className="text-sm font-medium text-[var(--color-text-primary)]">
              {t(authEnabled ? 'settings.auth_enabled' : 'settings.auth_disabled')}
            </div>
            <div className="text-xs text-[var(--color-text-muted)]">
              {authHealth?.auth_method && authHealth.auth_method !== 'disabled'
                ? t('settings.auth_method', { method: authHealth.auth_method })
                : t('settings.auth_disabled_hint')}
            </div>
          </div>
          <Badge variant={authEnabled ? 'success' : 'warning'} className="ml-auto">
            {authEnabled ? 'enabled' : 'disabled'}
          </Badge>
        </div>
      </SectionCard>

      <SectionCard title={t('settings.password_change')} description={t('settings.password_change_hint')}>
        {!showPwdForm ? (
          <div className="flex items-center justify-between">
            <div>
              <div className="text-sm font-medium text-[var(--color-text-primary)]">
                {t(pwdOk ? 'settings.password_changed' : 'settings.password')}
              </div>
              <div className="text-xs text-[var(--color-text-muted)] mt-0.5">
                {t(pwdOk ? 'settings.password_relogin_hint' : 'settings.password_button_hint')}
              </div>
            </div>
            <Button size="sm" variant="outline" onClick={() => setShowPwdForm(true)}>{t('settings.password_change')}</Button>
          </div>
        ) : (
           <form onSubmit={(event) => { event.preventDefault(); void handleChangePassword(); }}>
           <fieldset disabled={pwdSaving} className="space-y-3">
             <FormField label={t('settings.current_password')} required>
               <Input type="password" autoComplete="current-password" placeholder={t('settings.current_password_placeholder')} aria-label={t('settings.current_password')} value={pwd.current} onChange={(e) => setPwd({ ...pwd, current: e.target.value })} />
             </FormField>
             <FormField label={t('settings.new_password')} required>
               <Input type="password" autoComplete="new-password" placeholder={t('settings.new_password_placeholder')} aria-label={t('settings.new_password')} value={pwd.next} onChange={(e) => setPwd({ ...pwd, next: e.target.value })} />
             </FormField>
             <FormField label={t('settings.confirm_password')} required>
               <Input type="password" autoComplete="new-password" placeholder={t('settings.confirm_password_placeholder')} aria-label={t('settings.confirm_password')} value={pwd.confirm} onChange={(e) => setPwd({ ...pwd, confirm: e.target.value })} />
             </FormField>
            {pwdError && <p role="alert" className="text-xs text-[var(--color-error)]">{'key' in pwdError ? t(pwdError.key) : pwdError.message}</p>}
            <div className="flex items-center gap-2">
              <Button size="sm" onClick={handleChangePassword} loading={pwdSaving} disabled={pwdSaving}>
                {t('settings.confirm_password_change')}
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
              <h2 className="text-lg font-bold text-[var(--color-text-primary)]">Climber</h2>
              <p className="text-sm text-[var(--color-text-muted)]">{t('settings.version_unreported')}</p>
            </div>
          </div>
        </div>
        <div className="px-4 py-2">
          <div className="flex items-center justify-between py-2">
            <span className="text-sm text-[var(--color-text-secondary)]">{t('settings.version')}</span>
            {/* No backend endpoint reports a version, so say so instead of
                printing a plausible number. */}
            <span className="text-sm text-[var(--color-text-muted)]">{t('settings.not_reported')}</span>
          </div>
        </div>
      </Card>

      <SectionCard title={t('settings.related_links')}>
        <div className="space-y-1">
          {[
            { label: t('settings.help_docs'), icon: MessageSquare },
            { label: t('settings.api_docs'), icon: Database },
            { label: t('settings.github_repo'), icon: ExternalLink },
          ].map(link => {
            const Icon = link.icon;
            return (
              <a
                key={link.label}
                href="#"
                className="flex items-center justify-between px-3 py-2.5 rounded-lg hover:bg-[var(--color-bg-surface-2)] transition-colors group"
              >
                <div className="flex items-center gap-3">
                  <Icon size={14} className="text-[var(--color-text-muted)]" />
                  <span className="text-sm text-[var(--color-text-secondary)]">{link.label}</span>
                </div>
                <ChevronRight size={14} className="text-[var(--color-text-muted)] group-hover:translate-x-0.5 transition-transform" />
              </a>
            );
          })}
        </div>
      </SectionCard>
    </div>
  );
}

export default SettingsPage;
