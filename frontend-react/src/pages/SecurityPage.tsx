import { useCallback, useEffect, useState } from 'react';
import { Lock, RefreshCw, Save, Plus, Trash2, ShieldAlert } from 'lucide-react';
import {
  api,
  type SecurityQuotasOut,
  type SecurityFsConfigOut,
  type NetworkAllowlistOut,
} from '../api';
import { PageHeader } from '../components/ui/PageHeader';
import { Card, CardContent } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Badge } from '../components/ui/Badge';
import { Input } from '../components/ui/Input';
import { Switch } from '../components/ui/Switch';
import { FormField } from '../components/ui/Field';
import { SkeletonList } from '../components/ui/Skeleton';
import { useI18n } from '../i18n';

function joinLines(values: string[]): string {
  return values.join('\n');
}

function splitLines(raw: string): string[] {
  return raw.split('\n').map(line => line.trim()).filter(Boolean);
}

function FieldError({ message }: { message: string | null }) {
  if (!message) return null;
  return <p role="alert" className="mt-2 text-xs text-[var(--color-error)]">{message}</p>;
}

function QuotasCard({ data, onSaved }: { data: SecurityQuotasOut | null; onSaved: () => void }) {
  const { t } = useI18n();
  const [agentId, setAgentId] = useState('');
  const [cpuCores, setCpuCores] = useState('1');
  const [memoryMb, setMemoryMb] = useState('512');
  const [diskMb, setDiskMb] = useState('1024');
  const [networkKbps, setNetworkKbps] = useState('10000');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  const handleSave = async () => {
    if (!agentId.trim() || busy) return;
    setBusy(true);
    setError(null);
    setSaved(false);
    try {
      await api.updateSecurityQuota({
        agent_id: agentId.trim(),
        cpu_cores: Number.parseFloat(cpuCores) || 1,
        memory_mb: Number.parseInt(memoryMb, 10) || 512,
        disk_mb: Number.parseInt(diskMb, 10) || 1024,
        network_kbps: Number.parseInt(networkKbps, 10) || 10000,
      });
      setSaved(true);
      onSaved();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };

  const quotas = data ? Object.entries(data.quotas) : [];

  return (
    <Card variant="default" padding="none">
      <div className="px-4 py-4 border-b border-[var(--color-border-subtle)]">
        <h3 className="text-sm font-semibold text-[var(--color-text-primary)]">{t('security_policy.quotas.title', { defaultValue: 'Resource quotas' })}</h3>
        <p className="text-xs text-[var(--color-text-muted)] mt-1">{t('security_policy.quotas.desc', { defaultValue: 'Per-agent CPU, memory, disk and network limits.' })}</p>
      </div>
      <CardContent className="p-4 space-y-4">
        {quotas.length > 0 && (
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="text-left text-[var(--color-text-muted)] border-b border-[var(--color-border-subtle)]">
                  <th className="py-2 pr-3 font-medium">{t('security_policy.quotas.agent', { defaultValue: 'Agent' })}</th>
                  <th className="py-2 pr-3 font-medium">{t('security_policy.quotas.cpu', { defaultValue: 'CPU cores' })}</th>
                  <th className="py-2 pr-3 font-medium">{t('security_policy.quotas.memory', { defaultValue: 'Memory (MB)' })}</th>
                  <th className="py-2 pr-3 font-medium">{t('security_policy.quotas.disk', { defaultValue: 'Disk (MB)' })}</th>
                  <th className="py-2 font-medium">{t('security_policy.quotas.network', { defaultValue: 'Network (kbps)' })}</th>
                </tr>
              </thead>
              <tbody>
                {quotas.map(([id, quota]) => (
                  <tr key={id} className="border-b border-[var(--color-border-subtle)] last:border-0 text-[var(--color-text-secondary)]">
                    <td className="py-2 pr-3 font-mono">{id}</td>
                    <td className="py-2 pr-3 tabular-nums">{quota.cpu_cores}</td>
                    <td className="py-2 pr-3 tabular-nums">{quota.memory_mb}</td>
                    <td className="py-2 pr-3 tabular-nums">{quota.disk_mb}</td>
                    <td className="py-2 tabular-nums">{quota.network_kbps}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <div className="border-t border-[var(--color-border-subtle)] pt-4 space-y-3">
          <h4 className="text-xs font-semibold text-[var(--color-text-secondary)]">{t('security_policy.quotas.edit_title', { defaultValue: 'Set quota' })}</h4>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <FormField label={t('security_policy.quotas.agent', { defaultValue: 'Agent' })} required>
              <Input value={agentId} onChange={(e) => setAgentId(e.target.value)} placeholder="agent-id" />
            </FormField>
            <FormField label={t('security_policy.quotas.cpu', { defaultValue: 'CPU cores' })}>
              <Input value={cpuCores} onChange={(e) => setCpuCores(e.target.value)} inputMode="decimal" />
            </FormField>
            <FormField label={t('security_policy.quotas.memory', { defaultValue: 'Memory (MB)' })}>
              <Input value={memoryMb} onChange={(e) => setMemoryMb(e.target.value)} inputMode="numeric" />
            </FormField>
            <FormField label={t('security_policy.quotas.disk', { defaultValue: 'Disk (MB)' })}>
              <Input value={diskMb} onChange={(e) => setDiskMb(e.target.value)} inputMode="numeric" />
            </FormField>
            <FormField label={t('security_policy.quotas.network', { defaultValue: 'Network (kbps)' })}>
              <Input value={networkKbps} onChange={(e) => setNetworkKbps(e.target.value)} inputMode="numeric" />
            </FormField>
          </div>
          <div className="flex items-center gap-2">
            <Button size="sm" onClick={() => void handleSave()} loading={busy} disabled={!agentId.trim()} icon={<Save size={14} />}>
              {t('security_policy.save', { defaultValue: 'Save' })}
            </Button>
            {saved && <span className="text-xs text-[var(--color-success)]">{t('security_policy.saved', { defaultValue: 'Saved.' })}</span>}
          </div>
          <FieldError message={error} />
        </div>
      </CardContent>
    </Card>
  );
}

function FsConfigCard({ config, onSaved }: { config: SecurityFsConfigOut | null; onSaved: () => void }) {
  const { t } = useI18n();
  const [allowedPaths, setAllowedPaths] = useState('');
  const [blockedPaths, setBlockedPaths] = useState('');
  const [readOnlyPaths, setReadOnlyPaths] = useState('');
  const [maxFileSizeMb, setMaxFileSizeMb] = useState('50');
  const [allowedExtensions, setAllowedExtensions] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (!config) return;
    setAllowedPaths(joinLines(config.allowed_paths));
    setBlockedPaths(joinLines(config.blocked_paths));
    setReadOnlyPaths(joinLines(config.read_only_paths));
    setMaxFileSizeMb(String(config.max_file_size_mb));
    setAllowedExtensions(joinLines(config.allowed_extensions));
  }, [config]);

  const handleSave = async () => {
    if (busy) return;
    setBusy(true);
    setError(null);
    setSaved(false);
    try {
      await api.updateSecurityFsConfig({
        allowed_paths: splitLines(allowedPaths),
        blocked_paths: splitLines(blockedPaths),
        read_only_paths: splitLines(readOnlyPaths),
        max_file_size_mb: Number.parseInt(maxFileSizeMb, 10) || 50,
        allowed_extensions: splitLines(allowedExtensions),
      });
      setSaved(true);
      onSaved();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };

  const textareaClass = 'w-full rounded-[var(--radius-md)] border border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-1)] px-3 py-2 font-mono text-xs text-[var(--color-text-primary)]';

  return (
    <Card variant="default" padding="none">
      <div className="px-4 py-4 border-b border-[var(--color-border-subtle)]">
        <h3 className="text-sm font-semibold text-[var(--color-text-primary)]">{t('security_policy.fs.title', { defaultValue: 'File system isolation' })}</h3>
        <p className="text-xs text-[var(--color-text-muted)] mt-1">{t('security_policy.fs.desc', { defaultValue: 'Allowed, blocked and read-only paths; one entry per line.' })}</p>
      </div>
      <CardContent className="p-4 space-y-3">
        <FormField label={t('security_policy.fs.allowed_paths', { defaultValue: 'Allowed paths' })}>
          <textarea value={allowedPaths} onChange={(e) => setAllowedPaths(e.target.value)} rows={3} aria-label={t('security_policy.fs.allowed_paths', { defaultValue: 'Allowed paths' })} className={textareaClass} />
        </FormField>
        <FormField label={t('security_policy.fs.blocked_paths', { defaultValue: 'Blocked paths' })}>
          <textarea value={blockedPaths} onChange={(e) => setBlockedPaths(e.target.value)} rows={3} aria-label={t('security_policy.fs.blocked_paths', { defaultValue: 'Blocked paths' })} className={textareaClass} />
        </FormField>
        <FormField label={t('security_policy.fs.read_only_paths', { defaultValue: 'Read-only paths' })}>
          <textarea value={readOnlyPaths} onChange={(e) => setReadOnlyPaths(e.target.value)} rows={2} aria-label={t('security_policy.fs.read_only_paths', { defaultValue: 'Read-only paths' })} className={textareaClass} />
        </FormField>
        <FormField label={t('security_policy.fs.allowed_extensions', { defaultValue: 'Allowed extensions' })}>
          <textarea value={allowedExtensions} onChange={(e) => setAllowedExtensions(e.target.value)} rows={2} aria-label={t('security_policy.fs.allowed_extensions', { defaultValue: 'Allowed extensions' })} className={textareaClass} />
        </FormField>
        <FormField label={t('security_policy.fs.max_file_size', { defaultValue: 'Max file size (MB)' })}>
          <Input value={maxFileSizeMb} onChange={(e) => setMaxFileSizeMb(e.target.value)} inputMode="numeric" className="sm:w-40" />
        </FormField>
        <div className="flex items-center gap-2">
          <Button size="sm" onClick={() => void handleSave()} loading={busy} icon={<Save size={14} />}>
            {t('security_policy.save', { defaultValue: 'Save' })}
          </Button>
          {saved && <span className="text-xs text-[var(--color-success)]">{t('security_policy.saved', { defaultValue: 'Saved.' })}</span>}
        </div>
        <FieldError message={error} />
      </CardContent>
    </Card>
  );
}

function AllowlistCard({ data, onChanged }: { data: NetworkAllowlistOut | null; onChanged: () => void }) {
  const { t } = useI18n();
  const [newDomain, setNewDomain] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const run = useCallback(async (action: () => Promise<unknown>) => {
    setBusy(true);
    setError(null);
    try {
      await action();
      onChanged();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }, [onChanged]);

  const handleToggleStrict = (checked: boolean) => {
    void run(() => api.updateNetworkAllowlistPolicy(checked));
  };

  const handleAdd = () => {
    const domain = newDomain.trim();
    if (!domain) return;
    void run(async () => {
      await api.addNetworkAllowlistDomain(domain);
      setNewDomain('');
    });
  };

  const handleRemove = (domain: string) => {
    void run(() => api.removeNetworkAllowlistDomain(domain));
  };

  return (
    <Card variant="default" padding="none">
      <div className="px-4 py-4 border-b border-[var(--color-border-subtle)] flex items-center justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold text-[var(--color-text-primary)]">{t('security_policy.allowlist.title', { defaultValue: 'Network allowlist' })}</h3>
          <p className="text-xs text-[var(--color-text-muted)] mt-1">{t('security_policy.allowlist.desc', { defaultValue: 'Domains agents may reach; strict mode rejects everything else.' })}</p>
        </div>
        {data && (
          <Badge variant={data.strict_domain_mode ? 'warning' : 'secondary'}>
            {data.strict_domain_mode
              ? t('security_policy.allowlist.strict', { defaultValue: 'Strict' })
              : t('security_policy.allowlist.permissive', { defaultValue: 'Permissive' })}
          </Badge>
        )}
      </div>
      <CardContent className="p-4 space-y-4">
        <Switch
          checked={data?.strict_domain_mode ?? false}
          onChange={handleToggleStrict}
          disabled={busy || !data}
          label={t('security_policy.allowlist.strict_mode', { defaultValue: 'Strict domain mode' })}
          description={t('security_policy.allowlist.strict_mode_desc', { defaultValue: 'When enabled, only allowlisted domains are reachable.' })}
        />
        <div className="flex flex-col sm:flex-row gap-2">
          <Input
            value={newDomain}
            onChange={(e) => setNewDomain(e.target.value)}
            placeholder="example.com"
            aria-label={t('security_policy.allowlist.domain_placeholder', { defaultValue: 'Domain' })}
            className="flex-1"
            onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); handleAdd(); } }}
          />
          <Button size="sm" onClick={handleAdd} loading={busy} disabled={!newDomain.trim()} icon={<Plus size={14} />}>
            {t('security_policy.allowlist.add', { defaultValue: 'Add domain' })}
          </Button>
        </div>
        {data && data.allowed_domains.length > 0 ? (
          <ul className="divide-y divide-[var(--color-border-subtle)] rounded-[var(--radius-md)] border border-[var(--color-border-subtle)]">
            {data.allowed_domains.map(domain => (
              <li key={domain} className="flex items-center justify-between gap-3 px-3 py-2">
                <span className="font-mono text-xs text-[var(--color-text-secondary)] break-all">{domain}</span>
                <Button
                  size="sm"
                  variant="ghost"
                  disabled={busy}
                  onClick={() => handleRemove(domain)}
                  aria-label={t('security_policy.allowlist.remove', { defaultValue: 'Remove domain', domain })}
                  icon={<Trash2 size={14} className="text-[var(--color-error)]" />}
                />
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-xs text-[var(--color-text-muted)]">{t('security_policy.allowlist.empty', { defaultValue: 'No domains allowlisted yet.' })}</p>
        )}
        <FieldError message={error} />
      </CardContent>
    </Card>
  );
}

export function SecurityPage() {
  const { t } = useI18n();
  const [isAdmin, setIsAdmin] = useState<boolean | null>(null);
  const [quotas, setQuotas] = useState<SecurityQuotasOut | null>(null);
  const [fsConfig, setFsConfig] = useState<SecurityFsConfigOut | null>(null);
  const [allowlist, setAllowlist] = useState<NetworkAllowlistOut | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const user = await api.getCurrentUser();
      const admin = user?.role === 'admin' || (user?.scopes || []).includes('admin');
      setIsAdmin(admin);
      if (!admin) return;
      const [quotasRes, fsRes, allowlistRes] = await Promise.allSettled([
        api.getSecurityQuotas(),
        api.getSecurityFsConfig(),
        api.getNetworkAllowlist(),
      ]);
      setQuotas(quotasRes.status === 'fulfilled' ? quotasRes.value : null);
      setFsConfig(fsRes.status === 'fulfilled' ? fsRes.value : null);
      setAllowlist(allowlistRes.status === 'fulfilled' ? allowlistRes.value : null);
      const firstError = [quotasRes, fsRes, allowlistRes].find(r => r.status === 'rejected');
      if (firstError && firstError.status === 'rejected') {
        const reason = firstError.reason;
        setError(reason instanceof Error ? reason.message : String(reason));
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void load(); }, [load]);

  return (
    <div className="h-full overflow-y-auto page-transition">
      <div className="p-4 md:p-6 max-w-4xl mx-auto">
        <PageHeader
          title={t('security_policy.title', { defaultValue: 'Security policy' })}
          icon={<Lock size={20} />}
          className="border-b border-[var(--color-border-subtle)] pb-[var(--space-4)] [&_h1]:text-[length:var(--text-base)] [&_h1]:md:text-[length:var(--text-base)] [&_p]:text-[var(--color-text-muted)]"
          actions={
            <Button variant="secondary" size="sm" onClick={() => void load()} loading={loading} icon={<RefreshCw size={14} />}>
              {t('common.refresh')}
            </Button>
          }
        />
        <div className="mt-4 space-y-4">
          {loading ? (
            <div role="status" aria-label={t('common.loading_data')}>
              <SkeletonList count={3} />
            </div>
          ) : isAdmin === false ? (
            <Card variant="default">
              <CardContent className="p-4 flex items-center gap-3">
                <ShieldAlert size={18} className="text-[var(--color-warning)] shrink-0" />
                <p className="text-sm text-[var(--color-text-secondary)]">
                  {t('security_policy.admin_only', { defaultValue: 'Security policy is available to administrators only.' })}
                </p>
              </CardContent>
            </Card>
          ) : (
            <>
              {error && (
                <Card variant="default" className="border-[var(--color-error)]/30">
                  <CardContent className="p-4 flex items-center gap-3">
                    <ShieldAlert size={18} className="text-[var(--color-warning)] shrink-0" />
                    <p role="alert" className="text-sm text-[var(--color-text-secondary)] flex-1">{error}</p>
                    <Button variant="outline" size="sm" onClick={() => void load()}>{t('common.retry')}</Button>
                  </CardContent>
                </Card>
              )}
              <QuotasCard data={quotas} onSaved={() => void load()} />
              <FsConfigCard config={fsConfig} onSaved={() => void load()} />
              <AllowlistCard data={allowlist} onChanged={() => void load()} />
            </>
          )}
        </div>
      </div>
    </div>
  );
}

export default SecurityPage;
