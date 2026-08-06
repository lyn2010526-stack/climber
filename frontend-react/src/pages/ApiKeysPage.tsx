import { useState, useEffect, useCallback } from 'react';
import { Key, Plus, Trash2, Copy, Check, RefreshCw, AlertCircle } from 'lucide-react';
import { api } from '../api';
import { PageHeader } from '../components/ui/PageHeader';
import { Card, CardContent } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { Badge } from '../components/ui/Badge';
import { EmptyState } from '../components/ui/EmptyState';
import { SkeletonList } from '../components/ui/Skeleton';

const PROVIDERS = ['openai', 'anthropic', 'google', 'ollama', 'stepfun'];

export function ApiKeysPage() {
  const [keys, setKeys] = useState<any[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ provider: 'openai', name: '', api_key: '', base_url: '' });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [copiedId, setCopiedId] = useState<string | null>(null);

  const loadKeys = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.listApiKeys();
      setKeys(data);
    } catch (e: any) {
      setError(e.message || 'Failed to load API keys');
    }
    setLoading(false);
  }, []);

  useEffect(() => { loadKeys(); }, [loadKeys]);

  const addKey = async () => {
    try {
      await api.addApiKey(form);
      setShowForm(false);
      setForm({ provider: 'openai', name: '', api_key: '', base_url: '' });
      loadKeys();
    } catch (e: any) {
      setError(e.message || 'Failed to add key');
    }
  };

  const deleteKey = async (id: string) => {
    try {
      await api.deleteApiKey(id);
      loadKeys();
    } catch (e: any) {
      setError(e.message || 'Failed to delete key');
    }
  };

  const copyKey = (id: string, key: string) => {
    navigator.clipboard.writeText(key);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  return (
    <div className="h-full overflow-y-auto p-4 md:p-6 lg:p-8 page-transition">
      <div className="max-w-4xl mx-auto">
        <PageHeader
          title="API Keys"
          description="Manage model provider credentials"
          icon={<Key size={20} className="text-[var(--color-accent)]" />}
          actions={
            <Button variant="primary" size="sm" icon={<Plus size={14} />} onClick={() => setShowForm(!showForm)}>
              Add Key
            </Button>
          }
        />

        <div className="mt-4 md:mt-6">
          {error && (
            <Card variant="default" className="border-[var(--color-error)]/30">
              <CardContent className="p-3 md:p-4 flex items-center gap-3">
                <AlertCircle size={18} className="text-[var(--color-error)] shrink-0" />
                <p className="text-sm text-[var(--color-error)] flex-1">{error}</p>
                <Button variant="ghost" size="sm" onClick={loadKeys} icon={<RefreshCw size={14} />}>
                  Retry
                </Button>
              </CardContent>
            </Card>
          )}

          {showForm && (
            <Card variant="default" className="mb-4">
              <CardContent className="p-4 md:p-5">
                <h3 className="text-sm font-semibold text-[var(--color-text-primary)] mb-3">Add New Key</h3>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs font-medium text-[var(--color-text-secondary)] mb-1.5">Provider</label>
                    <select
                      value={form.provider}
                      onChange={(e) => setForm({ ...form, provider: e.target.value })}
                      className="flex h-10 w-full items-center justify-between rounded-[var(--radius-md)] border border-[var(--color-border-default)] bg-[var(--color-bg-surface-2)] px-3 text-sm text-[var(--color-text-primary)] transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-[var(--color-accent)]/20 focus:border-[var(--color-accent)]"
                    >
                      {PROVIDERS.map(p => <option key={p} value={p}>{p}</option>)}
                    </select>
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-[var(--color-text-secondary)] mb-1.5">Name</label>
                    <Input placeholder="Key name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-[var(--color-text-secondary)] mb-1.5">API Key</label>
                    <Input placeholder="sk-..." type="password" value={form.api_key} onChange={(e) => setForm({ ...form, api_key: e.target.value })} />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-[var(--color-text-secondary)] mb-1.5">Base URL (optional)</label>
                    <Input placeholder="https://..." value={form.base_url} onChange={(e) => setForm({ ...form, base_url: e.target.value })} />
                  </div>
                </div>
                <div className="flex items-center gap-2 mt-4">
                  <Button variant="primary" size="sm" onClick={addKey} disabled={!form.name || !form.api_key}>
                    Save Key
                  </Button>
                  <Button variant="ghost" size="sm" onClick={() => setShowForm(false)}>
                    Cancel
                  </Button>
                </div>
              </CardContent>
            </Card>
          )}

          {loading && <SkeletonList count={3} />}

          {!loading && !error && keys.length === 0 && !showForm && (
            <EmptyState
              icon={<Key size={28} className="text-[var(--color-text-muted)]" />}
              title="No API keys"
              description="Add your first API key to connect to model providers"
              action={
                <Button variant="primary" size="sm" onClick={() => setShowForm(true)} icon={<Plus size={14} />}>
                  Add Key
                </Button>
              }
            />
          )}

          {!loading && !error && keys.length > 0 && (
            <div className="space-y-2 md:space-y-3 stagger-children">
              {keys.map((key) => (
                <Card key={key.id} variant="default" className="hover-lift">
                  <CardContent className="p-3 md:p-4 flex items-center gap-3 md:gap-4">
                    <div className="h-9 w-9 rounded-[var(--radius-md)] bg-[var(--color-accent-muted)] flex items-center justify-center shrink-0 ring-1 ring-[var(--color-accent)]/20">
                      <Key size={16} className="text-[var(--color-accent)]" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium text-[var(--color-text-primary)] truncate">{key.name}</span>
                        <Badge variant="primary" size="xs">{key.provider}</Badge>
                      </div>
                      <p className="text-xs text-[var(--color-text-muted)] mt-0.5 font-mono truncate">
                        {key.api_key_preview || '••••••••••••'}
                      </p>
                    </div>
                    <div className="flex items-center gap-1 shrink-0">
                      <button
                        onClick={() => copyKey(key.id, key.api_key || '')}
                        className="flex h-8 w-8 items-center justify-center rounded-[var(--radius-md)] text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] hover:bg-[var(--color-bg-surface-2)] transition-all duration-200 focus-ring"
                      >
                        {copiedId === key.id ? <Check size={14} className="text-[var(--color-success)]" /> : <Copy size={14} />}
                      </button>
                      <button
                        onClick={() => deleteKey(key.id)}
                        className="flex h-8 w-8 items-center justify-center rounded-[var(--radius-md)] text-[var(--color-text-muted)] hover:text-[var(--color-error)] hover:bg-[var(--color-error-subtle)] transition-all duration-200 focus-ring"
                      >
                        <Trash2 size={14} />
                      </button>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
