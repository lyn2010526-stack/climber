import { useState } from 'react';
import {
  cn,
} from '../../lib/utils';
import {
  WifiOff, Play, Square, RotateCcw,
  ChevronDown, Zap, Clock,
  Activity, AlertCircle, CheckCircle2,
} from 'lucide-react';

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

const statusConfig = {
  connected: { color: 'bg-green-500', text: 'text-green-400', label: '已连接', icon: CheckCircle2 },
  connecting: { color: 'bg-yellow-500', text: 'text-yellow-400', label: '连接中', icon: Activity },
  disconnected: { color: 'bg-[var(--color-text-muted)]', text: 'text-[var(--color-text-muted)]', label: '未连接', icon: WifiOff },
  error: { color: 'bg-red-500', text: 'text-red-400', label: '错误', icon: AlertCircle },
};

const transportLabels: Record<string, string> = {
  stdio: '标准输入输出',
  http: 'HTTP',
  sse: 'SSE',
};

interface ServerCardProps {
  server: MCPServer;
  onStart: (id: string) => void;
  onStop: (id: string) => void;
  onRestart: (id: string) => void;
}

export function ServerCard({ server, onStart, onStop, onRestart }: ServerCardProps) {
  const [expanded, setExpanded] = useState(false);
  const config = statusConfig[server.status];

  return (
    <div className={cn(
      'rounded-2xl border transition-all duration-200',
      server.status === 'connected'
        ? 'border-green-500/20 bg-green-500/[0.02]'
        : server.status === 'error'
          ? 'border-red-500/20 bg-red-500/[0.02]'
          : 'border-white/[0.06] bg-white/[0.02]'
    )}>
      <div className="p-4">
        {/* Header row */}
        <div className="flex items-center gap-3">
          {/* Status indicator */}
          <div className="relative">
            <div className={cn('w-3 h-3 rounded-full', config.color)} />
            {server.status === 'connected' && (
              <div className={cn('absolute inset-0 w-3 h-3 rounded-full animate-ping', config.color, 'opacity-30')} />
            )}
          </div>

          {/* Server info */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <h4 className="text-sm font-semibold text-white truncate">{server.name}</h4>
              <span className="px-1.5 py-0.5 rounded-md text-[10px] bg-white/[0.04] text-[var(--color-text-muted)] font-medium">
                {transportLabels[server.transport]}
              </span>
            </div>
            <div className="flex items-center gap-3 mt-1">
              <span className={cn('text-[11px] font-medium', config.text)}>{config.label}</span>
              <span className="text-[11px] text-[var(--color-text-muted)]">{server.toolCount} 个工具</span>
              {server.lastPing != null && (
                <span className="text-[11px] text-[var(--color-text-muted)] flex items-center gap-1">
                  <Clock size={10} />
                  {server.lastPing}ms
                </span>
              )}
            </div>
          </div>

          {/* Actions */}
          <div className="flex items-center gap-1.5">
            {server.status === 'connected' ? (
              <>
                <button
                  onClick={() => onRestart(server.id)}
                  className="p-1.5 rounded-lg bg-white/[0.04] text-[var(--color-text-muted)] hover:text-white hover:bg-white/[0.08] transition-all"
                  title="重启"
                >
                  <RotateCcw size={13} />
                </button>
                <button
                  onClick={() => onStop(server.id)}
                  className="p-1.5 rounded-lg bg-white/[0.04] text-[var(--color-text-muted)] hover:text-red-400 hover:bg-red-500/10 transition-all"
                  title="停止"
                >
                  <Square size={13} />
                </button>
              </>
            ) : (
              <button
                onClick={() => onStart(server.id)}
                className="p-1.5 rounded-lg bg-green-500/10 text-green-400 hover:bg-green-500/15 transition-all"
                title="启动"
              >
                <Play size={13} />
              </button>
            )}
            <button
              onClick={() => setExpanded(!expanded)}
              className="p-1.5 rounded-lg bg-white/[0.04] text-[var(--color-text-muted)] hover:text-white hover:bg-white/[0.08] transition-all"
            >
              <ChevronDown size={13} className={cn('transition-transform', expanded && 'rotate-180')} />
            </button>
          </div>
        </div>

        {/* Connection detail */}
        <div className="mt-2 ml-6">
          <code className="text-[11px] text-[var(--color-text-muted)] font-mono">
            {server.transport === 'stdio' ? server.command : server.url}
          </code>
        </div>
      </div>

      {/* Expanded tool list */}
      {expanded && server.tools && server.tools.length > 0 && (
        <div className="px-4 pb-4 pt-1 border-t border-white/[0.04]">
          <div className="text-[10px] font-semibold text-[var(--color-text-muted)] uppercase tracking-wider mb-2">可用工具</div>
          <div className="space-y-1.5">
            {server.tools.map(tool => (
              <div key={tool.name} className="flex items-center gap-2 px-2.5 py-1.5 rounded-lg bg-white/[0.02] hover:bg-white/[0.04] transition-colors">
                <Zap size={11} className="text-blue-400 flex-shrink-0" />
                <span className="text-[11px] text-[var(--color-text-secondary)] font-mono flex-1 truncate">{tool.name}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
