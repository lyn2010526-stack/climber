import { useState, useEffect } from 'react';
import { Search, Download, Trash2, ToggleLeft, ToggleRight, RefreshCw, Package, AlertCircle } from 'lucide-react';
import { api } from '../api';

interface Plugin {
  id: string;
  name: string;
  type: string;
  source: string;
  status: string;
  description: string;
  icon: string;
  category: string;
  version: string;
  config: Record<string, any>;
  error: string | null;
}

export default function PluginPage() {
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

  useEffect(() => {
    loadPlugins();
  }, []);

  const loadPlugins = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.listPlugins();
      setPlugins(data);
    } catch (e: any) {
      setError(e.message || '加载插件失败');
    }
    setLoading(false);
  };

  const togglePlugin = async (plugin: Plugin) => {
    setToggling(plugin.id);
    try {
      if (plugin.status === 'enabled') {
        await api.disablePlugin(plugin.id);
        setPlugins(prev => prev.map(p => p.id === plugin.id ? { ...p, status: 'disabled' } : p));
      } else {
        await api.enablePlugin(plugin.id);
        setPlugins(prev => prev.map(p => p.id === plugin.id ? { ...p, status: 'enabled' } : p));
      }
    } catch (e: any) {
      setError(e.message || 'Failed to toggle plugin');
    }
    setToggling(null);
  };

  const deletePlugin = async (pluginId: string) => {
    setDeleting(pluginId);
    try {
      await api.uninstallPlugin(pluginId);
      setPlugins(prev => prev.filter(p => p.id !== pluginId));
    } catch (e: any) {
      setError(e.message || 'Failed to delete plugin');
    }
    setDeleting(null);
  };

  const importPlugin = async () => {
    if (!importUrl) return;
    setImporting(true);
    setError(null);
    try {
      await api.importPlugin(importUrl, importName);
      setImportUrl('');
      setImportName('');
      setShowImport(false);
      loadPlugins();
    } catch (e: any) {
      setError(e.message || 'Failed to import plugin');
    }
    setImporting(false);
  };

  const filtered = plugins.filter(p =>
    !searchQuery ||
    p.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    p.description.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="h-full overflow-y-auto p-8">
      <div className="max-w-5xl mx-auto">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h2 className="text-2xl font-bold text-[var(--color-text-primary)]">插件管理</h2>
            <p className="text-[var(--color-text-secondary)] text-sm mt-1">管理已安装的插件并导入新插件</p>
          </div>
          <button
            onClick={() => setShowImport(!showImport)}
            className="flex items-center gap-2 px-4 py-2.5 bg-[var(--color-accent)] hover:bg-[var(--color-accent-hover)] text-white rounded-2xl text-sm font-semibold transition-all duration-200 active:scale-[0.97]"
          >
             <Download size={16} /> 导入插件
          </button>
        </div>

        {showImport && (
          <div className="bg-[var(--color-bg-surface-1)] border border-[var(--color-border-subtle)] rounded-2xl p-6 mb-6">
             <h3 className="font-medium text-[var(--color-text-primary)] mb-4">从链接导入</h3>
            <div className="space-y-3">
              <input
                 placeholder="插件源地址（GitHub、MCP 配置...）"
                value={importUrl}
                onChange={(e) => setImportUrl(e.target.value)}
                className="w-full px-3 py-2.5 bg-[var(--color-bg-surface-2)] border border-[var(--color-border-subtle)] rounded-2xl text-sm text-[var(--color-text-primary)] focus:outline-none focus:border-[var(--color-accent)]/50 transition-all duration-200"
              />
              <input
                 placeholder="显示名称（可选）"
                value={importName}
                onChange={(e) => setImportName(e.target.value)}
                className="w-full px-3 py-2.5 bg-[var(--color-bg-surface-2)] border border-[var(--color-border-subtle)] rounded-2xl text-sm text-[var(--color-text-primary)] focus:outline-none focus:border-[var(--color-accent)]/50 transition-all duration-200"
              />
            </div>
            <div className="flex justify-end gap-3 mt-4">
              <button
                onClick={() => setShowImport(false)}
                className="px-4 py-2 text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] text-sm transition-colors"
              >
                 取消
              </button>
              <button
                onClick={importPlugin}
                disabled={!importUrl || importing}
                className="px-6 py-2 bg-[var(--color-accent)] hover:bg-[var(--color-accent-hover)] text-white rounded-2xl text-sm font-semibold disabled:opacity-50 transition-all duration-200 active:scale-[0.97]"
              >
                 {importing ? '导入中...' : '导入'}
              </button>
            </div>
          </div>
        )}

        {/* Search */}
        <div className="mb-6">
          <div className="relative">
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--color-text-muted)]" />
            <input
              type="text"
               placeholder="搜索插件..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2.5 bg-[var(--color-bg-surface-2)] border border-[var(--color-border-subtle)] rounded-2xl text-sm text-[var(--color-text-primary)] placeholder:text-[var(--color-text-muted)] focus:outline-none focus:border-[var(--color-accent)]/50 transition-all duration-200"
            />
          </div>
        </div>

        {/* Error state */}
        {error && (
          <div className="bg-[var(--color-error)]/10 border border-[var(--color-error)]/30 rounded-2xl p-4 mb-6 flex items-center gap-3">
            <AlertCircle size={18} className="text-[var(--color-error)] shrink-0" />
            <p className="text-sm text-[var(--color-error)] flex-1">{error}</p>
            <button
              onClick={loadPlugins}
              className="flex items-center gap-1.5 px-3 py-1.5 text-sm text-[var(--color-error)] hover:bg-[var(--color-error)]/10 rounded-xl transition-colors"
            >
               <RefreshCw size={14} /> 重试
            </button>
          </div>
        )}

        {/* Loading skeleton */}
        {loading && (
          <div className="space-y-3">
            {[1, 2, 3, 4].map(i => (
              <div key={i} className="bg-[var(--color-bg-surface-1)] border border-[var(--color-border-subtle)] rounded-2xl p-5 animate-pulse">
                <div className="flex items-center gap-4">
                  <div className="w-10 h-10 rounded-lg bg-white/[0.03]" />
                  <div className="flex-1 space-y-2">
                    <div className="h-4 w-32 bg-white/[0.03] rounded-xl" />
                    <div className="h-3 w-64 bg-white/[0.03] rounded-xl" />
                  </div>
                  <div className="h-6 w-16 bg-white/[0.03] rounded-full" />
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Plugin list */}
        {!loading && !error && (
          <div className="space-y-3">
            {filtered.map(plugin => (
              <div
                key={plugin.id}
                className="bg-[var(--color-bg-surface-1)] border border-[var(--color-border-subtle)] rounded-2xl p-5 flex items-center gap-4 hover:border-[var(--color-accent)]/30 transition-all duration-200"
              >
                <div className="w-10 h-10 rounded-lg bg-[var(--color-accent)]/10 flex items-center justify-center border border-[var(--color-accent)]/20">
                  <Package size={20} className="text-[var(--color-accent)]" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <h3 className="font-medium truncate text-[var(--color-text-primary)]">{plugin.name}</h3>
                    {plugin.version && (
                      <span className="text-xs text-[var(--color-text-muted)] bg-white/[0.03] border border-[var(--color-border-subtle)] px-2 py-0.5 rounded">v{plugin.version}</span>
                    )}
                    <span className="text-xs text-[var(--color-text-muted)] bg-white/[0.03] border border-[var(--color-border-subtle)] px-2 py-0.5 rounded">{plugin.type}</span>
                  </div>
                  <p className="text-sm text-[var(--color-text-muted)] mt-1 line-clamp-1">{plugin.description}</p>
                </div>
                <div className="flex items-center gap-3">
                  <button
                    onClick={() => togglePlugin(plugin)}
                    disabled={toggling === plugin.id}
                    className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-medium transition-all duration-200 ${
                      plugin.status === 'enabled'
                        ? 'bg-[var(--color-success)]/10 text-[var(--color-success)] hover:bg-[var(--color-success)]/20 border border-[var(--color-success)]/20'
                        : 'bg-white/[0.03] text-[var(--color-text-muted)] hover:bg-white/[0.06] border border-[var(--color-border-subtle)]'
                    }`}
                  >
                     {plugin.status === 'enabled' ? (
                       <><ToggleRight size={14} /> 已启用</>
                     ) : (
                       <><ToggleLeft size={14} /> 已禁用</>
                     )}
                  </button>
                  <button
                    onClick={() => deletePlugin(plugin.id)}
                    disabled={deleting === plugin.id}
                    className="p-2 hover:bg-[var(--color-error)]/10 rounded-xl text-[var(--color-text-muted)] hover:text-[var(--color-error)] transition-all duration-200"
                  >
                    <Trash2 size={16} />
                  </button>
                </div>
              </div>
            ))}
            {filtered.length === 0 && (
              <div className="text-center py-16 text-[var(--color-text-muted)]">
                <Package size={48} className="mx-auto mb-4 opacity-30" />
                <p>{searchQuery ? '没有匹配的插件。' : '尚未安装任何插件。'}</p>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
