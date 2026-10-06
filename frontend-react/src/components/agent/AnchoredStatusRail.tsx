import { useEffect, useRef, useSyncExternalStore } from 'react';
import { useI18n } from '../../i18n';
import { cn } from '../../lib/utils';
import { useAnchoredStore } from '../../store/anchored';
import type { AgentRunState } from '../../store/anchored';
import { usePermissionConfig } from '../workspace/usePermissionConfig';

/**
 * 底部状态栏（24px）。上半部分渲染 Codex 风格工作指示器
 * `• Working (0s • esc to interrupt)`，保留四态颜色与缓存 / Token 指标；
 * 下半部分渲染单行 footer（`? for shortcuts` / 排队提示 / Plan mode / 上下文余量）。
 * 后端未上报的指标显示“未上报”，不伪造数值。
 */

const STATE_META: Record<AgentRunState, { key: string; className: string; dot: string; motion: string }> = {
  thinking: {
    key: 'anchored.status.thinking',
    className: 'text-[var(--color-accent-foreground)]',
    dot: 'bg-[var(--color-accent-foreground)]',
    motion: 'motion-safe:animate-pulse',
  },
  executing_tool: {
    key: 'anchored.status.executing_tool',
    className: 'text-[var(--color-info)]',
    dot: 'bg-[var(--color-info)]',
    motion: 'motion-safe:animate-pulse',
  },
  awaiting_input: {
    key: 'anchored.status.awaiting_input',
    className: 'text-[var(--color-success)]',
    dot: 'bg-[var(--color-success)]',
    motion: '',
  },
  error: {
    key: 'anchored.status.error',
    className: 'text-[var(--color-error)]',
    dot: 'bg-[var(--color-error)]',
    motion: '',
  },
};

/** Codex 工作态：思考中 / 执行工具。其余状态为静止态。 */
const WORKING_STATES: ReadonlySet<AgentRunState> = new Set(['thinking', 'executing_tool']);

/** 关闭工作态时展示的中断提示（Codex `esc to interrupt`）。 */
const INTERRUPT_HINT = 'esc to interrupt';

/**
 * Composer 与 footer 之间的轻量信号：输入栈与状态栏位于同一会话列，
 * 这里只承载“是否有草稿”与“是否流式”，避免把业务事实塞进 anchored store。
 */
interface ComposerFooterSignal {
  hasDraft: boolean;
  isStreaming: boolean;
}

let composerFooterSignal: ComposerFooterSignal = { hasDraft: false, isStreaming: false };
const composerFooterListeners = new Set<() => void>();

export function setComposerFooterSignal(next: ComposerFooterSignal): void {
  if (next.hasDraft === composerFooterSignal.hasDraft && next.isStreaming === composerFooterSignal.isStreaming) return;
  composerFooterSignal = next;
  for (const listener of composerFooterListeners) listener();
}

function subscribeComposerFooter(listener: () => void): () => void {
  composerFooterListeners.add(listener);
  return () => {
    composerFooterListeners.delete(listener);
  };
}

function readComposerFooter(): ComposerFooterSignal {
  return composerFooterSignal;
}

/** `0s` / `1m 05s` / `1h 02m 03s`（Codex `fmt_elapsed_compact`）。 */
export function formatElapsedCompact(totalSeconds: number): string {
  const seconds = Math.max(0, Math.floor(totalSeconds));
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const rest = seconds % 60;
  if (hours > 0) return `${hours}h ${String(minutes).padStart(2, '0')}m ${String(rest).padStart(2, '0')}s`;
  if (minutes > 0) return `${minutes}m ${String(rest).padStart(2, '0')}s`;
  return `${rest}s`;
}

export interface AnchoredStatusRailProps {
  /** 显式覆盖工作态；缺省时读取 composer 信号并按 agentState 推导。 */
  isStreaming?: boolean;
  /** 显式覆盖草稿态；缺省时读取 composer 信号。 */
  hasDraft?: boolean;
  /** 上下文余量百分比；缺省时不渲染右侧上下文。 */
  contextPercent?: number | null;
  /** 显式覆盖 Plan mode；缺省时按权限模式推导。 */
  planMode?: boolean;
  /** Plan mode 是否展示 `(shift+tab to cycle)`。 */
  planModeCyclable?: boolean;
  /** 附加详情行，渲染为 `  └ ` 前缀。 */
  detailLines?: string[];
}

