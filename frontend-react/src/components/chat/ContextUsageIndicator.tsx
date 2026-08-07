import { cn } from '../../lib/utils';

interface ContextUsageIndicatorProps {
  currentTokens: number;
  maxTokens: number;
  className?: string;
}

export function ContextUsageIndicator({
  currentTokens,
  maxTokens,
  className,
}: ContextUsageIndicatorProps) {
  const percentage = Math.min((currentTokens / maxTokens) * 100, 100);
  const isWarning = percentage > 70;
  const isCritical = percentage > 90;

  const barColor = isCritical
    ? 'var(--color-error)'
    : isWarning
      ? 'var(--color-warning)'
      : 'var(--color-accent)';

  const textColor = isCritical
    ? 'var(--color-error)'
    : isWarning
      ? 'var(--color-warning)'
      : 'var(--color-text-muted)';

  return (
    <div className={cn('flex items-center gap-2', className)}>
      <div
        className="flex-1 h-1 rounded-full overflow-hidden"
        style={{ backgroundColor: 'var(--color-bg-surface-3)' }}
      >
        <div
          className="h-full rounded-full transition-all duration-500 ease-out"
          style={{
            width: `${percentage}%`,
            backgroundColor: barColor,
            boxShadow: isCritical ? `0 0 6px ${barColor}` : 'none',
          }}
        />
      </div>

      <span className="text-[10px] tabular-nums shrink-0" style={{ color: textColor }}>
        {currentTokens.toLocaleString()} / {maxTokens.toLocaleString()}
      </span>
    </div>
  );
}
