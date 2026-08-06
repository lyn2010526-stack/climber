import { useState, useEffect } from 'react';
import { Download, Trash2, Search, Check, Server, Star, RefreshCw, AlertCircle } from 'lucide-react';
import { api } from '../api';
import { PageHeader } from '../components/ui/PageHeader';
import { Card, CardContent } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Badge } from '../components/ui/Badge';
import { Input } from '../components/ui/Input';
import { EmptyState } from '../components/ui/EmptyState';
import { SkeletonCard } from '../components/ui/Skeleton';

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
  const [selectedCategory, setSelectedCategory] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [installing, setInstalling] = useState<string | null>(null);

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
    } catch { /* skip */ }
  };

  const installServer = async (serverId: string) => {
    setInstalling(serverId);
    try {
      await api.installMCPServer(serverId, {});
      setServers(prev => prev.map(s =>
        s.id === serverId ? { ...s, is_installed: true } : s
      ));
    } catch { /* skip */ }
    setInstalling(null);
  };

  const uninstallServer = async (serverId: string) => {
    try {
      await api.deleteMCPServer(serverId);
      setServers(prev => prev.map(s =>
        s.id === serverId ? { ...s, is_installed: false } : s
      ));
    } catch { /* skip */ }
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
    <div className="h-full overflow-y-auto page-transition">
      <div className="p-4 md:p-6 lg:p-8 max-w-6xl mx-auto">
        <PageHeader
          title="MCP 市场"
          description="安装 Model Context Protocol 服务器以扩展智能体能力"
          icon={<Server size={20} />}
        />

        <div className="flex flex-col sm:flex-row gap-3 mb-6">
          <div className="flex-1">
            <Input
              placeholder="搜索 MCP 服务器..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              icon={<Search size={16} />}
            />
          </div>
          <select
            value={selectedCategory}
            onChange={(e) => setSelectedCategory(e.target.value)}
            className="px-4 py-2.5 bg-[var(--color-bg-surface-2)] border border-[var(--color-border-subtle)] rounded-xl text-sm text-[var(--color-text-primary)] focus:outline-none focus:border-[var(--color-accent)]/50 transition-all duration-200"
          >
            <option value="">全部分类</option>
            {categories.map(c => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
        </div>

        {error && (
          <Card variant="default" className="mb-6 border-[var(--color-error)]/30">
            <CardContent className="p-4 flex items-center gap-3">
              <AlertCircle size={18} className="text-[var(--color-error)] shrink-0" />
              <p className="text-sm text-[var(--color-error)] flex-1">{error}</p>
              <Button variant="outline" size="sm" icon={<RefreshCw size={14} />} onClick={fetchServers}>
                重试
              </Button>
            </CardContent>
          </Card>
        )}

        {loading && (
          <div className="space-y-6">
            {[1, 2].map(i => (
              <div key={i}>
                <div className="h-4 w-20 bg-[var(--color-bg-surface-2)] rounded-xl mb-3" />
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {[1, 2].map(j => <SkeletonCard key={j} />)}
                </div>
              </div>
            ))}
          </div>
        )}

        {!loading && !error && filteredServers.length === 0 && (
          <EmptyState
            icon="file"
            title="未找到 MCP 服务器"
            description="尝试其他搜索关键词或分类"
          />
        )}

        {!loading && !error && Object.entries(groupedServers).map(([cat, catServers]) => (
          <div key={cat} className="mb-8">
            <h3 className="text-xs font-semibold text-[var(--color-text-muted)] uppercase tracking-wider mb-4">
              {cat} ({catServers.length})
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 stagger-children">
              {catServers.map(server => (
                <Card key={server.id} variant="default" className={`hover-lift ${server.is_installed ? 'border-[var(--color-success)]/30' : ''}`}>
                  <CardContent className="p-5">
                    <div className="flex items-start gap-3">
                      <div className="w-10 h-10 rounded-xl bg-[var(--color-accent)]/10 flex items-center justify-center border border-[var(--color-accent)]/20 shrink-0">
                        <Server size={18} className="text-[var(--color-accent)]" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <h3 className="font-semibold text-sm text-[var(--color-text-primary)] truncate">{server.name}</h3>
                          {server.is_installed && (
                            <Check size={14} className="text-[var(--color-success)] shrink-0" />
                          )}
                        </div>
                        <p className="text-xs text-[var(--color-text-muted)] mt-1 line-clamp-2">{server.description}</p>
                      </div>
                    </div>

                    <div className="mt-3 flex items-center gap-2">
                      <span className="text-xs text-[var(--color-text-muted)]">作者：{server.author}</span>
                      {server.popularity > 0 && (
                        <span className="flex items-center gap-1 text-xs text-[var(--color-warning)]">
                          <Star size={10} fill="currentColor" /> {server.popularity}
                        </span>
                      )}
                    </div>

                    {server.tags.length > 0 && (
                      <div className="mt-2 flex flex-wrap gap-1.5">
                        {server.tags.map(tag => (
                          <Badge key={tag} variant="default" size="xs">{tag}</Badge>
                        ))}
                      </div>
                    )}

                    <div className="mt-4 flex justify-end">
                      {server.is_installed ? (
                        <Button
                          variant="outline"
                          size="sm"
                          icon={<Trash2 size={14} />}
                          onClick={() => uninstallServer(server.id)}
                          className="text-[var(--color-error)] border-[var(--color-error)]/30 hover:bg-[var(--color-error)]/10"
                        >
                          卸载
                        </Button>
                      ) : (
                        <Button
                          variant="primary"
                          size="sm"
                          icon={<Download size={14} />}
                          onClick={() => installServer(server.id)}
                          disabled={installing === server.id}
                          loading={installing === server.id}
                        >
                          安装
                        </Button>
                      )}
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
