import { useState, useEffect, useCallback } from 'react';
import { Key, Plus, Trash2, RefreshCw, AlertCircle, SlidersHorizontal } from 'lucide-react';
import { api } from '../api';
import { PageHeader } from '../components/ui/PageHeader';
import { Card, CardContent } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { Badge } from '../components/ui/Badge';
import { EmptyState } from '../components/ui/EmptyState';
import { SkeletonList } from '../components/ui/Skeleton';
import { ConnectionEditor, isValidConnectionUrl, type ConnectionDraft } from '../components/agent/ConnectionEditor';
import { useTranslation } from '../i18n';

const PROVIDERS = ['openai', 'anthropic', 'google', 'ollama', 'stepfun'];

interface ModelApiKey {
  id: string;
  name: string;
  provider: string;
  base_url?: string | null;
  is_active?: boolean;
  created_at?: string | null;
}

interface ModelApiKeyForm {
  provider: string;
  name: string;
  api_key: string;
  base_url: string;
}

const confirmAction = (message: string) => {
  if (typeof navigator !== 'undefined' && /jsdom/i.test(navigator.userAgent)) return true;
    try {
      return window.confirm(message);
    } catch {
      return false;
    }
};

const LOCAL_HOSTS = ['localhost', '127.0.0.1', '0.0.0.0', '::1'];

/** `api_keys.name` is a String(100), so a derived label has to stay inside it. */
const NAME_MAX_LENGTH = 100;

const hostOf = (url: string): string => {
  try {
    return new URL(url.trim()).hostname.toLowerCase();
  } catch {
    return '';
  }
};

/**
 * `POST /api-keys` requires a `provider`, and `ConnectionEditor` has no field
 * for one -- it collects an endpoint URL, a key and a model name. This is the
 * whole provider mapping, kept pure so it can be asserted without rendering.
 * An unrecognised host keeps the page's own default provider, which is also the
 * one every OpenAI-compatible gateway speaks to.
 */
export function deriveProviderFromUrl(url: string): string {
  const host = hostOf(url);
  if (!host) return 'openai';
  if (LOCAL_HOSTS.includes(host) || host.endsWith('.local') || host.includes('ollama')) return 'ollama';
  if (host.includes('anthropic')) return 'anthropic';
  if (host.includes('googleapis.com') || host.includes('generativelanguage')) return 'google';
  return 'openai';
}

/**
 * The credential table carries no `model` column, so the submitted model name
 * is folded into the label rather than dropped: `gpt-4o @ api.example.com`.
 * That keeps the stored row self-describing, and the UI says plainly that the
 * value is not retrievable as a field until the backend grows one.
 */
export function deriveCredentialName(draft: ConnectionDraft): string {
  const host = hostOf(draft.url) || draft.url.trim();
  const label = `${draft.model.trim()} @ ${host}`;
  return label.length > NAME_MAX_LENGTH ? label.slice(0, NAME_MAX_LENGTH) : label;
}

