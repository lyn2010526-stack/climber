import { useState, useEffect, useCallback } from 'react';
import { Download, Trash2, Search, Server, RefreshCw, AlertCircle, CheckCircle2, CircleSlash, ChevronRight, ServerCog, CircleHelp } from 'lucide-react';
import { api } from '../api';
import { useTranslation } from '../i18n';
import { includesQuery } from '../lib/search';
import { PageHeader } from '../components/ui/PageHeader';
import { Button } from '../components/ui/Button';
import { Badge } from '../components/ui/Badge';
import { Input } from '../components/ui/Input';
import { EmptyState } from '../components/ui/EmptyState';

interface MCPServer {
  id: string;
  name: string;
  description: string;
  category: string;
  author: string;
  is_builtin: boolean;
  is_installed?: boolean;
  tags: string[];
  install_config: Record<string, any>;
  popularity: number;
  status?: string;
  tools?: Array<{ name: string; description?: string }> | string[];
  resources?: Array<{ name: string; uri?: string; description?: string }> | string[];
  tools_count?: number;
  resources_count?: number;
}

const selectClass = 'h-[var(--control-height-sm)] rounded-[var(--radius-md)] border border-[var(--color-border-default)] bg-[var(--color-bg-surface-2)] px-3 text-xs text-[var(--color-text-primary)] transition-all duration-200 focus:border-[var(--color-accent)] focus:outline-none focus:ring-2 focus:ring-[var(--color-accent)]/20';

