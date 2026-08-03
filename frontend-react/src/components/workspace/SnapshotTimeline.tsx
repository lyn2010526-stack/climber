import { useState } from 'react';
import {
  Camera, RotateCcw, Trash2, ChevronDown, ChevronRight,
} from 'lucide-react';

interface Snapshot {
  id: string;
  label: string;
  timestamp: number;
  messageCount: number;
  tokenCount: number;
  status: string;
}

interface SnapshotTimelineProps {
  snapshots: Snapshot[];
  onRestore: (id: string) => void;
  onDelete: (id: string) => void;
  onSave: () => void;
}

export function SnapshotTimeline({ snapshots, onRestore, onDelete, onSave }: SnapshotTimelineProps) {
  const [expanded, setExpanded] = useState(true);

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <button
          onClick={() => setExpanded(!expanded)}
          className="flex items-center gap-1.5 text-xs font-medium text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]"
        >
          {expanded ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
          <Camera size={12} className="text-blue-400" />
          Snapshots ({snapshots.length})
        </button>
        <button
          onClick={onSave}
          className="flex items-center gap-1 px-2 py-1 text-[10px] bg-blue-600/10 text-blue-400 rounded hover:bg-blue-600/20"
        >
          <Camera size={10} /> Save
        </button>
      </div>

      {expanded && (
        <div className="space-y-1 max-h-48 overflow-y-auto">
          {snapshots.length === 0 && (
             <p className="text-[10px] text-[var(--color-text-muted)] text-center py-3">No snapshots saved</p>
          )}
          {snapshots.map((snap, i) => (
            <div
              key={snap.id}
              className="flex items-center gap-2 p-2 bg-[var(--color-bg-surface-elevated)] rounded-lg group"
            >
              <div className="flex flex-col items-center">
                <div className="w-2 h-2 rounded-full bg-blue-600" />
                {i < snapshots.length - 1 &&                 <div className="w-0.5 h-3 bg-[var(--color-bg-surface-elevated)]" />}
              </div>
              <div className="flex-1 min-w-0">
                <span className="text-[10px] text-[var(--color-text-primary)] truncate block">{snap.label}</span>
                <span className="text-[9px] text-[var(--color-text-muted)]">
                  {new Date(snap.timestamp).toLocaleTimeString()} · {snap.messageCount} msgs · {(snap.tokenCount / 1000).toFixed(1)}k tok
                </span>
              </div>
              <div className="flex gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity">
                <button
                  onClick={() => onRestore(snap.id)}
                   className="p-1 text-[var(--color-text-muted)] hover:text-blue-400"
                   title="恢复"
                >
                  <RotateCcw size={10} />
                </button>
                <button
                  onClick={() => onDelete(snap.id)}
                   className="p-1 text-[var(--color-text-muted)] hover:text-red-400"
                   title="删除"
                >
                  <Trash2 size={10} />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
