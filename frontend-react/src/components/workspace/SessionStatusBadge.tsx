import { Cpu } from 'lucide-react';

interface SessionStatusBadgeProps {
  status: 'idle' | 'running' | 'paused' | 'waiting' | 'error' | 'completed';
  tokens?: number;
  modelName?: string;
}

const statusConfig: Record<SessionStatusBadgeProps['status'], { label: string; dotClass: string; pulseClass: string }> = {
  idle: {
    label: '空闲',
    dotClass: 'bg-gray-500',
    pulseClass: '',
  },
  running: {
    label: '运行中',
    dotClass: 'bg-blue-400',
    pulseClass: 'animate-pulse',
  },
  paused: {
    label: '已暂停',
    dotClass: 'bg-yellow-400',
    pulseClass: '',
  },
  waiting: {
    label: '等待中',
    dotClass: 'bg-amber-400',
    pulseClass: '',
  },
  error: {
    label: '错误',
    dotClass: 'bg-red-400',
    pulseClass: '',
  },
  completed: {
    label: '完成',
    dotClass: 'bg-green-400',
    pulseClass: '',
  },
};

function formatTokens(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return String(n);
}

export function SessionStatusBadge({ status, tokens, modelName }: SessionStatusBadgeProps) {
  const config = statusConfig[status];
  const tooltipParts = [config.label];
  if (modelName) tooltipParts.push(modelName);
  if (tokens !== undefined) tooltipParts.push(`${formatTokens(tokens)} tokens 已用`);

  return (
    <div
      className="relative group"
      title={tooltipParts.join(' · ')}
    >
      <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-medium bg-gray-800 border border-gray-700 text-gray-100 cursor-default">
        <span className={`w-1.5 h-1.5 rounded-full ${config.dotClass} ${config.pulseClass}`} />
        <Cpu size={10} className="text-gray-400" />
        {config.label}
      </span>

      {(tokens !== undefined || modelName) && (
        <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-2 py-1 bg-gray-800 border border-gray-700 rounded text-[10px] text-gray-100 whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-50 shadow-lg">
          {modelName && <div className="text-gray-400">{modelName}</div>}
          {tokens !== undefined && <div className="text-gray-400">{formatTokens(tokens)} tokens 已用</div>}
        </div>
      )}
    </div>
  );
}
