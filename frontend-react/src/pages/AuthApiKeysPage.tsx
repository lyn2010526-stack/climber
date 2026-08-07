import { useState, useEffect, useCallback } from 'react';
import { Plus, Trash2, Key, Copy, Check, Shield, Clock, AlertTriangle } from 'lucide-react';

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

export function AuthApiKeysPage() {
    const [keys, setKeys] = useState<ApiKeyItem[]>([]);
    const [loading, setLoading] = useState(true);
    const [showForm, setShowForm] = useState(false);
    const [newKey, setNewKey] = useState<{ name: string; owner: string; scopes: string[]; ttl_days: number | null }>({
        name: '',
        owner: 'admin',
        scopes: ['read', 'write'],
        ttl_days: null,
    });
    const [createdKey, setCreatedKey] = useState<{ id: string; raw_key: string } | null>(null);
    const [copied, setCopied] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const loadKeys = useCallback(async () => {
        try {
            const token = localStorage.getItem('auth_token');
            const response = await fetch('/api/v1/auth/keys', {
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`,
                },
            });
            if (response.ok) {
                const data = await response.json();
                setKeys(data.keys || []);
            }
        } catch (err) {
            console.error('Failed to load API keys:', err);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        loadKeys();
    }, [loadKeys]);

    const createKey = async () => {
        setError(null);
        try {
            const token = localStorage.getItem('auth_token');
            const response = await fetch('/api/v1/auth/keys', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`,
                },
                body: JSON.stringify(newKey),
            });

            if (!response.ok) {
                const data = await response.json().catch(() => ({}));
                throw new Error(data.detail || 'Failed to create API key');
            }

            const data = await response.json();
            setCreatedKey({ id: data.id, raw_key: data.raw_key });
            setShowForm(false);
            setNewKey({ name: '', owner: 'admin', scopes: ['read', 'write'], ttl_days: null });
            loadKeys();
        } catch (err: any) {
            setError(err.message);
        }
    };

    const revokeKey = async (keyId: string) => {
        if (!confirm('Are you sure you want to revoke this API key? This action cannot be undone.')) {
            return;
        }

        try {
            const token = localStorage.getItem('auth_token');
            await fetch(`/api/v1/auth/keys/${keyId}`, {
                method: 'DELETE',
                headers: {
                    'Authorization': `Bearer ${token}`,
                },
            });
            loadKeys();
        } catch (err) {
            console.error('Failed to revoke key:', err);
        }
    };

    const copyToClipboard = (text: string) => {
        navigator.clipboard.writeText(text);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
    };

    const toggleScope = (scope: string) => {
        setNewKey(prev => ({
            ...prev,
            scopes: prev.scopes.includes(scope)
                ? prev.scopes.filter(s => s !== scope)
                : [...prev.scopes, scope],
        }));
    };

    return (
        <div className="h-full overflow-y-auto p-8">
            <div className="max-w-4xl mx-auto">
                <div className="flex items-center justify-between mb-8">
                    <div>
                        <h2 className="text-2xl font-bold text-[var(--color-text-primary)]">API Keys</h2>
                        <p className="text-[var(--color-text-secondary)] text-sm mt-1.5">
                            Manage programmatic access keys for authentication
                        </p>
                    </div>
                    <button
                        onClick={() => { setShowForm(!showForm); setCreatedKey(null); }}
                        className="flex items-center gap-2 px-5 py-2.5 bg-[var(--color-accent)] hover:bg-[var(--color-accent-hover)] text-white rounded-2xl text-sm font-semibold transition-all duration-200 shadow-lg shadow-[var(--color-accent)]/20 active:scale-[0.97]"
                    >
                        <Plus size={16} /> Create Key
                    </button>
                </div>

                {error && (
                    <div className="mb-6 p-4 bg-[var(--color-error)]/10 border border-[var(--color-error)]/20 rounded-2xl flex items-center gap-3">
                        <AlertTriangle size={18} className="text-[var(--color-error)] flex-shrink-0" />
                        <span className="text-sm text-[var(--color-error)]">{error}</span>
                    </div>
                )}

                {createdKey && (
                    <div className="mb-6 p-6 bg-[var(--color-success)]/10 border border-[var(--color-success)]/20 rounded-2xl">
                        <div className="flex items-center gap-3 mb-3">
                            <Shield size={20} className="text-[var(--color-success)]" />
                            <h3 className="font-semibold text-[var(--color-success)]">API Key Created</h3>
                        </div>
                        <p className="text-sm mb-3 text-[var(--color-text-secondary)]">
                            Copy this key now. You won't be able to see it again!
                        </p>
                        <div className="flex items-center gap-2 p-3 bg-[var(--color-bg-surface-2)] rounded-xl">
                            <code className="flex-1 text-sm font-mono text-[var(--color-text-primary)] break-all">
                                {createdKey.raw_key}
                            </code>
                            <button
                                onClick={() => copyToClipboard(createdKey.raw_key)}
                                className="p-2 hover:bg-[var(--color-bg-surface-3)] rounded-lg transition-colors"
                                style={{ color: 'var(--color-text-muted)' }}
                            >
                                {copied ? <Check size={16} className="text-[var(--color-success)]" /> : <Copy size={16} />}
                            </button>
                        </div>
                    </div>
                )}

                {showForm && (
                    <div className="bg-[var(--color-bg-surface-1)] border border-[var(--color-border-subtle)] rounded-3xl p-6 mb-6">
                        <h3 className="font-semibold text-[var(--color-text-primary)] mb-4">Create New API Key</h3>
                        <div className="grid grid-cols-2 gap-4">
                            <div>
                                <label className="block text-xs font-medium mb-1.5 text-[var(--color-text-secondary)]">Name</label>
                                <input
                                    placeholder="Key name (optional)"
                                    value={newKey.name}
                                    onChange={e => setNewKey({ ...newKey, name: e.target.value })}
                                    className="w-full px-4 py-2.5 bg-[var(--color-bg-surface-2)] border border-[var(--color-border-subtle)] rounded-2xl text-sm text-[var(--color-text-primary)] placeholder:text-[var(--color-text-muted)] focus:outline-none focus:border-[var(--color-accent)]/50 transition-all duration-200"
                                />
                            </div>
                            <div>
                                <label className="block text-xs font-medium mb-1.5 text-[var(--color-text-secondary)]">Owner</label>
                                <input
                                    placeholder="Owner identifier"
                                    value={newKey.owner}
                                    onChange={e => setNewKey({ ...newKey, owner: e.target.value })}
                                    className="w-full px-4 py-2.5 bg-[var(--color-bg-surface-2)] border border-[var(--color-border-subtle)] rounded-2xl text-sm text-[var(--color-text-primary)] placeholder:text-[var(--color-text-muted)] focus:outline-none focus:border-[var(--color-accent)]/50 transition-all duration-200"
                                />
                            </div>
                            <div>
                                <label className="block text-xs font-medium mb-1.5 text-[var(--color-text-secondary)]">Scopes</label>
                                <div className="flex gap-2">
                                    {['read', 'write', 'admin'].map(scope => (
                                        <button
                                            key={scope}
                                            type="button"
                                            onClick={() => toggleScope(scope)}
                                            className={`px-3 py-1.5 rounded-xl text-xs font-medium transition-all ${
                                                newKey.scopes.includes(scope)
                                                    ? 'bg-[var(--color-accent)] text-white'
                                                    : 'bg-[var(--color-bg-surface-2)] text-[var(--color-text-muted)] border border-[var(--color-border-subtle)]'
                                            }`}
                                        >
                                            {scope}
                                        </button>
                                    ))}
                                </div>
                            </div>
                            <div>
                                <label className="block text-xs font-medium mb-1.5 text-[var(--color-text-secondary)]">Expires In (days)</label>
                                <input
                                    type="number"
                                    placeholder="No expiration"
                                    value={newKey.ttl_days || ''}
                                    onChange={e => setNewKey({ ...newKey, ttl_days: e.target.value ? parseInt(e.target.value) : null })}
                                    className="w-full px-4 py-2.5 bg-[var(--color-bg-surface-2)] border border-[var(--color-border-subtle)] rounded-2xl text-sm text-[var(--color-text-primary)] placeholder:text-[var(--color-text-muted)] focus:outline-none focus:border-[var(--color-accent)]/50 transition-all duration-200"
                                />
                            </div>
                        </div>
                        <div className="flex justify-end gap-3 mt-4">
                            <button
                                onClick={() => setShowForm(false)}
                                className="px-4 py-2 text-sm text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] transition-colors"
                            >
                                Cancel
                            </button>
                            <button
                                onClick={createKey}
                                disabled={!newKey.owner || newKey.scopes.length === 0}
                                className="px-6 py-2.5 bg-[var(--color-accent)] hover:bg-[var(--color-accent-hover)] text-white rounded-2xl text-sm font-semibold disabled:opacity-40 transition-all duration-200 active:scale-[0.97]"
                            >
                                Create
                            </button>
                        </div>
                    </div>
                )}

                <div className="space-y-3">
                    {loading ? (
                        <div className="text-center py-16">
                            <div className="w-5 h-5 border-2 rounded-full animate-spin mx-auto mb-4" style={{ borderColor: 'var(--color-accent)', borderTopColor: 'transparent' }} />
                            <p className="text-xs" style={{ color: 'var(--color-text-muted)' }}>Loading...</p>
                        </div>
                    ) : keys.length === 0 ? (
                        <div className="text-center py-16">
                            <div className="w-16 h-16 rounded-3xl bg-white/5 border border-[var(--color-border-subtle)] flex items-center justify-center mx-auto mb-4">
                                <Key size={28} className="text-[var(--color-text-muted)]" />
                            </div>
                            <p className="text-[var(--color-text-muted)] text-sm">No API keys yet. Create one to enable programmatic access.</p>
                        </div>
                    ) : (
                        keys.map(key => (
                            <div
                                key={key.id}
                                className={`bg-[var(--color-bg-surface-1)] border rounded-2xl p-5 flex items-center gap-4 transition-all duration-200 ${
                                    key.is_active
                                        ? 'border-[var(--color-border-subtle)] hover:border-[var(--color-accent)]/30'
                                        : 'border-[var(--color-error)]/20 opacity-60'
                                }`}
                            >
                                <div className={`w-10 h-10 rounded-2xl flex items-center justify-center ${
                                    key.is_active
                                        ? 'bg-[var(--color-accent)]/10 border border-[var(--color-accent)]/20'
                                        : 'bg-[var(--color-error)]/10 border border-[var(--color-error)]/20'
                                }`}>
                                    <Key size={20} className={key.is_active ? 'text-[var(--color-accent)]' : 'text-[var(--color-error)]'} />
                                </div>
                                <div className="flex-1 min-w-0">
                                    <div className="flex items-center gap-2 mb-1">
                                        <h3 className="font-semibold text-[var(--color-text-primary)] truncate">
                                            {key.name || 'Unnamed Key'}
                                        </h3>
                                        {!key.is_active && (
                                            <span className="px-2 py-0.5 text-[10px] font-medium bg-[var(--color-error)]/10 text-[var(--color-error)] rounded-lg">
                                                REVOKED
                                            </span>
                                        )}
                                    </div>
                                    <div className="flex items-center gap-3 text-xs text-[var(--color-text-muted)]">
                                        <span>Owner: {key.owner}</span>
                                        <span>Scopes: {key.scopes.join(', ')}</span>
                                        {key.expires_at && (
                                            <span className="flex items-center gap-1">
                                                <Clock size={12} />
                                                Expires: {new Date(key.expires_at).toLocaleDateString()}
                                            </span>
                                        )}
                                    </div>
                                </div>
                                {key.is_active && (
                                    <button
                                        onClick={() => revokeKey(key.id)}
                                        className="p-2 hover:bg-[var(--color-error)]/10 rounded-xl text-[var(--color-text-muted)] hover:text-[var(--color-error)] transition-all duration-200"
                                        title="Revoke key"
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
