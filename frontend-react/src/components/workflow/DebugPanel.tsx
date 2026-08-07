import { useState, useRef, useEffect } from 'react';
import {
  Terminal, Trash2, ChevronDown, ChevronRight,
  CheckCircle2, XCircle, Clock, Loader2, AlertCircle,
} from 'lucide-react';
import { cn } from '../../lib/utils';

interface LogEntry {
  nodeId: string;
  status: string;
  timestamp: number;
  message?: string;
}

interface DebugPanelProps {
  logs: LogEntry[];
  onClear: () => void;
  breakpoints: Set<string>;
  onToggleBreakpoint: (nodeId: string) => void;
  nodeIds: string[];
}

function StatusIcon({ status }: { status: string }) {
  switch (status) {
    case 'success':
      return <CheckCircle2 size={11} className="text-emerald-400" />;
    case 'error':
    case 'failed':
      return <XCircle size={11} className="text-red-400" />;
    case 'running':
      return <Loader2 size={11} className="text-blue-400 animate-spin" />;
    case 'waiting':
      return <Clock size={11} className="text-amber-400" />;
    default:
      return <AlertCircle size={11} className="text-[var(--color-text-muted)]" />;
  }
}

function formatTime(timestamp: number): string {
  return new Date(timestamp).toLocaleTimeString('en-US', {
    hour12: false,
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
}

export function DebugPanel({
  logs,
  onClear,
  breakpoints,
  onToggleBreakpoint,
  nodeIds,
}: DebugPanelProps) {
  const [activeTab, setActiveTab] = useState<'logs' | 'breakpoints'>('logs');
  const [expanded, setExpanded] = useState(true);
  const logsEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  return (
    <div className="flex flex-col h-full border-t border-[var(--color-border-subtle)] bg-[var(--color-bg-surface)]/50">
      {/* Header */}
      <div
        className="flex items-center gap-2 px-3 py-2 cursor-pointer hover:bg-[var(--color-bg-surface-elevated)]/50 transition-colors"
        onClick={() => setExpanded(!expanded)}
      >
        {expanded ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
        <Terminal size={12} className="text-[var(--color-accent)]" />
        <span className="text-[11px] font-semibold text-[var(--color-text-primary)]">Debug</span>
        {logs.length > 0 && (
          <span className="text-[9px] px-1.5 py-0.5 rounded-full bg-[var(--color-accent)]/15 text-[var(--color-accent)]">
            {logs.length}
          </span>
        )}
      </div>

      {expanded && (
        <>
          {/* Tabs */}
          <div className="flex items-center gap-1 px-3 pb-2">
            <button
              onClick={() => setActiveTab('logs')}
              className={cn(
                'px-2.5 py-1 rounded text-[10px] font-medium transition-colors',
                activeTab === 'logs'
                  ? 'bg-[var(--color-accent)]/15 text-[var(--color-accent)]'
                  : 'text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)]'
              )}
            >
              Logs
            </button>
            <button
              onClick={() => setActiveTab('breakpoints')}
              className={cn(
                'px-2.5 py-1 rounded text-[10px] font-medium transition-colors',
                activeTab === 'breakpoints'
                  ? 'bg-[var(--color-accent)]/15 text-[var(--color-accent)]'
                  : 'text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)]'
              )}
            >
              Breakpoints
            </button>
            <div className="flex-1" />
            <button
              onClick={(e) => { e.stopPropagation(); onClear(); }}
              className="p-1 rounded hover:bg-[var(--color-bg-surface-elevated)] text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)] transition-colors"
              title="Clear logs"
            >
              <Trash2 size={11} />
            </button>
          </div>

          {/* Content */}
          <div className="flex-1 overflow-y-auto px-3 pb-3">
            {activeTab === 'logs' && (
              <div className="space-y-1">
                {logs.length === 0 ? (
                  <p className="text-[10px] text-[var(--color-text-muted)] text-center py-4">
                    No execution logs yet. Run the workflow to see logs.
                  </p>
                ) : (
                  logs.map((log, index) => (
                    <div
                      key={index}
                      className="flex items-start gap-2 px-2 py-1.5 rounded bg-[var(--color-bg-deep)]/30 hover:bg-[var(--color-bg-deep)]/50 transition-colors"
                    >
                      <StatusIcon status={log.status} />
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="text-[10px] font-mono text-[var(--color-text-primary)] truncate">
                            {log.nodeId}
                          </span>
                          <span className="text-[9px] text-[var(--color-text-muted)] ml-auto shrink-0">
                            {formatTime(log.timestamp)}
                          </span>
                        </div>
                        {log.message && (
                          <p className="text-[9px] text-[var(--color-text-muted)] mt-0.5 truncate">
                            {log.message}
                          </p>
                        )}
                      </div>
                    </div>
                  ))
                )}
                <div ref={logsEndRef} />
              </div>
            )}

            {activeTab === 'breakpoints' && (
              <div className="space-y-1">
                {nodeIds.length === 0 ? (
                  <p className="text-[10px] text-[var(--color-text-muted)] text-center py-4">
                    No nodes in the workflow.
                  </p>
                ) : (
                  nodeIds.map((nodeId) => (
                    <div
                      key={nodeId}
                      className="flex items-center gap-2 px-2 py-1.5 rounded hover:bg-[var(--color-bg-deep)]/30 transition-colors"
                    >
                      <button
                        onClick={() => onToggleBreakpoint(nodeId)}
                        className={cn(
                          'w-2.5 h-2.5 rounded-full transition-colors',
                          breakpoints.has(nodeId)
                            ? 'bg-red-500 shadow-sm shadow-red-500/30'
                            : 'bg-[var(--color-border-elevated)] hover:bg-red-500/50'
                        )}
                      />
                      <span className="text-[10px] font-mono text-[var(--color-text-primary)] truncate">
                        {nodeId}
                      </span>
                    </div>
                  ))
                )}
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}
