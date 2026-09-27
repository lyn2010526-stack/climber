import { useState, useEffect, useCallback } from 'react';
import {
  Search, Download, Trash2, Power, PowerOff, Package, Brain, Server, FileText,
  ChevronRight, Plus, RefreshCw, AlertCircle,
} from 'lucide-react';
import { api } from '../api';
import { useTranslation } from '../i18n';
import { includesQuery } from '../lib/search';
import {
  normalizePluginStatus,
  pluginViewDescriptor,
  type PluginViewStatus,
} from '../components/plugins/pluginViewStatus';
import { PageHeader } from '../components/ui/PageHeader';
import { Button } from '../components/ui/Button';
import { Badge } from '../components/ui/Badge';
import { Input } from '../components/ui/Input';
import { EmptyState } from '../components/ui/EmptyState';
import { Modal } from '../components/ui/Modal';

interface Plugin {
  id: string;
  name: string;
  description: string;
  type: 'skill' | 'mcp' | 'prompt';
  source: string;
  /** Mirrors `PluginRecord.status` in app/storage/models_plugins.py. */
  status: PluginViewStatus;
  icon: string;
  category: string;
  version: string;
  tools?: string[];
  tags?: string[];
  popularity?: number;
  error?: string;
  config?: Record<string, unknown>;
}

const TYPE_CONFIG: Record<Plugin['type'], { icon: typeof Brain; label: string }> = {
  skill: { icon: Brain, label: 'Skill' },
  mcp: { icon: Server, label: 'MCP' },
  prompt: { icon: FileText, label: 'Prompt' },
};

const CATEGORY_ALL = 'all';
const CATEGORY_INSTALLED = 'installed';

const inputClass = 'h-[var(--control-height-md)] w-full rounded-[var(--radius-md)] border border-[var(--color-border-default)] bg-[var(--color-bg-surface-2)] px-3 text-sm text-[var(--color-text-primary)] transition-all duration-200 placeholder:text-[var(--color-text-muted)] focus:border-[var(--color-accent)] focus:outline-none focus:ring-2 focus:ring-[var(--color-accent)]/20';

const labelClass = 'mb-1.5 block text-xs font-medium text-[var(--color-text-secondary)]';

function PluginStatus({ status }: { status: PluginViewStatus }) {
  const { t } = useTranslation();
  const view = pluginViewDescriptor(status, t);
  const StatusIcon = view.icon;
  return (
    <span
      role="status"
      data-plugin-status={status}
      className={`inline-flex shrink-0 items-center gap-1.5 text-xs ${view.tone}`}
    >
      <StatusIcon size={13} aria-hidden="true" className="shrink-0" />
      {view.label}
    </span>
  );
}