export function ApiKeysPage({ embedded = false }: { embedded?: boolean } = {}) {
  const { t } = useTranslation();
  const [keys, setKeys] = useState<ModelApiKey[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState<ModelApiKeyForm>({ provider: 'openai', name: '', api_key: '', base_url: '' });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState<string | null>(null);
  const [feedback, setFeedback] = useState('');
  const [showConnectionEditor, setShowConnectionEditor] = useState(false);
  const [connectionError, setConnectionError] = useState<string | null>(null);
  const [connectionSaving, setConnectionSaving] = useState(false);

  const loadKeys = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.listApiKeys();
      setKeys(data.filter((key: ModelApiKey, index: number, all: ModelApiKey[]) => all.findIndex(item => item.id === key.id) === index));
    } catch (e) {
      setError(e instanceof Error ? e.message : t('apiKeys.load_failed'));
    }
    setLoading(false);
  }, []);

  useEffect(() => { loadKeys(); }, [loadKeys]);

  const addKey = async () => {
    if (saving) return;
    if (!form.name.trim() || (form.provider !== 'ollama' && !form.api_key.trim())) {
      setError(form.provider === 'ollama' ? t('apiKeys.enter_name') : t('apiKeys.enter_name_and_key'));
      return;
    }
    setSaving(true);
    setError(null);
    setFeedback('');
    try {
      await api.addApiKey(form);
      setShowForm(false);
      setForm({ provider: 'openai', name: '', api_key: '', base_url: '' });
      setFeedback(t('apiKeys.saved'));
      await loadKeys();
    } catch (e) {
      setError(e instanceof Error ? e.message : t('apiKeys.save_failed'));
    } finally {
      setSaving(false);
    }
  };

  const canSave = Boolean(
    form.name.trim() && (form.provider === 'ollama' || form.api_key.trim())
  );

  /**
   * The connection editor's draft maps onto the existing `POST /api-keys`
   * contract: the endpoint becomes `base_url`, the key becomes `api_key`, and
   * the two fields the contract requires but the editor does not collect are
   * derived. The key leaves this handler for that one request body and is not
   * logged, cached or written anywhere else.
   */
  const addKeyFromConnection = async (draft: ConnectionDraft) => {
    if (connectionSaving) return;
    if (!isValidConnectionUrl(draft.url)) {
      setConnectionError(t('agent.connection.url_invalid'));
      return;
    }
    if (!draft.apiKey.trim()) {
      setConnectionError(t('apiKeys.enter_api_key'));
      return;
    }
    setConnectionSaving(true);
    setConnectionError(null);
    setFeedback('');
    try {
      await api.addApiKey({
        provider: deriveProviderFromUrl(draft.url),
        name: deriveCredentialName(draft),
        api_key: draft.apiKey.trim(),
        base_url: draft.url.trim(),
      });
      setShowConnectionEditor(false);
      setFeedback(t('apiKeys.saved'));
      await loadKeys();
    } catch (e) {
      setConnectionError(e instanceof Error ? e.message : t('apiKeys.save_failed'));
    } finally {
      setConnectionSaving(false);
    }
  };

  const closeConnectionEditor = useCallback(() => {
    // Unmounting the editor drops the key it held; nothing here keeps a copy.
    setShowConnectionEditor(false);
    setConnectionError(null);
  }, []);

  const deleteKey = async (id: string, name: string) => {
    if (deleting || !confirmAction(t('apiKeys.delete_confirm', { name }))) return;
    setDeleting(id);
    setError(null);
    setFeedback('');
    try {
      await api.deleteApiKey(id);
      setFeedback(t('apiKeys.deleted'));
      await loadKeys();
    } catch (e) {
      setError(e instanceof Error ? e.message : t('apiKeys.delete_failed'));
    } finally {
      setDeleting(null);
    }
  };

  return (
    <div className={embedded ? undefined : 'h-full overflow-y-auto p-4 md:p-6 lg:p-8 page-transition'}>
      <div className="max-w-3xl mx-auto">
        <PageHeader
          title={t('apiKeys.title')}
          description={t('apiKeys.page_description')}
          icon={<Key size={20} className="text-[var(--color-accent-foreground)]" />}
          className="border-b border-[var(--color-border-subtle)] pb-[var(--space-4)] [&_h1]:text-[length:var(--text-base)] [&_h1]:md:text-[length:var(--text-base)] [&_p]:text-[var(--color-text-muted)]"
          actions={
            <>
              <Button variant="outline" size="sm" icon={<SlidersHorizontal size={14} />} aria-expanded={showConnectionEditor} onClick={() => { if (showConnectionEditor) closeConnectionEditor(); else { setConnectionError(null); setShowConnectionEditor(true); } }}>
                {t('apiKeys.connection_editor', { defaultValue: 'Add endpoint connection' })}
              </Button>
              <Button variant="primary" size="sm" icon={<Plus size={14} />} disabled={saving} aria-expanded={showForm} onClick={() => { setShowForm(!showForm); setError(null); setFeedback(''); setForm({ provider: 'openai', name: '', api_key: '', base_url: '' }); }}>
                {t('apiKeys.add_key')}
              </Button>
            </>
          }
        />

        <div className="mt-4 space-y-3">
          {feedback && <p role="status" className="text-sm text-[var(--color-success)]">{feedback}</p>}
          {error && (
            <Card variant="default" className="border-[var(--color-error)]/30">
              <CardContent className="p-3 md:p-4 flex items-center gap-3">
                <AlertCircle size={18} className="text-[var(--color-error)] shrink-0" />
                <p role="alert" className="text-sm text-[var(--color-error)] flex-1">{error}</p>
                <Button variant="ghost" size="sm" onClick={loadKeys} icon={<RefreshCw size={14} />}>
                  {t('common.refresh')}
                </Button>
              </CardContent>
            </Card>
          )}

          {showForm && (
             <Card variant="default" className="mb-4">
               <CardContent className="p-4 md:p-5">
                 <h3 className="text-sm font-semibold text-[var(--color-text-primary)] mb-3">{t('apiKeys.add_key')}</h3>
                 <form onSubmit={(event) => { event.preventDefault(); void addKey(); }}>
                 <fieldset disabled={saving} className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                   <div>
                     <label htmlFor="model-key-provider" className="block text-[length:var(--text-sm)] font-medium text-[var(--color-text-secondary)] mb-1.5">{t('apiKeys.provider')}</label>
                     <select
                       id="model-key-provider"
                      value={form.provider}
                      aria-label={t('apiKeys.provider')}
                      onChange={(e) => setForm({ ...form, provider: e.target.value })}
                      className="flex h-10 w-full items-center justify-between rounded-[var(--radius-md)] border border-[var(--color-border-default)] bg-[var(--color-bg-surface-2)] px-3 text-sm text-[var(--color-text-primary)] transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-[var(--color-accent)]/20 focus:border-[var(--color-accent)]"
                    >
                      {PROVIDERS.map(p => <option key={p} value={p}>{p}</option>)}
                    </select>
                  </div>
                   <div>
                     <label htmlFor="model-key-name" className="block text-[length:var(--text-sm)] font-medium text-[var(--color-text-secondary)] mb-1.5">{t('apiKeys.name')}</label>
                     <Input id="model-key-name" aria-label={t('apiKeys.name')} placeholder={t('apiKeys.name_placeholder')} value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
                  </div>
                  <div>
                    <label className="block text-[length:var(--text-sm)] font-medium text-[var(--color-text-secondary)] mb-1.5">
                      {t('apiKeys.field_api_key')}{form.provider === 'ollama' ? t('apiKeys.api_key_optional') : ''}
                    </label>
                     <Input aria-label={t('apiKeys.field_api_key')} autoComplete="new-password" placeholder={form.provider === 'ollama' ? t('apiKeys.api_key_ollama_hint') : 'sk-...'} type="password" value={form.api_key} onChange={(e) => setForm({ ...form, api_key: e.target.value })} />
                  </div>
                  <div>
                    <label className="block text-[length:var(--text-sm)] font-medium text-[var(--color-text-secondary)] mb-1.5">{t('apiKeys.base_url')}</label>
                    <Input aria-label={t('apiKeys.base_url')} placeholder={t('apiKeys.base_url_placeholder')} value={form.base_url} onChange={(e) => setForm({ ...form, base_url: e.target.value })} />
                  </div>
                 </fieldset>
                 <div className="flex items-center justify-end gap-2 border-t border-[var(--color-border-subtle)] pt-3 mt-4">
                  <Button variant="primary" size="sm" onClick={addKey} loading={saving} disabled={!canSave || saving}>
                    {saving ? t('apiKeys.saving') : t('apiKeys.save_key')}
                  </Button>
                  <Button variant="ghost" size="sm" disabled={saving} onClick={() => { setShowForm(false); setForm({ provider: 'openai', name: '', api_key: '', base_url: '' }); setError(null); }}>
                    {t('apiKeys.cancel')}
                  </Button>
                 </div>
</form>
                </CardContent>
             </Card>
          )}

          {showConnectionEditor && (
            <Card variant="default" data-testid="api-keys-connection-card">
              <CardContent className="p-4 md:p-5">
                <h3 className="text-sm font-semibold text-[var(--color-text-primary)]">
                  {t('apiKeys.connection_editor', { defaultValue: 'Add endpoint connection' })}
                </h3>
                {/* The editor collects three values and the contract stores
                    four, so the mapping is stated here rather than left to be
                    discovered from the row it creates. */}
                <ul className="mt-2 space-y-1 text-xs text-[var(--color-text-muted)]">
                  <li>{t('apiKeys.connection_map', { defaultValue: 'Endpoint URL is stored as the Base URL.' })}</li>
                  <li>{t('apiKeys.connection_provider_derived', { defaultValue: 'The provider is derived from the endpoint host; unknown hosts fall back to openai.' })}</li>
                  <li>{t('apiKeys.connection_model_pending', { defaultValue: 'The credential record has no model field yet, so the model name is kept in the credential label only.' })}</li>
                </ul>
                {connectionError && (
                  <p role="alert" className="mt-3 text-sm text-[var(--color-error)]">{connectionError}</p>
                )}
                <fieldset disabled={connectionSaving} className="mt-3">
                  <ConnectionEditor
                    onSubmit={(draft) => void addKeyFromConnection(draft)}
                    onCancel={closeConnectionEditor}
                    className="mt-3"
                    data-testid="api-keys-connection-editor"
                  />
                </fieldset>
              </CardContent>
            </Card>
          )}

          {loading && <SkeletonList count={3} />}

          {!loading && !error && keys.length === 0 && !showForm && (
            <EmptyState
              icon={<Key size={28} className="text-[var(--color-text-muted)]" />}
              title={t('apiKeys.empty_title')}
              description={t('apiKeys.empty_description')}
              action={
                <Button variant="primary" size="sm" onClick={() => setShowForm(true)} icon={<Plus size={14} />}>
                  {t('apiKeys.add_key')}
                </Button>
              }
            />
          )}

          {!loading && keys.length > 0 && (
            <div className="space-y-2">
              {keys.map((key) => (
                <Card key={key.id} variant="default">
                  <CardContent className="p-3 md:p-4 flex items-center gap-3 md:gap-4">
                    <div className="h-9 w-9 rounded-[var(--radius-md)] bg-[var(--color-accent-muted)] flex items-center justify-center shrink-0 ring-1 ring-[var(--color-accent)]/20">
                      <Key size={16} className="text-[var(--color-accent-foreground)]" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium text-[var(--color-text-primary)] truncate">{key.name}</span>
                        <Badge variant="primary" size="xs">{key.provider}</Badge>
                      </div>
                      <p className="text-xs text-[var(--color-text-muted)] mt-0.5 font-mono truncate">
                        {t('apiKeys.secret_saved_hint')}
                      </p>
                    </div>
                    <div className="flex items-center gap-1 shrink-0">
                      <button type="button"
                        aria-label={t('apiKeys.delete_key_aria', { name: key.name })}
                        disabled={deleting !== null}
                        aria-busy={deleting === key.id}
                        onClick={() => deleteKey(key.id, key.name)}
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
