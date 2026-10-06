import { useI18n } from '../../i18n';
import { cn } from '../../lib/utils';

/**
 * Codex 底部 footer 的上下文行（`footer.rs:954-972` 形态）：
 * `cwd · model · tokens`，mono、tabular-nums、13px，顶部一条 hairline。
 * 后端未上报的字段显示为“未上报”，绝不伪造数值。
 */

/** `format_tokens_compact`（`status/helpers.rs:106-145`）：1000 → 1K、12345 → 12.3K。 */
export function formatTokensCompact(value: number): string {
  const n = Math.max(0, Math.floor(value));
  if (n === 0) return '0';
  if (n < 1_000) return String(n);
  const [scale, suffix] = n >= 1_000_000_000_000 ? [1_000_000_000_000, 'T']
    : n >= 1_000_000_000 ? [1_000_000_000, 'B']
      : n >= 1_000_000 ? [1_000_000, 'M']
        : [1_000, 'K'];
  const scaled = n / scale;
  const decimals = scaled < 10 ? 2 : scaled < 100 ? 1 : 0;
  const fixed = scaled.toFixed(decimals);
  const trimmed = fixed.includes('.') ? fixed.replace(/0+$/, '').replace(/\.$/, '') : fixed;
  return `${trimmed}${suffix}`;
}

export interface ComposerStatusBarProps {
  /** 当前工作目录；未上报时显示“未上报”。 */
  cwd?: string | null;
  /** 模型名；未上报时显示“未上报”。 */
  model?: string | null;
  /** 本轮 token 用量；未上报时显示“未上报”。 */
  turnTokens?: number | null;
  className?: string;
}

export function ComposerStatusBar({ cwd, model, turnTokens, className }: ComposerStatusBarProps) {
  const { t } = useI18n();
  const unreported = t('anchored.status.unreported', { defaultValue: '未上报' });
  const hasTokens = turnTokens !== null && turnTokens !== undefined && !Number.isNaN(turnTokens);

  const items: Array<{ key: string; value: string; tone: string }> = [
    { key: 'cwd', value: cwd?.trim() ? cwd.trim() : unreported, tone: 'text-[var(--color-text-secondary)]' },
    { key: 'model', value: model?.trim() ? model.trim() : unreported, tone: 'text-[var(--color-text-primary)]' },
    { key: 'tokens', value: hasTokens ? formatTokensCompact(turnTokens) : unreported, tone: 'text-[var(--color-text-muted)]' },
  ];

  return (
    <div
      data-testid="composer-status-bar"
      className={cn(
        'flex min-w-0 flex-wrap items-center gap-x-[var(--space-2)] gap-y-[var(--space-1)]',
        'border-t border-[var(--color-border-subtle)] px-[var(--space-6)] pt-[var(--space-1)]',
        'font-mono text-[length:13px] tabular-nums leading-normal',
        className,
      )}
    >
      {items.map((item, index) => (
        <span key={item.key} className="flex min-w-0 items-center gap-x-[var(--space-2)]">
          {index > 0 && (
            <span aria-hidden="true" className="shrink-0 text-[var(--color-text-muted)]">
              ·
            </span>
          )}
          <span data-testid={`composer-status-${item.key}`} className={cn('min-w-0 truncate', item.tone)}>
            {item.value}
          </span>
        </span>
      ))}
    </div>
  );
}

export default ComposerStatusBar;