export function PluginsPage() {
  const { t } = useTranslation();
  const pluginText = (key: string, defaultValue: string, options?: Record<string, unknown>) => t(key, { defaultValue, ...options });
  const [error, setError] = useState<string | null>(null);
  const [importing, setImporting] = useState(false);
  const [plugins, setPlugins] = useState<Plugin[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState(CATEGORY_ALL);
  const [selectedType, setSelectedType] = useState<string>('');
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [importModalOpen, setImportModalOpen] = useState(false);
  const [importUrl, setImportUrl] = useState('');
  const [importName, setImportName] = useState('');
  const [importType, setImportType] = useState('mcp');
  const [expandedPlugin, setExpandedPlugin] = useState<string | null>(null);
  const [actionErrors, setActionErrors] = useState<Record<string, string>>({});

  const fetchPlugins = useCallback(async () => {
    setError(null);
    try {
      const data = await api.listPlugins();
      setPlugins(data.map((p) => ({ ...p, status: normalizePluginStatus(p.status) })));
    } catch (e) {
      setError(e instanceof Error ? e.message : t('common.error'));
    } finally {
      setLoading(false);
    }
  }, [t]);

  useEffect(() => { fetchPlugins(); }, [fetchPlugins]);

  const handleInstall = async (id: string) => {
    if (actionLoading) return;
    setError(null);
    setActionLoading(id);
    try {
      await api.installPlugin(id);
      setActionErrors(prev => { const next = { ...prev }; delete next[id]; return next; });
      await fetchPlugins();
    } catch (e) {
      const message = e instanceof Error ? e.message : t('common.error');
      setActionErrors(prev => ({ ...prev, [id]: message }));
      setError(message);
    }
    finally { setActionLoading(null); }
  };

  const handleUninstall = async (id: string) => {
    if (actionLoading) return;
    setError(null);
    setActionLoading(id);
    try {
      await api.uninstallPlugin(id);
      setActionErrors(prev => { const next = { ...prev }; delete next[id]; return next; });
      await fetchPlugins();
    } catch (e) {
      const message = e instanceof Error ? e.message : t('common.error');
      setActionErrors(prev => ({ ...prev, [id]: message }));
      setError(message);
    }
    finally { setActionLoading(null); }
  };

  const handleToggle = async (plugin: Plugin) => {
    if (actionLoading) return;
    setError(null);
    setActionLoading(plugin.id);
    try {
      if (plugin.status === 'enabled') {
        await api.disablePlugin(plugin.id);
      } else {
        await api.enablePlugin(plugin.id);
      }
      setActionErrors(prev => { const next = { ...prev }; delete next[plugin.id]; return next; });
      await fetchPlugins();
    } catch (e) {
      const message = e instanceof Error ? e.message : t('common.error');
      setActionErrors(prev => ({ ...prev, [plugin.id]: message }));
      setError(message);
    }
    finally { setActionLoading(null); }
  };

  const handleImport = async () => {
    if (!importUrl.trim() || importing) return;
    setImporting(true);
    setError(null);
    try {
      await api.importPlugin(importUrl, importName, importType);
      setImportModalOpen(false);
      setImportUrl('');
      setImportName('');
      await fetchPlugins();
    } catch (e) { setError(e instanceof Error ? e.message : t('common.error')); }
    finally { setImporting(false); }
  };

  const filtered = plugins.filter(plugin => {
    const matchSearch = includesQuery([plugin.name, plugin.description, ...(plugin.tags ?? [])], searchQuery);
    const matchType = !selectedType || plugin.type === selectedType;
    const matchCat = selectedCategory === CATEGORY_ALL ||
      (selectedCategory === CATEGORY_INSTALLED && plugin.status === 'enabled') ||
      plugin.category === selectedCategory;
    return matchSearch && matchType && matchCat;
  });

  const categories = [...new Set(plugins.map(p => p.category).filter(Boolean))];
  const categoryCount = (cat: string) =>
    cat === CATEGORY_ALL
      ? plugins.length
      : cat === CATEGORY_INSTALLED
        ? plugins.filter(p => p.status === 'enabled').length
        : plugins.filter(p => p.category === cat).length;

  return (
    <div className="page-scroll page-transition">
      <div className="page-container">
        <PageHeader
          title={t('navigation.plugins')}
          icon={<Package size={20} aria-hidden="true" />}
          actions={
            <>
              <Button variant="outline" size="sm" icon={<RefreshCw size={14} />} disabled={loading} onClick={fetchPlugins}>
                {t('common.refresh')}
              </Button>
              <Button variant="primary" size="sm" icon={<Plus size={14} aria-hidden="true" />} onClick={() => setImportModalOpen(true)}>
                {pluginText('plugins.import_action', 'Import plugin')}
              </Button>
            </>
          }
        />

        {error && (
          <div role="alert" className="mb-3 flex items-center gap-3 rounded-[var(--radius-md)] border border-[var(--color-error)]/30 bg-[var(--color-error-subtle)] p-3">
            <AlertCircle size={16} aria-hidden="true" className="shrink-0 text-[var(--color-error)]" />
            <p className="flex-1 break-words text-sm text-[var(--color-error)]">{error}</p>
            <Button variant="ghost" size="sm" icon={<RefreshCw size={14} />} onClick={fetchPlugins}>
              {t('common.retry')}
            </Button>
          </div>
        )}

        {!loading && plugins.length > 0 && (
          <div className="mb-3 space-y-2">
            <div className="flex flex-wrap items-center gap-3">
              <div className="w-full max-w-xs">
                <Input
                  size="sm"
                  placeholder={t('plugins.catalog_search_placeholder')}
                  aria-label={t('common.search')}
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  icon={<Search size={14} aria-hidden="true" />}
                />
              </div>
              <div className="flex flex-wrap items-center gap-1" role="group" aria-label={t('common.filter')}>
                {(['', 'skill', 'mcp', 'prompt'] as const).map(type => (
                  <button
                    key={type || 'all'}
                    type="button"
                    aria-pressed={selectedType === type}
                    onClick={() => setSelectedType(type)}
                    className={`rounded-[var(--radius-md)] border px-2.5 py-1 text-xs font-medium transition-colors ${
                      selectedType === type
                        ? 'border-[var(--color-border-strong)] bg-[var(--color-bg-surface-3)] text-[var(--color-text-primary)]'
                        : 'border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-2)] text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]'
                    }`}
                  >
                    {type ? TYPE_CONFIG[type].label : t('common.all')}
                  </button>
                ))}
              </div>
              <span className="shrink-0 text-xs tabular-nums text-[var(--color-text-muted)]" aria-live="polite">
                {filtered.length} / {plugins.length}
              </span>
            </div>
            {categories.length > 0 && (
              <div className="flex flex-wrap items-center gap-1" role="group" aria-label={t('common.filter')}>
                <button
                  type="button"
                  onClick={() => setSelectedCategory(CATEGORY_ALL)}
                  aria-pressed={selectedCategory === CATEGORY_ALL}
                  className={`rounded-[var(--radius-md)] border px-2.5 py-1 text-xs font-medium transition-colors ${
                    selectedCategory === CATEGORY_ALL
                      ? 'border-[var(--color-border-strong)] bg-[var(--color-bg-surface-3)] text-[var(--color-text-primary)]'
                      : 'border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-2)] text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]'
                  }`}
                >
                  {t('plugins.category_all', { count: categoryCount(CATEGORY_ALL) })}
                </button>
                <button
                  type="button"
                  onClick={() => setSelectedCategory(CATEGORY_INSTALLED)}
                  aria-pressed={selectedCategory === CATEGORY_INSTALLED}
                  className={`rounded-[var(--radius-md)] border px-2.5 py-1 text-xs font-medium transition-colors ${
                    selectedCategory === CATEGORY_INSTALLED
                      ? 'border-[var(--color-border-strong)] bg-[var(--color-bg-surface-3)] text-[var(--color-text-primary)]'
                      : 'border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-2)] text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]'
                  }`}
                >
                  {t('plugins.category_installed', { count: categoryCount(CATEGORY_INSTALLED) })}
                </button>
                {categories.map(cat => (
                  <button
                    key={cat}
                    type="button"
                    onClick={() => setSelectedCategory(cat)}
                    aria-pressed={selectedCategory === cat}
                    className={`rounded-[var(--radius-md)] border px-2.5 py-1 text-xs font-medium capitalize transition-colors ${
                      selectedCategory === cat
                        ? 'border-[var(--color-border-strong)] bg-[var(--color-bg-surface-3)] text-[var(--color-text-primary)]'
                        : 'border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-2)] text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]'
                    }`}
                  >
                    {cat} ({categoryCount(cat)})
                  </button>
                ))}
              </div>
            )}
          </div>
        )}

        {loading && (
          <div className="overflow-hidden rounded-[var(--radius-md)] border border-[var(--color-border-subtle)]" aria-busy="true" aria-label={t('common.loading')}>
            {[1, 2, 3].map(i => (
              <div key={i} className="flex items-center gap-3 border-b border-[var(--color-border-subtle)] px-3 py-2.5 last:border-b-0 md:px-4">
                <div className="h-3.5 w-3.5 shrink-0 rounded skeleton-shimmer" style={{ animationDelay: `${i * 100}ms` }} />
                <div className="h-3.5 flex-1 rounded skeleton-shimmer" style={{ animationDelay: `${i * 100}ms` }} />
                <div className="h-3.5 w-16 shrink-0 rounded skeleton-shimmer" style={{ animationDelay: `${i * 100}ms` }} />
              </div>
            ))}
          </div>
        )}

        {!loading && filtered.length > 0 && (
          <ul className="divide-y divide-[var(--color-border-subtle)] overflow-hidden rounded-[var(--radius-md)] border border-[var(--color-border-subtle)]" aria-label={t('navigation.plugins')}>
            {filtered.map(plugin => {
              const typeConf = TYPE_CONFIG[plugin.type] ?? TYPE_CONFIG.skill;
              const TypeIcon = typeConf.icon;
              const isEnabled = plugin.status === 'enabled';
              const isInstalled = isEnabled || plugin.status === 'installed' || plugin.status === 'disabled' || plugin.status === 'error';
              const isExpanded = expandedPlugin === plugin.id;
              const configFields = Object.keys(plugin.config || {});
              return (
                <li key={plugin.id} className="bg-[var(--color-bg-surface-1)] px-3 py-2 md:px-4">
                  <div className="flex flex-wrap items-center gap-3">
                    <TypeIcon size={16} aria-hidden="true" className="shrink-0 text-[var(--color-text-muted)]" />
                    <div className="min-w-0 flex-1">
                      <div className="flex min-w-0 items-center gap-2">
                        <span className="truncate text-sm font-medium text-[var(--color-text-primary)]">{plugin.name}</span>
                        <Badge variant="secondary" size="xs">{typeConf.label}</Badge>
                        {plugin.version && <span className="shrink-0 text-xs text-[var(--color-text-muted)]">v{plugin.version}</span>}
                      </div>
                      <p className="truncate text-xs text-[var(--color-text-muted)]">
                        {[plugin.description, plugin.category].filter(Boolean).join(' · ')}
                      </p>
                    </div>
                    {plugin.tools && plugin.tools.length > 0 && (
                      <span className="hidden shrink-0 text-xs tabular-nums text-[var(--color-text-muted)] sm:inline">
                        {plugin.tools.length} {t('agents.step_tools').toLocaleLowerCase()}
                      </span>
                    )}
                    <PluginStatus status={plugin.status} />
                    <button
                      type="button"
                      onClick={() => setExpandedPlugin(isExpanded ? null : plugin.id)}
                      aria-expanded={isExpanded}
                      aria-controls={`plugin-detail-${plugin.id}`}
                      className="flex h-11 min-w-11 shrink-0 items-center justify-center gap-1 rounded-[var(--radius-md)] px-1.5 text-xs text-[var(--color-text-muted)] transition-colors hover:bg-[var(--color-bg-surface-2)] hover:text-[var(--color-text-primary)] sm:min-w-0"
                    >
                      {t('plugins.details_action')}
                      <ChevronRight size={12} aria-hidden="true" className={isExpanded ? 'rotate-90 transition-transform' : 'transition-transform'} />
                    </button>
                    <div className="flex shrink-0 items-center gap-1.5">
                      {actionLoading === plugin.id ? null : plugin.status === 'unknown' ? (
                        <Button variant="outline" size="sm" disabled aria-label={`${pluginText('plugins.status.unknown', 'Unreported')}: ${plugin.name}`}>{pluginText('plugins.status.unknown', 'Unreported')}</Button>
                      ) : isInstalled ? (
                        <>
                          <Button
                            variant="outline"
                            size="sm"
                            icon={isEnabled ? <Power size={13} aria-hidden="true" /> : <PowerOff size={13} aria-hidden="true" />}
                            onClick={() => handleToggle(plugin)}
                            disabled={actionLoading !== null}
                          >
                            {isEnabled ? pluginText('plugins.disable', 'Disable') : pluginText('plugins.enable', 'Enable')}
                          </Button>
                          {plugin.source !== 'builtin' && (
                            <Button
                              variant="ghost"
                              size="icon-sm"
                              icon={<Trash2 size={14} aria-hidden="true" />}
                              onClick={() => handleUninstall(plugin.id)}
                              disabled={actionLoading !== null}
                              aria-label={`${t('common.remove')} ${plugin.name}`}
                              className="text-[var(--color-text-muted)] hover:bg-[var(--color-error-subtle)] hover:text-[var(--color-error)]"
                            />
                          )}
                        </>
                      ) : (
                        <Button
                          variant="secondary"
                          size="sm"
                          icon={<Download size={13} aria-hidden="true" />}
                          onClick={() => handleInstall(plugin.id)}
                          disabled={actionLoading !== null}
                        >
                          {pluginText('plugins.install', 'Install')}
                        </Button>
                      )}
                    </div>
                  </div>
                  {isExpanded && (
                    <dl
                      id={`plugin-detail-${plugin.id}`}
                      className="mt-2 grid gap-x-4 gap-y-1 pl-7 text-xs text-[var(--color-text-secondary)] sm:grid-cols-2"
                    >
                      <div className="flex gap-2"><dt className="text-[var(--color-text-muted)]">{t('plugins.detail_source')}</dt><dd className="min-w-0 break-all">{plugin.source || t('common.none')}</dd></div>
                      <div className="flex gap-2"><dt className="text-[var(--color-text-muted)]">{t('plugins.detail_version')}</dt><dd>{plugin.version || t('common.none')}</dd></div>
                      <div className="flex min-w-0 gap-2 sm:col-span-2"><dt className="shrink-0 text-[var(--color-text-muted)]">{t('plugins.detail_config_fields')}</dt><dd className="min-w-0 break-all">{configFields.join(', ') || t('common.none')}</dd></div>
                      {plugin.tools && plugin.tools.length > 0 && (
                        <div className="flex min-w-0 gap-2 sm:col-span-2"><dt className="shrink-0 text-[var(--color-text-muted)]">{t('plugins.detail_tools')}</dt><dd className="min-w-0 break-all font-mono">{plugin.tools.join(', ')}</dd></div>
                      )}
                    </dl>
                  )}
                   {plugin.error && (
                     <p className="mt-1.5 pl-7 text-xs break-words text-[var(--color-error)]">{plugin.error}</p>
                   )}
                   {actionErrors[plugin.id] && !plugin.error && (
                     <div role="alert" className="mt-2 flex items-center gap-2 pl-7 text-xs text-[var(--color-error)]">
                       <span className="min-w-0 flex-1 break-words">{actionErrors[plugin.id]}</span>
                       <Button
                         variant="ghost"
                         size="sm"
                         disabled={actionLoading !== null}
                         loading={actionLoading === plugin.id}
                         onClick={() => plugin.status === 'enabled' ? handleToggle(plugin) : plugin.status === 'installed' || plugin.status === 'disabled' || plugin.status === 'error' ? handleToggle(plugin) : handleInstall(plugin.id)}
                       >
                         {t('common.retry')}
                       </Button>
                     </div>
                   )}
                </li>
              );
            })}
          </ul>
        )}

        {!loading && !error && filtered.length === 0 && (
          <div className="overflow-hidden rounded-[var(--radius-md)] border border-[var(--color-border-subtle)]">
            <EmptyState
              className="w-full"
              icon={<Search size={20} aria-hidden="true" />}
              title={t('plugins.empty_title')}
              description={t('plugins.empty_description')}
            />
          </div>
        )}

        <Modal
          open={importModalOpen}
          onClose={() => setImportModalOpen(false)}
          title={t('plugins.import_title')}
          size="lg"
          footer={
            <div className="flex justify-end gap-2">
              <Button variant="ghost" size="sm" onClick={() => setImportModalOpen(false)}>
                {t('common.cancel')}
              </Button>
              <Button variant="primary" size="sm" onClick={handleImport} disabled={!importUrl.trim()} loading={importing}>
                {importing ? t('common.loading') : t('plugins.import_submit')}
              </Button>
            </div>
          }
        >
          {error && <p role="alert" className="mb-3 text-sm text-[var(--color-error)]">{error}</p>}
          <div className="space-y-4">
            <div>
              <label htmlFor="plugin-source" className={labelClass}>{t('plugins.import_url_label')}</label>
              <input
                id="plugin-source"
                type="url"
                value={importUrl}
                onChange={(e) => setImportUrl(e.target.value)}
                placeholder={t('plugins.import_url_placeholder')}
                className={inputClass}
              />
            </div>
            <div>
              <label htmlFor="plugin-name" className={labelClass}>{t('plugins.import_name_label')}</label>
              <input
                id="plugin-name"
                type="text"
                value={importName}
                onChange={(e) => setImportName(e.target.value)}
                placeholder={t('plugins.import_name_placeholder')}
                className={inputClass}
              />
            </div>
            <div>
              <label htmlFor="plugin-type" className={labelClass}>{t('plugins.import_type_label')}</label>
              <select
                id="plugin-type"
                value={importType}
                onChange={(e) => setImportType(e.target.value)}
                className={inputClass}
              >
                <option value="mcp">{t('plugins.import_type_mcp')}</option>
                <option value="skill">{t('plugins.import_type_skill')}</option>
                <option value="prompt">{t('plugins.import_type_prompt')}</option>
              </select>
            </div>
          </div>
        </Modal>
      </div>
    </div>
  );
}
