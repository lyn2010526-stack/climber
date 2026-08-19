import { useState, useEffect, useCallback } from 'react';
import {
  Search, Download, Trash2, Power, PowerOff, Package, Brain,
  Server, FileText, Star, ChevronRight, X,
  Loader2, Plus, Filter, Zap,
} from 'lucide-react';
import { api } from '../api';

interface Plugin {
  id: string;
  name: string;
  description: string;
  type: 'skill' | 'mcp' | 'prompt';
  source: string;
  status: 'enabled' | 'disabled' | 'installed' | 'error';
  icon: string;
  category: string;
  version: string;
  tools?: string[];
  tags?: string[];
  popularity?: number;
  error?: string;
}

const TYPE_CONFIG = {
  skill: { icon: Brain, color: 'text-purple-400', bg: 'bg-purple-500/10', border: 'border-purple-500/20', label: 'Skill' },
  mcp: { icon: Server, color: 'text-blue-400', bg: 'bg-blue-500/10', border: 'border-blue-500/20', label: 'MCP' },
  prompt: { icon: FileText, color: 'text-amber-400', bg: 'bg-amber-500/10', border: 'border-amber-500/20', label: 'Prompt' },
};

const CATEGORY_ALL = 'all';
const CATEGORY_INSTALLED = 'installed';

