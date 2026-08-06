import { useState, useEffect, useCallback } from 'react';
import {
  User, Cpu, Key, Bell, Shield, Info,
  Mail,
   Trash2, Plus, Copy, Check,
   ChevronRight, AlertCircle, RefreshCw, Loader2,
  Sparkles, MessageSquare, Database, ExternalLink,
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

type SettingsSection = 'profile' | 'models' | 'apikeys' | 'notifications' | 'security' | 'about';

interface NavItem {
  id: SettingsSection;
  label: string;
  icon: typeof User;
  description: string;
}

const getNavItems = (t: (key: string) => string): NavItem[] => [
  { id: 'profile', label: t('settings.general'), icon: User, description: t('settings.account_settings') },
  { id: 'models', label: t('settings.api_settings'), icon: Cpu, description: t('settings.api_settings') },
  { id: 'apikeys', label: t('navigation.api_keys'), icon: Key, description: t('navigation.api_keys') },
  { id: 'notifications', label: t('settings.notifications'), icon: Bell, description: t('settings.notifications') },
  { id: 'security', label: t('settings.security'), icon: Shield, description: t('settings.security') },
  { id: 'about', label: t('settings.advanced'), icon: Info, description: t('settings.advanced') },
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
        <nav className="flex-1 overflow-auto p-2" aria-label="设置分组">
          <div className="settings-nav-list">
            {NAV_ITEMS.map(item => {
              const Icon = item.icon;
              const isActive = activeSection === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => handleSectionChange(item.id)}
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
                      ? 'bg-[var(--color-accent)]/15 text-[var(--color-accent)]'
                      : 'bg-[var(--color-bg-surface-2)] text-[var(--color-text-muted)]'
                  )}>
                    <Icon size={14} />
                  </div>
                  <div className="flex-1 min-w0">
                    <div className={cn(
                      'text-sm font-medium truncate',
                      isActive ? 'text-[var(--color-text-primary)]' : 'text-[var(--color-text-secondary)]'
                    )}>
                      {item.label}
                    </div>
                    <div className="text-[10px] text-[var(--color-text-muted)] truncate">{item.description}</div>
                  </div>
                  {isActive && <ChevronRight size={12} className="text-[var(--color-accent)] shrink-0" />}
                </button>
              );
            })}
          </div>
        </nav>
      </aside>
       <main className="min-w-0 flex-1 overflow-y-auto">
         <div className="mx-auto max-w-2xl p-4 md:p-8">
          {activeSection === 'profile' && <ProfileSection />}
          {activeSection === 'models' && <ModelsSection />}
          {activeSection === 'apikeys' && <ApiKeysSection />}
          {activeSection === 'notifications' && <NotificationsSection />}
          {activeSection === 'security' && <SecuritySection />}
          {activeSection === 'about' && <AboutSection />}
        </div>
      </main>
    </div>
  );
}

function SectionHeader({ title, description }: { title: string; description?: string }) {
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
      <div className="px-5 py-4 border-b border-[var(--color-border-subtle)]">
        <h3 className="text-sm font-semibold text-[var(--color-text-primary)]">{title}</h3>
        {description && <p className="text-xs text-[var(--color-text-muted)] mt-0.5">{description}</p>}
      </div>
      <div className="p-5">{children}</div>
    </Card>
  );
}

interface ErrorBannerProps {
  message: string;
  onRetry?: () => void;
}

