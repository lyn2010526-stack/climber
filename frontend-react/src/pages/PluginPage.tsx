import { useState, useEffect, useCallback } from 'react';
import { Search, Trash2, ToggleLeft, ToggleRight, RefreshCw, Package, AlertCircle, ChevronRight } from 'lucide-react';
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
  type: string;
  source: string;
  /** The raw `PluginRecord.status`; resolved through the shared vocabulary. */
  status: string;
  description: string;
  icon: string;
  category: string;
  version: string;
  config: Record<string, any>;
  error: string | null;
}

export default function PluginPage() {
  const { t } = useTranslation();
  const pluginText = (key: string, defaultValue: string) => t(key, { defaultValue });
  const [plugins, setPlugins] = useState<Plugin[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [toggling, setToggling] = useState<string | null>(null);
  const [deleting, setDeleting] = useState<string | null>(null);
  const [showImport, setShowImport] = useState(false);
  const [importUrl, setImportUrl] = useState('');
  const [importName, setImportName] = useState('');
  const [importing, setImporting] = useState(false);
  const [expanded, setExpanded] = useState<string | null>(null);

  const loadPlugins = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.listPlugins();
      setPlugins(data.map(plugin => ({ ...plugin, status: normalizePluginStatus(plugin.status) })));
    } catch (e) {
      setError(e instanceof Error ? e.message : t('common.error'));
    }
    setLoading(false);
  }, [t]);

  useEffect(() => {
    loadPlugins();
  }, [loadPlugins]);

  const togglePlugin = async (plugin: Plugin) => {
    if (toggling || deleting) return;
    setError(null);
    setToggling(plugin.id);
    try {
      const status = normalizePluginStatus(plugin.status);
      if (status === 'unknown') return;
      if (status === 'enabled') {
        await api.disablePlugin(plugin.id);
      } else {
        await api.enablePlugin(plugin.id);
      }
      await loadPlugins();
    } catch (e) {
      setError(e instanceof Error ? e.message : t('common.error'));
    } finally {
      setToggling(null);
    }
  };

  const deletePlugin = async (pluginId: string) => {
    if (toggling || deleting) return;
    setError(null);
    setDeleting(pluginId);
    try {
      await api.uninstallPlugin(pluginId);
      setPlugins(prev => prev.filter(p => p.id !== pluginId));
    } catch (e) {
      setError(e instanceof Error ? e.message : t('common.error'));
    } finally {
      setDeleting(null);
    }
  };

  const importPlugin = async () => {
    if (!importUrl.trim() || importing) return;
    setImporting(true);
    setError(null);
    try {
      await api.importPlugin(importUrl, importName);
      setImportUrl('');
      setImportName('');
      setShowImport(false);
      await loadPlugins();
    } catch (e) {
      setError(e instanceof Error ? e.message : t('common.error'));
    } finally {
      setImporting(false);
    }
  };

  const filtered = plugins.filter(p => includesQuery([p.name, p.description, p.type, p.category], searchQuery));
  const hasFilters = Boolean(searchQuery);
  const showList = !loading && (!error || filtered.length > 0);
  const enabledCount = plugins.filter(p => p.status === 'enabled').length;

  return (
    <div className="page-scroll page-transition">
      <div className="page-container">
        <PageHeader
          title={t('navigation.plugin_management')}
          icon={<Package size={20} aria-hidden="true" />}
          actions={
            <>
              <Button variant="outline" size="sm" icon={<RefreshCw size={14} />} disabled={loading} onClick={loadPlugins}>
                {t('common.refresh')}
              </Button>
              <Button variant="primary" size="sm" onClick={() => setShowImport(true)}>
                {t('plugins.import_action')}
              </Button>
            </>
          }
        />

        {error && (
          <div role="alert" className="mb-3 flex items-center gap-3 rounded-[var(--radius-md)] border border-[var(--color-error)]/30 bg-[var(--color-error-subtle)] p-3">
            <AlertCircle size={16} aria-hidden="true" className="shrink-0 text-[var(--color-error)]" />
            <p className="flex-1 break-words text-sm text-[var(--color-error)]">{error}</p>
            <Button variant="ghost" size="sm" icon={<RefreshCw size={14} />} onClick={loadPlugins}>
              {t('common.retry')}
            </Button>
          </div>
        )}

        {!loading && plugins.length > 0 && (
          <div className="mb-3 flex flex-wrap items-center gap-3">
            <div className="w-full max-w-xs">
              <Input
                size="sm"
                placeholder={t('plugins.manage_search_placeholder')}
                aria-label={t('common.search')}
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                icon={<Search size={14} aria-hidden="true" />}
              />
            </div>
            <span className="shrink-0 text-xs tabular-nums text-[var(--color-text-muted)]" aria-live="polite">
              {filtered.length} / {plugins.length} · {t('plugins.enabled_summary', { count: enabledCount })}
            </span>
          </div>
        )}

        {loading && (
          <div className="overflow-hidden rounded-[var(--radius-md)] border border-[var(--color-border-subtle)]" aria-busy="true" aria-label={t('common.loading')}>
            {[1, 2, 3, 4].map(i => (
              <div key={i} className="flex items-center gap-3 border-b border-[var(--color-border-subtle)] px-3 py-2.5 last:border-b-0 md:px-4">
                <div className="h-3.5 w-3.5 shrink-0 rounded skeleton-shimmer" style={{ animationDelay: `${i * 100}ms` }} />
                <div className="h-3.5 flex-1 rounded skeleton-shimmer" style={{ animationDelay: `${i * 100}ms` }} />
                <div className="h-3.5 w-16 shrink-0 rounded skeleton-shimmer" style={{ animationDelay: `${i * 100}ms` }} />
              </div>
            ))}
          </div>
        )}

        {showList && filtered.length === 0 && (
          <div className="overflow-hidden rounded-[var(--radius-md)] border border-[var(--color-border-subtle)]">
            <EmptyState
              className="w-full"
              icon={hasFilters ? <Search size={20} aria-hidden="true" /> : <Package size={20} aria-hidden="true" />}
              title={hasFilters ? t('plugins.manage_empty_filtered_title') : t('plugins.manage_empty_title')}
              description={hasFilters ? t('plugins.manage_empty_filtered_description') : t('plugins.manage_empty_description')}
              action={hasFilters ? (
                <Button variant="outline" size="sm" onClick={() => setSearchQuery('')}>
                  {t('common.clear')}
                </Button>
              ) : undefined}
            />
          </div>
        )}

        {showList && filtered.length > 0 && (
          <ul className="divide-y divide-[var(--color-border-subtle)] overflow-hidden rounded-[var(--radius-md)] border border-[var(--color-border-subtle)]" aria-label={t('navigation.plugin_management')}>
            {filtered.map(plugin => {
              const viewStatus: PluginViewStatus = normalizePluginStatus(plugin.status);
              const view = pluginViewDescriptor(viewStatus, t);
              const StatusIcon = view.icon;
               const isEnabled = viewStatus === 'enabled';
              const isExpanded = expanded === plugin.id;
              const configFields = Object.keys(plugin.config || {});
              return (
                <li key={plugin.id} className="bg-[var(--color-bg-surface-1)] px-3 py-2 md:px-4">
                  <div className="flex flex-wrap items-center gap-3">
                    <Package size={16} aria-hidden="true" className="shrink-0 text-[var(--color-text-muted)]" />
                    <div className="min-w-0 flex-1">
                      <div className="flex min-w-0 items-center gap-2">
                        <span className="truncate text-sm font-medium text-[var(--color-text-primary)]">{plugin.name}</span>
                        {plugin.type && <Badge variant="secondary" size="xs">{plugin.type}</Badge>}
                        {plugin.version && <span className="shrink-0 text-xs text-[var(--color-text-muted)]">v{plugin.version}</span>}
                      </div>
                      {plugin.description && (
                        <p className="truncate text-xs text-[var(--color-text-muted)]">{plugin.description}</p>
                      )}
                    </div>
                    <span
                      role="status"
                      data-plugin-status={plugin.status}
                      className={`inline-flex shrink-0 items-center gap-1.5 text-xs ${view.tone}`}
                    >
                      <StatusIcon size={13} aria-hidden="true" className="shrink-0" />
                      {view.label}
                    </span>
                    <button
                      type="button"
                      onClick={() => setExpanded(isExpanded ? null : plugin.id)}
                      aria-expanded={isExpanded}
                      aria-controls={`plugin-manage-detail-${plugin.id}`}
                      className="flex h-11 min-w-11 shrink-0 items-center justify-center gap-1 rounded-[var(--radius-md)] px-1.5 text-xs text-[var(--color-text-muted)] transition-colors hover:bg-[var(--color-bg-surface-2)] hover:text-[var(--color-text-primary)] sm:min-w-0"
                    >
                      <span className="hidden sm:inline">{t('plugins.details_action')}</span>
                      <ChevronRight size={12} aria-hidden="true" className={isExpanded ? 'rotate-90 transition-transform' : 'transition-transform'} />
                    </button>
                    <div className="flex shrink-0 items-center gap-1.5">
                      {viewStatus === 'unknown' ? (
                        <Button variant="outline" size="sm" disabled aria-label={`${pluginText('plugins.status.unknown', 'Unreported')}: ${plugin.name}`}>{pluginText('plugins.status.unknown', 'Unreported')}</Button>
                      ) : <Button
                        variant="outline"
                        size="sm"
                        icon={isEnabled ? <ToggleRight size={14} aria-hidden="true" /> : <ToggleLeft size={14} aria-hidden="true" />}
                        onClick={() => togglePlugin(plugin)}
                        disabled={toggling !== null || deleting !== null}
                        loading={toggling === plugin.id}
                      >
                        {isEnabled ? pluginText('plugins.disable', 'Disable') : pluginText('plugins.enable', 'Enable')}
                      </Button>}
                      <Button
                        variant="ghost"
                        size="icon-sm"
                        icon={<Trash2 size={14} aria-hidden="true" />}
                        onClick={() => deletePlugin(plugin.id)}
                        disabled={deleting !== null || toggling !== null}
                        loading={deleting === plugin.id}
                        aria-label={`${t('common.remove')} ${plugin.name}`}
                        className="text-[var(--color-text-muted)] hover:bg-[var(--color-error-subtle)] hover:text-[var(--color-error)]"
                      />
                    </div>
                  </div>
                  {isExpanded && (
                    <dl
                      id={`plugin-manage-detail-${plugin.id}`}
                      className="mt-2 grid gap-x-4 gap-y-1 pl-7 text-xs text-[var(--color-text-secondary)] sm:grid-cols-2"
                    >
                      <div className="flex min-w-0 gap-2"><dt className="shrink-0 text-[var(--color-text-muted)]">{t('plugins.detail_source')}</dt><dd className="min-w-0 break-all">{plugin.source || t('common.none')}</dd></div>
                      <div className="flex gap-2"><dt className="text-[var(--color-text-muted)]">{t('plugins.detail_type')}</dt><dd>{plugin.type || t('common.none')}</dd></div>
                      <div className="flex min-w-0 gap-2 sm:col-span-2"><dt className="shrink-0 text-[var(--color-text-muted)]">{t('plugins.detail_config_fields')}</dt><dd className="min-w-0 break-all">{configFields.join(', ') || t('common.none')}</dd></div>
                    </dl>
                  )}
                  {plugin.error && (
                    <p className="mt-1.5 pl-7 text-xs break-words text-[var(--color-error)]">{plugin.error}</p>
                  )}
                </li>
              );
            })}
          </ul>
        )}

        <Modal
          open={showImport}
          onClose={() => setShowImport(false)}
          title={t('plugins.import_from_link_title')}
          size="lg"
          footer={
            <div className="flex justify-end gap-2">
              <Button variant="ghost" size="sm" onClick={() => setShowImport(false)}>
                {t('common.cancel')}
              </Button>
              <Button variant="primary" size="sm" onClick={importPlugin} disabled={!importUrl.trim()} loading={importing}>
                {importing ? t('common.loading') : t('plugins.import_submit')}
              </Button>
            </div>
          }
        >
          {error && <p role="alert" className="mb-3 text-sm text-[var(--color-error)]">{error}</p>}
          <div className="space-y-3">
            <div>
              <label htmlFor="manage-plugin-source" className="mb-1.5 block text-xs font-medium text-[var(--color-text-secondary)]">{t('plugins.import_source_label')}</label>
              <Input
                id="manage-plugin-source"
                placeholder={t('plugins.import_source_placeholder')}
                value={importUrl}
                onChange={(e) => setImportUrl(e.target.value)}
              />
            </div>
            <div>
              <label htmlFor="manage-plugin-name" className="mb-1.5 block text-xs font-medium text-[var(--color-text-secondary)]">{t('plugins.import_name_label')}</label>
              <Input
                id="manage-plugin-name"
                placeholder={t('plugins.import_name_label')}
                value={importName}
                onChange={(e) => setImportName(e.target.value)}
              />
            </div>
          </div>
        </Modal>
      </div>
    </div>
  );
}
