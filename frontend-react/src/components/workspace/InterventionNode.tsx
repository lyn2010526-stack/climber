import { User, GitBranch, RotateCcw } from 'lucide-react';

interface InterventionNodeProps {
  timestamp: number;
  userMessage: string;
  dagState: string;
  onUndo: () => void;
}

export function InterventionNode({ timestamp, userMessage, dagState, onUndo }: InterventionNodeProps) {
  return (
    <div className="mx-auto max-w-[80%] my-3">
      {/* Divider line with label */}
      <div className="flex items-center gap-3">
        <div className="flex-1 h-px bg-gradient-to-r from-transparent via-blue-500/30 to-transparent" />
        <div className="flex items-center gap-2 px-3 py-1.5 bg-[var(--color-bg-surface-1)] border border-blue-500/20 rounded-full">
          <GitBranch size={11} className="text-blue-400" />
           <span className="text-[10px] font-medium text-blue-400">干预节点</span>
        </div>
        <div className="flex-1 h-px bg-gradient-to-r from-transparent via-blue-500/30 to-transparent" />
      </div>

      {/* Intervention content */}
      <div className="mt-2 p-3 bg-[var(--color-bg-surface-1)] border border-blue-500/10 rounded-xl">
        <div className="flex items-start gap-2">
          <div className="w-6 h-6 rounded-full bg-blue-600/10 flex items-center justify-center shrink-0">
            <User size={12} className="text-blue-400" />
          </div>
          <div className="flex-1">
            <p className="text-xs text-[var(--color-text-primary)]">{userMessage}</p>
            <div className="flex items-center gap-2 mt-1.5">
              <span className="text-[10px] text-[var(--color-text-muted)]">
                {new Date(timestamp).toLocaleTimeString()}
              </span>
              <span className="text-[10px] text-blue-400">{dagState}</span>
            </div>
          </div>
          <button
            onClick={onUndo}
             className="p-1 text-[var(--color-text-muted)] hover:text-blue-400 transition-colors"
             title="撤销此干预"
          >
            <RotateCcw size={12} />
          </button>
        </div>
      </div>
    </div>
  );
}