export function PluginsPage() {
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

  const fetchPlugins = useCallback(async () => {
    try {
      const data = await api.listPlugins();
      setPlugins(data);
    } catch (e) {
      console.error('加载插件失败:', e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchPlugins(); }, [fetchPlugins]);

  const handleInstall = async (id: string) => {
    setActionLoading(id);
    try {
      await api.installPlugin(id);
      await fetchPlugins();
    } catch (e) { console.error(e); }
    finally { setActionLoading(null); }
  };

  const handleUninstall = async (id: string) => {
    setActionLoading(id);
    try {
      await api.uninstallPlugin(id);
      await fetchPlugins();
    } catch (e) { console.error(e); }
    finally { setActionLoading(null); }
  };

  const handleToggle = async (plugin: Plugin) => {
    setActionLoading(plugin.id);
    try {
      if (plugin.status === 'enabled') {
        await api.disablePlugin(plugin.id);
      } else {
        await api.enablePlugin(plugin.id);
      }
      await fetchPlugins();
    } catch (e) { console.error(e); }
    finally { setActionLoading(null); }
  };

  const handleImport = async () => {
    if (!importUrl.trim()) return;
    try {
      await api.importPlugin(importUrl, importName, importType);
      setImportModalOpen(false);
      setImportUrl('');
      setImportName('');
      await fetchPlugins();
    } catch (e) { console.error(e); }
  };

  const filtered = plugins.filter(p => {
    const matchSearch = !searchQuery ||
      p.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      p.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (p.tags || []).some(t => t.toLowerCase().includes(searchQuery.toLowerCase()));
    const matchType = !selectedType || p.type === selectedType;
    const matchCat = selectedCategory === CATEGORY_ALL ||
      (selectedCategory === CATEGORY_INSTALLED && (p.status === 'enabled' || p.status === 'installed')) ||
      p.category === selectedCategory;
    return matchSearch && matchType && matchCat;
  });

  const categories = [...new Set(plugins.map(p => p.category).filter(Boolean))];
  const grouped: Record<string, Plugin[]> = {};
  for (const p of filtered) {
    const cat = p.category || 'other';
    if (!grouped[cat]) grouped[cat] = [];
    grouped[cat].push(p);
  }

  const enabledCount = plugins.filter(p => p.status === 'enabled').length;
  const totalCount = plugins.length;

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center">
        <Loader2 size={32} className="text-[var(--color-accent)] animate-spin" />
      </div>
    );
  }

  return (
    <div className="h-full overflow-y-auto p-8">
      <div className="max-w-7xl mx-auto">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h2 className="text-2xl font-bold text-[var(--color-text-primary)] flex items-center gap-3">
              <div className="w-10 h-10 rounded-2xl bg-[var(--color-accent)]/10 flex items-center justify-center border border-[var(--color-accent)]/20">
                <Package size={20} className="text-[var(--color-accent)]" />
              </div>
                插件市场
             </h2>
             <p className="text-[var(--color-text-secondary)] text-sm mt-1">
               共 {totalCount} 个插件，{enabledCount} 个已启用 — 技能、MCP 服务器、提示词模板
             </p>
          </div>
          <button
            onClick={() => setImportModalOpen(true)}
            className="flex items-center gap-2 px-4 py-2.5 bg-[var(--color-accent)] hover:bg-[var(--color-accent-hover)] text-white rounded-2xl text-sm font-semibold transition-all duration-200 active:scale-[0.97]"
          >
             <Plus size={16} /> 导入插件
          </button>
        </div>

        <div className="flex gap-3 mb-6">
          <div className="flex-1 relative">
            <Search size={16} className="absolute left-4 top-1/2 -translate-y-1/2 text-[var(--color-text-muted)]" />
            <input
              type="text"
              placeholder="按名称、描述或标签搜索插件..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-11 pr-4 py-3 bg-[var(--color-bg-surface-2)] border border-[var(--color-border-subtle)] rounded-2xl text-sm text-[var(--color-text-primary)] placeholder:text-[var(--color-text-muted)] focus:outline-none focus:border-[var(--color-accent)]/50 transition-all duration-200"
            />
          </div>
          <div className="flex gap-2">
            {(['', 'skill', 'mcp', 'prompt'] as const).map(type => (
              <button
                key={type || 'all'}
                onClick={() => setSelectedType(type)}
                className={`px-4 py-2 rounded-2xl text-sm font-medium border transition-all duration-200 ${
                  selectedType === type
                    ? 'bg-[var(--color-accent)]/15 border-[var(--color-accent)]/30 text-[var(--color-text-primary)]'
                    : 'bg-white/[0.03] border-[var(--color-border-subtle)] text-[var(--color-text-muted)] hover:border-[var(--color-accent)]/30'
                }`}
              >
                 {type ? TYPE_CONFIG[type].label : '全部'}
              </button>
            ))}
          </div>
        </div>

        <div className="flex gap-2 mb-8 overflow-x-auto pb-2">
          <button
            onClick={() => setSelectedCategory(CATEGORY_ALL)}
            className={`px-3 py-1.5 rounded-xl text-xs font-medium whitespace-nowrap border transition-all duration-200 ${
              selectedCategory === CATEGORY_ALL
                ? 'bg-[var(--color-accent)]/15 text-[var(--color-accent)] border-[var(--color-accent)]/30'
                : 'bg-white/[0.03] text-[var(--color-text-muted)] border-[var(--color-border-subtle)] hover:text-[var(--color-text-primary)]'
            }`}
          >
              全部 ({totalCount})
          </button>
          <button
            onClick={() => setSelectedCategory(CATEGORY_INSTALLED)}
            className={`px-3 py-1.5 rounded-xl text-xs font-medium whitespace-nowrap border transition-all duration-200 ${
              selectedCategory === CATEGORY_INSTALLED
                ? 'bg-[var(--color-accent)]/15 text-[var(--color-accent)] border-[var(--color-accent)]/30'
                : 'bg-white/[0.03] text-[var(--color-text-muted)] border-[var(--color-border-subtle)] hover:text-[var(--color-text-primary)]'
            }`}
          >
              已启用 ({enabledCount})
          </button>
          {categories.map(cat => {
            const count = plugins.filter(p => p.category === cat).length;
            return (
              <button
                key={cat}
                onClick={() => setSelectedCategory(cat)}
                className={`px-3 py-1.5 rounded-xl text-xs font-medium whitespace-nowrap capitalize border transition-all duration-200 ${
                  selectedCategory === cat
                    ? 'bg-[var(--color-accent)]/15 text-[var(--color-accent)] border-[var(--color-accent)]/30'
                    : 'bg-white/[0.03] text-[var(--color-text-muted)] border-[var(--color-border-subtle)] hover:text-[var(--color-text-primary)]'
                }`}
              >
                {cat} ({count})
              </button>
            );
          })}
        </div>

        {Object.entries(grouped).map(([cat, catPlugins]) => (
          <div key={cat} className="mb-10">
            <h3 className="text-sm font-semibold text-[var(--color-text-muted)] uppercase tracking-wider mb-4 flex items-center gap-2">
              <Filter size={12} />
              {cat}
              <span className="text-[var(--color-text-muted)] font-normal">({catPlugins.length})</span>
            </h3>
            <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-4">
              {catPlugins.map(plugin => (
                <PluginCard
                  key={plugin.id}
                  plugin={plugin}
                  isExpanded={expandedPlugin === plugin.id}
                  isActionLoading={actionLoading === plugin.id}
                  onToggle={() => handleToggle(plugin)}
                  onInstall={() => handleInstall(plugin.id)}
                  onUninstall={() => handleUninstall(plugin.id)}
                  onExpand={() => setExpandedPlugin(expandedPlugin === plugin.id ? null : plugin.id)}
                />
              ))}
            </div>
          </div>
        ))}

        {filtered.length === 0 && (
          <div className="text-center py-20">
            <Package size={48} className="mx-auto mb-4 text-[var(--color-text-muted)] opacity-30" />
             <p className="text-[var(--color-text-muted)] text-lg">未找到插件</p>
             <p className="text-[var(--color-text-muted)] text-sm mt-1">尝试调整搜索或筛选条件</p>
          </div>
        )}
      </div>

      {importModalOpen && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50" onClick={() => setImportModalOpen(false)}>
          <div className="bg-[var(--color-bg-surface-1)] border border-[var(--color-border-subtle)] rounded-2xl p-6 w-full max-w-lg shadow-2xl" onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-lg font-semibold text-[var(--color-text-primary)] flex items-center gap-2">
                 <Download size={18} className="text-[var(--color-accent)]" /> 导入插件
               </h3>
               <button onClick={() => setImportModalOpen(false)} className="p-1 rounded-xl hover:bg-white/[0.06] text-[var(--color-text-muted)]">
                 <X size={18} />
               </button>
            </div>

            <div className="space-y-4">
              <div>
                 <label className="block text-sm font-medium text-[var(--color-text-secondary)] mb-1.5">源地址</label>
                 <input
                   type="url"
                   value={importUrl}
                   onChange={(e) => setImportUrl(e.target.value)}
                   placeholder="https://github.com/user/mcp-server 或原始 JSON URL"
                  className="w-full px-4 py-2.5 bg-[var(--color-bg-surface-2)] border border-[var(--color-border-subtle)] rounded-2xl text-sm text-[var(--color-text-primary)] placeholder:text-[var(--color-text-muted)] focus:outline-none focus:border-[var(--color-accent)]/50 transition-all duration-200"
                 />
               </div>
               <div>
                 <label className="block text-sm font-medium text-[var(--color-text-secondary)] mb-1.5">名称（可选）</label>
                 <input
                   type="text"
                   value={importName}
                   onChange={(e) => setImportName(e.target.value)}
                   placeholder="我的自定义插件"
                  className="w-full px-4 py-2.5 bg-[var(--color-bg-surface-2)] border border-[var(--color-border-subtle)] rounded-2xl text-sm text-[var(--color-text-primary)] placeholder:text-[var(--color-text-muted)] focus:outline-none focus:border-[var(--color-accent)]/50 transition-all duration-200"
                 />
               </div>
               <div>
                 <label className="block text-sm font-medium text-[var(--color-text-secondary)] mb-1.5">类型</label>
                <select
                  value={importType}
                  onChange={(e) => setImportType(e.target.value)}
                  className="w-full px-4 py-2.5 bg-[var(--color-bg-surface-2)] border border-[var(--color-border-subtle)] rounded-2xl text-sm text-[var(--color-text-primary)]"
                >
                   <option value="mcp">MCP 服务器</option>
                   <option value="skill">技能</option>
                   <option value="prompt">提示词模板</option>
                 </select>
               </div>
             </div>

            <div className="flex justify-end gap-3 mt-6">
              <button
                onClick={() => setImportModalOpen(false)}
                className="px-4 py-2 rounded-xl text-sm text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] transition-colors"
              >
                  取消
              </button>
              <button
                onClick={handleImport}
                disabled={!importUrl.trim()}
                className="px-5 py-2 bg-[var(--color-accent)] hover:bg-[var(--color-accent-hover)] text-white rounded-2xl text-sm font-semibold disabled:opacity-50 transition-all duration-200 active:scale-[0.97]"
              >
                  导入
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function PluginCard({
  plugin,
  isExpanded,
  isActionLoading,
  onToggle,
  onInstall,
  onUninstall,
  onExpand,
}: {
  plugin: Plugin;
  isExpanded: boolean;
  isActionLoading: boolean;
  onToggle: () => void;
  onInstall: () => void;
  onUninstall: () => void;
  onExpand: () => void;
}) {
  const typeConf = TYPE_CONFIG[plugin.type] || TYPE_CONFIG.skill;
  const TypeIcon = typeConf.icon;
  const isEnabled = plugin.status === 'enabled';
  const isInstalled = isEnabled || plugin.status === 'installed';

  return (
    <div
      className={`group relative bg-[var(--color-bg-surface-1)] border rounded-2xl p-5 transition-all duration-200 ${
        isEnabled
          ? 'border-[var(--color-accent)]/30 shadow-lg shadow-[var(--color-accent)]/5 hover:border-[var(--color-accent)]/50'
          : 'border-[var(--color-border-subtle)] hover:border-[var(--color-accent)]/30'
      }`}
    >
      {isEnabled && (
        <div className="absolute top-4 right-4 flex items-center gap-1.5">
          <div className="w-2 h-2 rounded-full bg-[var(--color-success)] animate-pulse" />
           <span className="text-xs text-[var(--color-success)] font-medium">已启用</span>
        </div>
      )}

      <div className="flex items-start gap-3 mb-3">
        <div className={`w-10 h-10 rounded-xl ${typeConf.bg} flex items-center justify-center shrink-0 border ${typeConf.border}`}>
          {plugin.icon ? (
            <span className="text-lg">{plugin.icon}</span>
          ) : (
            <TypeIcon size={18} className={typeConf.color} />
          )}
        </div>
        <div className="flex-1 min-w-0">
          <h4 className="font-medium text-sm truncate pr-16 text-[var(--color-text-primary)]">{plugin.name}</h4>
          <div className="flex items-center gap-2 mt-0.5">
            <span className={`px-2 py-0.5 rounded-lg text-xs font-medium border ${typeConf.bg} ${typeConf.color} ${typeConf.border}`}>
              {typeConf.label}
            </span>
            {plugin.popularity && plugin.popularity > 0 && (
              <span className="flex items-center gap-0.5 text-xs text-amber-400">
                <Star size={10} fill="currentColor" /> {plugin.popularity}
              </span>
            )}
          </div>
        </div>
      </div>

      <p className="text-xs text-[var(--color-text-muted)] leading-relaxed mb-3 line-clamp-2">
        {plugin.description}
      </p>

      {plugin.tags && plugin.tags.length > 0 && (
        <div className="flex flex-wrap gap-1.5 mb-3">
          {plugin.tags.slice(0, 3).map(tag => (
            <span key={tag} className="px-2 py-0.5 bg-white/[0.03] rounded-lg text-xs text-[var(--color-text-muted)] border border-[var(--color-border-subtle)]">
              {tag}
            </span>
          ))}
          {plugin.tags.length > 3 && (
            <span className="px-2 py-0.5 text-xs text-[var(--color-text-muted)]">+{plugin.tags.length - 3}</span>
          )}
        </div>
      )}

      {plugin.type === 'mcp' && plugin.tools && plugin.tools.length > 0 && (
        <div className="flex items-center gap-1.5 mb-3 text-xs text-[var(--color-text-muted)]">
          <Zap size={10} />
           <span>{plugin.tools.length} 个可用工具</span>
        </div>
      )}

      {isExpanded && (
        <div className="mt-3 pt-3 border-t border-[var(--color-border-subtle)] space-y-2">
          <div className="flex items-center justify-between text-xs">
             <span className="text-[var(--color-text-muted)]">来源</span>
            <span className="text-[var(--color-text-secondary)] capitalize">{plugin.source}</span>
          </div>
          <div className="flex items-center justify-between text-xs">
             <span className="text-[var(--color-text-muted)]">版本</span>
            <span className="text-[var(--color-text-secondary)]">{plugin.version || '1.0.0'}</span>
          </div>
          {plugin.error && (
            <div className="mt-2 p-2 bg-[var(--color-error)]/10 rounded-xl text-xs text-[var(--color-error)] border border-[var(--color-error)]/20">
              {plugin.error}
            </div>
          )}
        </div>
      )}

      <div className="flex items-center justify-between mt-4 pt-3 border-t border-[var(--color-border-subtle)]">
        <button
          onClick={onExpand}
          className="flex items-center gap-1 text-xs text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] transition-colors"
        >
          Details <ChevronRight size={12} className={`transition-transform duration-200 ${isExpanded ? 'rotate-90' : ''}`} />
        </button>

        <div className="flex items-center gap-2">
          {isActionLoading ? (
            <LoaderSize16 />
          ) : isInstalled ? (
            <>
              <button
                onClick={onToggle}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-medium transition-all duration-200 border ${
                  isEnabled
                    ? 'bg-[var(--color-success)]/10 text-[var(--color-success)] hover:bg-[var(--color-success)]/20 border-[var(--color-success)]/20'
                    : 'bg-white/[0.03] text-[var(--color-text-muted)] hover:bg-white/[0.06] border-[var(--color-border-subtle)]'
                }`}
              >
                {isEnabled ? <Power size={12} /> : <PowerOff size={12} />}
                {isEnabled ? '已启用' : '启用'}
              </button>
              {plugin.source !== 'builtin' && (
                <button
                  onClick={onUninstall}
                  className="p-2 rounded-xl text-[var(--color-text-muted)] hover:text-[var(--color-error)] hover:bg-[var(--color-error)]/10 transition-all duration-200"
                >
                  <Trash2 size={14} />
                </button>
              )}
            </>
          ) : (
            <button
              onClick={onInstall}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-[var(--color-accent)] hover:bg-[var(--color-accent-hover)] text-white rounded-xl text-xs font-semibold transition-all duration-200 active:scale-[0.97]"
            >
              <Download size={12} /> Install
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

function LoaderSize16() {
  return <Loader2 size={16} className="text-[var(--color-accent)] animate-spin" />;
}
