import { useEffect, useRef } from 'react';
import { useI18n } from '../../i18n';
import { cn } from '../../lib/utils';
import { formatElapsedCompact } from './AnchoredStatusRail';

/**
 * Codex 工作指示器（`status_indicator_widget.rs:222-290` 形态）：
 *   `• Working (elapsed • esc to interrupt) · inline-msg`
 *   `  └ details`（超宽由 `truncate` 收成 `…`）
 *
 * 首行只承载工作态、已用时长与中断提示；可选的内联消息挂在固定位置之后，
 * 详情行统一用 `  └ ` 前缀，避免主信息与次要信息争夺同一行。
 * 时长复用状态栏的 `formatElapsedCompact`，不自造格式。
 */
export interface StatusIndicatorProps {
  /** 是否处于工作态；为 false 时整个指示器不渲染。 */
  isWorking: boolean;
  /** 工作态标签，缺省为 `工作中`。 */
  label?: string;
  /** 计时起点（毫秒），缺省为挂载时刻。 */
  startedAt?: number | null;
  /** 追加在时长/中断提示之后的单行内联消息。 */
  inlineMessage?: string | null;
  /** 详情行，每行渲染为 `  └ ` 前缀的截断行。 */
  detailLines?: string[];
  /** 中断提示，缺省为 `esc 中断`。 */
  interruptHint?: string;
  /** 显式覆盖已用秒数（测试用）；提供时不再自计时。 */
  elapsedSeconds?: number;
  className?: string;
}

export function StatusIndicator({
  isWorking,
  label,
  startedAt,
  inlineMessage,
  detailLines,
  interruptHint,
  elapsedSeconds,
  className,
}: StatusIndicatorProps) {
  const { t } = useI18n();
  const resolvedLabel = label ?? t('agent.status_indicator.working', { defaultValue: '工作中' });
  const resolvedHint = interruptHint ?? t('agent.status_indicator.interrupt', { defaultValue: 'esc 中断' });

  // 已用秒数走直接 DOM 写（ref.textContent），不经过 React state：这是一个每秒
  // 一跳的自足小显示，用 setState 会让整个树根每秒多产生一次 commit（任务48 的
  // 流式渲染预算按 chunks/4 计，窗口内所有 commit 都计入）。绕过 React 后，计时
  // 跳动零 commit。
  const secondsRef = useRef<HTMLSpanElement | null>(null);
  useEffect(() => {
    if (!isWorking || elapsedSeconds !== undefined) return undefined;
    const start = startedAt ?? Date.now();
    const paint = () => {
      if (secondsRef.current) {
        secondsRef.current.textContent = formatElapsedCompact(Math.max(0, Math.floor((Date.now() - start) / 1000)));
      }
    };
    paint();
    const timer = setInterval(paint, 1000);
    return () => clearInterval(timer);
  }, [isWorking, startedAt, elapsedSeconds]);

  if (!isWorking) return null;

  const details = detailLines ?? [];

  return (
    <div
      data-testid="status-indicator"
      className={cn(
        'flex min-w-0 flex-col font-mono text-[length:var(--text-xs)] leading-[var(--leading-normal)]',
        className,
      )}
    >
      <p className="flex min-w-0 items-center gap-[var(--space-1-5)]">
        <span
          aria-hidden="true"
          data-testid="status-indicator-bullet"
          className="shrink-0 select-none font-bold text-[var(--color-accent-foreground)] motion-safe:animate-pulse"
        >
          •
        </span>
        <span className="shrink-0 font-bold text-[var(--color-text-primary)]">{resolvedLabel}</span>
        <span className="min-w-0 truncate text-[var(--color-text-muted)]">
          ({elapsedSeconds !== undefined
            ? formatElapsedCompact(elapsedSeconds)
            : <span ref={secondsRef} data-testid="status-indicator-elapsed">{formatElapsedCompact(0)}</span>} • {resolvedHint})
        </span>
        {inlineMessage && (
          <span className="min-w-0 truncate text-[var(--color-text-muted)]">· {inlineMessage}</span>
        )}
      </p>
      {details.length > 0 && (
        <ul data-testid="status-indicator-details" className="pl-[2ch] text-[var(--color-text-muted)]">
          {details.map((line, index) => (
            <li key={index} className="truncate">
              <span aria-hidden="true">{'  └ '}</span>
              {line}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export default StatusIndicator;
