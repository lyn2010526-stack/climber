// @ts-nocheck
import { useState } from 'react';
import {
  Search, Download, Trash2, Power, Star,
  Plus, Package, Brain, Server, FileText, Zap, ExternalLink, Settings,
} from 'lucide-react';
import { cn } from '../../lib/utils';
import { Card } from '../ui/Card';
import { Button } from '../ui/Button';
import { Badge } from '../ui/Badge';
import { Tabs } from '../ui/Controls';
import { Modal } from '../ui/Modal';

interface Plugin {
  id: string;
  name: string;
  description: string;
  type: 'skill' | 'mcp' | 'prompt';
  source: string;
  status: 'available' | 'installed' | 'enabled' | 'disabled' | 'error';
  category: string;
  version: string;
  author?: string;
  stars?: number;
  downloads?: number;
  tags?: string[];
  tools?: string[];
  rating?: number;
}

const TYPE_CONFIG = {
  skill: { icon: Brain, color: 'text-purple-400', bg: 'bg-purple-500/10', border: 'border-purple-500/20', label: 'Skill' },
  mcp: { icon: Server, color: 'text-blue-400', bg: 'bg-blue-500/10', border: 'border-blue-500/20', label: 'MCP' },
  prompt: { icon: FileText, color: 'text-amber-400', bg: 'bg-amber-500/10', border: 'border-amber-500/20', label: 'Prompt' },
};

const MOCK_PLUGINS: Plugin[] = [
  { id: '1', name: 'Code Runner', description: 'Execute code snippets in multiple languages', type: 'skill', source: 'official', status: 'installed', category: 'Development', version: '1.2.0', author: 'Climber Team', stars: 1240, downloads: 5800, tags: ['code', 'execution'], tools: ['python', 'javascript', 'bash'], rating: 4.8 },
  { id: '2', name: 'Web Search', description: 'Search the web for real-time information', type: 'mcp', source: 'official', status: 'enabled', category: 'Search', version: '2.0.1', author: 'Climber Team', stars: 2100, downloads: 12000, tags: ['search', 'web'], tools: ['google', 'bing'], rating: 4.9 },
  { id: '3', name: 'GitHub Integration', description: 'Interact with GitHub repos, PRs, and issues', type: 'mcp', source: 'community', status: 'available', category: 'Development', version: '1.5.0', author: 'devtools', stars: 890, downloads: 3200, tags: ['github', 'git'], tools: ['repos', 'prs', 'issues'], rating: 4.5 },
  { id: '4', name: 'Advanced Prompt', description: 'Enhanced prompt templates for coding tasks', type: 'prompt', source: 'community', status: 'installed', category: 'Prompts', version: '1.0.0', author: 'promptmaster', stars: 450, downloads: 1800, tags: ['coding', 'templates'], rating: 4.2 },
  { id: '5', name: 'Database Query', description: 'Query SQL databases directly', type: 'mcp', source: 'official', status: 'available', category: 'Data', version: '1.1.0', author: 'Climber Team', stars: 670, downloads: 2100, tags: ['sql', 'database'], tools: ['mysql', 'postgres'], rating: 4.6 },
  { id: '6', name: 'Image Generator', description: 'Generate images using AI models', type: 'skill', source: 'community', status: 'disabled', category: 'Creative', version: '0.9.0', author: 'creative-ai', stars: 320, downloads: 980, tags: ['image', 'dall-e'], rating: 4.0 },
];

const CATEGORIES = ['all', 'Development', 'Search', 'Prompts', 'Data', 'Creative'];

