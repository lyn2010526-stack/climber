import { CheckCircle2, AlertCircle, Clock, Cpu, Timer, Pause, Play, Square } from 'lucide-react';

interface ProgressHeaderProps {
  status: string;
  currentRound: number;
  maxRounds: number;
  activeMember?: string;
  totalTokens?: number;
  elapsedTime?: number;
  onPause?: () => void;
  onResume?: () => void;
  onStop?: () => void;
}

const STATUS_LABELS: Record<string, string> = {
  idle: '就绪',
  running: '执行中',
  reviewing: '审查中',
  paused: '已暂停',
  completed: '已完成',
  partial: '部分完成',
  failed: '失败',
  stopped: '已停止',
};

const STATUS_COLORS: Record<string, string> = {
  idle: 'text-gray-500',
  running: 'text-blue-400',
  reviewing: 'text-amber-400',
  paused: 'text-amber-400',
  completed: 'text-green-400',
  partial: 'text-amber-400',
  failed: 'text-red-400',
  stopped: 'text-gray-500',
};

export function ProgressHeader({ status, currentRound, maxRounds, activeMember, totalTokens, elapsedTime = 0, onPause, onResume, onStop }: ProgressHeaderProps) {
  const progressPct = Math.min(Math.round((currentRound / Math.max(maxRounds, 1)) * 100), 100);

  const formatTime = (seconds: number): string => {
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return `${m}:${s.toString().padStart(2, '0')}`;
  };

  return (
    <div className="h-10 flex items-center px-4 border-b border-gray-700 bg-gray-800/50 gap-4">
      {/* Status */}
      <div className="flex items-center gap-1.5">
        {status === 'completed' ? (
          <CheckCircle2 size={12} className="text-green-400" />
        ) : status === 'failed' ? (
          <AlertCircle size={12} className="text-red-400" />
        ) : (
          <Clock size={12} className={STATUS_COLORS[status] || 'text-gray-500'} />
        )}
        <span className={`text-[10px] font-medium ${STATUS_COLORS[status] || 'text-gray-500'}`}>
          {STATUS_LABELS[status] || status}
        </span>
      </div>

      {/* Progress bar */}
      <div className="flex-1 max-w-48">
        <div className="h-1.5 bg-gray-700 rounded-full overflow-hidden">
          <div
            className="h-full bg-blue-600 rounded-full transition-all duration-300"
            style={{ width: `${progressPct}%` }}
          />
        </div>
      </div>

      {/* Round info */}
      <span className="text-[10px] text-gray-500">
        轮次 {currentRound}/{maxRounds}
      </span>

      {/* Active member */}
      {activeMember && (
        <span className="text-[10px] text-blue-400">
          {activeMember} 执行中...
        </span>
      )}

      {/* Token usage */}
      {totalTokens !== undefined && totalTokens > 0 && (
        <div className="flex items-center gap-1 text-[10px] text-gray-500">
          <Cpu size={10} />
          {totalTokens.toLocaleString()} tokens
        </div>
      )}

      {/* Elapsed time */}
      {(status === 'running' || status === 'reviewing' || status === 'completed') && (
        <div className="flex items-center gap-1 text-[10px] text-gray-500">
          <Timer size={10} />
          {formatTime(elapsedTime)}
        </div>
      )}

      {/* Controls */}
      {status === 'running' && (
        <div className="flex items-center gap-1 ml-auto">
          {onPause && (
            <button
              onClick={onPause}
              className="p-1 rounded hover:bg-gray-700 text-gray-400 hover:text-white transition-colors"
              title="暂停"
            >
              <Pause size={12} />
            </button>
          )}
          {onStop && (
            <button
              onClick={onStop}
              className="p-1 rounded hover:bg-gray-700 text-gray-400 hover:text-red-400 transition-colors"
              title="停止"
            >
              <Square size={12} />
            </button>
          )}
        </div>
      )}
      {status === 'paused' && (
        <div className="flex items-center gap-1 ml-auto">
          {onResume && (
            <button
              onClick={onResume}
              className="p-1 rounded hover:bg-gray-700 text-green-400 hover:text-green-300 transition-colors"
              title="恢复"
            >
              <Play size={12} />
            </button>
          )}
          {onStop && (
            <button
              onClick={onStop}
              className="p-1 rounded hover:bg-gray-700 text-gray-400 hover:text-red-400 transition-colors"
              title="停止"
            >
              <Square size={12} />
            </button>
          )}
        </div>
      )}
    </div>
  );
}