export function MCPPage() {
  const { t } = useTranslation();
  const [installedOnly, setInstalledOnly] = useState(false);
  const [servers, setServers] = useState<MCPServer[]>([]);
  const [categories, setCategories] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedCategory, setSelectedCategory] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [installing, setInstalling] = useState<string | null>(null);
  const [actionErrors, setActionErrors] = useState<Record<string, string>>({});
  const [expanded, setExpanded] = useState<string | null>(null);

  const fetchServers = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.listMCPServers();
      setServers(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : t('common.error'));
    }
    setLoading(false);
  }, [t]);

  useEffect(() => {
    fetchServers();
    api.listMCPCategories()
      .then(data => setCategories(Array.isArray(data) ? data : []))
      .catch(() => {});
  }, [fetchServers]);

  const installServer = async (serverId: string) => {
    if (installing) return;
    setError(null);
    setInstalling(serverId);
    try {
      await api.installMCPServer(serverId, {});
      setActionErrors(prev => { const next = { ...prev }; delete next[serverId]; return next; });
      await fetchServers();
    } catch (e) {
      const message = e instanceof Error ? e.message : t('common.error');
      setActionErrors(prev => ({ ...prev, [serverId]: message }));
      setError(message);
    } finally {
      setInstalling(null);
    }
  };

  const uninstallServer = async (serverId: string) => {
    if (installing) return;
    setInstalling(serverId);
    setError(null);
    try {
      await api.deleteMCPServer(serverId);
      setActionErrors(prev => { const next = { ...prev }; delete next[serverId]; return next; });
      await fetchServers();
    } catch (e) {
      const message = e instanceof Error ? e.message : t('common.error');
      setActionErrors(prev => ({ ...prev, [serverId]: message }));
      setError(message);
    } finally {
      setInstalling(null);
    }
  };

  const filteredServers = servers.filter(server =>
    (!selectedCategory || server.category === selectedCategory) &&
    includesQuery([server.name, server.description, server.author, ...(server.tags ?? [])], searchQuery) &&
    (!installedOnly || server.is_installed)
  );

  const hasFilters = Boolean(searchQuery || selectedCategory || installedOnly);
  const showList = !loading && (!error || filteredServers.length > 0);
  const installedCount = servers.filter(s => s.is_installed === true).length;

  return (
    <div className="page-scroll page-transition">
      <div className="page-container">
        <PageHeader
          title={t('navigation.mcp')}
          icon={<Server size={20} aria-hidden="true" />}
          actions={
            <Button variant="outline" size="sm" icon={<RefreshCw size={14} />} disabled={loading} onClick={fetchServers}>
              {t('common.refresh')}
            </Button>
          }
        />

        {error && (
          <div role="alert" className="mb-3 flex items-center gap-3 rounded-[var(--radius-md)] border border-[var(--color-error)]/30 bg-[var(--color-error-subtle)] p-3">
            <AlertCircle size={16} aria-hidden="true" className="shrink-0 text-[var(--color-error)]" />
            <p className="flex-1 break-words text-sm text-[var(--color-error)]">{error}</p>
            <Button variant="ghost" size="sm" icon={<RefreshCw size={14} />} onClick={fetchServers}>
              {t('common.retry')}
            </Button>
          </div>
        )}

        {!loading && servers.length > 0 && (
          <div className="mb-3 flex flex-wrap items-center gap-3">
            <div className="w-full max-w-xs">
              <Input
                size="sm"
                placeholder="搜索 MCP 服务器..."
                aria-label={t('common.search')}
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                icon={<Search size={14} aria-hidden="true" />}
              />
            </div>
            <select
              aria-label={t('common.filter')}
              value={selectedCategory}
              onChange={(e) => setSelectedCategory(e.target.value)}
              className={selectClass}
            >
              <option value="">全部分类</option>
              {categories.map(cat => (
                <option key={cat} value={cat}>{cat}</option>
              ))}
            </select>
            <label className="inline-flex shrink-0 cursor-pointer items-center gap-1.5 text-xs text-[var(--color-text-secondary)]">
              <input
                type="checkbox"
                checked={installedOnly}
                onChange={e => setInstalledOnly(e.target.checked)}
                className="h-3.5 w-3.5 accent-[var(--color-accent)]"
              />
              已安装
            </label>
            <span className="shrink-0 text-xs tabular-nums text-[var(--color-text-muted)]" aria-live="polite">
              {filteredServers.length} / {servers.length} · {installedCount} 已安装
            </span>
          </div>
        )}

        {loading && (
          <div className="overflow-hidden rounded-[var(--radius-md)] border border-[var(--color-border-subtle)]" aria-busy="true" aria-label={t('common.loading')}>
            {[1, 2, 3].map(i => (
              <div key={i} className="flex items-center gap-3 border-b border-[var(--color-border-subtle)] px-3 py-2.5 last:border-b-0 md:px-4">
                <div className="h-3.5 w-3.5 shrink-0 rounded skeleton-shimmer" style={{ animationDelay: `${i * 100}ms` }} />
                <div className="h-3.5 flex-1 rounded skeleton-shimmer" style={{ animationDelay: `${i * 100}ms` }} />
                <div className="h-3.5 w-20 shrink-0 rounded skeleton-shimmer" style={{ animationDelay: `${i * 100}ms` }} />
              </div>
            ))}
          </div>
        )}

        {showList && filteredServers.length === 0 && (
          <div className="overflow-hidden rounded-[var(--radius-md)] border border-[var(--color-border-subtle)]">
            <EmptyState
              className="w-full"
              icon={hasFilters ? <Search size={20} aria-hidden="true" /> : <Server size={20} aria-hidden="true" />}
              title={hasFilters ? t('common.no_results') : t('common.no_data')}
              action={hasFilters ? (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => { setSearchQuery(''); setSelectedCategory(''); setInstalledOnly(false); }}
                >
                  {t('common.clear')}
                </Button>
              ) : undefined}
            />
          </div>
        )}

        {showList && filteredServers.length > 0 && (
          <ul className="divide-y divide-[var(--color-border-subtle)] overflow-hidden rounded-[var(--radius-md)] border border-[var(--color-border-subtle)]" aria-label={t('navigation.mcp')}>
            {filteredServers.map(server => {
                      const configFields = Object.keys(server.install_config || {});
                      const isExpanded = expanded === server.id;
                      const actionError = actionErrors[server.id];
                      const toolCount = server.tools_count ?? server.tools?.length;
                      const resourceCount = server.resources_count ?? server.resources?.length;
                      const tools = server.tools ?? [];
                      const resources = server.resources ?? [];
                      const retry = server.is_installed === true ? () => uninstallServer(server.id) : () => installServer(server.id);
              return (
                <li key={server.id} className="bg-[var(--color-bg-surface-1)] px-3 py-2 md:px-4">
                  <div className="flex flex-wrap items-center gap-3">
                    <Server size={16} aria-hidden="true" className="shrink-0 text-[var(--color-text-muted)]" />
                    <div className="min-w-0 flex-1">
                      <div className="flex min-w-0 items-center gap-2">
                        <span className="truncate text-sm font-medium text-[var(--color-text-primary)]">{server.name}</span>
                        {server.category && <Badge variant="secondary" size="xs">{server.category}</Badge>}
                      </div>
                      <p className="truncate text-xs text-[var(--color-text-muted)]">
                        {[server.description, server.author, server.status].filter(Boolean).join(' · ')}
                      </p>
                    </div>
                    <span
                      role="status"
                      data-mcp-installed={server.is_installed === undefined ? 'unreported' : server.is_installed ? 'installed' : 'available'}
                      className={`inline-flex shrink-0 items-center gap-1.5 text-xs ${server.is_installed === undefined ? 'text-[var(--color-text-disabled)]' : server.is_installed ? 'text-[var(--color-text-secondary)]' : 'text-[var(--color-text-muted)]'}`}
                    >
                      {server.is_installed === undefined
                        ? <CircleHelp size={13} aria-hidden="true" className="shrink-0" />
                        : server.is_installed
                        ? <CheckCircle2 size={13} aria-hidden="true" className="shrink-0" />
                        : <CircleSlash size={13} aria-hidden="true" className="shrink-0" />}
                      {server.is_installed === undefined ? '未上报' : server.is_installed ? '已安装' : '未安装'}
                    </span>
                    <button
                      type="button"
                      onClick={() => setExpanded(isExpanded ? null : server.id)}
                      aria-expanded={isExpanded}
                      aria-controls={`mcp-config-${server.id}`}
                      className="flex h-11 min-w-11 shrink-0 items-center justify-center gap-1 rounded-[var(--radius-md)] px-1.5 text-xs text-[var(--color-text-muted)] transition-colors hover:bg-[var(--color-bg-surface-2)] hover:text-[var(--color-text-primary)] sm:min-w-0"
                    >
                      <ServerCog size={13} aria-hidden="true" />
                      <span className="hidden sm:inline">安装配置</span>
                      <ChevronRight size={12} aria-hidden="true" className={isExpanded ? 'rotate-90 transition-transform' : 'transition-transform'} />
                    </button>
                    {server.is_installed === true ? (
                      <Button
                        variant="ghost"
                        size="sm"
                        icon={<Trash2 size={13} aria-hidden="true" />}
                        onClick={() => uninstallServer(server.id)}
                        disabled={installing !== null}
                        loading={installing === server.id}
                        aria-label={`卸载 ${server.name}`}
                        className="shrink-0 text-[var(--color-error)] hover:bg-[var(--color-error-subtle)]"
                      >
                        卸载
                      </Button>
                    ) : server.is_installed === false ? (
                      <Button
                        variant="secondary"
                        size="sm"
                        icon={<Download size={13} aria-hidden="true" />}
                        onClick={() => installServer(server.id)}
                        disabled={installing !== null}
                        loading={installing === server.id}
                        className="shrink-0"
                      >
                        安装
                      </Button>
                    ) : (
                      <Button variant="outline" size="sm" disabled aria-label="状态未上报">未上报</Button>
                    )}
                  </div>
                  {isExpanded && (
                      <div id={`mcp-config-${server.id}`} className="mt-2 pl-7 text-xs text-[var(--color-text-secondary)]">
                       <div className="grid gap-2 sm:grid-cols-3">
                         <div><span className="text-[var(--color-text-muted)]">Server</span><p className="mt-0.5 break-all">{server.name}</p></div>
                         <div><span className="text-[var(--color-text-muted)]">Tools</span><p className="mt-0.5">{toolCount ?? t('common.none')}</p></div>
                         <div><span className="text-[var(--color-text-muted)]">Resources</span><p className="mt-0.5">{resourceCount ?? t('common.none')}</p></div>
                       </div>
                       <p className="mt-2 break-words">配置字段：{configFields.join(', ') || t('common.none')}</p>
                       {tools.length > 0 && (
                         <div className="mt-2 border-l border-[var(--color-border-default)] pl-3">
                           <p className="text-[var(--color-text-muted)]">Tools</p>
                           <ul className="mt-1 space-y-1">
                             {tools.map((tool, index) => <li key={typeof tool === 'string' ? tool : `${tool.name}-${index}`} className="break-words">{typeof tool === 'string' ? tool : tool.name}{typeof tool !== 'string' && tool.description ? ` · ${tool.description}` : ''}</li>)}
                           </ul>
                         </div>
                       )}
                       {resources.length > 0 && (
                         <div className="mt-2 border-l border-[var(--color-border-default)] pl-3">
                           <p className="text-[var(--color-text-muted)]">Resources</p>
                           <ul className="mt-1 space-y-1">
                             {resources.map((resource, index) => <li key={typeof resource === 'string' ? resource : `${resource.name}-${index}`} className="break-words">{typeof resource === 'string' ? resource : [resource.name, resource.uri, resource.description].filter(Boolean).join(' · ')}</li>)}
                           </ul>
                         </div>
                       )}
                      {server.tags && server.tags.length > 0 && (
                        <div className="mt-1 flex flex-wrap gap-1.5">
                          {server.tags.map(tag => (
                            <Badge key={tag} variant="secondary" size="xs">{tag}</Badge>
                          ))}
                        </div>
                   )}
                   {actionError && (
                     <div role="alert" className="mt-2 flex items-center gap-2 pl-7 text-xs text-[var(--color-error)]">
                       <span className="min-w-0 flex-1 break-words">{actionError}</span>
                       <Button variant="ghost" size="sm" onClick={retry} disabled={installing !== null} loading={installing === server.id}>{t('common.retry')}</Button>
                     </div>
                   )}
                    </div>
                  )}
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </div>
  );
}
