import { cn } from '../../lib/utils';
import cards from './chatCards.module.css';

/**
 * 工具/流状态色点：running 为 teal 呼吸脉动，success / error 静色，
 * pending 暗淡。纯装饰（aria-hidden），状态文本由调用方以 pill 呈现。
 */
export type ChatStatus = 'running' | 'success' | 'error' | 'pending';

const DOT_CLASS: Record<ChatStatus, string | undefined> = {
  running: cards.statusDotRunning,
  success: cards.statusDotSuccess,
  error: cards.statusDotError,
  pending: cards.statusDotPending,
};

export function StatusDot({ status, className }: { status: ChatStatus; className?: string }) {
  return (
    <span
      aria-hidden="true"
      data-status-dot={status}
      className={cn(cards.statusDot, DOT_CLASS[status], className)}
    />
  );
}
