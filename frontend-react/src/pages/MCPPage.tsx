import { useState, useEffect } from 'react';
import { Download, Trash2, Search, Check, Server, Star, RefreshCw, AlertCircle } from 'lucide-react';
import { api } from '../api';

interface MCPServer {
  id: string;
  name: string;
  description: string;
  category: string;
  author: string;
  is_builtin: boolean;
  is_installed: boolean;
  tags: string[];
  install_config: Record<string, any>;
  popularity: number;
}

export function MCPPage() {
  const [servers, setServers] = useState<MCPServer[]>([]);
  const [categories, setCategories] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [selectedCategory, setSelectedCategory] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [pendingServerId, setPendingServerId] = useState<string | null>(null);

  useEffect(() => {
    fetchServers();
    fetchCategories();
  }, []);

  const fetchServers = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.listMCPServers();
        setServers(data);
     } catch (e: any) {
       setError(e.message || '加载 MCP 服务器失败');
     }
    setLoading(false);
  };

  const fetchCategories = async () => {
    try {
      const data = await api.listMCPCategories();
        setCategories(data);
    } catch (e) {
      console.error('加载分类失败:', e);
    }
  };

  const installServer = async (serverId: string) => {
    if (pendingServerId) return;
    setPendingServerId(serverId);
    setActionError(null);
    try {
      await api.installMCPServer(serverId, {});
        setServers(prev => prev.map(s =>
          s.id === serverId ? { ...s, is_installed: true } : s
        ));
    } catch (e) {
      console.error('Failed to install:', e);
      setActionError('安装 MCP 服务器失败，请重试');
    } finally {
      setPendingServerId(null);
    }
  };

  const uninstallServer = async (serverId: string) => {
    if (pendingServerId) return;
    setPendingServerId(serverId);
    setActionError(null);
    try {
      await api.deleteMCPServer(serverId);
        setServers(prev => prev.map(s =>
          s.id === serverId ? { ...s, is_installed: false } : s
        ));
    } catch (e) {
      console.error('Failed to uninstall:', e);
      setActionError('卸载 MCP 服务器失败，请重试');
    } finally {
      setPendingServerId(null);
    }
  };

  const filteredServers = servers.filter(s => {
    const matchesCategory = !selectedCategory || s.category === selectedCategory;
    const matchesSearch = !searchQuery ||
      s.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      s.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
      s.tags.some(t => t.toLowerCase().includes(searchQuery.toLowerCase()));
    return matchesCategory && matchesSearch;
  });

  const groupedServers: Record<string, MCPServer[]> = {};
  for (const srv of filteredServers) {
    if (!groupedServers[srv.category]) groupedServers[srv.category] = [];
    groupedServers[srv.category]!.push(srv);
  }



  return (
    <div className="h-full overflow-y-auto p-8">
      <div className="max-w-5xl mx-auto">
        <div className="mb-8">
          <h2 className="text-2xl font-bold text-[var(--color-text-primary)]">MCP 市场</h2>
          <p className="text-[var(--color-text-secondary)] text-sm mt-1.5">
            安装 Model Context Protocol 服务器以扩展智能体能力
          </p>
        </div>

        {/* Search and filter */}
        <div className="flex gap-3 mb-6">
          <div className="flex-1 relative">
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--color-text-muted)]" />
            <input
              type="text"
              placeholder="搜索 MCP 服务器..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2.5 bg-[var(--color-bg-surface-2)] border border-[var(--color-border-subtle)] rounded-2xl text-sm text-[var(--color-text-primary)] placeholder:text-[var(--color-text-muted)] focus:outline-none focus:border-[var(--color-accent)]/50 transition-all duration-200"
            />
          </div>
          <select
            value={selectedCategory}
            onChange={(e) => setSelectedCategory(e.target.value)}
            className="px-4 py-2.5 bg-[var(--color-bg-surface-2)] border border-[var(--color-border-subtle)] rounded-2xl text-sm text-[var(--color-text-primary)] focus:outline-none focus:border-[var(--color-accent)]/50 transition-all duration-200"
          >
            <option value="">全部分类</option>
            {categories.map(c => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
        </div>

        {/* Error state */}
        {error && (
          <div role="alert" className="bg-[var(--color-error)]/10 border border-[var(--color-error)]/30 rounded-2xl p-4 mb-6 flex items-center gap-3">
            <AlertCircle size={18} className="text-[var(--color-error)] shrink-0" />
            <p className="text-sm text-[var(--color-error)] flex-1">{error}</p>
            <button
              onClick={fetchServers}
              className="flex items-center gap-1.5 px-3 py-1.5 text-sm text-[var(--color-error)] hover:bg-[var(--color-error)]/10 rounded-xl transition-colors"
            >
               <RefreshCw size={14} /> 重试
            </button>
          </div>
        )}

        {actionError && (
          <div role="alert" className="bg-[var(--color-error)]/10 border border-[var(--color-error)]/30 rounded-2xl p-4 mb-6 flex items-center gap-3">
            <AlertCircle size={18} className="text-[var(--color-error)] shrink-0" />
            <p className="text-sm text-[var(--color-error)] flex-1">{actionError}</p>
          </div>
        )}

        {/* Loading skeleton */}
        {loading && (
          <div className="space-y-6">
            {[1, 2].map(i => (
              <div key={i} className="animate-pulse">
                <div className="h-4 w-20 bg-[var(--color-bg-surface-2)] rounded-xl mb-3" />
                <div className="grid grid-cols-2 gap-4">
                  {[1, 2].map(j => (
                    <div key={j} className="bg-[var(--color-bg-surface-2)] border border-[var(--color-border-default)] rounded-2xl p-5">
                      <div className="flex items-start gap-3">
                        <div className="w-10 h-10 rounded-2xl bg-[var(--color-bg-surface-2)]" />
                        <div className="flex-1 space-y-2">
                          <div className="h-4 w-24 bg-[var(--color-bg-surface-2)] rounded-xl" />
                          <div className="h-3 w-full bg-[var(--color-bg-surface-2)] rounded-xl" />
                          <div className="h-3 w-3/4 bg-[var(--color-bg-surface-2)] rounded-xl" />
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Server grid grouped by category */}
        {!loading && !error && Object.entries(groupedServers).map(([cat, catServers]) => (
          <div key={cat} className="mb-8">
            <h3 className="text-sm font-semibold text-[var(--color-text-secondary)] mb-3 uppercase tracking-wide">
              {cat} ({catServers.length})
            </h3>
            <div className="grid grid-cols-2 gap-4">
              {catServers.map(server => (
                <div
                  key={server.id}
                  className={`bg-[var(--color-bg-surface-1)] border border-[var(--color-border-subtle)] rounded-2xl p-5 transition-all duration-200 ${
                    server.is_installed ? 'border-[var(--color-success)]/30' : 'hover:border-[var(--color-accent)]/30'
                  }`}
                >
                  <div className="flex items-start gap-3">
                    <div className="w-10 h-10 rounded-2xl bg-[var(--color-accent)]/10 flex items-center justify-center border border-[var(--color-accent)]/20">
                      <Server size={18} className="text-[var(--color-accent)]" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <h3 className="font-semibold truncate text-[var(--color-text-primary)]">{server.name}</h3>
                        {server.is_installed && (
                          <Check size={14} className="text-[var(--color-success)]" />
                        )}
                      </div>
                      <p className="text-sm text-[var(--color-text-muted)] mt-1 line-clamp-2">{server.description}</p>
                    </div>
                  </div>

                  {/* Meta */}
                  <div className="mt-3 flex items-center gap-2">
                     <span className="text-xs text-[var(--color-text-muted)]">作者：{server.author}</span>
                    {server.popularity > 0 && (
                      <span className="flex items-center gap-1 text-xs text-[var(--color-warning)]">
                        <Star size={10} fill="currentColor" /> {server.popularity}
                      </span>
                    )}
                  </div>

                  {/* Tags */}
                  <div className="mt-2 flex flex-wrap gap-1.5">
                    {server.tags.map(tag => (
                      <span key={tag} className="px-2.5 py-1 bg-[var(--color-bg-surface-2)] text-[var(--color-text-muted)] rounded-xl text-xs font-medium border border-[var(--color-border-subtle)]">
                        {tag}
                      </span>
                    ))}
                  </div>

                  {/* Action */}
                  <div className="mt-4 flex justify-end">
                    {server.is_installed ? (
                      <button
                        onClick={() => uninstallServer(server.id)}
                        disabled={pendingServerId !== null}
                        aria-label={`卸载 ${server.name}`}
                        className="flex items-center gap-2 px-4 py-2 border border-[var(--color-error)]/30 text-[var(--color-error)] hover:bg-[var(--color-error)]/10 rounded-2xl text-sm font-medium transition-all duration-200 disabled:opacity-40"
                      >
                        <Trash2 size={14} /> {pendingServerId === server.id ? '卸载中...' : '卸载'}
                      </button>
                    ) : (
                      <button
                        onClick={() => installServer(server.id)}
                        disabled={pendingServerId !== null}
                        aria-label={`安装 ${server.name}`}
                        className="flex items-center gap-2 px-4 py-2 bg-[var(--color-accent)] hover:bg-[var(--color-accent-hover)] text-white rounded-2xl text-sm font-semibold disabled:opacity-40 transition-all duration-200 active:scale-[0.97] shadow-lg shadow-[var(--color-accent)]/20"
                      >
                        <Download size={14} />
                        {pendingServerId === server.id ? '安装中...' : '安装'}
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        ))}

        {!loading && !error && filteredServers.length === 0 && (
          <div className="text-center py-16">
            <div className="w-16 h-16 rounded-3xl bg-[var(--color-bg-surface-2)] border border-[var(--color-border-subtle)] flex items-center justify-center mx-auto mb-4">
              <Server size={28} className="text-[var(--color-text-muted)]" />
            </div>
            <p className="text-[var(--color-text-muted)] text-sm">未找到 MCP 服务器。</p>
          </div>
        )}
      </div>
    </div>
  );
}
