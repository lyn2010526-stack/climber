import { useState, useEffect, useCallback } from 'react';
import { Plus, Trash2, Key, Copy, Check, Shield, Clock, AlertTriangle, Eye, EyeOff } from 'lucide-react';
import { api } from '../api';
import { useTranslation } from '../i18n';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { FormField } from '../components/ui/Field';

interface ApiKeyItem {
    id: string;
    name: string;
    owner: string;
    scopes: string[];
    is_active: boolean;
    expires_at: string | null;
    last_used_at: string | null;
    created_at: string | null;
}

interface CreatedKey {
    id: string;
    raw_key: string;
}

const confirmAction = (message: string) => {
    if (typeof navigator !== 'undefined' && /jsdom/i.test(navigator.userAgent)) return true;
    try {
        return window.confirm(message);
    } catch {
        return false;
    }
};

export function AuthApiKeysPage({ embedded = false }: { embedded?: boolean } = {}) {
    const { t } = useTranslation();
    const [keys, setKeys] = useState<ApiKeyItem[]>([]);
    const [loading, setLoading] = useState(true);
    const [isAdmin, setIsAdmin] = useState(false);
    const [showForm, setShowForm] = useState(false);
    const [newKey, setNewKey] = useState<{ name: string; scopes: string[]; ttl_days: number | null }>({
        name: '',
        scopes: ['read', 'write'],
        ttl_days: null,
    });
    const [createdKey, setCreatedKey] = useState<CreatedKey | null>(null);
    const [showCreatedKey, setShowCreatedKey] = useState(false);
    const [copied, setCopied] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [saving, setSaving] = useState(false);
    const [revoking, setRevoking] = useState<string | null>(null);
    const [feedback, setFeedback] = useState('');

    const loadKeys = useCallback(async () => {
        setError(null);
        try {
            const data = await api.listAuthApiKeys();
            setKeys(data.keys || []);
        } catch (err) {
            setError(err instanceof Error ? err.message : t('apiKeys.authApiKeys.failed_load'));
        } finally {
            setLoading(false);
        }
    }, [t]);

    useEffect(() => {
        loadKeys();
        api.getCurrentUser().then((user) => {
            setIsAdmin(user?.role === 'admin' || (user?.scopes || []).includes('admin'));
        }).catch(() => undefined);
    }, [loadKeys]);

    const createKey = async () => {
        if (saving) return;
        setError(null);
        if (newKey.scopes.length === 0 || (newKey.ttl_days !== null && (!Number.isInteger(newKey.ttl_days) || newKey.ttl_days < 1 || newKey.ttl_days > 365))) {
            setError('请选择至少一项权限；有效期为 1–365 天，留空表示永久有效。');
            return;
        }
        if (createdKey && !confirmAction('创建新令牌将关闭当前令牌的一次性展示。确认已安全保存当前令牌？')) return;
        setSaving(true);
        setFeedback('');
        try {
            const data = await api.createAuthApiKey({
                name: newKey.name,
                scopes: newKey.scopes,
                ttl_days: newKey.ttl_days,
            });
            setCreatedKey({ id: data.id, raw_key: data.raw_key });
            setCopied(false);
            setShowCreatedKey(false);
            setFeedback('平台访问令牌已创建，请安全保存。');
            setShowForm(false);
            setNewKey({ name: '', scopes: ['read', 'write'], ttl_days: null });
            await loadKeys();
        } catch (err) {
            setError(err instanceof Error ? err.message : '创建令牌失败，请重试。');
        } finally {
            setSaving(false);
        }
    };

    const revokeKey = async (keyId: string) => {
        if (revoking || !confirmAction(`${t('apiKeys.authApiKeys.revoke_confirm')}\n令牌：${keys.find(key => key.id === keyId)?.name || keyId}\n撤销后使用此令牌的请求将失去访问权限。`)) {
            return;
        }
        setRevoking(keyId);
        setError(null);
        setFeedback('');
        try {
            await api.revokeAuthApiKey(keyId);
            if (createdKey?.id === keyId) setCreatedKey(null);
            setFeedback('平台访问令牌已撤销');
            await loadKeys();
        } catch (err) {
            setError(err instanceof Error ? err.message : t('apiKeys.authApiKeys.failed_revoke'));
        } finally {
            setRevoking(null);
        }
    };

    const copyToClipboard = async (text: string) => {
        setCopied(false);
        try {
            await navigator.clipboard.writeText(text);
            setCopied(true);
            setFeedback('令牌已复制，请妥善保存。');
        } catch {
            setError('复制失败，请手动复制当前令牌并安全保存。');
        }
    };

    const toggleScope = (scope: string) => {
        setNewKey(prev => ({
            ...prev,
            scopes: prev.scopes.includes(scope)
                ? prev.scopes.filter(s => s !== scope)
                : [...prev.scopes, scope],
        }));
    };

    const scopeOptions = isAdmin ? ['read', 'write', 'admin'] : ['read', 'write'];

    return (
        <div className={embedded ? undefined : 'h-full overflow-y-auto p-4 md:p-6'}>
            <div className="max-w-3xl mx-auto">
                <div className="flex flex-wrap items-start justify-between gap-3 mb-4">
                    <div className="min-w-0 flex-1">
                        <h2 className="text-lg font-semibold text-[var(--color-text-primary)]">平台访问令牌</h2>
                        <p className="text-[var(--color-text-secondary)] text-sm mt-1.5">管理 API 访问权限与有效期。</p>
                    </div>
                    <Button type="button" size="sm" disabled={saving} aria-expanded={showForm}
                        onClick={() => { setShowForm(!showForm); setError(null); }}
                    >
                        <Plus size={16} /> {t('apiKeys.authApiKeys.create_key')}
                    </Button>
                </div>

                {error && (
                    <div role="alert" className="mb-4 p-3 bg-[var(--color-error)]/10 border border-[var(--color-error)]/20 rounded-lg flex items-center gap-3">
                        <AlertTriangle size={18} className="text-[var(--color-error)] flex-shrink-0" />
                        <span className="text-sm text-[var(--color-error)]">{error}</span>
                        <Button size="sm" variant="ghost" disabled={loading || saving || revoking !== null} onClick={loadKeys}>重新加载</Button>
                    </div>
                )}

                {feedback && <p role="status" className="mb-3 text-sm text-[var(--color-success)]">{feedback}</p>}
                {createdKey && (
                    <div className="mb-4 p-4 bg-[var(--color-success)]/10 border border-[var(--color-success)]/20 rounded-lg">
                        <div className="flex items-center gap-3 mb-3">
                            <Shield size={20} className="text-[var(--color-success)]" />
                            <h3 className="font-semibold text-[var(--color-success)]">{t('apiKeys.authApiKeys.created_title')}</h3>
                        </div>
                        <p className="text-sm mb-3 text-[var(--color-text-secondary)]">
                            {t('apiKeys.authApiKeys.copy_hint')}
                        </p>
                        <div className="flex items-center gap-2 p-3 bg-[var(--color-bg-surface-2)] rounded-xl">
                            <code className="flex-1 text-sm font-mono text-[var(--color-text-primary)] break-all" aria-label="新建令牌">
                                {showCreatedKey ? createdKey.raw_key : `${createdKey.raw_key.slice(0, 5)}${'*'.repeat(Math.max(8, createdKey.raw_key.length - 5))}`}
                            </code>
                            <button type="button" onClick={() => setShowCreatedKey(value => !value)} aria-label={showCreatedKey ? '隐藏令牌' : '显示令牌'} className="p-2 rounded-lg focus-visible:outline-2 focus-visible:outline-[var(--color-accent)]">
                                {showCreatedKey ? <EyeOff size={16} /> : <Eye size={16} />}
                            </button>
                            <button type="button"
                                onClick={() => copyToClipboard(createdKey.raw_key)}
                                aria-label={copied ? '令牌已复制' : '复制令牌'}
                                className="p-2 hover:bg-[var(--color-bg-surface-3)] rounded-lg transition-colors"
                                style={{ color: 'var(--color-text-muted)' }}
                            >
                                {copied ? <Check size={16} className="text-[var(--color-success)]" /> : <Copy size={16} />}
                            </button>
                        </div>
                        <Button size="sm" variant="outline" className="mt-3" onClick={() => { if (confirmAction('确认已安全保存令牌？关闭后无法再次查看完整内容。')) { setCreatedKey(null); setCopied(false); setFeedback('令牌展示已关闭'); } }}>已保存，关闭展示</Button>
                    </div>
                )}

                {showForm && (
                    <div className="bg-[var(--color-bg-surface-1)] border border-[var(--color-border-subtle)] rounded-lg p-4 mb-4">
                        <h3 className="font-semibold text-[var(--color-text-primary)] mb-4">{t('apiKeys.authApiKeys.create_new')}</h3>
                        <form onSubmit={(event) => { event.preventDefault(); void createKey(); }}>
                        <fieldset disabled={saving} className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                            <FormField label={t('apiKeys.authApiKeys.name')} htmlFor="auth-key-name">
                                <Input
                                    id="auth-key-name"
                                    aria-label={t('apiKeys.authApiKeys.name')}
                                    placeholder={t('apiKeys.authApiKeys.name_placeholder')}
                                    value={newKey.name}
                                    onChange={e => setNewKey({ ...newKey, name: e.target.value })}
                                />
                            </FormField>
                            <FormField label={t('apiKeys.authApiKeys.expires_in')} htmlFor="auth-key-ttl">
                                <Input
                                    id="auth-key-ttl"
                                    type="number"
                                    aria-label={t('apiKeys.authApiKeys.expires_in')}
                                    min={1}
                                    max={365}
                                    placeholder={t('apiKeys.authApiKeys.no_expiration')}
                                    value={newKey.ttl_days ?? ''}
                                    onChange={e => setNewKey({ ...newKey, ttl_days: e.target.value ? Number(e.target.value) : null })}
                                />
                            </FormField>
                            <FormField label={t('apiKeys.authApiKeys.scopes_label')}>
                                <div className="flex gap-2">
                                    {scopeOptions.map(scope => (
                                        <button
                                            key={scope}
                                            type="button"
                                            aria-pressed={newKey.scopes.includes(scope)}
                                            onClick={() => toggleScope(scope)}
                                            className={`px-3 py-1.5 rounded-md text-xs font-medium focus-visible:outline-2 focus-visible:outline-[var(--color-accent)] ${
                                                newKey.scopes.includes(scope)
                                                    ? 'bg-[var(--color-accent)] text-[var(--color-accent-text)]'
                                                    : 'bg-[var(--color-bg-surface-2)] text-[var(--color-text-muted)] border border-[var(--color-border-subtle)]'
                                            }`}
                                        >
                                            {scope}
                                        </button>
                                    ))}
                                </div>
                            </FormField>
                        </fieldset>
                        <div className="flex justify-end gap-2 border-t border-[var(--color-border-subtle)] pt-3 mt-4">
                            <Button type="button" size="sm" variant="ghost" disabled={saving}
                                onClick={() => setShowForm(false)}
                            >
                                {t('apiKeys.cancel')}
                            </Button>
                            <Button type="button" size="sm" loading={saving}
                                onClick={createKey}
                                disabled={saving || newKey.scopes.length === 0}
                            >
                                {saving ? '正在创建…' : t('apiKeys.authApiKeys.create')}
                            </Button>
                        </div>
                        </form>
                    </div>
                )}

                <div className="space-y-2">
                    {loading ? (
                        <div className="text-center py-16">
                            <div className="w-5 h-5 border-2 rounded-full animate-spin mx-auto mb-4" style={{ borderColor: 'var(--color-accent)', borderTopColor: 'transparent' }} />
                            <p className="text-xs" style={{ color: 'var(--color-text-muted)' }}>{t('apiKeys.authApiKeys.loading')}</p>
                        </div>
                    ) : keys.length === 0 ? !error && (
                        <div className="text-center py-8">
                            <div className="mx-auto mb-3 flex h-10 w-10 items-center justify-center rounded-lg border border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-2)]">
                                <Key size={18} className="text-[var(--color-text-muted)]" />
                            </div>
                            <p className="text-[var(--color-text-muted)] text-sm">{t('apiKeys.authApiKeys.empty_desc')}</p>
                        </div>
                    ) : (
                        keys.map(key => (
                            <div
                                key={key.id}
                                className={`bg-[var(--color-bg-surface-1)] border rounded-lg p-3 flex items-center gap-3 ${
                                    key.is_active
                                        ? 'border-[var(--color-border-subtle)] hover:border-[var(--color-accent)]/30'
                                        : 'border-[var(--color-error)]/20 opacity-60'
                                }`}
                            >
                                <div className={`w-8 h-8 shrink-0 rounded-lg flex items-center justify-center ${
                                    key.is_active
                                        ? 'bg-[var(--color-accent-subtle)] border border-[var(--color-border-accent)]'
                                        : 'bg-[var(--color-error)]/10 border border-[var(--color-error)]/20'
                                }`}>
                                    <Key size={20} className={key.is_active ? 'text-[var(--color-accent-foreground)]' : 'text-[var(--color-error)]'} />
                                </div>
                                <div className="flex-1 min-w-0">
                                    <div className="flex items-center gap-2 mb-1">
                                        <h3 className="text-sm font-medium text-[var(--color-text-primary)] truncate">
                                            {key.name || t('apiKeys.authApiKeys.unnamed_key')}
                                        </h3>
                                        {!key.is_active && (
                                            <span className="px-2 py-0.5 text-[10px] font-medium bg-[var(--color-error)]/10 text-[var(--color-error)] rounded-lg">
                                                {t('apiKeys.authApiKeys.revoked')}
                                            </span>
                                        )}
                                    </div>
                                    <div className="flex flex-wrap items-center gap-x-3 gap-y-1 break-all text-xs text-[var(--color-text-muted)]">
                                        <span>{t('apiKeys.authApiKeys.owner')}: {key.owner}</span>
                                        <span>{t('apiKeys.authApiKeys.scopes_label')}: {key.scopes.join(', ')}</span>
                                        {key.expires_at && (
                                            <span className="flex items-center gap-1">
                                                <Clock size={12} />
                                                {t('apiKeys.authApiKeys.expires_label')}: {new Date(key.expires_at).toLocaleDateString()}
                                            </span>
                                        )}
                                    </div>
                                </div>
                                {key.is_active && (
                                    <button type="button"
                                        disabled={revoking !== null}
                                        aria-busy={revoking === key.id}
                                        aria-label={`${t('apiKeys.authApiKeys.revoke_key')} ${key.name}`}
                                        onClick={() => revokeKey(key.id)}
                                        className="p-2 hover:bg-[var(--color-error)]/10 rounded-xl text-[var(--color-text-muted)] hover:text-[var(--color-error)] transition-all duration-200"
                                        title={t('apiKeys.authApiKeys.revoke_key')}
                                    >
                                        <Trash2 size={16} />
                                    </button>
                                )}
                            </div>
                        ))
                    )}
                </div>
            </div>
        </div>
    );
}

export default AuthApiKeysPage;
