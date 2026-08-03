import { useState, useMemo } from 'react';
import {
  Search, Plus, Server, Activity,
  CheckCircle2, WifiOff,
} from 'lucide-react';
import { ServerCard } from './ServerCard';
import { AddServerWizard } from './AddServerWizard';

interface MCPServer {
  id: string;
  name: string;
  transport: 'stdio' | 'http' | 'sse';
  url?: string;
  command?: string;
  status: 'connected' | 'connecting' | 'disconnected' | 'error';
  toolCount: number;
  lastPing?: number;
  tools?: Array<{ name: string; description: string }>;
}

const mockServers: MCPServer[] = [
  {
    id: '1',
    name: 'Filesystem',
    transport: 'stdio',
    command: 'npx -y @modelcontextprotocol/server-filesystem /workspace',
    status: 'connected',
    toolCount: 8,
    lastPing: 12,
    tools: [
      { name: 'read_file', description: '读取文件内容' },
      { name: 'write_file', description: '写入文件内容' },
      { name: 'list_directory', description: '列出目录内容' },
      { name: 'create_directory', description: '创建新目录' },
      { name: 'move_file', description: '移动或重命名文件' },
      { name: 'search_files', description: '搜索文件' },
      { name: 'get_file_info', description: '获取文件信息' },
      { name: 'read_multiple_files', description: '读取多个文件' },
    ],
  },
  {
    id: '2',
    name: 'GitHub',
    transport: 'stdio',
    command: 'npx -y @modelcontextprotocol/server-github',
    status: 'connected',
    toolCount: 15,
    lastPing: 45,
    tools: [
      { name: 'create_issue', description: '创建 Issue' },
      { name: 'list_repositories', description: '列出仓库' },
      { name: 'search_code', description: '搜索代码' },
    ],
  },
  {
    id: '3',
    name: 'PostgreSQL',
    transport: 'stdio',
    command: 'npx -y @modelcontextprotocol/server-postgres postgresql://localhost/db',
    status: 'disconnected',
    toolCount: 5,
  },
  {
    id: '4',
    name: 'Remote API',
    transport: 'http',
    url: 'https://api.example.com/mcp',
    status: 'error',
    toolCount: 0,
  },
  {
    id: '5',
    name: 'Stream Events',
    transport: 'sse',
    url: 'https://events.example.com/sse',
    status: 'connecting',
    toolCount: 3,
  },
];

export function MCPManager() {
  const [search, setSearch] = useState('');
  const [servers, setServers] = useState(mockServers);
  const [showWizard, setShowWizard] = useState(false);

  const filtered = useMemo(() => {
    if (!search) return servers;
    return servers.filter(s =>
      s.name.toLowerCase().includes(search.toLowerCase()) ||
      s.transport.includes(search.toLowerCase())
    );
  }, [servers, search]);

  const stats = useMemo(() => ({
    total: servers.length,
    connected: servers.filter(s => s.status === 'connected').length,
    tools: servers.reduce((sum, s) => sum + s.toolCount, 0),
  }), [servers]);

  const handleStart = (id: string) => {
    setServers(prev => prev.map(s =>
      s.id === id ? { ...s, status: 'connecting' as const } : s
    ));
    setTimeout(() => {
      setServers(prev => prev.map(s =>
        s.id === id ? { ...s, status: 'connected' as const, lastPing: Math.floor(Math.random() * 50) + 5 } : s
      ));
    }, 1500);
  };

  const handleStop = (id: string) => {
    setServers(prev => prev.map(s =>
      s.id === id ? { ...s, status: 'disconnected' as const } : s
    ));
  };

  const handleRestart = (id: string) => {
    handleStop(id);
    setTimeout(() => handleStart(id), 500);
  };

  const handleAdd = (data: any) => {
    const newServer: MCPServer = {
      id: String(Date.now()),
      name: data.name,
      transport: data.transport,
      command: data.command,
      url: data.url,
      status: 'disconnected',
      toolCount: 0,
    };
    setServers(prev => [newServer, ...prev]);
  };

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="px-6 pt-6 pb-4">
        <div className="flex items-center justify-between mb-5">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-xl bg-gradient-to-br from-emerald-500 to-teal-500 shadow-lg shadow-emerald-500/20">
              <Server size={18} className="text-white" />
            </div>
            <div>
              <h1 className="text-lg font-semibold text-white">MCP 服务器</h1>
              <p className="text-xs text-[var(--color-text-muted)] mt-0.5">管理模型上下文协议服务器连接</p>
            </div>
          </div>
          <button
            onClick={() => setShowWizard(true)}
            className="flex items-center gap-1.5 px-4 py-2 rounded-xl bg-gradient-to-r from-emerald-500 to-teal-500 text-white text-xs font-medium shadow-lg shadow-emerald-500/20 hover:shadow-emerald-500/30 hover:brightness-110 transition-all"
          >
            <Plus size={13} />
            添加服务器
          </button>
        </div>

        {/* Stats bar */}
        <div className="grid grid-cols-3 gap-3 mb-4">
          <div className="p-3 rounded-xl bg-white/[0.03] border border-white/[0.06]">
            <div className="flex items-center gap-2 mb-1">
              <Server size={12} className="text-[var(--color-text-muted)]" />
              <span className="text-[10px] text-[var(--color-text-muted)]">服务器总数</span>
            </div>
            <div className="text-lg font-semibold text-white">{stats.total}</div>
          </div>
          <div className="p-3 rounded-xl bg-white/[0.03] border border-white/[0.06]">
            <div className="flex items-center gap-2 mb-1">
              <CheckCircle2 size={12} className="text-green-400" />
              <span className="text-[10px] text-[var(--color-text-muted)]">已连接</span>
            </div>
            <div className="text-lg font-semibold text-green-400">{stats.connected}</div>
          </div>
          <div className="p-3 rounded-xl bg-white/[0.03] border border-white/[0.06]">
            <div className="flex items-center gap-2 mb-1">
              <Activity size={12} className="text-blue-400" />
              <span className="text-[10px] text-[var(--color-text-muted)]">可用工具</span>
            </div>
            <div className="text-lg font-semibold text-blue-400">{stats.tools}</div>
          </div>
        </div>

        {/* Search */}
        <div className="relative">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--color-text-muted)]" />
          <input
            type="text"
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="搜索服务器..."
            className="w-full h-9 pl-9 pr-4 rounded-xl bg-white/[0.04] border border-white/[0.08] text-sm text-[var(--color-text-secondary)] placeholder:text-[var(--color-text-muted)] focus:outline-none focus:border-[var(--color-success)]/40 focus:bg-white/[0.06] transition-all"
          />
        </div>
      </div>

      {/* Server list */}
      <div className="flex-1 overflow-y-auto px-6 pb-6">
        {filtered.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16">
              <WifiOff size={32} className="text-[var(--color-text-muted)] mb-3" />
            <p className="text-sm text-[var(--color-text-muted)]">没有找到服务器</p>
            <p className="text-xs text-[var(--color-text-muted)] mt-1">尝试其他搜索词或添加新服务器</p>
          </div>
        ) : (
          <div className="space-y-3">
            {filtered.map(server => (
              <ServerCard
                key={server.id}
                server={server}
                onStart={handleStart}
                onStop={handleStop}
                onRestart={handleRestart}
              />
            ))}
          </div>
        )}
      </div>

      <AddServerWizard
        isOpen={showWizard}
        onClose={() => setShowWizard(false)}
        onAdd={handleAdd}
      />
    </div>
  );
}