export function PluginMarketplace() {
  const [plugins, setPlugins] = useState<Plugin[]>(MOCK_PLUGINS);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [viewMode, setViewMode] = useState<'marketplace' | 'installed'>('marketplace');
  const [selectedPlugin, setSelectedPlugin] = useState<Plugin | null>(null);
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  const filteredPlugins = plugins.filter((p) => {
    if (viewMode === 'installed') {
      if (p.status !== 'installed' && p.status !== 'enabled' && p.status !== 'disabled') return false;
    }
    if (selectedCategory !== 'all' && p.category !== selectedCategory) return false;
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      return p.name.toLowerCase().includes(q) || p.description.toLowerCase().includes(q) || p.tags?.some(t => t.includes(q));
    }
    return true;
  });

  const handleInstall = async (id: string) => {
    setActionLoading(id);
    await new Promise(r => setTimeout(r, 1000));
    setPlugins(prev => prev.map(p => p.id === id ? { ...p, status: 'installed' as const } : p));
    setActionLoading(null);
  };

  const handleUninstall = async (id: string) => {
    setActionLoading(id);
    await new Promise(r => setTimeout(r, 800));
    setPlugins(prev => prev.map(p => p.id === id ? { ...p, status: 'available' as const } : p));
    setActionLoading(null);
  };

  const handleToggle = async (plugin: Plugin) => {
    setActionLoading(plugin.id);
    await new Promise(r => setTimeout(r, 500));
    setPlugins(prev => prev.map(p =>
      p.id === plugin.id
        ? { ...p, status: p.status === 'enabled' ? 'disabled' as const : 'enabled' as const }
        : p
    ));
    setActionLoading(null);
  };

  return (
    <div className="max-w-6xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-bold text-[var(--color-text-primary)]">插件市场</h1>
          <p className="text-sm text-[var(--color-text-muted)] mt-1">发现和安装扩展插件</p>
        </div>
        <Button variant="primary" size="sm" leftIcon={<Plus size={14} />}>
          开发插件
        </Button>
      </div>

      <div className="flex items-center gap-3 mb-4">
        <div className="flex-1 relative">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--color-text-muted)]" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="搜索插件..."
            className="w-full pl-9 pr-3 py-2 rounded-xl text-xs bg-[var(--color-bg-surface-2)] border border-[var(--color-border-subtle)] text-[var(--color-text-primary)] placeholder:text-[var(--color-text-muted)] focus:outline-none focus:border-[var(--color-accent)]/30 transition-colors"
            aria-label="搜索插件"
          />
        </div>
        <Tabs
          tabs={[
            { id: 'marketplace', label: '发现' },
            { id: 'installed', label: '已安装' },
          ]}
          activeTab={viewMode}
          onChange={(id) => setViewMode(id as 'marketplace' | 'installed')}
        />
      </div>

      <div className="flex items-center gap-2 mb-4 overflow-x-auto pb-2">
        {CATEGORIES.map((cat) => (
          <button
            key={cat}
            onClick={() => setSelectedCategory(cat)}
            className={cn(
              'px-3 py-1.5 rounded-full text-xs font-medium transition-all duration-200 whitespace-nowrap',
              selectedCategory === cat
                ? 'bg-[var(--color-accent)] text-white'
                : 'bg-[var(--color-bg-surface-2)] text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-surface-3)]'
            )}
          >
            {cat === 'all' ? '全部' : cat}
          </button>
        ))}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {filteredPlugins.map((plugin) => {
          const typeConfig = TYPE_CONFIG[plugin.type];
          const TypeIcon = typeConfig.icon;
          const isLoading = actionLoading === plugin.id;

          return (
            <Card key={plugin.id} variant="interactive" padding="md" className="group">
              <div className="flex items-start gap-3">
                <div className={cn('p-2 rounded-xl border', typeConfig.bg, typeConfig.border)}>
                  <TypeIcon size={18} className={typeConfig.color} />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <h3 className="text-sm font-semibold text-[var(--color-text-primary)] truncate">{plugin.name}</h3>
                    <Badge variant="default" size="xs">v{plugin.version}</Badge>
                  </div>
                  <p className="text-xs text-[var(--color-text-muted)] mt-1 line-clamp-2">{plugin.description}</p>
                  <div className="flex items-center gap-3 mt-2">
                    {plugin.rating !== undefined && (
                      <div className="flex items-center gap-1">
                        <Star size={10} className="text-amber-400 fill-amber-400" />
                        <span className="text-[10px] text-[var(--color-text-muted)]">{plugin.rating}</span>
                      </div>
                    )}
                    {plugin.downloads !== undefined && (
                      <div className="flex items-center gap-1">
                        <Download size={10} className="text-[var(--color-text-muted)]" />
                        <span className="text-[10px] text-[var(--color-text-muted)]">{plugin.downloads > 1000 ? `${(plugin.downloads / 1000).toFixed(1)}k` : plugin.downloads}</span>
                      </div>
                    )}
                    <span className="text-[10px] text-[var(--color-text-muted)]">{plugin.author}</span>
                  </div>
                </div>
              </div>

              <div className="flex items-center gap-2 mt-3 pt-3 border-t border-[var(--color-border-subtle)]">
                {plugin.status === 'available' ? (
                  <Button size="xs" variant="primary" onClick={() => handleInstall(plugin.id)} loading={isLoading} leftIcon={<Download size={12} />} className="flex-1">
                    安装
                  </Button>
                ) : (
                  <>
                    <Button size="xs" variant={plugin.status === 'enabled' ? 'secondary' : 'primary'} onClick={() => handleToggle(plugin)} loading={isLoading} leftIcon={plugin.status === 'enabled' ? <Power size={12} /> : <Zap size={12} />} className="flex-1">
                      {plugin.status === 'enabled' ? '禁用' : '启用'}
                    </Button>
                    <Button size="xs" variant="ghost" onClick={() => handleUninstall(plugin.id)} loading={isLoading} leftIcon={<Trash2 size={12} />}>
                      卸载
                    </Button>
                  </>
                )}
                <Button size="xs" variant="ghost" onClick={() => setSelectedPlugin(plugin)} leftIcon={<Settings size={12} />}>
                  详情
                </Button>
              </div>

              {plugin.tags && plugin.tags.length > 0 && (
                <div className="flex items-center gap-1 mt-2 flex-wrap">
                  {plugin.tags.slice(0, 3).map((tag) => (
                    <span key={tag} className="px-1.5 py-0.5 rounded text-[9px] bg-[var(--color-bg-surface-3)] text-[var(--color-text-muted)]">
                      #{tag}
                    </span>
                  ))}
                </div>
              )}
            </Card>
          );
        })}
      </div>

      {filteredPlugins.length === 0 && (
        <div className="text-center py-16">
          <Package size={48} className="mx-auto mb-4 text-[var(--color-text-muted)] opacity-30" />
          <p className="text-sm text-[var(--color-text-muted)]">未找到匹配的插件</p>
        </div>
      )}

      <Modal
        open={!!selectedPlugin}
        onClose={() => setSelectedPlugin(null)}
      >
        {selectedPlugin && (
          <div className="space-y-4">
            <h2 className="text-lg font-semibold text-[var(--color-text-primary)]">{selectedPlugin.name}</h2>
            <div className="flex items-center gap-3">
              <div className={cn('p-3 rounded-xl border', TYPE_CONFIG[selectedPlugin.type].bg, TYPE_CONFIG[selectedPlugin.type].border)}>
                {(() => { const Icon = TYPE_CONFIG[selectedPlugin.type].icon; return <Icon size={24} className={TYPE_CONFIG[selectedPlugin.type].color} />; })()}
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <Badge variant="default" size="sm">{TYPE_CONFIG[selectedPlugin.type].label}</Badge>
                  <Badge variant="default" size="sm">v{selectedPlugin.version}</Badge>
                </div>
                <p className="text-xs text-[var(--color-text-muted)] mt-1">by {selectedPlugin.author}</p>
              </div>
            </div>

            <p className="text-sm text-[var(--color-text-secondary)] leading-relaxed">{selectedPlugin.description}</p>

            {selectedPlugin.tools && selectedPlugin.tools.length > 0 && (
              <div>
                <h4 className="text-xs font-semibold text-[var(--color-text-muted)] uppercase tracking-wider mb-2">支持的工具</h4>
                <div className="flex flex-wrap gap-2">
                  {selectedPlugin.tools.map((tool) => (
                    <Badge key={tool} variant="default" size="sm">{tool}</Badge>
                  ))}
                </div>
              </div>
            )}

            <div className="flex items-center gap-4 pt-3 border-t border-[var(--color-border-subtle)]">
              <Button variant="primary" size="sm" leftIcon={<Download size={14} />}>
                安装插件
              </Button>
              <Button variant="ghost" size="sm" leftIcon={<ExternalLink size={14} />}>
                查看文档
              </Button>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}

export default PluginMarketplace;
