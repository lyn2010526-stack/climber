import { CircleAlert } from 'lucide-react';
import { useI18n } from '../../i18n';
import { cn } from '../../lib/utils';
import cards from './chatCards.module.css';

/**
 * 聊天列三态里的「加载」与「错误」。空态由 ChatEmptyState 承载，
 * 这两个组件补齐同一视觉语言下的另外两态：
 *
 * - ChatStreamSkeleton：消息流骨架。微脉冲只动 opacity（必要时 transform），
 *   骨架本身零位移，prefers-reduced-motion 下由模块内媒体查询压平。
 * - ChatStreamError：错误卡。1px hairline + 12px 圆角 + 状态色点，
 *   附同一个重试入口；渲染契约（role=alert + retry）由调用方决定。
 */

interface ChatStreamSkeletonProps {
  /** 骨架行数；默认 3 行，足够读出「这是一列消息」。 */
  rows?: number;
  className?: string;
  'data-testid'?: string;
}

/** 一行骨架：40px 头像瓦片 + 两行文本条。 */
function SkeletonRow({ index }: { index: number }) {
  return (
    <div className="flex min-w-0 items-start gap-[var(--space-3)]" data-testid="chat-skeleton-row">
      <span
        aria-hidden="true"
        className={cn(cards.skeleton, cards.skeletonPulse, 'size-10 shrink-0 rounded-[var(--radius-md)]')}
        style={{ animationDelay: `${index * 120}ms` }}
      />
      <span className="flex min-w-0 flex-1 flex-col gap-[var(--space-2)] pt-[var(--space-1)]">
        <span
          aria-hidden="true"
          className={cn(cards.skeleton, cards.skeletonPulse, 'h-3 w-3/5')}
          style={{ animationDelay: `${index * 120 + 60}ms` }}
        />
        <span
          aria-hidden="true"
          className={cn(cards.skeleton, cards.skeletonPulse, 'h-3 w-2/5')}
          style={{ animationDelay: `${index * 120 + 120}ms` }}
        />
      </span>
    </div>
  );
}

export function ChatStreamSkeleton({ rows = 3, className, 'data-testid': testId }: ChatStreamSkeletonProps) {
  return (
    <div
      role="status"
      aria-busy="true"
      data-testid={testId ?? 'chat-stream-skeleton'}
      className={cn('flex w-full min-w-0 flex-col gap-[var(--space-3)]', className)}
    >
      <span className="sr-only">Loading…</span>
      {Array.from({ length: rows }, (_, index) => (
        <SkeletonRow key={index} index={index} />
      ))}
    </div>
  );
}

interface ChatStreamErrorProps {
  message: string;
  onRetry?: () => void;
  retryDisabled?: boolean;
  className?: string;
  'data-testid'?: string;
}

export function ChatStreamError({
  message,
  onRetry,
  retryDisabled = false,
  className,
  'data-testid': testId,
}: ChatStreamErrorProps) {
  const { t } = useI18n();
  return (
    <div
      role="alert"
      data-testid={testId ?? 'chat-stream-error'}
      className={cn(cards.card, 'px-[var(--space-4)] py-[var(--space-3)]', className)}
    >
      <div className="flex flex-row items-center gap-[var(--space-3)]">
        <span aria-hidden="true" className={cn(cards.statusDot, cards.statusDotError)} />
        <CircleAlert size={14} aria-hidden="true" className="shrink-0 text-[var(--color-error)]" />
        <p className="min-w-0 flex-1 whitespace-pre-wrap break-words text-[length:var(--text-xs)] leading-relaxed text-[var(--color-error)]">
          {message}
        </p>
        {onRetry && (
          <button
            type="button"
            onClick={onRetry}
            disabled={retryDisabled}
            className={cn(cards.cardButton, cards.cardButtonOutline, 'shrink-0')}
          >
            {t('common.retry', { defaultValue: '重试' })}
          </button>
        )}
      </div>
    </div>
  );
}