export function AnchoredStatusRail({
  isStreaming,
  hasDraft,
  contextPercent = null,
  planMode,
  planModeCyclable = false,
  detailLines,
}: AnchoredStatusRailProps = {}) {
  const { t } = useI18n();
  const agentState = useAnchoredStore((s) => s.agentState);
  const cacheHitRate = useAnchoredStore((s) => s.cacheHitRate);
  const turnTokens = useAnchoredStore((s) => s.turnTokens);
  const signal = useSyncExternalStore(subscribeComposerFooter, readComposerFooter, readComposerFooter);

  const meta = STATE_META[agentState];
  const streaming = isStreaming ?? signal.isStreaming ?? WORKING_STATES.has(agentState);
  const draft = hasDraft ?? signal.hasDraft;
  const working = streaming || WORKING_STATES.has(agentState);
  const stateLabel = t(meta.key);

  const planInput = usePermissionConfig();
  const inPlanMode = planMode ?? planInput.mode === 'plan';

  // 已用秒数走直接 DOM 写（ref.textContent），不经过 React state：每秒一跳的自足
  // 显示若用 setState，会让整个树根每秒多产生一次 commit（任务48 的流式渲染预算
  // 按 chunks/4 计，窗口内所有 commit 都计入）。绕过 React 后计时跳动零 commit。
  const elapsedRef = useRef<HTMLSpanElement | null>(null);
  const startedAtRef = useRef<number | null>(null);
  useEffect(() => {
    if (!working) {
      startedAtRef.current = null;
      return;
    }
    if (startedAtRef.current === null) startedAtRef.current = Date.now();
    const paint = () => {
      if (elapsedRef.current) {
        elapsedRef.current.textContent = formatElapsedCompact(Math.floor((Date.now() - (startedAtRef.current ?? Date.now())) / 1000));
      }
    };
    paint();
    const timer = setInterval(paint, 1000);
    return () => clearInterval(timer);
  }, [working]);

  const footerItems: string[] = [];
  if (streaming && draft) footerItems.push('Tab to queue message');
  if (inPlanMode) footerItems.push(planModeCyclable ? 'Plan mode (shift+tab to cycle)' : 'Plan mode');
  if (!draft) footerItems.push(t('anchored.status.shortcuts_hint'));
  if (contextPercent !== null && Number.isFinite(contextPercent)) footerItems.push(`${Math.round(contextPercent)}% context left`);

  return (
    <footer
      className="shrink-0 border-t border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-1)] text-[length:var(--text-2xs)] text-[var(--color-text-muted)]"
    >
      <div
        data-testid="anchored-status-rail"
        data-agent-state={agentState}
        aria-label={t('anchored.status.label')}
        className="flex h-6 shrink-0 items-center gap-[var(--space-4)] px-[var(--space-3)]"
      >
        <span className={cn('flex min-w-0 items-center gap-[var(--space-1-5)]', meta.className)}>
          {working ? (
            <span aria-hidden="true" className={cn('shrink-0 font-bold leading-none', meta.dot, meta.motion)}>
              •
            </span>
          ) : (
            <span aria-hidden="true" className={cn('size-[6px] shrink-0 rounded-[var(--radius-pill)]', meta.dot, meta.motion)} />
          )}
          <span className="truncate">{stateLabel}</span>
          {working && (
            <span className="truncate">
              (<span ref={elapsedRef} data-testid="anchored-status-elapsed">{formatElapsedCompact(0)}</span> • {INTERRUPT_HINT})
            </span>
          )}
        </span>

        <span className="flex items-center gap-[var(--space-1)]">
          <span>{t('anchored.status.cache_hit_rate')}</span>
          <span data-testid="anchored-status-cache" className="tabular-nums text-[var(--color-text-secondary)]">
            {cacheHitRate === null || Number.isNaN(cacheHitRate)
              ? t('anchored.status.unreported')
              : t('anchored.status.cache_percent', { value: Math.round(cacheHitRate * 100) })}
          </span>
        </span>

        <span className="flex items-center gap-[var(--space-1)]">
          <span>{t('anchored.status.turn_tokens')}</span>
          <span data-testid="anchored-status-tokens" className="tabular-nums text-[var(--color-text-secondary)]">
            {turnTokens === null || Number.isNaN(turnTokens)
              ? t('anchored.status.unreported')
              : turnTokens.toLocaleString()}
          </span>
        </span>
      </div>

      {detailLines && detailLines.length > 0 && (
        <ul data-testid="anchored-status-details" className="pl-[2ch] text-[var(--color-text-muted)]">
          {detailLines.map((line, index) => (
            <li key={index} className="truncate">
              <span aria-hidden="true">{'  └ '}</span>
              {line}
            </li>
          ))}
        </ul>
      )}

      <div data-testid="anchored-composer-footer" className="truncate pb-[var(--space-1)] pl-[2ch] text-[var(--color-text-muted)]">
        {footerItems.join(' · ')}
      </div>
    </footer>
  );
}
