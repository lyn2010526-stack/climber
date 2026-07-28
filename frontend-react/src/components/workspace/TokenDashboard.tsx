import { Brain, MessageSquare, Database, AlertTriangle } from 'lucide-react';

interface TokenDashboardProps {
  workingMemory: number;
  workingMemoryLimit: number;
  persistentMemoryLoad: number;
  persistentMemoryLimit: number;
  singleRequestLimit: number;
  singleRequestUsed: number;
}

export function TokenDashboard({
  workingMemory,
  workingMemoryLimit = 128000,
  persistentMemoryLoad,
  persistentMemoryLimit = 50000,
  singleRequestLimit = 4096,
  singleRequestUsed,
}: TokenDashboardProps) {
  const hasData = workingMemory !== undefined || persistentMemoryLoad !== undefined || singleRequestUsed !== undefined;

  const workingPct = workingMemory ? (workingMemory / workingMemoryLimit) * 100 : 0;
  const persistentPct = persistentMemoryLoad ? (persistentMemoryLoad / persistentMemoryLimit) * 100 : 0;
  const singlePct = singleRequestUsed ? (singleRequestUsed / singleRequestLimit) * 100 : 0;

  const isWarning = workingPct > 80 || persistentPct > 80 || singlePct > 90;

  return (
    <div className="space-y-3">
      {!hasData && (
        <div className="text-center py-4">
          <p className="text-xs text-gray-500">暂无 Token 使用数据</p>
          <p className="text-[10px] text-gray-600 mt-1">Start a session to see usage metrics</p>
        </div>
      )}

      {isWarning && (
        <div className="flex items-center gap-2 p-2 bg-amber-500/10 border border-amber-500/30 rounded-lg">
          <AlertTriangle size={12} className="text-amber-400" />
           <span className="text-[10px] text-amber-400">上下文使用量过高 — 建议归档</span>
        </div>
      )}

      <TokenGauge
         label="工作记忆"
        icon={MessageSquare}
        used={workingMemory}
        limit={workingMemoryLimit}
        percentage={workingPct}
        color="accent"
      />
      <TokenGauge
         label="持久记忆"
        icon={Database}
        used={persistentMemoryLoad}
        limit={persistentMemoryLimit}
        percentage={persistentPct}
        color="purple"
      />
      <TokenGauge
         label="单次请求"
        icon={Brain}
        used={singleRequestUsed}
        limit={singleRequestLimit}
        percentage={singlePct}
        color="success"
      />

      <button className="w-full px-3 py-1.5 text-xs text-blue-400 bg-blue-600/10 rounded-lg hover:bg-blue-600/20 transition-colors">
         自动归档关键信息
      </button>
    </div>
  );
}

function TokenGauge({
  label,
  icon: Icon,
  used,
  limit,
  percentage,
  color,
}: {
  label: string;
  icon: any;
  used?: number;
  limit: number;
  percentage: number;
  color: string;
}) {
  const colorMap: Record<string, string> = {
    accent: 'bg-blue-600',
    purple: 'bg-purple-400',
    success: 'bg-green-500',
    warning: 'bg-amber-500',
  };

  const barColor = percentage > 90 ? 'bg-red-500' : percentage > 80 ? 'bg-amber-500' : colorMap[color] || 'bg-blue-600';
  const hasValue = used !== undefined && used !== null;

  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1.5">
          <Icon size={11} className="text-gray-500" />
          <span className="text-[10px] text-gray-400">{label}</span>
        </div>
        <span className="text-[10px] text-gray-500">
          {hasValue ? `${(used / 1000).toFixed(1)}k / ${(limit / 1000).toFixed(0)}k` : '—'}
        </span>
      </div>
      <div className="w-full h-1.5 bg-gray-700 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all ${barColor}`}
          style={{ width: `${Math.min(percentage, 100)}%` }}
        />
      </div>
    </div>
  );
}
