import { Loader2, Wifi, WifiOff, AlertTriangle } from 'lucide-react';
import { cn } from '../../lib/utils';

export type StreamingState = 'idle' | 'connecting' | 'streaming' | 'paused' | 'error' | 'complete';

interface StreamingStatusProps {
  state: StreamingState;
  tokensPerSecond?: number;
  totalTokens?: number;
  className?: string;
}

const stateConfig = {
  idle: { color: 'var(--color-text-muted)', label: '' },
  connecting: { color: 'var(--color-warning)', label: '连接中...' },
  streaming: { color: 'var(--color-success)', label: '生成中' },
  paused: { color: 'var(--color-warning)', label: '已暂停' },
  error: { color: 'var(--color-error)', label: '连接中断' },
  complete: { color: 'var(--color-text-muted)', label: '完成' },
};

export function StreamingStatus({ state, tokensPerSecond, totalTokens, className }: StreamingStatusProps) {
  const config = stateConfig[state];

  if (state === 'idle') return null;

  return (
    <div className={cn('flex items-center gap-2 px-3 py-1.5 rounded-lg', className)}>
      <div className="flex items-center gap-1.5">
        {state === 'streaming' && (
          <Loader2 size={11} className="animate-spin" style={{ color: config.color }} />
        )}
        {state === 'error' && <WifiOff size={11} style={{ color: config.color }} />}
        {state === 'complete' && <Wifi size={11} style={{ color: config.color }} />}

        <span className="text-[10px] font-medium" style={{ color: config.color }}>
          {config.label}
        </span>
      </div>

      {state === 'streaming' && tokensPerSecond !== undefined && (
        <span className="text-[10px] text-[var(--color-text-muted)] tabular-nums">
          {tokensPerSecond.toFixed(1)} tok/s
        </span>
      )}

      {totalTokens !== undefined && state === 'complete' && (
        <span className="text-[10px] text-[var(--color-text-muted)]">
          {totalTokens} tokens
        </span>
      )}
    </div>
  );
}
