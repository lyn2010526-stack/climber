import { useState } from 'react';
import {
  FileText, Plus, Minus, ArrowRight,
  ChevronDown, ChevronRight, Check,
  RotateCcw, Eye,
} from 'lucide-react';
import { cn } from '../../lib/utils';
import { Button } from '../ui/Button';

export interface FileChange {
  path: string;
  type: 'created' | 'modified' | 'deleted';
  additions?: number;
  deletions?: number;
  diff?: string;
  preview?: string;
}

interface FileModificationDisplayProps {
  changes: FileChange[];
  className?: string;
  onRevert?: (path: string) => void;
  onPreview?: (path: string) => void;
}

const typeConfig = {
  created: { icon: Plus, color: 'text-green-400', bg: 'bg-green-500/10', label: '新增' },
  modified: { icon: ArrowRight, color: 'text-amber-400', bg: 'bg-amber-500/10', label: '修改' },
  deleted: { icon: Minus, color: 'text-red-400', bg: 'bg-red-500/10', label: '删除' },
};

function DiffLine({ line }: { line: string }) {
  const isAddition = line.startsWith('+');
  const isDeletion = line.startsWith('-');
  const isContext = !isAddition && !isDeletion;

  return (
    <div
      className={cn(
        'flex items-start gap-2 px-3 py-0.5 text-[11px] font-mono',
        isAddition && 'bg-green-500/[0.06]',
        isDeletion && 'bg-red-500/[0.06]',
        isContext && 'bg-transparent'
      )}
    >
      <span className={cn(
        'w-3 text-right shrink-0 select-none',
        isAddition && 'text-green-500/60',
        isDeletion && 'text-red-500/60',
        isContext && 'text-[var(--color-text-muted)]'
      )}>
        {isAddition ? '+' : isDeletion ? '-' : ' '}
      </span>
      <span className={cn(
        'whitespace-pre-wrap break-all',
        isAddition && 'text-green-300/90',
        isDeletion && 'text-red-300/90',
        isContext && 'text-[var(--color-text-muted)]'
      )}>
        {line.slice(1) || line}
      </span>
    </div>
  );
}

