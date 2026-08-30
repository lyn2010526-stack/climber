import React, { useState } from 'react';
import {
  ChevronDown, ChevronRight, CheckCircle2, XCircle,
  Loader2, Terminal, Code2, FileSearch, Globe,
  Database, Wrench,
} from 'lucide-react';
import { cn } from '../../lib/utils';

export interface ToolCall {
  id: string;
  name: string;
  displayName?: string;
  arguments: Record<string, unknown>;
  result?: string;
  error?: string;
  status: 'pending' | 'running' | 'success' | 'error';
  duration?: number;
  startTime?: number;
  toolType?: 'builtin' | 'mcp' | 'custom';
}

interface ToolCallVisualizationProps {
  calls: ToolCall[];
  className?: string;
  defaultExpanded?: boolean;
}

const toolIcons: Record<string, React.ElementType> = {
  file_read: FileSearch,
  file_write: Code2,
  run_command: Terminal,
  web_search: Globe,
  database_query: Database,
};

function getToolIcon(name: string): React.ElementType {
  for (const [key, icon] of Object.entries(toolIcons)) {
    if (name.includes(key) || name.includes(key.replace('_', ''))) return icon;
  }
  return Wrench;
}

function formatDuration(ms: number): string {
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

function ToolCallCard({ call, defaultExpanded }: { call: ToolCall; defaultExpanded: boolean }) {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded && call.status !== 'success');
  const [showArgs, setShowArgs] = useState(false);
  const [showResult, setShowResult] = useState(false);

  const Icon = getToolIcon(call.name);

  const statusConfig = {
    pending: { icon: Loader2, color: 'text-[var(--color-text-muted)]', bg: 'bg-[var(--color-text-muted)]/10', label: '等待中', spin: true },
    running: { icon: Loader2, color: 'text-[var(--color-accent)]', bg: 'bg-blue-500/10', label: '执行中', spin: true },
    success: { icon: CheckCircle2, color: 'text-green-400', bg: 'bg-green-500/10', label: '完成', spin: false },
    error: { icon: XCircle, color: 'text-red-400', bg: 'bg-red-500/10', label: '失败', spin: false },
  }[call.status];

  const StatusIcon = statusConfig.icon;

  return (
    <div
      className={cn(
        'rounded-xl border transition-all duration-200 ease-[cubic-bezier(0.16,1,0.3,1)]',
        call.status === 'error'
          ? 'border-red-500/20 bg-red-500/[0.02]'
          : call.status === 'running'
          ? 'border-blue-500/20 bg-blue-500/[0.02]'
          : 'border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-2)]'
      )}
    >
      {/* Main row */}
      <button
        type="button"
        aria-expanded={isExpanded}
        aria-label={`${call.displayName || call.name}，${statusConfig.label}`}
        className="w-full flex items-center gap-3 px-3 py-2.5 text-left hover:bg-[var(--color-bg-surface-2)] transition-colors rounded-lg"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className={cn('p-1.5 rounded-lg', statusConfig.bg)}>
          <Icon size={13} className={statusConfig.color} />
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="text-xs font-medium text-[var(--color-text-primary)] truncate">
              {call.displayName || call.name}
            </span>
            <span className={cn('shrink-0 text-[10px] font-medium', statusConfig.color)}>
              {statusConfig.label}
            </span>
            <StatusIcon
              size={11}
              className={cn(statusConfig.color, statusConfig.spin && 'animate-spin')}
            />
            {call.duration !== undefined && (
              <span className="text-[10px] text-[var(--color-text-muted)] ml-auto shrink-0">
                {formatDuration(call.duration)}
              </span>
            )}
          </div>
          {!isExpanded && call.status === 'success' && call.result && (
            <p className="text-[11px] text-[var(--color-text-muted)] truncate mt-0.5">
              {call.result.slice(0, 80)}
            </p>
          )}
          {!isExpanded && call.status === 'error' && call.error && (
            <p className="text-[11px] text-red-400/70 truncate mt-0.5">
              {call.error.slice(0, 80)}
            </p>
          )}
        </div>

        {isExpanded ? (
          <ChevronDown size={14} className="text-[var(--color-text-muted)] shrink-0" />
        ) : (
          <ChevronRight size={14} className="text-[var(--color-text-muted)] shrink-0" />
        )}
      </button>

      {/* Expanded content */}
      {isExpanded && (
        <div className="px-3 pb-3 space-y-2 animate-[fadeIn_0.15s_ease_forwards]">
          {/* Arguments */}
          {Object.keys(call.arguments).length > 0 && (
            <div>
              <button
                className="flex items-center gap-1.5 text-[10px] font-medium text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] transition-colors"
                onClick={() => setShowArgs(!showArgs)}
              >
                {showArgs ? <ChevronDown size={10} /> : <ChevronRight size={10} />}
                参数 <span className="font-mono">{Object.keys(call.arguments).length}</span>
              </button>
              {showArgs && (
                <pre className="mt-1.5 text-[11px] text-[var(--color-text-secondary)] font-mono bg-black/30 rounded-lg p-2.5 overflow-x-auto whitespace-pre-wrap max-h-[150px] overflow-y-auto">
                  {JSON.stringify(call.arguments, null, 2)}
                </pre>
              )}
            </div>
          )}

          {/* Result */}
          {call.result && (
            <div>
              <button
                className="flex items-center gap-1.5 text-[10px] font-medium text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] transition-colors"
                onClick={() => setShowResult(!showResult)}
              >
                {showResult ? <ChevronDown size={10} /> : <ChevronRight size={10} />}
                结果
              </button>
              {showResult && (
                <pre className="mt-1.5 text-[11px] text-green-300/80 font-mono bg-black/30 rounded-lg p-2.5 overflow-x-auto whitespace-pre-wrap max-h-[200px] overflow-y-auto">
                  {call.result}
                </pre>
              )}
            </div>
          )}

          {/* Error */}
          {call.error && (
            <div>
              <span className="text-[10px] font-medium text-red-400">错误信息</span>
              <pre className="mt-1.5 text-[11px] text-red-300/80 font-mono bg-red-500/5 rounded-lg p-2.5 overflow-x-auto whitespace-pre-wrap max-h-[150px] overflow-y-auto border border-red-500/10">
                {call.error}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export function ToolCallVisualization({
  calls,
  className,
  defaultExpanded = false,
}: ToolCallVisualizationProps) {
  const [allExpanded, setAllExpanded] = useState(defaultExpanded);

  if (calls.length === 0) return null;

  const runningCount = calls.filter(c => c.status === 'running').length;
  const successCount = calls.filter(c => c.status === 'success').length;
  const errorCount = calls.filter(c => c.status === 'error').length;

  return (
    <div className={cn('space-y-1.5', className)}>
      {/* Summary bar */}
      <div className="flex items-center justify-between px-1 mb-2">
        <div className="flex items-center gap-2">
          <span className="text-[11px] font-semibold text-[var(--color-text-secondary)]">
            工具调用 <span className="font-mono text-[var(--color-text-muted)]">{calls.length}</span>
          </span>
          {runningCount > 0 && (
            <span className="flex items-center gap-1 text-[10px] text-[var(--color-accent)]">
              <Loader2 size={9} className="animate-spin" />
              {runningCount} 运行中
            </span>
          )}
          {successCount > 0 && (
            <span className="flex items-center gap-1 text-[10px] text-green-400">
              <CheckCircle2 size={9} />
              {successCount}
            </span>
          )}
          {errorCount > 0 && (
            <span className="flex items-center gap-1 text-[10px] text-red-400">
              <XCircle size={9} />
              {errorCount}
            </span>
          )}
        </div>
        <button
          className="text-[10px] text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)] transition-colors"
          onClick={() => setAllExpanded(!allExpanded)}
        >
          {allExpanded ? '全部折叠' : '全部展开'}
        </button>
      </div>

      {/* Tool call cards */}
      {calls.map(call => (
        <ToolCallCard key={call.id} call={call} defaultExpanded={allExpanded} />
      ))}

      <style>{`
        @keyframes fadeIn {
          from { opacity: 0; transform: translateY(-3px); }
          to { opacity: 1; transform: translateY(0); }
        }
      `}</style>
    </div>
  );
}
