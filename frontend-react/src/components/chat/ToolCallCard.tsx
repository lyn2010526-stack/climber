import { useState } from 'react';
import { Terminal, ChevronDown, CheckCircle2, XCircle, Loader2, Clock, RotateCcw } from 'lucide-react';
import { cn } from '../../lib/utils';

interface ToolCallCardProps {
  name: string;
  arguments: Record<string, unknown>;
  result?: string | undefined;
  error?: string | undefined;
  isRunning?: boolean;
  duration?: number;
  onRetry?: () => void;
}

export function ToolCallCard({
  name,
  arguments: args,
  result,
  error,
  isRunning,
  duration,
  onRetry,
}: ToolCallCardProps) {
  const [expanded, setExpanded] = useState(false);
  const status = error ? 'error' : isRunning ? 'running' : result ? 'success' : 'running';

  const statusConfig = {
    running: {
      icon: Loader2,
      color: 'var(--color-accent)',
      bg: 'var(--color-accent-subtle)',
      label: '执行中',
      iconClass: 'animate-spin',
    },
    success: {
      icon: CheckCircle2,
      color: 'var(--color-success)',
      bg: 'var(--color-success-subtle)',
      label: '完成',
      iconClass: '',
    },
    error: {
      icon: XCircle,
      color: 'var(--color-error)',
      bg: 'var(--color-error-subtle)',
      label: '失败',
      iconClass: '',
    },
  };

  const config = statusConfig[status];
  const StatusIcon = config.icon;
  const hasOutput = result || error || Object.keys(args).length > 0;

  return (
    <div
      className="rounded-2xl border overflow-hidden transition-all duration-200"
      style={{
        borderColor: expanded ? 'var(--color-border-default)' : 'var(--color-border-subtle)',
        backgroundColor: expanded ? 'var(--color-bg-surface-2)' : 'var(--color-bg-surface-1)',
        boxShadow: expanded
          ? '0 4px 16px rgba(0, 0, 0, 0.2)'
          : '0 1px 4px rgba(0, 0, 0, 0.1)',
        maxWidth: '85%',
      }}
    >
      {/* Header */}
      <button
        onClick={() => hasOutput && setExpanded(!expanded)}
        className={cn(
          'w-full flex items-center gap-2.5 px-4 py-2.5 text-left transition-colors',
          hasOutput && 'cursor-pointer hover:bg-[var(--color-bg-surface-3)]/50',
        )}
        disabled={!hasOutput}
      >
        <div
          className="p-1.5 rounded-lg flex items-center justify-center shrink-0"
          style={{ backgroundColor: config.bg, color: config.color }}
        >
          <StatusIcon size={13} className={config.iconClass} />
        </div>

        <span className="text-xs font-semibold flex-1 text-[var(--color-text-primary)] truncate">
          {name}
        </span>

        {Object.keys(args).length > 0 && !expanded && (
          <span className="text-[10px] text-[var(--color-text-muted)] truncate max-w-[100px]">
            {Object.keys(args).slice(0, 2).join(', ')}
          </span>
        )}

        {duration !== undefined && !isRunning && (
          <span className="flex items-center gap-1 text-[10px] text-[var(--color-text-muted)]">
            <Clock size={10} />
            {(duration / 1000).toFixed(1)}s
          </span>
        )}

        <span
          className="px-2 py-0.5 rounded-full text-[10px] font-medium"
          style={{ backgroundColor: config.bg, color: config.color }}
        >
          {config.label}
        </span>

        {error && onRetry && (
          <button
            onClick={(e) => {
              e.stopPropagation();
              onRetry();
            }}
            className="p-1 rounded-md text-[var(--color-text-muted)] hover:text-[var(--color-accent)] hover:bg-[var(--color-accent-subtle)] transition-colors"
            title="重试"
          >
            <RotateCcw size={12} />
          </button>
        )}

        {hasOutput && (
          <div
            className="p-1 rounded-md transition-transform duration-200"
            style={{
              color: 'var(--color-text-muted)',
              transform: expanded ? 'rotate(180deg)' : 'rotate(0deg)',
            }}
          >
            <ChevronDown size={14} />
          </div>
        )}
      </button>

      {/* Expanded content */}
      {expanded && (
        <div className="px-4 pb-4 space-y-3 fade-enter">
          {Object.keys(args).length > 0 && (
            <div>
              <div className="text-[10px] font-semibold uppercase tracking-wider mb-1.5 text-[var(--color-text-muted)]">
                Input
              </div>
              <pre
                className="text-xs font-mono whitespace-pre-wrap p-3 rounded-xl"
                style={{
                  backgroundColor: 'var(--color-code-bg)',
                  border: '1px solid var(--color-code-border)',
                  color: 'var(--color-text-secondary)',
                }}
              >
                {JSON.stringify(args, null, 2)}
              </pre>
            </div>
          )}

          {result && (
            <div>
              <div className="text-[10px] font-semibold uppercase tracking-wider mb-1.5 text-[var(--color-text-muted)]">
                Output
              </div>
              <pre
                className="text-xs font-mono whitespace-pre-wrap p-3 rounded-xl max-h-60 overflow-y-auto"
                style={{
                  backgroundColor: 'var(--color-code-bg)',
                  border: '1px solid var(--color-code-border)',
                  color: 'var(--color-text-secondary)',
                }}
              >
                {result}
              </pre>
            </div>
          )}

          {error && (
            <div>
              <div className="text-[10px] font-semibold uppercase tracking-wider mb-1.5 text-[var(--color-error)]">
                Error
              </div>
              <pre
                className="text-xs font-mono whitespace-pre-wrap p-3 rounded-xl"
                style={{
                  backgroundColor: 'var(--color-error-subtle)',
                  border: '1px solid var(--color-error)/20',
                  color: 'var(--color-error)',
                }}
              >
                {error}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