function FileChangeRow({ change, onRevert, onPreview }: {
  change: FileChange;
  onRevert?: (path: string) => void;
  onPreview?: (path: string) => void;
}) {
  const [isExpanded, setIsExpanded] = useState(change.type === 'modified');
  const [showPreview, setShowPreview] = useState(false);

  const config = typeConfig[change.type];
  const TypeIcon = config.icon;

  const fileName = change.path.split('/').pop() || change.path;
  const dirPath = change.path.split('/').slice(0, -1).join('/');

  return (
    <div className="rounded-xl border border-white/[0.06] bg-white/[0.02] overflow-hidden">
      {/* File header */}
      <button
        className="w-full flex items-center gap-3 px-3 py-2.5 text-left hover:bg-white/[0.02] transition-colors"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className={cn('p-1.5 rounded-lg', config.bg)}>
          {change.type === 'deleted' ? (
            <FileText size={13} className={config.color} />
          ) : (
            <TypeIcon size={13} className={config.color} />
          )}
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="text-xs font-medium text-[var(--color-text-secondary)] truncate">{fileName}</span>
            <span className={cn(
              'px-1.5 py-0.5 rounded-md text-[9px] font-medium',
              config.bg, config.color
            )}>
              {config.label}
            </span>
          </div>
          {dirPath && (
            <p className="text-[10px] text-[var(--color-text-muted)] truncate mt-0.5">{dirPath}/</p>
          )}
        </div>

        {/* Stats */}
        <div className="flex items-center gap-2 shrink-0">
          {change.additions !== undefined && change.additions > 0 && (
            <span className="text-[10px] text-green-400 font-mono">+{change.additions}</span>
          )}
          {change.deletions !== undefined && change.deletions > 0 && (
            <span className="text-[10px] text-red-400 font-mono">-{change.deletions}</span>
          )}
            {isExpanded ? (
             <ChevronDown size={13} className="text-[var(--color-text-muted)]" />
           ) : (
             <ChevronRight size={13} className="text-[var(--color-text-muted)]" />
           )}
        </div>
      </button>

      {/* Expanded content */}
      {isExpanded && (
        <div className="border-t border-white/[0.04] animate-[fadeIn_0.15s_ease_forwards]">
          {/* View toggle */}
          <div className="flex items-center gap-1 px-3 py-2 bg-white/[0.01]">
            <button
              className={cn(
                 'px-2 py-1 rounded-md text-[10px] font-medium transition-colors',
                 !showPreview ? 'bg-white/[0.08] text-white' : 'text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)]'
              )}
              onClick={() => setShowPreview(false)}
            >
              差异
            </button>
            <button
              className={cn(
                'px-2 py-1 rounded-md text-[10px] font-medium transition-colors',
                 showPreview ? 'bg-white/[0.08] text-white' : 'text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)]'
              )}
              onClick={() => setShowPreview(true)}
            >
              预览
            </button>
          </div>

          {/* Diff or preview */}
          <div className="max-h-[250px] overflow-y-auto">
            {!showPreview && change.diff ? (
              <div className="py-1">
                {change.diff.split('\n').map((line, i) => (
                  <DiffLine key={i} line={line} />
                ))}
              </div>
            ) : showPreview && change.preview ? (
              <pre className="text-[11px] text-[var(--color-text-secondary)] font-mono p-3 whitespace-pre-wrap">
                {change.preview}
              </pre>
            ) : (
              <div className="flex items-center justify-center py-8">
                <p className="text-xs text-[var(--color-text-muted)]">
                  {change.type === 'deleted' ? '文件已被删除' : '无差异信息'}
                </p>
              </div>
            )}
          </div>

          {/* Actions */}
          {(onRevert || onPreview) && (
            <div className="flex items-center gap-2 px-3 py-2 border-t border-white/[0.04] bg-white/[0.01]">
              {onRevert && change.type !== 'created' && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => onRevert(change.path)}
                >
                  <RotateCcw size={11} />
                  撤销
                </Button>
              )}
              {onPreview && change.type !== 'deleted' && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => onPreview(change.path)}
                >
                  <Eye size={11} />
                  查看文件
                </Button>
              )}
              <div className="flex-1" />
              <span className="text-[10px] text-[var(--color-text-muted)] flex items-center gap-1">
                <Check size={9} className="text-green-400" />
                已保存
              </span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export function FileModificationDisplay({
  changes,
  className,
  onRevert,
  onPreview,
}: FileModificationDisplayProps) {
  if (changes.length === 0) return null;

  const createdCount = changes.filter(c => c.type === 'created').length;
  const modifiedCount = changes.filter(c => c.type === 'modified').length;
  const deletedCount = changes.filter(c => c.type === 'deleted').length;
  const totalAdditions = changes.reduce((sum, c) => sum + (c.additions || 0), 0);
  const totalDeletions = changes.reduce((sum, c) => sum + (c.deletions || 0), 0);

  return (
    <div className={cn('space-y-2', className)}>
      {/* Summary header */}
      <div className="flex items-center justify-between px-1 mb-2">
        <div className="flex items-center gap-2">
          <FileText size={13} className="text-[var(--color-text-muted)]" />
          <span className="text-[11px] font-medium text-[var(--color-text-muted)]">
            {changes.length} 个文件变更
          </span>
          {createdCount > 0 && (
            <span className="text-[10px] text-green-400">{createdCount} 新增</span>
          )}
          {modifiedCount > 0 && (
            <span className="text-[10px] text-amber-400">{modifiedCount} 修改</span>
          )}
          {deletedCount > 0 && (
            <span className="text-[10px] text-red-400">{deletedCount} 删除</span>
          )}
        </div>
        {(totalAdditions > 0 || totalDeletions > 0) && (
          <div className="flex items-center gap-1.5">
            <span className="text-[10px] text-green-400 font-mono">+{totalAdditions}</span>
            <span className="text-[10px] text-red-400 font-mono">-{totalDeletions}</span>
          </div>
        )}
      </div>

      {/* File list */}
      {changes.map((change, index) => (
        <FileChangeRow
          key={`${change.path}-${index}`}
          change={change}
          {...(onRevert ? { onRevert } : {})}
          {...(onPreview ? { onPreview } : {})}
        />
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
