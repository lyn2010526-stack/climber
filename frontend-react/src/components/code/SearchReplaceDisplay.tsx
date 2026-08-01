import React, { useState } from 'react';
import {
  ArrowRight, Check, X, Copy, ChevronDown, ChevronRight,
  FileEdit,
} from 'lucide-react';
import { cn } from '../../lib/utils';
import { Button } from '../ui/Button';

/**
 * 搜索/替换块显示组件
 * 参考 Aider 的 diff 格式: <<<<<<< SEARCH / ======= / >>>>>>> REPLACE
 * 文档: aider.chat/docs/more/edit-formats.html
 */

export interface SearchReplaceBlock {
  id: string;
  filePath: string;
  searchContent: string;
  replaceContent: string;
  status: 'pending' | 'applied' | 'rejected' | 'failed';
  error?: string;
}

interface SearchReplaceDisplayProps {
  blocks: SearchReplaceBlock[];
  className?: string;
  onApply?: (id: string) => void;
  onReject?: (id: string) => void;
  onApplyAll?: () => void;
}

/** 计算两个文本的差异行 */
function computeLineDiff(oldText: string, newText: string): { type: 'same' | 'add' | 'del'; content: string }[] {
  const oldLines = oldText.split('\n');
  const newLines = newText.split('\n');
  const result: { type: 'same' | 'add' | 'del'; content: string }[] = [];

  let oi = 0;
  let ni = 0;

  while (oi < oldLines.length || ni < newLines.length) {
    if (oi >= oldLines.length) {
      result.push({ type: 'add', content: newLines[ni] });
      ni++;
    } else if (ni >= newLines.length) {
      result.push({ type: 'del', content: oldLines[oi] });
      oi++;
    } else if (oldLines[oi] === newLines[ni]) {
      result.push({ type: 'same', content: oldLines[oi] });
      oi++;
      ni++;
    } else {
      // 查找下一行匹配
      let foundMatch = false;
      for (let lookAhead = 1; lookAhead <= 3; lookAhead++) {
        if (ni + lookAhead < newLines.length && oldLines[oi] === newLines[ni + lookAhead]) {
          // 添加新增行
          for (let i = 0; i < lookAhead; i++) {
            result.push({ type: 'add', content: newLines[ni + i] });
          }
          ni += lookAhead;
          foundMatch = true;
          break;
        }
        if (oi + lookAhead < oldLines.length && oldLines[oi + lookAhead] === newLines[ni]) {
          // 删除旧行
          for (let i = 0; i < lookAhead; i++) {
            result.push({ type: 'del', content: oldLines[oi + i] });
          }
          oi += lookAhead;
          foundMatch = true;
          break;
        }
      }
      if (!foundMatch) {
        result.push({ type: 'del', content: oldLines[oi] });
        result.push({ type: 'add', content: newLines[ni] });
        oi++;
        ni++;
      }
    }
  }

  return result;
}

