import { useState, useMemo, useEffect, useRef, useId, type ReactNode } from 'react';
import { Plus, Minus, FileText, ChevronDown, ChevronRight, Copy, FileDiff } from 'lucide-react';
import { cn } from '../../lib/utils';
import { StatusIcon } from '../ui/StatusIcon';

/**
 * Diff 面板组件
 * 参考 MonkeyCode desktop/ui/src/diffView.tsx
 * 统一 diff 解析器 + 行号 + CSS 变量主题
 *
 * 配色只有 diff 专用角色：新增、删除、hunk 头各自一套前景与底色
 * (`--color-diff-*`)，语义色 success/error 不参与，因为它们是为正文调的，
 * 在密集的代码行上不成立。行内的关键字、字符串、数字、函数名走
 * `--color-syntax-*`，与代码块共用一套色。
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
        // "\ No newline at end of file" — 跳过
      }
    } else if (line.startsWith('+++ ') || line.startsWith('--- ')) {
      // 文件头标记 — 跳过
    }
  }

  if (currentFile) {
    if (currentHunk) currentFile.hunks.push(currentHunk);
    files.push(currentFile);
  }

  return files;
}

type SyntaxKind = 'comment' | 'string' | 'number' | 'keyword' | 'function' | 'punctuation' | 'plain';

/**
 * 语法 token 角色。每个取值都是 `--color-syntax-*`，与代码块高亮里
 * `.code-block .token-*` 解析到的是同一套色板，因此 diff 与代码块读起来是
 * 一个界面，而不是两块调色板。
 */
const SYNTAX_TEXT: Record<SyntaxKind, string> = {
  comment: 'text-[var(--color-syntax-comment)] italic',
  string: 'text-[var(--color-syntax-string)]',
  number: 'text-[var(--color-syntax-number)]',
  keyword: 'text-[var(--color-syntax-keyword)]',
  function: 'text-[var(--color-syntax-function)]',
  punctuation: 'text-[var(--color-text-muted)]',
  plain: '',
};

const KEYWORDS = new Set([
  'as', 'async', 'await', 'break', 'case', 'catch', 'class', 'const', 'continue',
  'def', 'default', 'delete', 'do', 'elif', 'else', 'export', 'extends', 'finally',
  'for', 'from', 'function', 'if', 'import', 'in', 'instanceof', 'interface', 'let',
  'new', 'of', 'return', 'switch', 'this', 'throw', 'try', 'typeof', 'var', 'while',
  'with', 'yield',
]);

/** 单趟扫描一行：注释、字符串、数字、单词、空白、标点。 */
const TOKEN_PATTERN = /\/\/.*$|#[^\s].*$|"(?:[^"\\]|\\.)*"?|'(?:[^'\\]|\\.)*'?|`(?:[^`\\]|\\.)*`?|\b\d+(?:\.\d+)?\b|[A-Za-z_$][\w$]*|\s+|[^\s\w]/;

