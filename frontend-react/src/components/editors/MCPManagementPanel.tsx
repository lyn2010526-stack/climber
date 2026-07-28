import { useState } from 'react';
import {
  Server, Power, PowerOff, Settings, Plus,
  Shield, Hash, CheckCircle2,
} from 'lucide-react';

interface MCPServerConfig {
  id: string;
  name: string;
  type: 'stdio' | 'http' | 'sse';
  url: string;
  status: 'online' | 'offline' | 'error';
  tools: MCPToolConfig[];
  rateLimit: number;
  timeout: number;
  maxResultLength: number;
}

interface MCPToolConfig {
  name: string;
  enabled: boolean;
  description: string;
}

export function MCPManagementPanel() {
  const [servers, setServers] = useState<MCPServerConfig[]>([
    {
      id: 'filesystem',
      name: 'Filesystem',
      type: 'stdio',
      url: 'npx -y @modelcontextprotocol/server-filesystem',
      status: 'online',
      tools: [
        { name: 'read_file', enabled: true, description: 'Read file contents' },
        { name: 'write_file', enabled: true, description: 'Write to file' },
        { name: 'delete_file', enabled: false, description: 'Delete file (dangerous)' },
      ],
      rateLimit: 60,
      timeout: 30,
      maxResultLength: 50000,
    },
    {
      id: 'github',
      name: 'GitHub',
      type: 'stdio',
      url: 'npx -y @modelcontextprotocol/server-github',
      status: 'online',
      tools: [
        { name: 'create_issue', enabled: true, description: 'Create GitHub issue' },
        { name: 'create_pr', enabled: true, description: 'Create pull request' },
      ],
      rateLimit: 30,
      timeout: 60,
      maxResultLength: 100000,
    },
  ]);

  const [selectedServer, setSelectedServer] = useState<string | null>(servers[0]?.id || null);
  const activeServer = servers.find(s => s.id === selectedServer);

  const toggleServer = (id: string) => {
    setServers(prev => prev.map(s =>
      s.id === id ? { ...s, status: s.status === 'online' ? 'offline' : 'online' } : s
    ));
  };

  const toggleTool = (serverId: string, toolName: string) => {
    setServers(prev => prev.map(s =>
      s.id === serverId
        ? { ...s, tools: s.tools.map(t => t.name === toolName ? { ...t, enabled: !t.enabled } : t) }
        : s
    ));
  };

  return (
    <div className="h-full flex">
      {/* Server list */}
      <div className="w-48 border-r border-gray-700 flex flex-col">
        <div className="p-2 border-b border-gray-700">
          <div className="flex items-center justify-between px-1 mb-1">
            <span className="text-[10px] font-semibold text-gray-500 uppercase">服务器</span>
            <button className="p-0.5 text-gray-500 hover:text-blue-400">
              <Plus size={12} />
            </button>
          </div>
        </div>
        <div className="flex-1 overflow-y-auto p-1 space-y-0.5">
          {servers.map(server => (
            <button
              key={server.id}
              onClick={() => setSelectedServer(server.id)}
              className={`w-full flex items-center gap-2 px-2 py-1.5 rounded-lg text-left transition-colors ${
                selectedServer === server.id
                  ? 'bg-blue-600/10 text-blue-400'
                  : 'text-gray-400 hover:bg-gray-700/50'
              }`}
            >
              <Server size={12} />
              <span className="text-xs truncate flex-1">{server.name}</span>
              <span className={`w-1.5 h-1.5 rounded-full ${
                server.status === 'online' ? 'bg-green-500' :
                server.status === 'error' ? 'bg-red-500' : 'bg-text-muted'
              }`} />
            </button>
          ))}
        </div>
      </div>

      {/* Server detail */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {activeServer ? (
          <>
            {/* Header */}
            <div className="px-4 py-3 border-b border-gray-700 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Server size={14} className="text-blue-400" />
                <span className="text-sm font-medium">{activeServer.name}</span>
                <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium ${
                  activeServer.status === 'online' ? 'bg-green-500/10 text-green-400' :
                  activeServer.status === 'error' ? 'bg-red-500/10 text-red-400' :
                  'bg-gray-700 text-gray-500'
                }`}>
                  {activeServer.status}
                </span>
              </div>
              <button
                onClick={() => toggleServer(activeServer.id)}
                className={`p-1.5 rounded-lg transition-colors ${
                  activeServer.status === 'online'
                    ? 'text-green-400 hover:bg-green-500/10'
                    : 'text-gray-500 hover:bg-gray-700/50'
                }`}
              >
                {activeServer.status === 'online' ? <Power size={14} /> : <PowerOff size={14} />}
              </button>
            </div>

            {/* Config */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4">
              {/* Connection info */}
              <div className="space-y-2">
                <h4 className="text-xs font-medium text-gray-400 flex items-center gap-1.5">
                  <Settings size={11} /> Connection
                </h4>
                <div className="p-2 bg-gray-700 rounded-lg">
                  <div className="flex justify-between text-xs">
                     <span className="text-gray-500">类型</span>
                    <span className="text-gray-400 capitalize">{activeServer.type}</span>
                  </div>
                  <div className="flex justify-between text-xs mt-1">
                     <span className="text-gray-500">命令</span>
                    <span className="text-gray-400 font-mono text-[10px] truncate max-w-[200px]">{activeServer.url}</span>
                  </div>
                </div>
              </div>

              {/* Rate limits */}
              <div className="space-y-2">
                <h4 className="text-xs font-medium text-gray-400 flex items-center gap-1.5">
                  <Shield size={11} /> Limits
                </h4>
                <div className="grid grid-cols-3 gap-2">
                  <div className="p-2 bg-gray-700 rounded-lg text-center">
                    <div className="text-xs font-medium">{activeServer.rateLimit}</div>
                     <div className="text-[10px] text-gray-500">请求/分</div>
                  </div>
                  <div className="p-2 bg-gray-700 rounded-lg text-center">
                    <div className="text-xs font-medium">{activeServer.timeout}s</div>
                     <div className="text-[10px] text-gray-500">超时</div>
                  </div>
                  <div className="p-2 bg-gray-700 rounded-lg text-center">
                    <div className="text-xs font-medium">{(activeServer.maxResultLength / 1000).toFixed(0)}k</div>
                     <div className="text-[10px] text-gray-500">最大字符</div>
                  </div>
                </div>
              </div>

              {/* Tool-level permissions */}
              <div className="space-y-2">
                <h4 className="text-xs font-medium text-gray-400 flex items-center gap-1.5">
                  <Hash size={11} /> Tool Permissions
                </h4>
                <div className="space-y-1">
                  {activeServer.tools.map(tool => (
                    <div
                      key={tool.name}
                      className="flex items-center gap-2 p-2 bg-gray-700 rounded-lg"
                    >
                      <button
                        onClick={() => toggleTool(activeServer.id, tool.name)}
                        className={`w-4 h-4 rounded border flex items-center justify-center transition-colors ${
                          tool.enabled
                            ? 'bg-blue-600 border-blue-500'
                            : 'border-gray-600'
                        }`}
                      >
                        {tool.enabled && <CheckCircle2 size={10} className="text-white" />}
                      </button>
                      <div className="flex-1 min-w-0">
                        <span className="text-xs font-mono text-gray-100">{tool.name}</span>
                        <p className="text-[10px] text-gray-500 truncate">{tool.description}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </>
        ) : (
          <div className="flex-1 flex items-center justify-center text-gray-500">
            <p className="text-sm">Select a server to configure</p>
          </div>
        )}
      </div>
    </div>
  );
}