function SearchReplaceCard({
  block,
  onApply,
  onReject,
}: {
  block: SearchReplaceBlock;
  onApply?: (id: string) => void;
  onReject?: (id: string) => void;
}) {
  const [isExpanded, setIsExpanded] = useState(true);
  const [showRawFormat, setShowRawFormat] = useState(false);
  const [copied, setCopied] = useState(false);

  const diffLines = computeLineDiff(block.searchContent, block.replaceContent);

  const fileName = block.filePath.split('/').pop() || block.filePath;
  const dirPath = block.filePath.split('/').slice(0, -1).join('/');

  const addedCount = diffLines.filter(l => l.type === 'add').length;
  const removedCount = diffLines.filter(l => l.type === 'del').length;

  const statusConfig = {
    pending: { label: '待应用', color: 'text-amber-400', bg: 'bg-amber-500/10' },
    applied: { label: '已应用', color: 'text-green-400', bg: 'bg-green-500/10' },
    rejected: { label: '已拒绝', color: 'text-red-400', bg: 'bg-red-500/10' },
    failed: { label: '失败', color: 'text-red-400', bg: 'bg-red-500/10' },
  }[block.status];

  const handleCopy = () => {
    const raw = `${block.filePath}\n<<<<<<< SEARCH\n${block.searchContent}\n=======\n${block.replaceContent}\n>>>>>>> REPLACE`;
    navigator.clipboard.writeText(raw);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div
      className={cn(
        'rounded-xl border overflow-hidden transition-all duration-200',
        block.status === 'pending'
          ? 'border-amber-500/20 bg-amber-500/[0.02]'
          : block.status === 'applied'
          ? 'border-green-500/20 bg-green-500/[0.02]'
          : block.status === 'failed'
          ? 'border-red-500/20 bg-red-500/[0.02]'
          : 'border-white/[0.06] bg-white/[0.02]'
      )}
    >
      {/* Header */}
      <button
        className="w-full flex items-center gap-2.5 px-3 py-2.5 text-left hover:bg-white/[0.02] transition-colors"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        {isExpanded ? (
          <ChevronDown size={13} className="text-gray-500 shrink-0" />
        ) : (
          <ChevronRight size={13} className="text-gray-500 shrink-0" />
        )}

        <FileEdit size={13} className="text-blue-400 shrink-0" />

        <div className="flex-1 min-w-0">
          <span className="text-xs font-medium text-gray-200">{fileName}</span>
          {dirPath && (
            <span className="text-[10px] text-gray-500 ml-1.5">{dirPath}/</span>
          )}
        </div>

        {/* Status and stats */}
        <div className="flex items-center gap-2 shrink-0">
          <span className={cn('px-1.5 py-0.5 rounded-md text-[9px] font-medium', statusConfig.bg, statusConfig.color)}>
            {statusConfig.label}
          </span>
          {addedCount > 0 && (
            <span className="text-[10px] text-green-400 font-mono">+{addedCount}</span>
          )}
          {removedCount > 0 && (
            <span className="text-[10px] text-red-400 font-mono">-{removedCount}</span>
          )}
        </div>
      </button>

      {/* Expanded content */}
      {isExpanded && (
        <div className="border-t border-white/[0.04] animate-[fadeIn_0.15s_ease_forwards]">
          {/* View toggle */}
          <div className="flex items-center justify-between px-3 py-2 bg-white/[0.01]">
            <div className="flex items-center gap-1">
              <button
                className={cn(
                  'px-2 py-1 rounded-md text-[10px] font-medium transition-colors',
                  !showRawFormat ? 'bg-white/[0.08] text-white' : 'text-gray-400 hover:text-gray-200'
                )}
                onClick={() => setShowRawFormat(false)}
              >
                差异视图
              </button>
              <button
                className={cn(
                  'px-2 py-1 rounded-md text-[10px] font-medium transition-colors',
                  showRawFormat ? 'bg-white/[0.08] text-white' : 'text-gray-400 hover:text-gray-200'
                )}
                onClick={() => setShowRawFormat(true)}
              >
                原始格式
              </button>
            </div>
            <button
              onClick={handleCopy}
              className="p-1 rounded hover:bg-white/[0.06] text-gray-400 transition-colors"
            >
              {copied ? <Check size={12} className="text-green-400" /> : <Copy size={12} />}
            </button>
          </div>

          {/* Content */}
          <div className="max-h-[300px] overflow-y-auto">
            {showRawFormat ? (
              /* Aider 原始格式 */
              <div className="p-3 font-mono text-[11px] space-y-1">
                <div className="text-gray-400 mb-2">{block.filePath}</div>
                <div className="text-red-400/60">{'<<<<<<< SEARCH'}</div>
                <pre className="text-red-300/80 whitespace-pre-wrap bg-red-500/[0.03] rounded-lg p-2">
                  {block.searchContent}
                </pre>
                <div className="text-gray-500">{'======='}</div>
                <pre className="text-green-300/80 whitespace-pre-wrap bg-green-500/[0.03] rounded-lg p-2">
                  {block.replaceContent}
                </pre>
                <div className="text-green-400/60">{'>>>>>>> REPLACE'}</div>
              </div>
            ) : (
              /* 行内差异视图 */
              <div className="py-1">
                {diffLines.map((line, i) => (
                  <div
                    key={i}
                    className={cn(
                      'flex items-start font-mono text-[11px] px-3 py-0.5',
                      line.type === 'add' && 'bg-green-500/[0.06]',
                      line.type === 'del' && 'bg-red-500/[0.06]',
                    )}
                  >
                    <span className={cn(
                      'w-4 text-center shrink-0 mr-2 select-none',
                      line.type === 'add' && 'text-green-500/60',
                      line.type === 'del' && 'text-red-500/60',
                      line.type === 'same' && 'text-gray-600',
                    )}>
                      {line.type === 'add' ? '+' : line.type === 'del' ? '-' : ' '}
                    </span>
                    <span className={cn(
                      'whitespace-pre-wrap break-all',
                      line.type === 'add' && 'text-green-300/90',
                      line.type === 'del' && 'text-red-300/90',
                      line.type === 'same' && 'text-gray-400/70',
                    )}>
                      {line.content || ' '}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Actions */}
          {block.status === 'pending' && (onApply || onReject) && (
            <div className="flex items-center gap-2 px-3 py-2.5 border-t border-white/[0.04] bg-white/[0.01]">
              {onApply && (
                <Button variant="primary" size="sm" onClick={() => onApply(block.id)}>
                  <Check size={12} />
                  应用
                </Button>
              )}
              {onReject && (
                <Button variant="outline" size="sm" onClick={() => onReject(block.id)}>
                  <X size={12} />
                  拒绝
                </Button>
              )}
            </div>
          )}

          {/* Error display */}
          {block.status === 'failed' && block.error && (
            <div className="px-3 py-2 border-t border-red-500/10 bg-red-500/[0.03]">
              <p className="text-[11px] text-red-400/80">{block.error}</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export function SearchReplaceDisplay({
  blocks,
  className,
  onApply,
  onReject,
  onApplyAll,
}: SearchReplaceDisplayProps) {
  if (blocks.length === 0) return null;

  const pendingCount = blocks.filter(b => b.status === 'pending').length;
  const appliedCount = blocks.filter(b => b.status === 'applied').length;

  return (
    <div className={cn('space-y-2', className)}>
      {/* Summary */}
      <div className="flex items-center justify-between px-1 mb-2">
        <div className="flex items-center gap-2">
          <ArrowRight size={13} className="text-blue-400" />
          <span className="text-[11px] font-medium text-gray-400">
            {blocks.length} 个编辑
          </span>
          {pendingCount > 0 && (
            <span className="text-[10px] text-amber-400">{pendingCount} 待应用</span>
          )}
          {appliedCount > 0 && (
            <span className="text-[10px] text-green-400">{appliedCount} 已应用</span>
          )}
        </div>
        {pendingCount > 1 && onApplyAll && (
          <Button variant="ghost" size="sm" onClick={onApplyAll}>
            <Check size={11} />
            全部应用
          </Button>
        )}
      </div>

      {/* Cards */}
      {blocks.map(block => (
        <SearchReplaceCard
          key={block.id}
          block={block}
          onApply={onApply}
          onReject={onReject}
        />
      ))}
    </div>
  );
}