function ErrorBanner({ message, onRetry }: ErrorBannerProps) {
  return (
    <Card variant="default" className="mb-4 border-[var(--color-error)]/30">
      <CardContent className="p-3 md:p-4 flex items-center gap-3">
        <AlertCircle size={18} className="text-[var(--color-error)] shrink-0" />
        <p className="text-sm text-[var(--color-error)] flex-1">{message}</p>
        {onRetry && (
          <Button variant="ghost" size="sm" onClick={onRetry} icon={<RefreshCw size={14} />}>
            Retry
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
  const [error, setError] = useState<string | null>(null);
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [saveOk, setSaveOk] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getCurrentUser();
      setUser(data);
      setUsername(data.username || '');
      setEmail(data.email || '');
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load profile');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const handleSave = async () => {
    setSaving(true);
    setSaveError(null);
    setSaveOk(false);
    try {
      await api.updateSettings({
        profile: { username, email },
        autonomous_agent_mode: false,
      });
      setSaveError('后端暂未支持账户资料更新接口，修改未持久化。');
    } catch (e) {
      setSaveError(e instanceof Error ? e.message : 'Failed to save profile');
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div>
        <SectionHeader title={t('settings.account_settings')} description={t('settings.account_settings')} />
        <SkeletonList count={2} />
      </div>
    );
  }

  if (error) {
    return (
      <div>
        <SectionHeader title={t('settings.account_settings')} description={t('settings.account_settings')} />
        <ErrorBanner message={error} onRetry={load} />
      </div>
    );
  }

  return (
    <div>
      <SectionHeader title={t('settings.account_settings')} description={t('settings.account_settings')} />

      <SectionCard title="基本信息">
        <div className="space-y-4">
          <FormField label="用户名" description="你的公开显示名称" required>
            <Input
              placeholder="输入用户名"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
            />
          </FormField>
          <FormField label="邮箱地址" description="用于登录和接收通知" required>
            <Input
              type="email"
              placeholder="your@email.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              leftIcon={<Mail size={14} />}
            />
          </FormField>
          <FormField label="角色" description="账户权限角色">
            <Input value={user?.role || ''} disabled />
          </FormField>
        </div>
      </SectionCard>

      {saveError && <ErrorBanner message={saveError} />}

      <div className="flex justify-end gap-3 mt-6">
        <Button variant="outline" onClick={load} disabled={saving}>{t('common.cancel')}</Button>
        <Button onClick={handleSave} loading={saving} disabled={saving}>
          {saveOk ? t('common.saved') : t('settings.save_changes')}
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
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
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
      setError(e instanceof Error ? e.message : 'Failed to load settings');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const updateFlag = async (key: 'autonomous_agent_mode' | 'token_throttle_mcp_enabled', value: boolean) => {
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
      setTimeout(() => setSaveOk(false), 1500);
    } catch (e) {
      setSaveError(e instanceof Error ? e.message : 'Failed to update setting');
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div>
        <SectionHeader title={t('settings.api_settings')} description={t('settings.api_settings')} />
        <SkeletonList count={2} />
      </div>
    );
  }

  if (error) {
    return (
      <div>
        <SectionHeader title={t('settings.api_settings')} description={t('settings.api_settings')} />
        <ErrorBanner message={error} onRetry={load} />
      </div>
    );
  }

  return (
    <div>
      <SectionHeader title={t('settings.api_settings')} description={t('settings.api_settings')} />

      <SectionCard title="执行模式" description="控制智能体的运行行为">
        <div className="space-y-4">
          <Switch
            label="自主智能体模式"
            description="开启后智能体可自主决策执行多步任务"
            checked={settings?.autonomous_agent_mode ?? false}
            onChange={(v) => updateFlag('autonomous_agent_mode', v)}
            disabled={saving}
          />
          <Switch
            label="MCP Token 节流"
            description="对 MCP 工具调用进行 Token 限流，防止超额消耗"
            checked={settings?.token_throttle_mcp_enabled ?? false}
            onChange={(v) => updateFlag('token_throttle_mcp_enabled', v)}
            disabled={saving}
          />
        </div>
      </SectionCard>

      <SectionCard title="MCP 状态" description="当前 MCP 进程的连接状态">
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
              {settings?.mcp_ready ? '已就绪' : '未就绪'}
            </div>
            <div className="text-xs text-[var(--color-text-muted)]">{settings?.mcp_status}</div>
          </div>
          <Badge variant={settings?.mcp_ready ? 'success' : 'secondary'} className="ml-auto">
            {settings?.mcp_status}
          </Badge>
        </div>
      </SectionCard>

      {saveError && <ErrorBanner message={saveError} onRetry={load} />}

      <div className="flex justify-end gap-3 mt-6">
        <Button variant="outline" onClick={load} disabled={saving}>{t('common.refresh')}</Button>
        <Button onClick={load} loading={saving} disabled={saving}>
          {saveOk ? t('common.saved') : t('common.refresh')}
        </Button>
      </div>
    </div>
  );
}

interface AuthApiKey {
  id: string;
  name: string;
  owner: string;
  scopes: string[];
  is_active: boolean;
  expires_at: string | null;
  last_used_at: string | null;
  created_at: string | null;
}

interface CreatedKey extends AuthApiKey {
  raw_key: string;
}

function ApiKeysSection() {
  const { t } = useI18n();
  const [keys, setKeys] = useState<AuthApiKey[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ name: '', owner: '', scopes: 'read,write', ttl_days: '' });
  const [creating, setCreating] = useState(false);
  const [newlyCreated, setNewlyCreated] = useState<CreatedKey | null>(null);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [revokingId, setRevokingId] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.listAuthApiKeys();
      const list = (data?.keys ?? []) as AuthApiKey[];
      setKeys(list);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load API keys');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const handleCreate = async () => {
    setCreating(true);
    setError(null);
    try {
      const scopes = form.scopes.split(',').map(s => s.trim()).filter(Boolean);
      const ttl = form.ttl_days ? Number(form.ttl_days) : null;
      const created = await api.createAuthApiKey({
        name: form.name,
        owner: form.owner,
        scopes,
        ttl_days: ttl,
      });
      setNewlyCreated(created as CreatedKey);
      setShowForm(false);
      setForm({ name: '', owner: '', scopes: 'read,write', ttl_days: '' });
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to create API key');
    } finally {
      setCreating(false);
    }
  };

  const handleRevoke = async (id: string) => {
    setRevokingId(id);
    setError(null);
    try {
      await api.revokeAuthApiKey(id);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to revoke key');
    } finally {
      setRevokingId(null);
    }
  };

  const handleCopy = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const formatDate = (s: string | null) => {
    if (!s) return '-';
    try {
      return new Date(s).toLocaleString();
    } catch {
      return s;
    }
  };

  return (
    <div>
      <SectionHeader title={t('navigation.api_keys')} description={t('navigation.api_keys')} />

      <div className="flex items-center justify-between mb-4">
        <p className="text-sm text-[var(--color-text-muted)]">共 {keys.length} 个密钥</p>
        <Button size="sm" icon={<Plus size={14} />} onClick={() => setShowForm(!showForm)}>
          创建新密钥
        </Button>
      </div>

      {error && <ErrorBanner message={error} onRetry={load} />}

      {newlyCreated && (
        <Card variant="default" padding="md" className="mb-4 border-[var(--color-success)]/30 bg-[var(--color-success-subtle)]">
          <div className="flex items-start gap-3">
            <Check size={16} className="text-[var(--color-success)] shrink-0 mt-0.5" />
            <div className="flex-1 min-w-0">
              <h4 className="text-sm font-medium text-[var(--color-success)]">密钥已创建</h4>
              <p className="text-xs text-[var(--color-text-muted)] mt-1">
                请立即复制保存，此密钥仅显示一次：
              </p>
              <div className="flex items-center gap-2 mt-2">
                <code className="text-xs font-mono text-[var(--color-text-primary)] bg-[var(--color-bg-surface-2)] px-2 py-0.5 rounded break-all">
                  {newlyCreated.raw_key}
                </code>
                <button
                  onClick={() => handleCopy(newlyCreated.raw_key, 'new')}
                  className="p-1 rounded hover:bg-[var(--color-bg-surface-2)] text-[var(--color-text-muted)] shrink-0"
                >
                  {copiedId === 'new' ? <Check size={12} className="text-[var(--color-success)]" /> : <Copy size={12} />}
                </button>
              </div>
              <Button size="sm" variant="ghost" className="mt-2" onClick={() => setNewlyCreated(null)}>
                {t('common.close')}
              </Button>
            </div>
          </div>
        </Card>
      )}

      {showForm && (
        <Card variant="default" padding="md" className="mb-4">
          <h3 className="text-sm font-semibold text-[var(--color-text-primary)] mb-3">创建新密钥</h3>
          <div className="space-y-3">
            <FormField label="名称" required>
              <Input placeholder="例如：生产环境" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
            </FormField>
            <FormField label="所有者" required>
              <Input placeholder="owner 标识" value={form.owner} onChange={(e) => setForm({ ...form, owner: e.target.value })} />
            </FormField>
            <FormField label="权限范围" description="逗号分隔，如 read,write">
              <Input placeholder="read,write" value={form.scopes} onChange={(e) => setForm({ ...form, scopes: e.target.value })} />
            </FormField>
            <FormField label="有效期（天）" description="留空表示永久">
              <Input
                type="number"
                placeholder="例如：30"
                value={form.ttl_days}
                onChange={(e) => setForm({ ...form, ttl_days: e.target.value })}
              />
            </FormField>
            <div className="flex items-center gap-2">
              <Button size="sm" onClick={handleCreate} loading={creating} disabled={!form.name || !form.owner || creating}>
                创建
              </Button>
              <Button size="sm" variant="ghost" onClick={() => setShowForm(false)}>
                {t('common.cancel')}
              </Button>
            </div>
          </div>
        </Card>
      )}

      {loading && <SkeletonList count={2} />}

      {!loading && keys.length === 0 && !showForm && (
        <Card variant="default" padding="md">
          <div className="text-center py-6">
            <Key size={28} className="text-[var(--color-text-muted)] mx-auto mb-2" />
            <p className="text-sm text-[var(--color-text-muted)]">暂无 API 密钥</p>
            <Button size="sm" className="mt-3" icon={<Plus size={14} />} onClick={() => setShowForm(true)}>
              创建第一个密钥
            </Button>
          </div>
        </Card>
      )}

      {!loading && keys.length > 0 && (
        <div className="space-y-3">
          {keys.map(item => (
            <Card key={item.id} variant="default" padding="md" className="hover:border-[var(--color-border-default)] transition-colors">
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1 flex-wrap">
                    <h4 className="text-sm font-medium text-[var(--color-text-primary)]">{item.name || '(未命名)'}</h4>
                    <Badge variant={item.is_active ? 'success' : 'destructive'} size="xs">
                      {item.is_active ? 'active' : 'revoked'}
                    </Badge>
                    <div className="flex gap-1 flex-wrap">
                      {item.scopes.map(p => (
                        <Badge key={p} variant="secondary" size="xs">{p}</Badge>
                      ))}
                    </div>
                  </div>
                  <div className="text-xs text-[var(--color-text-muted)] mb-1">所有者: {item.owner || '-'}</div>
                  <div className="flex items-center gap-4 text-[10px] text-[var(--color-text-muted)] flex-wrap">
                    <span>创建于 {formatDate(item.created_at)}</span>
                    <span>最后使用: {formatDate(item.last_used_at)}</span>
                    <span>过期: {formatDate(item.expires_at)}</span>
                  </div>
                </div>
                <button
                  onClick={() => handleRevoke(item.id)}
                  disabled={!item.is_active || revokingId === item.id}
                  className="p-2 rounded-lg hover:bg-[var(--color-error-subtle)] text-[var(--color-text-muted)] hover:text-[var(--color-error)] transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
                  title={item.is_active ? '撤销密钥' : '已撤销'}
                >
                  {revokingId === item.id ? <Loader2 size={14} className="animate-spin" /> : <Trash2 size={14} />}
                </button>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}

interface NotificationSettings {
  email_system: boolean;
  email_task_done: boolean;
  email_weekly: boolean;
  email_marketing: boolean;
  webhook_url: string;
  webhook_task_done: boolean;
  webhook_task_failed: boolean;
}

const DEFAULT_NOTIFICATIONS: NotificationSettings = {
  email_system: false,
  email_task_done: false,
  email_weekly: false,
  email_marketing: false,
  webhook_url: '',
  webhook_task_done: false,
  webhook_task_failed: false,
};

function NotificationsSection() {
  const { t } = useI18n();
  const [settings, setSettings] = useState<NotificationSettings>(DEFAULT_NOTIFICATIONS);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [saveOk, setSaveOk] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getSettings();
      const n = (data.notifications ?? {}) as Partial<NotificationSettings>;
      setSettings({
        email_system: n.email_system ?? false,
        email_task_done: n.email_task_done ?? false,
        email_weekly: n.email_weekly ?? false,
        email_marketing: n.email_marketing ?? false,
        webhook_url: n.webhook_url ?? '',
        webhook_task_done: n.webhook_task_done ?? false,
        webhook_task_failed: n.webhook_task_failed ?? false,
      });
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load notification settings');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const handleSave = async () => {
    setSaving(true);
    setSaveError(null);
    setSaveOk(false);
    try {
      await api.updateSettings({ notifications: settings });
      setSaveOk(true);
      setTimeout(() => setSaveOk(false), 2000);
    } catch (e) {
      setSaveError(e instanceof Error ? e.message : 'Failed to save notification settings');
    } finally {
      setSaving(false);
    }
  };

  const toggle = (key: keyof NotificationSettings, value: boolean) => {
    setSettings(prev => ({ ...prev, [key]: value }));
  };

  if (loading) {
    return (
      <div>
        <SectionHeader title={t('settings.notifications')} description={t('settings.notifications')} />
        <SkeletonList count={2} />
      </div>
    );
  }

  if (error) {
    return (
      <div>
        <SectionHeader title={t('settings.notifications')} description={t('settings.notifications')} />
        <ErrorBanner message={error} onRetry={load} />
      </div>
    );
  }

  return (
    <div>
      <SectionHeader title={t('settings.notifications')} description={t('settings.notifications')} />

      <SectionCard title="邮件通知" description="通过邮件接收重要更新">
        <div className="space-y-4">
          <Switch label="系统通知" description="接收系统更新、维护公告和安全警报" checked={settings.email_system} onChange={(v) => toggle('email_system', v)} disabled={saving} />
          <Switch label="任务完成" description="当 Agent 任务执行完成时通知我" checked={settings.email_task_done} onChange={(v) => toggle('email_task_done', v)} disabled={saving} />
          <Switch label="周报摘要" description="每周一发送使用统计和摘要" checked={settings.email_weekly} onChange={(v) => toggle('email_weekly', v)} disabled={saving} />
          <Switch label="营销邮件" description="接收产品更新和优惠信息" checked={settings.email_marketing} onChange={(v) => toggle('email_marketing', v)} disabled={saving} />
        </div>
      </SectionCard>

      <SectionCard title="Webhook" description="通过 Webhook 将事件推送到外部系统">
        <div className="space-y-4">
          <FormField label="Webhook URL" description="接收事件推送的 URL 地址">
            <Input
              placeholder="https://your-webhook-url.com/endpoint"
              value={settings.webhook_url}
              onChange={(e) => setSettings(prev => ({ ...prev, webhook_url: e.target.value }))}
              disabled={saving}
            />
          </FormField>
          <FormField label="触发事件">
            <div className="space-y-2 mt-1">
              <Switch label="任务完成" description="Agent 任务执行结束时触发" checked={settings.webhook_task_done} onChange={(v) => toggle('webhook_task_done', v)} disabled={saving} />
              <Switch label="任务失败" description="Agent 任务执行失败时触发" checked={settings.webhook_task_failed} onChange={(v) => toggle('webhook_task_failed', v)} disabled={saving} />
            </div>
          </FormField>
        </div>
      </SectionCard>

      {saveError && <ErrorBanner message={saveError} />}

      <div className="flex justify-end gap-3 mt-6">
        <Button variant="outline" onClick={load} disabled={saving}>{t('common.reset')}</Button>
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
  const [error, setError] = useState<string | null>(null);

  const [showPwdForm, setShowPwdForm] = useState(false);
  const [pwd, setPwd] = useState({ current: '', next: '', confirm: '' });
  const [pwdSaving, setPwdSaving] = useState(false);
  const [pwdError, setPwdError] = useState<string | null>(null);
  const [pwdOk, setPwdOk] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getAuthHealth();
      setAuthHealth(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load security status');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const handleChangePassword = async () => {
    setPwdError(null);
    if (pwd.next !== pwd.confirm) {
      setPwdError('两次输入的新密码不一致');
      return;
    }
    if (pwd.next.length < 6) {
      setPwdError('新密码至少 6 位');
      return;
    }
    setPwdSaving(true);
    try {
      await api.changePassword(pwd.current, pwd.next);
      setPwd({ current: '', next: '', confirm: '' });
      setShowPwdForm(false);
      setPwdOk(true);
      setTimeout(() => setPwdOk(false), 2500);
    } catch (e) {
      setPwdError(e instanceof Error ? e.message : 'Failed to change password');
    } finally {
      setPwdSaving(false);
    }
  };

  if (loading) {
    return (
      <div>
        <SectionHeader title={t('settings.security')} description={t('settings.security')} />
        <SkeletonList count={2} />
      </div>
    );
  }

  if (error) {
    return (
      <div>
        <SectionHeader title={t('settings.security')} description={t('settings.security')} />
        <ErrorBanner message={error} onRetry={load} />
      </div>
    );
  }

  const authEnabled = authHealth?.authentication_enabled;

  return (
    <div>
      <SectionHeader title={t('settings.security')} description={t('settings.security')} />

      <SectionCard title="认证状态" description="当前账户的认证配置">
        <div className="flex items-center gap-3">
          <div className={cn(
            'p-2 rounded-xl',
            authEnabled ? 'bg-[var(--color-success-subtle)]' : 'bg-[var(--color-bg-surface-2)]'
          )}>
            <Shield size={20} className={authEnabled ? 'text-[var(--color-success)]' : 'text-[var(--color-text-muted)]'} />
          </div>
          <div>
            <div className="text-sm font-medium text-[var(--color-text-primary)]">
              {authEnabled ? '认证已启用' : '认证未启用'}
            </div>
            <div className="text-xs text-[var(--color-text-muted)]">
              {authHealth?.auth_method && authHealth.auth_method !== 'disabled'
                ? `认证方式: ${authHealth.auth_method}`
                : '当前未启用认证'}
            </div>
          </div>
          <Badge variant={authEnabled ? 'success' : 'warning'} className="ml-auto">
            {authEnabled ? 'enabled' : 'disabled'}
          </Badge>
        </div>
      </SectionCard>

      <SectionCard title="修改密码" description="定期更换密码以保障账户安全">
        {!showPwdForm ? (
          <div className="flex items-center justify-between">
            <div>
              <div className="text-sm font-medium text-[var(--color-text-primary)]">
                {pwdOk ? '密码已成功修改' : '密码'}
              </div>
              <div className="text-xs text-[var(--color-text-muted)] mt-0.5">
                {pwdOk ? '请使用新密码重新登录' : '点击右侧按钮修改当前账户密码'}
              </div>
            </div>
            <Button size="sm" variant="outline" onClick={() => setShowPwdForm(true)}>修改密码</Button>
          </div>
        ) : (
          <div className="space-y-3">
            <FormField label="当前密码" required>
              <Input type="password" placeholder="输入当前密码" value={pwd.current} onChange={(e) => setPwd({ ...pwd, current: e.target.value })} />
            </FormField>
            <FormField label="新密码" required>
              <Input type="password" placeholder="输入新密码（至少 6 位）" value={pwd.next} onChange={(e) => setPwd({ ...pwd, next: e.target.value })} />
            </FormField>
            <FormField label="确认新密码" required>
              <Input type="password" placeholder="再次输入新密码" value={pwd.confirm} onChange={(e) => setPwd({ ...pwd, confirm: e.target.value })} />
            </FormField>
            {pwdError && <p className="text-xs text-[var(--color-error)]">{pwdError}</p>}
            <div className="flex items-center gap-2">
              <Button size="sm" onClick={handleChangePassword} loading={pwdSaving} disabled={pwdSaving}>
                确认修改
              </Button>
              <Button size="sm" variant="ghost" onClick={() => { setShowPwdForm(false); setPwdError(null); }}>
                {t('common.cancel')}
              </Button>
            </div>
          </div>
        )}
      </SectionCard>
    </div>
  );
}

function AboutSection() {
  const { t } = useI18n();
  return (
    <div>
      <SectionHeader title={t('settings.advanced')} description={t('settings.advanced')} />

      <Card variant="default" padding="none" className="mb-4 overflow-hidden">
        <div className="p-6 bg-gradient-to-br from-[var(--color-accent-subtle)] to-transparent">
          <div className="flex items-center gap-4">
            <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-[var(--color-accent)] to-purple-500 flex items-center justify-center">
              <Sparkles size={24} className="text-white" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-[var(--color-text-primary)]">Climber</h2>
              <p className="text-sm text-[var(--color-text-muted)]">版本 1.0.0</p>
            </div>
          </div>
        </div>
        <div className="p-5 space-y-3">
          <div className="flex items-center justify-between py-2">
            <span className="text-sm text-[var(--color-text-secondary)]">版本</span>
            <span className="text-sm font-mono text-[var(--color-text-primary)]">v1.0.0</span>
          </div>
        </div>
      </Card>

      <SectionCard title="相关链接">
        <div className="space-y-1">
          {[
            { label: '帮助文档', icon: MessageSquare },
            { label: 'API 文档', icon: Database },
            { label: 'GitHub 仓库', icon: ExternalLink },
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
