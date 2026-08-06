import { useState, useEffect } from 'react';
import { Search, Download, Trash2, ToggleLeft, ToggleRight, RefreshCw, Package, AlertCircle } from 'lucide-react';
import { api } from '../api';
import { PageHeader } from '../components/ui/PageHeader';
import { Card, CardContent } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Badge } from '../components/ui/Badge';
import { Input } from '../components/ui/Input';
import { EmptyState } from '../components/ui/EmptyState';
import { SkeletonList } from '../components/ui/Skeleton';

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
      setError(e.message || '操作失败');
    }
    setToggling(null);
  };

  const deletePlugin = async (pluginId: string) => {
    setDeleting(pluginId);
    try {
      await api.uninstallPlugin(pluginId);
      setPlugins(prev => prev.filter(p => p.id !== pluginId));
    } catch (e: any) {
      setError(e.message || '删除失败');
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
      setError(e.message || '导入失败');
    }
    setImporting(false);
  };

  const filtered = plugins.filter(p =>
    !searchQuery ||
    p.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    p.description.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="h-full overflow-y-auto page-transition">
      <div className="p-4 md:p-6 lg:p-8 max-w-5xl mx-auto">
        <PageHeader
          title="插件管理"
          description="管理已安装的插件并导入新插件"
          icon={<Package size={20} />}
          actions={
            <Button
              variant="primary"
              size="sm"
              icon={<Download size={14} />}
              onClick={() => setShowImport(!showImport)}
            >
              导入插件
            </Button>
          }
        />

        {showImport && (
          <Card variant="default" className="mb-6">
            <CardContent className="p-5 space-y-3">
              <h3 className="text-sm font-semibold text-[var(--color-text-primary)]">从链接导入</h3>
              <Input
                placeholder="插件源地址（GitHub、MCP 配置...）"
                value={importUrl}
                onChange={(e) => setImportUrl(e.target.value)}
              />
              <Input
                placeholder="显示名称（可选）"
                value={importName}
                onChange={(e) => setImportName(e.target.value)}
              />
              <div className="flex justify-end gap-3 pt-1">
                <Button variant="ghost" size="sm" onClick={() => setShowImport(false)}>取消</Button>
                <Button variant="primary" size="sm" onClick={importPlugin} disabled={!importUrl} loading={importing}>
                  导入
                </Button>
              </div>
            </CardContent>
          </Card>
        )}

        <div className="mb-6">
          <Input
            placeholder="搜索插件..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            icon={<Search size={16} />}
          />
        </div>

        {error && (
          <Card variant="default" className="mb-6 border-[var(--color-error)]/30">
            <CardContent className="p-4 flex items-center gap-3">
              <AlertCircle size={18} className="text-[var(--color-error)] shrink-0" />
              <p className="text-sm text-[var(--color-error)] flex-1">{error}</p>
              <Button variant="outline" size="sm" onClick={loadPlugins} icon={<RefreshCw size={14} />}>
                重试
              </Button>
            </CardContent>
          </Card>
        )}

        {loading && <SkeletonList count={4} />}

        {!loading && !error && filtered.length === 0 && (
          <EmptyState
            icon="file"
            title={searchQuery ? '没有匹配的插件' : '尚未安装任何插件'}
            description={searchQuery ? '尝试其他搜索关键词' : '导入插件以开始使用'}
          />
        )}

        {!loading && !error && filtered.length > 0 && (
          <div className="space-y-3 stagger-children">
            {filtered.map(plugin => (
              <Card key={plugin.id} variant="default" className="hover-lift">
                <CardContent className="p-5 flex items-center gap-4">
                  <div className="w-10 h-10 rounded-xl bg-[var(--color-accent)]/10 flex items-center justify-center border border-[var(--color-accent)]/20 shrink-0">
                    <Package size={20} className="text-[var(--color-accent)]" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <h3 className="font-semibold text-sm text-[var(--color-text-primary)] truncate">{plugin.name}</h3>
                      {plugin.version && (
                        <Badge variant="default" size="xs">v{plugin.version}</Badge>
                      )}
                      <Badge variant="info" size="xs">{plugin.type}</Badge>
                    </div>
                    <p className="text-xs text-[var(--color-text-muted)] mt-1 line-clamp-1">{plugin.description}</p>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <Button
                      variant={plugin.status === 'enabled' ? 'success' : 'outline'}
                      size="xs"
                      onClick={() => togglePlugin(plugin)}
                      disabled={toggling === plugin.id}
                      icon={plugin.status === 'enabled' ? <ToggleRight size={14} /> : <ToggleLeft size={14} />}
                    >
                      {plugin.status === 'enabled' ? '已启用' : '已禁用'}
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => deletePlugin(plugin.id)}
                      disabled={deleting === plugin.id}
                      className="text-[var(--color-text-muted)] hover:text-[var(--color-error)]"
                    >
                      <Trash2 size={16} />
                    </Button>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
