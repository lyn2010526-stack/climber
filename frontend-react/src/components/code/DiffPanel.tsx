import { useState, useMemo } from 'react';
import {
  Plus, Minus, FileText, ChevronDown, ChevronRight,
  Copy, Check,
} from 'lucide-react';
import { cn } from '../../lib/utils';

/**
 * Diff 面板组件
 * 参考 MonkeyCode desktop/ui/src/diffView.tsx
 * 统一 diff 解析器 + 行号 + CSS 变量主题
 */

interface DiffRow {
  kind: 'h' | 'add' | 'del' | 'ctx';
  content: string;
  oldN: number | null;
  newN: number | null;
}

interface DiffHunk {
  header: string;
  oldStart: number;
  newStart: number;
  rows: DiffRow[];
}

interface DiffFile {
  path: string;
  hunks: DiffHunk[];
  additions: number;
  deletions: number;
  status: 'added' | 'modified' | 'deleted';
}

/** 解析 unified diff 文本 */
export function parseDiff(diffText: string): DiffFile[] {
  const files: DiffFile[] = [];
  const lines = diffText.split('\n');

  let currentFile: DiffFile | null = null;
  let currentHunk: DiffHunk | null = null;
  let oldN = 0;
  let newN = 0;
  let additions = 0;
  let deletions = 0;

  for (const line of lines) {
    if (line.startsWith('diff --git')) {
      if (currentFile) {
        if (currentHunk) currentFile.hunks.push(currentHunk);
        files.push(currentFile);
      }
      const match = line.match(/b\/(.+)$/);
      const path = match?.[1] ?? 'unknown';
      currentFile = { path, hunks: [], additions: 0, deletions: 0, status: 'modified' };
      currentHunk = null;
      additions = 0;
      deletions = 0;
    } else if (line.startsWith('@@')) {
      if (currentFile && currentHunk) {
        currentFile.hunks.push(currentHunk);
      }
      const match = line.match(/@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@/);
      if (match?.[1] && match?.[2]) {
        oldN = parseInt(match[1], 10);
        newN = parseInt(match[2], 10);
        currentHunk = { header: line, oldStart: oldN, newStart: newN, rows: [] };
      }
    } else if (currentHunk && line.length > 0) {
      const marker = line[0];
      const content = line.slice(1);
      if (marker === '+') {
        currentHunk.rows.push({ kind: 'add', content, oldN: null, newN });
        newN++;
        additions++;
        if (currentFile) currentFile.additions++;
      } else if (marker === '-') {
        currentHunk.rows.push({ kind: 'del', content, oldN, newN: null });
        oldN++;
        deletions++;
        if (currentFile) currentFile.deletions++;
      } else if (marker === ' ') {
        currentHunk.rows.push({ kind: 'ctx', content, oldN, newN });
        oldN++;
        newN++;
      } else if (marker === '\\') {
        // "\ No newline at end of file" — skip
      }
    } else if (line.startsWith('+++ ') || line.startsWith('--- ')) {
      // File header markers — skip
    }
  }

  if (currentFile) {
    if (currentHunk) currentFile.hunks.push(currentHunk);
    files.push(currentFile);
  }

  return files;
}

