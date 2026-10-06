import { useMemo } from 'react';
import { useI18n } from '../../i18n';
import { cn } from '../../lib/utils';

/**
 * Codex 单栏 diff 单元格（`diff_render.rs:442-520` 形态）：
 *   `• Edited path (+A -R)`
 *   `  └ path`
 *   行号 gutter + sign（`+` / `-` / 空格）+ 内容
 *
 * 与旧的左右分栏 DiffBlock 并存：DiffBlock 及其 `splitDiffRows` / `looksLikeDiff`
 * 导出保持不变，本组件只在工具卡展开区承担单栏 diff 呈现。
 */
export type DiffSign = ' ' | '+' | '-';

export interface DiffCellLine {
  /** 旧文件行号；新增行与 hunk 头为 null。 */
  oldNo: number | null;
  /** 新文件行号；删除行为 null。 */
  newNo: number | null;
  sign: DiffSign;
  text: string;
}

export interface ParsedDiffCell {
  /** 新文件路径（删除文件回退到旧路径）；无法解析时为 null。 */
  path: string | null;
  added: number;
  removed: number;
  lines: DiffCellLine[];
}

const stripPathPrefix = (value: string): string => value.replace(/^[ab]\//, '');

/** 把 unified diff 解析成单栏结构：跳过文件头/hunk 头，只保留可染色的内容行。 */
export function parseDiffCell(diffText: string): ParsedDiffCell {
  let path: string | null = null;
  let added = 0;
  let removed = 0;
  let oldNo = 0;
  let newNo = 0;
  const lines: DiffCellLine[] = [];

  for (const raw of diffText.split('\n')) {
    if (raw.startsWith('diff --git ')) {
      const match = raw.match(/^diff --git a\/(.+?) b\/(.+)$/);
      if (match?.[2]) path = match[2];
      continue;
    }
    if (raw.startsWith('--- ')) {
      const candidate = raw.slice(4).trim();
      if (!path && candidate && candidate !== '/dev/null') path = stripPathPrefix(candidate);
      continue;
    }
    if (raw.startsWith('+++ ')) {
      const candidate = raw.slice(4).trim();
      if (candidate && candidate !== '/dev/null') path = stripPathPrefix(candidate);
      continue;
    }
    if (raw.startsWith('@@')) {
      const match = raw.match(/@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@/);
      if (match?.[1]) oldNo = Number.parseInt(match[1], 10);
      if (match?.[2]) newNo = Number.parseInt(match[2], 10);
      continue;
    }
    if (raw === '') continue;
    const sign = raw[0];
    const text = raw.slice(1);
    if (sign === '+') {
      lines.push({ oldNo: null, newNo: newNo++, sign: '+', text });
      added += 1;
    } else if (sign === '-') {
      lines.push({ oldNo: oldNo++, newNo: null, sign: '-', text });
      removed += 1;
    } else if (sign === ' ' || sign === '\t') {
      lines.push({ oldNo: oldNo++, newNo: newNo++, sign: ' ', text });
    }
  }

  return { path, added, removed, lines };
}

const SIGN_TONE: Record<DiffSign, string> = {
  ' ': 'text-[var(--color-text-secondary)]',
  '+': 'text-[var(--color-diff-added)]',
  '-': 'text-[var(--color-diff-removed)]',
};

export function DiffCell({ diffText, className }: { diffText: string; className?: string }) {
  const { t } = useI18n();
  const parsed = useMemo(() => parseDiffCell(diffText), [diffText]);
  const path = parsed.path ?? t('anchored.messages.diff_unknown_path', { defaultValue: '未命名文件' });

  return (
    <div
      data-testid="anchored-diff-cell"
      role="table"
      aria-label={t('anchored.messages.diff_block', { defaultValue: '代码差异' })}
      className={cn(
        'mt-[var(--space-2)] min-w-0 font-mono text-[length:var(--text-2xs)] leading-[var(--leading-normal)]',
        className,
      )}
    >
      <p className="flex min-w-0 items-baseline gap-[var(--space-1-5)]">
        <span aria-hidden="true" className="shrink-0 select-none font-bold text-[var(--color-text-muted)]">•</span>
        <span className="shrink-0 font-bold text-[var(--color-text-primary)]">
          {t('anchored.messages.diff_edited', { defaultValue: '已编辑' })}
        </span>
        <span className="min-w-0 truncate text-[var(--color-text-secondary)]">{path}</span>
        <span className="shrink-0 text-[var(--color-success)]">+{parsed.added}</span>
        <span className="shrink-0 text-[var(--color-error)]">-{parsed.removed}</span>
      </p>

      <p className="flex min-w-0 gap-[var(--space-1-5)] text-[var(--color-text-muted)]">
        <span aria-hidden="true" className="shrink-0 select-none">{'  └ '}</span>
        <span className="min-w-0 truncate">{path}</span>
      </p>

      <div role="rowgroup" className="max-h-[var(--anchored-result-height)] overflow-auto">
        {parsed.lines.map((line, index) => (
          <div role="row" key={index} className="flex min-w-0 gap-[var(--space-1-5)]">
            <span role="cell" className="w-8 shrink-0 select-none text-right text-[var(--color-syntax-comment)]">
              {line.oldNo ?? ''}
            </span>
            <span role="cell" className="w-8 shrink-0 select-none text-right text-[var(--color-syntax-comment)]">
              {line.newNo ?? ''}
            </span>
            <span role="cell" aria-hidden="true" className={cn('w-[1ch] shrink-0 select-none font-bold', SIGN_TONE[line.sign])}>
              {line.sign === ' ' ? ' ' : line.sign}
            </span>
            <span role="cell" className={cn('min-w-0 [overflow-wrap:anywhere] whitespace-pre-wrap', SIGN_TONE[line.sign])}>
              {line.text}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

export default DiffCell;
