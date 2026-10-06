import { useState, useEffect, useCallback } from 'react';
import { Plus, Trash2, Key, Copy, Check, Shield, Clock, AlertTriangle, Eye, EyeOff } from 'lucide-react';
import { api, type AuthApiKeyCreatedOut, type AuthApiKeyItem } from '../api';
import { useTranslation } from '../i18n';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { FormField } from '../components/ui/Field';

type ApiKeyItem = AuthApiKeyItem;
type CreatedKey = AuthApiKeyCreatedOut;

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
    }, []);

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
            setError(t('apiKeys.authApiKeys.valid_scope_hint'));
            return;
        }
        if (createdKey && !confirmAction(t('apiKeys.authApiKeys.recreate_confirm'))) return;
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
            setFeedback(t('apiKeys.authApiKeys.created_feedback'));
            setShowForm(false);
            setNewKey({ name: '', scopes: ['read', 'write'], ttl_days: null });
            await loadKeys();
        } catch (err) {
            setError(err instanceof Error ? err.message : t('apiKeys.authApiKeys.create_failed'));
        } finally {
            setSaving(false);
        }
    };

    const revokeKey = async (keyId: string) => {
        if (revoking || !confirmAction(t('apiKeys.authApiKeys.revoke_confirm_full', { name: keys.find(key => key.id === keyId)?.name || keyId }))) {
            return;
        }
        setRevoking(keyId);
        setError(null);
        setFeedback('');
        try {
            await api.revokeAuthApiKey(keyId);
            if (createdKey?.id === keyId) setCreatedKey(null);
            setFeedback(t('apiKeys.authApiKeys.revoked_feedback'));
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
            setFeedback(t('apiKeys.authApiKeys.copied_feedback'));
        } catch {
            setError(t('apiKeys.authApiKeys.copy_failed'));
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
                <div className="flex flex-wrap items-start justify-between gap-3 mb-4 border-b border-[var(--color-border-subtle)] pb-[var(--space-4)]">
                    <div className="min-w-0 flex-1">
                        <h2 className="text-[length:var(--text-base)] font-semibold text-[var(--color-text-primary)]">{t('apiKeys.authApiKeys.page_title')}</h2>
                        <p className="text-[length:var(--text-sm)] text-[var(--color-text-muted)] mt-1.5">{t('apiKeys.authApiKeys.page_description')}</p>
                    </div>
                    <Button type="button" size="sm" disabled={saving} aria-expanded={showForm}
                        onClick={() => { setShowForm(!showForm); setError(null); }}
                    >
                        <Plus size={16} /> {t('apiKeys.authApiKeys.create_key')}
                    </Button>
                </div>

                {error && (
                    <div role="alert" className="mb-4 p-3 bg-[var(--color-error)]/10 border border-[var(--color-error)]/20 rounded-[var(--radius-md)] flex items-center gap-3">
                        <AlertTriangle size={18} className="text-[var(--color-error)] flex-shrink-0" />
                        <span className="text-sm text-[var(--color-error)]">{error}</span>
                        <Button size="sm" variant="ghost" disabled={loading || saving || revoking !== null} onClick={loadKeys}>{t('common.refresh')}</Button>
                    </div>
                )}

                {feedback && <p role="status" className="mb-3 text-sm text-[var(--color-success)]">{feedback}</p>}
                {createdKey && (
                    <div className="mb-4 p-4 bg-[var(--color-success)]/10 border border-[var(--color-success)]/20 rounded-[var(--radius-md)]">
                        <div className="flex items-center gap-3 mb-3">
                            <Shield size={20} className="text-[var(--color-success)]" />
                            <h3 className="font-semibold text-[var(--color-success)]">{t('apiKeys.authApiKeys.created_title')}</h3>
                        </div>
                        <p className="text-sm mb-3 text-[var(--color-text-secondary)]">
                            {t('apiKeys.authApiKeys.copy_hint')}
                        </p>
                        <div className="flex items-center gap-2 p-3 bg-[var(--color-bg-surface-2)] rounded-[var(--radius-lg)]">
                            <code className="flex-1 text-sm font-mono text-[var(--color-text-primary)] break-all" aria-label={t('apiKeys.authApiKeys.new_token_aria')}>
                                {showCreatedKey ? createdKey.raw_key : `${createdKey.raw_key.slice(0, 5)}${'*'.repeat(Math.max(8, createdKey.raw_key.length - 5))}`}
                            </code>
                            <button type="button" onClick={() => setShowCreatedKey(value => !value)} aria-label={showCreatedKey ? t('apiKeys.authApiKeys.hide_token') : t('apiKeys.authApiKeys.show_token')} className="p-2 rounded-[var(--radius-md)] focus-visible:outline-2 focus-visible:outline-[var(--color-accent)]">
                                {showCreatedKey ? <EyeOff size={16} /> : <Eye size={16} />}
                            </button>
                            <button type="button"
                                onClick={() => copyToClipboard(createdKey.raw_key)}
                                aria-label={copied ? t('apiKeys.authApiKeys.copied_aria') : t('apiKeys.authApiKeys.copy_token_aria')}
                                className="p-2 hover:bg-[var(--color-bg-surface-3)] rounded-[var(--radius-md)] transition-colors motion-reduce:transition-none"
                                style={{ color: 'var(--color-text-muted)' }}
                            >
                                {copied ? <Check size={16} className="text-[var(--color-success)]" /> : <Copy size={16} />}
                            </button>
                        </div>
                        <Button size="sm" variant="outline" className="mt-3" onClick={() => { if (confirmAction(t('apiKeys.authApiKeys.close_confirm'))) { setCreatedKey(null); setCopied(false); setFeedback(t('apiKeys.authApiKeys.display_closed')); } }}>{t('apiKeys.authApiKeys.saved_close')}</Button>
                    </div>
                )}

                {showForm && (
                    <div className="bg-[var(--color-bg-surface-1)] border border-[var(--color-border-subtle)] rounded-[var(--radius-lg)] p-4 mb-4">
                        <h3 className="text-[length:var(--text-sm)] font-semibold text-[var(--color-text-primary)] mb-4">{t('apiKeys.authApiKeys.create_new')}</h3>
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
                                            className={`px-3 py-1.5 rounded-[var(--radius-md)] text-xs font-medium focus-visible:outline-2 focus-visible:outline-[var(--color-accent)] ${
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
                                {saving ? t('apiKeys.authApiKeys.creating') : t('apiKeys.authApiKeys.create')}
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
                            <div className="mx-auto mb-3 flex h-10 w-10 items-center justify-center rounded-[var(--radius-lg)] border border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-2)]">
                                <Key size={18} className="text-[var(--color-text-muted)]" />
                            </div>
                            <p className="text-[var(--color-text-muted)] text-sm">{t('apiKeys.authApiKeys.empty_desc')}</p>
                        </div>
                    ) : (
                        keys.map(key => (
                            <div
                                key={key.id}
                                className={`bg-[var(--color-bg-surface-1)] border rounded-[var(--radius-lg)] p-3 flex items-center gap-3 ${
                                    key.is_active
                                        ? 'border-[var(--color-border-subtle)] hover:border-[var(--color-accent)]/30'
                                        : 'border-[var(--color-error)]/20 opacity-60'
                                }`}
                            >
                                <div className={`w-8 h-8 shrink-0 rounded-[var(--radius-md)] flex items-center justify-center ${
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
                                            <span className="px-2 py-0.5 text-[length:var(--text-2xs)] font-medium bg-[var(--color-error)]/10 text-[var(--color-error)] rounded-[var(--radius-pill)]">
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
                                        className="p-2 hover:bg-[var(--color-error)]/10 rounded-[var(--radius-md)] text-[var(--color-text-muted)] hover:text-[var(--color-error)] transition-colors motion-reduce:transition-none"
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