/** 行内高亮组件 */
function HighlightedLine({ line }: { line: string }) {
  // 简单的语法高亮：关键字、字符串、注释
  const parts = line.split(/(\s+|[{}()[\];,.:=<>!+\-*/]|"[^"]*"|'[^']*'|`[^`]*`)/g);
  return (
    <>
      {parts.map((part, i) => {
        if (/^(import|from|def|class|return|if|else|elif|for|while|try|except|with|as|async|await|function|const|let|var|export|default|new|this|return)$/.test(part)) {
          return <span key={i} className="text-violet-400">{part}</span>;
        }
        if (/^["'`]/.test(part)) {
          return <span key={i} className="text-green-300">{part}</span>;
        }
        if (/^[{}()[\];,.:=<>!+\-*/]$/.test(part)) {
          return <span key={i} className="text-[var(--color-text-muted)]">{part}</span>;
        }
        return <span key={i}>{part}</span>;
      })}
    </>
  );
}

interface DiffLineProps {
  row: DiffRow;
  showLineNumbers: boolean;
}

function DiffLine({ row, showLineNumbers }: DiffLineProps) {
  const bgColor = {
    add: 'bg-green-500/[0.06]',
    del: 'bg-red-500/[0.06]',
    ctx: 'bg-transparent',
    h: 'bg-[var(--codeBg,#1a1a2e)]',
  }[row.kind];

  const gutterBg = {
    add: 'bg-green-500/[0.12]',
    del: 'bg-red-500/[0.12]',
    ctx: 'bg-transparent',
    h: 'bg-[var(--codeBg,#1a1a2e)]',
  }[row.kind];

  const prefix = {
    add: '+',
    del: '-',
    ctx: ' ',
    h: ' ',
  }[row.kind];

  const prefixColor = {
    add: 'text-green-500/70',
    del: 'text-red-500/70',
    ctx: 'text-[var(--color-text-muted)]',
    h: 'text-[var(--color-text-muted)]',
  }[row.kind];

  const textColor = {
    add: 'text-green-200/90',
    del: 'text-red-200/90',
    ctx: 'text-[var(--color-text-secondary)]',
    h: 'text-blue-300/70',
  }[row.kind];

  if (row.kind === 'h') {
    return (
      <div className={cn('flex items-center px-2 py-1', bgColor)}>
        <span className="text-[11px] font-mono italic truncate">
          {row.content || '@@'}
        </span>
      </div>
    );
  }

  return (
    <div className={cn('flex items-start', bgColor)}>
      {showLineNumbers && (
        <div className={cn(
          'flex items-center justify-end gap-1 shrink-0 select-none',
          'w-[72px] px-2 py-0.5 font-mono text-[11px]',
          gutterBg
        )}>
          <span className="w-6 text-right text-[var(--color-text-muted)]">
            {row.oldN ?? ''}
          </span>
          <span className="w-6 text-right text-[var(--color-text-muted)]">
            {row.newN ?? ''}
          </span>
          <span className={cn('w-3 text-center', prefixColor)}>
            {prefix}
          </span>
        </div>
      )}
      {!showLineNumbers && (
        <span className={cn('w-4 text-center text-[11px] font-mono shrink-0 py-0.5', prefixColor)}>
          {prefix}
        </span>
      )}
      <pre className={cn('flex-1 text-[11px] font-mono py-0.5 px-2 overflow-x-auto', textColor)}>
        <HighlightedLine line={row.content} />
      </pre>
    </div>
  );
}

interface DiffFileViewProps {
  file: DiffFile;
  defaultExpanded?: boolean;
  showLineNumbers?: boolean;
}

function DiffFileView({ file, defaultExpanded = true, showLineNumbers = true }: DiffFileViewProps) {
  const [expanded, setExpanded] = useState(defaultExpanded);
  const [copied, setCopied] = useState(false);

  const statusIcon = {
    added: <Plus size={12} className="text-green-400" />,
    modified: <FileText size={12} className="text-amber-400" />,
    deleted: <Minus size={12} className="text-red-400" />,
  }[file.status];

  const handleCopy = () => {
    const diffText = file.hunks
      .flatMap(h => [h.header, ...h.rows.map(r => `${r.kind === 'add' ? '+' : r.kind === 'del' ? '-' : ' '}${r.content}`)])
      .join('\n');
    navigator.clipboard.writeText(diffText);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const fileName = file.path.split('/').pop() || file.path;
  const dirPath = file.path.split('/').slice(0, -1).join('/');

  const totalLines = file.hunks.reduce((sum, h) => sum + h.rows.length, 0);

  return (
    <div className="rounded-xl border border-white/[0.06] bg-white/[0.02] overflow-hidden">
      {/* File header */}
      <button
        className="w-full flex items-center gap-2.5 px-3 py-2.5 text-left hover:bg-white/[0.02] transition-colors"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="shrink-0">
          {expanded ? (
            <ChevronDown size={14} className="text-[var(--color-text-muted)]" />
          ) : (
            <ChevronRight size={14} className="text-[var(--color-text-muted)]" />
          )}
        </div>
        {statusIcon}
        <div className="flex-1 min-w-0">
          <span className="text-xs font-medium text-[var(--color-text-secondary)]">{fileName}</span>
          {dirPath && (
            <span className="text-[10px] text-[var(--color-text-muted)] ml-2">{dirPath}/</span>
          )}
        </div>

        {/* Stats */}
        <div className="flex items-center gap-2 shrink-0">
          <span className="text-[10px] text-[var(--color-text-muted)] font-mono">{totalLines} 行</span>
          {file.additions > 0 && (
            <span className="text-[10px] text-green-400 font-mono">+{file.additions}</span>
          )}
          {file.deletions > 0 && (
            <span className="text-[10px] text-red-400 font-mono">-{file.deletions}</span>
          )}
          <button
            onClick={(e) => { e.stopPropagation(); handleCopy(); }}
            className="p-1 rounded hover:bg-white/[0.06] text-[var(--color-text-muted)] transition-colors"
          >
            {copied ? <Check size={12} className="text-green-400" /> : <Copy size={12} />}
          </button>
        </div>
      </button>

      {/* Diff content */}
      {expanded && (
        <div className="border-t border-white/[0.04] overflow-x-auto">
          {file.hunks.map((hunk, hi) => (
            <div key={hi}>
              <DiffLine
                row={{ kind: 'h', content: hunk.header, oldN: null, newN: null }}
                showLineNumbers={showLineNumbers}
              />
              {hunk.rows.map((row, ri) => (
                <DiffLine key={ri} row={row} showLineNumbers={showLineNumbers} />
              ))}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

interface DiffPanelProps {
  diffText?: string;
  files?: DiffFile[];
  className?: string;
  title?: string;
  showLineNumbers?: boolean;
}

/**
 * Diff 面板 — 显示 unified diff 格式的文件变更
 *
 * 用法:
 * ```tsx
 * <DiffPanel diffText={gitDiffOutput} />
 * <DiffPanel files={parsedFiles} />
 * ```
 */
export function DiffPanel({
  diffText,
  files: propFiles,
  className,
  title = '文件变更',
  showLineNumbers = true,
}: DiffPanelProps) {
  const files = useMemo(() => {
    if (propFiles) return propFiles;
    if (diffText) return parseDiff(diffText);
    return [];
  }, [diffText, propFiles]);

  if (files.length === 0) return null;

  const totalAdditions = files.reduce((sum, f) => sum + f.additions, 0);
  const totalDeletions = files.reduce((sum, f) => sum + f.deletions, 0);

  return (
    <div className={cn('space-y-2', className)}>
      {/* Summary */}
      <div className="flex items-center justify-between px-1 mb-2">
        <div className="flex items-center gap-2">
          <FileText size={13} className="text-[var(--color-text-muted)]" />
          <span className="text-[11px] font-medium text-[var(--color-text-muted)]">{title}</span>
          <span className="text-[10px] text-[var(--color-text-muted)]">
            {files.length} 个文件
          </span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="text-[10px] text-green-400 font-mono">+{totalAdditions}</span>
          <span className="text-[10px] text-red-400 font-mono">-{totalDeletions}</span>
        </div>
      </div>

      {/* File list */}
      {files.map((file, index) => (
        <DiffFileView
          key={`${file.path}-${index}`}
          file={file}
          showLineNumbers={showLineNumbers}
        />
      ))}
    </div>
  );
}

export type { DiffFile, DiffRow, DiffHunk };
