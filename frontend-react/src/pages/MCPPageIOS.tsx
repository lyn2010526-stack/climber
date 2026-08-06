import { useState } from 'react';
import { Wifi, WifiOff, Plus } from 'lucide-react';
import {
  IOSPage,
  IOSListGroup,
  IOSListItem,
  IOSSearchBar,
  IOSFab,
  IOSBadge,
  IOSSwitch,
  toast,
} from '../components/ios';
import { cn } from '../lib/utils';

interface MCPServer {
  name: string;
  url: string;
  enabled: boolean;
  connected: boolean;
}

const initialServers: MCPServer[] = [
  { name: 'Filesystem', url: 'mcp://filesystem.local', enabled: true, connected: true },
  { name: 'GitHub', url: 'mcp://github.com/mcp', enabled: true, connected: true },
  { name: 'Database', url: 'mcp://db.internal:5432', enabled: true, connected: false },
  { name: 'Browser', url: 'mcp://browser.local', enabled: false, connected: false },
  { name: 'Playwright', url: 'mcp://playwright.local', enabled: true, connected: true },
  { name: 'Redis', url: 'mcp://cache.internal:6379', enabled: false, connected: false },
];

export function MCPPageIOS() {
  const [search, setSearch] = useState('');
  const [servers, setServers] = useState<MCPServer[]>(initialServers);

  const connectedCount = servers.filter((s) => s.connected).length;
  const enabledCount = servers.filter((s) => s.enabled).length;
  const totalCount = servers.length;

  const filteredServers = servers.filter(
    (s) =>
      s.name.toLowerCase().includes(search.toLowerCase()) ||
      s.url.toLowerCase().includes(search.toLowerCase())
  );

  const toggleEnabled = (index: number) => {
    setServers((prev) =>
      prev.map((s, i) => (i === index ? { ...s, enabled: !s.enabled } : s))
    );
  };

  return (
    <IOSPage className="h-full overflow-y-auto pb-24">
      <div className="px-4 pt-6 pb-2">
        <h1 className="ios-title-1 text-[var(--color-text-primary)]">MCP 服务器</h1>
        <p className="ios-subhead text-[var(--color-text-muted)] mt-1">
          Model Connection Protocol 管理
        </p>
      </div>

      <div className="flex gap-3 px-4 py-3">
        <div className="flex-1 ios-card rounded-xl p-3 text-center">
          <p className="ios-title-1 text-[var(--color-success)]">{connectedCount}</p>
          <p className="ios-caption text-[var(--color-text-muted)]">已连接</p>
        </div>
        <div className="flex-1 ios-card rounded-xl p-3 text-center">
          <p className="ios-title-1 text-[var(--color-accent)]">{enabledCount}</p>
          <p className="ios-caption text-[var(--color-text-muted)]">可用</p>
        </div>
        <div className="flex-1 ios-card rounded-xl p-3 text-center">
          <p className="ios-title-1 text-[var(--color-text-primary)]">{totalCount}</p>
          <p className="ios-caption text-[var(--color-text-muted)]">总数</p>
        </div>
      </div>

      <div className="px-4 pb-3">
        <IOSSearchBar
          value={search}
          onChange={setSearch}
          placeholder="搜索服务器..."
        />
      </div>

      <IOSListGroup title="已配置服务器" className="mb-6">
        {filteredServers.map((server, index) => (
          <IOSListItem
            key={server.name}
            icon={
              server.connected ? (
                <Wifi size={18} className="text-white" />
              ) : (
                <WifiOff size={18} className="text-white" />
              )
            }
            iconBg={server.connected ? 'var(--color-success)' : 'var(--color-text-muted)'}
            title={
              <span className="flex flex-col">
                <span>{server.name}</span>
                <span className="ios-footnote text-[var(--color-text-muted)] font-normal">
                  {server.url}
                </span>
              </span>
            }
            detail={
              <span className="flex items-center gap-2">
                <IOSBadge variant={server.connected ? 'success' : 'error'}>
                  {server.connected ? '已连接' : '已断开'}
                </IOSBadge>
                <IOSSwitch
                  checked={server.enabled}
                  onChange={() => toggleEnabled(index)}
                />
              </span>
            }
            showChevron={false}
          />
        ))}
      </IOSListGroup>

      <IOSFab
        icon={<Plus size={20} />}
        label="添加服务器"
        onClick={() => toast.info('打开添加服务器对话框')}
      />
    </IOSPage>
  );
}

export default MCPPageIOS;