function classifyToken(token: string, rest: string): SyntaxKind {
  if (token.startsWith('//') || (token.startsWith('#') && !/^#\d/.test(token))) return 'comment';
  if (/^["'`]/.test(token)) return 'string';
  if (/^\d/.test(token)) return 'number';
  if (/^[A-Za-z_$]/.test(token)) {
    if (KEYWORDS.has(token)) return 'keyword';
    // 紧跟调用括号的单词是可调用名。
    return /^\s*\(/.test(rest) ? 'function' : 'plain';
  }
  if (/^\s+$/.test(token)) return 'plain';
  return 'punctuation';
}

/** 行内高亮组件 */
function HighlightedLine({ line }: { line: string }) {
  const parts: ReactNode[] = [];
  let rest = line;
  let index = 0;
  while (rest.length > 0) {
    const match = TOKEN_PATTERN.exec(rest);
    if (!match || match.index === undefined) {
      parts.push(rest);
      break;
    }
    if (match.index > 0) parts.push(rest.slice(0, match.index));
    const token = match[0];
    const kind = classifyToken(token, rest.slice(match.index + token.length));
    const className = SYNTAX_TEXT[kind];
    parts.push(className
      ? <span key={index++} className={className}>{token}</span>
      : <span key={index++}>{token}</span>);
    rest = rest.slice(match.index + token.length);
  }
  return <>{parts}</>;
}

interface DiffLineProps {
  row: DiffRow;
  showLineNumbers: boolean;
}

/**
 * 行类型到 diff 角色类，就是 `index.css` 为这件事发布的三个类。用类而不是
 * 工具类，是因为一行同时带前景与底色，一个类保证两者不会走散。这里自身不画
 * 任何颜色。
 */
const ROW_ROLE: Record<DiffRow['kind'], string> = {
  add: 'diff-line-added',
  del: 'diff-line-removed',
  ctx: '',
  h: 'diff-hunk-header',
};

const PREFIX: Record<DiffRow['kind'], string> = { add: '+', del: '-', ctx: ' ', h: ' ' };

function DiffLine({ row, showLineNumbers }: DiffLineProps) {
  if (row.kind === 'h') {
    return (
      <div className={cn('flex items-center px-[var(--space-2)] py-[var(--space-1)]', ROW_ROLE.h, 'bg-[var(--color-bg-surface-2)]')}>
        <span className="truncate font-mono text-[length:var(--text-2xs)] italic">{row.content || '@@'}</span>
      </div>
    );
  }

  return (
    <div className={cn('flex items-start font-mono text-[length:var(--text-2xs)] leading-normal', ROW_ROLE[row.kind], row.kind === 'ctx' && 'text-[var(--color-text-secondary)]')}>
      {showLineNumbers ? (
        <span className="flex shrink-0 select-none items-stretch py-[var(--space-0-5)] pe-[var(--space-2)]">
          <span className="w-[var(--space-8)] pe-[var(--space-1)] text-end tabular-nums text-[var(--color-text-muted)]">{row.oldN ?? ''}</span>
          <span className="w-[var(--space-8)] pe-[var(--space-1)] text-end tabular-nums text-[var(--color-text-muted)]">{row.newN ?? ''}</span>
          <span className={cn('w-[var(--space-4)] text-center', row.kind === 'ctx' && 'text-[var(--color-text-muted)]')}>{PREFIX[row.kind]}</span>
        </span>
      ) : (
        <span className={cn('w-[var(--space-4)] shrink-0 py-[var(--space-0-5)] text-center', row.kind === 'ctx' && 'text-[var(--color-text-muted)]')}>
          {PREFIX[row.kind]}
        </span>
      )}
      <pre className="min-w-0 flex-1 whitespace-pre py-[var(--space-0-5)] pe-[var(--space-2)]">
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
  const [copyError, setCopyError] = useState(false);
  const copyTimer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const contentId = useId();
  useEffect(() => () => clearTimeout(copyTimer.current), []);

  // 文件级状态是 diff 事实，因此取 diff 角色：新增与删除借行的颜色，修改借
  // hunk 的颜色，因为 hunk 头已经在用那个强调色。
  const statusIcon = {
    added: <Plus size={12} className="text-[var(--color-diff-added)]" />,
    modified: <FileText size={12} className="text-[var(--color-diff-hunk)]" />,
    deleted: <Minus size={12} className="text-[var(--color-diff-removed)]" />,
  }[file.status];

  const handleCopy = async () => {
    const diffText = file.hunks
      .flatMap(h => [h.header, ...h.rows.map(r => `${r.kind === 'add' ? '+' : r.kind === 'del' ? '-' : ' '}${r.content}`)])
      .join('\n');
    setCopyError(false);
    setCopied(false);
    try {
      await navigator.clipboard.writeText(diffText);
      setCopied(true);
      clearTimeout(copyTimer.current);
      copyTimer.current = setTimeout(() => setCopied(false), 2000);
    } catch {
      setCopyError(true);
    }
  };

  const fileName = file.path.split('/').pop() || file.path;
  const dirPath = file.path.split('/').slice(0, -1).join('/');

  const totalLines = file.hunks.reduce((sum, h) => sum + h.rows.length, 0);

  return (
    <div className="overflow-hidden rounded-[var(--radius-md)] border border-[var(--color-border-default)] bg-[var(--color-bg-surface-1)]">
      <div className="flex items-center border-b border-[var(--color-border-subtle)] pr-[var(--space-1)]">
      <button type="button"
        aria-expanded={expanded} aria-controls={contentId} title={file.path}
        className="flex min-w-0 flex-1 items-center gap-[var(--space-2)] px-[var(--space-3)] py-[var(--space-2)] text-start transition-colors hover:bg-[var(--color-bg-surface-2)] focus-visible:outline-none focus-visible:shadow-[var(--focus-ring)] motion-reduce:transition-none"
        onClick={() => setExpanded(!expanded)}
      >
        <span className="shrink-0 text-[var(--color-text-muted)]">
          {expanded
            ? <ChevronDown size={14} aria-hidden="true" />
            : <ChevronRight size={14} aria-hidden="true" />}
        </span>
        {statusIcon}
        {/* The whole path, in the typeface a path belongs in, with the leaf
            picked out so a long directory does not hide which file this is. */}
        <span className="min-w-0 flex-1 truncate font-mono text-[length:var(--text-xs)]">
          {dirPath && <span className="text-[var(--color-text-muted)]">{dirPath}/</span>}
          <span className="text-[var(--color-text-primary)]">{fileName}</span>
        </span>

        <span className="flex shrink-0 items-center gap-[var(--space-2)] font-mono text-[length:var(--text-2xs)] tabular-nums">
          <span className="text-[var(--color-text-muted)]">{totalLines} 行</span>
          {file.additions > 0 && <span className="text-[var(--color-diff-added)]">+{file.additions}</span>}
          {file.deletions > 0 && <span className="text-[var(--color-diff-removed)]">-{file.deletions}</span>}
        </span>
      </button>
      <button type="button" onClick={handleCopy} aria-label={copied ? '已复制' : `复制 ${file.path} 的差异`} title={copied ? '已复制' : '复制差异'}
        className="flex size-[var(--control-height-sm)] shrink-0 items-center justify-center rounded-[var(--radius-sm)] text-[var(--color-text-muted)] transition-colors hover:bg-[var(--color-bg-surface-2)] focus-visible:outline-none focus-visible:shadow-[var(--focus-ring)]">
        {copied ? <StatusIcon tone="success" size="sm" /> : <Copy size={14} aria-hidden="true" />}
      </button>
      </div>
      {copyError && (
        <p role="alert" className="flex items-center gap-[var(--space-2)] border-b border-[var(--color-error)]/30 bg-[var(--color-error-subtle)] px-[var(--space-3)] py-[var(--space-2)] text-[length:var(--text-xs)] text-[var(--color-error)]">
          <StatusIcon tone="error" size="xs" />
          复制失败，请检查剪贴板权限后重试。
        </p>
      )}
      {expanded && (
        <div id={contentId} className="overflow-x-auto">
          <div className="w-max min-w-full">
            {file.hunks.length === 0 && <p className="px-[var(--space-3)] py-[var(--space-4)] text-[length:var(--text-xs)] text-[var(--color-text-muted)]">此文件没有可显示的文本差异。</p>}
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

  if (files.length === 0) return (
    <section className={cn('rounded-[var(--radius-md)] border border-[var(--color-border-default)] bg-[var(--color-bg-surface-1)] p-[var(--space-4)]', className)} aria-label={title}>
      <div className="flex items-center gap-[var(--space-2)] text-[length:var(--text-xs)] font-medium text-[var(--color-text-primary)]"><FileDiff size={15} aria-hidden="true" />{title}</div>
      <p role="status" className="mt-[var(--space-3)] text-[length:var(--text-sm)] text-[var(--color-text-secondary)]">{diffText?.trim() ? '无法显示此差异格式' : '暂无文件变更'}</p>
      <p className="mt-[var(--space-1)] text-[length:var(--text-xs)] text-[var(--color-text-muted)]">{diffText?.trim() ? '请提供包含文件头的 unified diff。' : '文件修改后，差异将在此显示。'}</p>
    </section>
  );

  const totalAdditions = files.reduce((sum, f) => sum + f.additions, 0);
  const totalDeletions = files.reduce((sum, f) => sum + f.deletions, 0);

  return (
    <div className={cn('space-y-[var(--space-2)]', className)}>
      {/* Summary */}
      <div className="mb-[var(--space-2)] flex items-center justify-between px-[var(--space-1)]">
        <div className="flex items-center gap-[var(--space-2)]">
          <FileText size={13} className="text-[var(--color-text-muted)]" aria-hidden="true" />
          <span className="text-[length:var(--text-2xs)] font-medium uppercase tracking-wide text-[var(--color-text-muted)]">{title}</span>
          <span className="font-mono text-[length:var(--text-2xs)] tabular-nums text-[var(--color-text-disabled)]">
            {files.length} 个文件
          </span>
        </div>
        <div className="flex items-center gap-[var(--space-1-5)] font-mono text-[length:var(--text-2xs)] tabular-nums">
          <span className="text-[var(--color-diff-added)]">+{totalAdditions}</span>
          <span className="text-[var(--color-diff-removed)]">-{totalDeletions}</span>
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
