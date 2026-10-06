import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react';
import { useI18n } from '../../i18n';
import { cn } from '../../lib/utils';
import { useChat } from '../../useChat';
import { usePanelAutoReveal } from '../../hooks/usePanelAutoReveal';
import { api } from '../../api';
import { useWorkspaceStore } from '../../store/workspace';
import type { RuntimeReport } from '../../types/chatEvents';
import { useAnchoredStore, resetAnchoredStore } from '../../store/anchored';
import { useSmoothScroll } from '../../hooks/useSmoothScroll';
import { ScrollReveal } from '../motion/ScrollReveal';
import { AnchoredComposer } from './AnchoredComposer';
import { AnchoredMessageFlow } from './AnchoredMessageFlow';
import { AnchoredStatusRail } from './AnchoredStatusRail';
import { StatusIndicator } from './StatusIndicator';
import { ChatEmptyState } from './ChatEmptyState';
import { ChatStreamError } from '../chat/ChatStreamStates';
import { LoopStatusPanel } from './LoopStatusPanel';
import { RawRenderedToggle } from './RawRenderedToggle';
import { TypewriterModeToggle } from './TypewriterModeToggle';
import { DeliverablesCard } from './DeliverablesCard';
import { selectTurnDeliverables } from './deliverables';
import type { ContentView } from './RawRenderedToggle';
import { WorkbenchIcon } from '../ui/WorkbenchIcon';
import { Button } from '../ui/Button';

/** 运行报告的四个分类与其中的 i18n 键；渲染视图与"是否存在原始载荷"共用这一份顺序。 */
const REPORT_SECTIONS = [
  ['completed', 'anchored.report.section_completed'],
  ['executing', 'anchored.report.section_executing'],
  ['queued', 'anchored.report.section_queued'],
  ['risks', 'anchored.report.section_risks'],
] as const satisfies ReadonlyArray<readonly [keyof RuntimeReport, string]>;

const INPUT_STATUS_KEYS = {
  pending: 'anchored.queue.st_pending',
  unconfirmed: 'anchored.queue.st_unconfirmed',
  queued: 'anchored.queue.st_queued',
  applied: 'anchored.queue.st_applied',
  started: 'anchored.queue.st_started',
  completed: 'anchored.queue.st_completed',
  blocked: 'anchored.queue.st_blocked',
  failed: 'anchored.queue.st_failed',
} as const;

/**
 * 中间栏（自上而下）：顶部标题栏 48px → 消息流 → 底部输入栈（64–240px）→
 * 底部状态栏 24px。流式事件在这里接进 anchored store：驱动状态栏四态、
 * 任务看板 / 任务树 / 文件预览的自动展开与 5 秒自动折叠。
 */
export function AnchoredChatColumn({ sessionId, onToggleInfo }: { sessionId: string | null; onToggleInfo?: () => void }) {
  const { t } = useI18n();
  const { handleChatEvent, reset: resetPanelReveal } = usePanelAutoReveal({
    i18n: { approvalTitle: () => t('anchored.popup.approval_title') },
  });
   const { messages, isStreaming, error, sendMessage, stopStreaming, retry, inputs = [], runtimeReport, submitInput, retryInput, resumeInputs, resumePending, resumeFeedback, startInputs } = useChat(sessionId, { onEvent: handleChatEvent });
  const [reviewedSession, setReviewedSession] = useState<string | null>(null);
  useSmoothScroll();
  useEffect(() => { setReviewedSession(null); }, [sessionId, inputs]);
  const session = useWorkspaceStore((s) => s.sessions.find((item) => item.id === sessionId));
  const scrollRef = useRef<HTMLDivElement>(null);
  const wasStreamingRef = useRef(false);
  const [reportView, setReportView] = useState<ContentView>('rendered');
  useEffect(() => { resetAnchoredStore(); resetPanelReveal(); }, [sessionId, resetPanelReveal]);

  // 换会话后回到渲染视图；报告消失（新回合开始）也复位，新的报告不沿用上一轮的 Raw 选择。
  useEffect(() => { setReportView('rendered'); }, [sessionId]);
  useEffect(() => { if (!runtimeReport) setReportView('rendered'); }, [runtimeReport]);

  const noteTurnStart = useAnchoredStore((s) => s.noteTurnStart);
  const noteTurnEnd = useAnchoredStore((s) => s.noteTurnEnd);
  const markToolFailed = useAnchoredStore((s) => s.markToolFailed);
  const setUsage = useAnchoredStore((s) => s.setUsage);

  // 交付物卡片：最近一个产出交付物的回合（文件变更 / 网页），流式中即时更新。
  const deliverables = useMemo(() => selectTurnDeliverables(messages), [messages]);

  const openDeliverableFile = useCallback((path: string) => {
    const state = useAnchoredStore.getState();
    const existing = state.previews.find((preview) => preview.path === path);
    if (existing) {
      useAnchoredStore.setState({
        cardsOpen: { ...state.cardsOpen, filePreview: true },
        activePreviewId: existing.id,
      });
      return;
    }
    state.openFilePreview({
      name: path.split('/').at(-1) ?? path,
      path,
      lines: [{ marker: 'ctx', text: path }],
    });
  }, []);

  // 新回合开始：触发规则（调用工具 → 状态栏、新任务 → 任务看板）。
  useEffect(() => {
    if (isStreaming) noteTurnStart();
    else if (wasStreamingRef.current) noteTurnEnd();
    wasStreamingRef.current = isStreaming;
  }, [isStreaming, noteTurnStart, noteTurnEnd]);

  // 工具状态：本轮有运行中的工具 → 执行工具；否则 → 思考中；异常 → 异常。
  const lastMessage = messages.at(-1);
  const runningTool = useMemo(
    () =>
      (lastMessage?.toolCalls ?? []).some((call) => call.status === 'running'),
    [lastMessage],
  );
  // 工作指示器的 `  └ ` 详情行：当前正在执行的工具名，未运行时留空不编造。
  const runningToolName = useMemo(
    () => (lastMessage?.toolCalls ?? []).find((call) => call.status === 'running')?.name,
    [lastMessage],
  );
  const popups = useAnchoredStore((s) => s.popups);
  const agentStateMessage = useAnchoredStore((s) => s.agentStateMessage);
  const agentState = error
     ? ('error' as const)
     : popups.some((popup) => popup.kind === 'approval')
       ? ('awaiting_input' as const)
    : isStreaming
      ? runningTool
        ? ('executing_tool' as const)
        : ('thinking' as const)
      : ('awaiting_input' as const);

  useEffect(() => {
    useAnchoredStore.setState({ agentState });
  }, [agentState]);

  // 失败：以失败收尾的回合，自动展开该工具结果块（markToolFailed）。
  useEffect(() => {
    if (!lastMessage?.failed) return;
    for (const call of lastMessage.toolCalls ?? []) {
      if (call.status === 'running' || call.status === undefined) markToolFailed(call.id);
    }
  }, [lastMessage, markToolFailed]);

  // 指标：回合结束后拉取统计，未上报时保持 null（界面显示“未上报”）。
  useEffect(() => {
    if (isStreaming) return;
    let active = true;
    api
      .getStats()
      .then((stats: Record<string, unknown> | null | undefined) => {
        if (!active) return;
        const hitRate = stats?.['cache_hit_rate'] ?? stats?.['cacheHitRate'];
        const tokens = stats?.['turn_tokens'] ?? stats?.['turnTokens'];
        setUsage({
          cacheHitRate: typeof hitRate === 'number' ? hitRate : null,
          turnTokens: typeof tokens === 'number' ? tokens : null,
        });
      })
      .catch(() => {
        if (active) setUsage({ cacheHitRate: null, turnTokens: null });
      });
    return () => {
      active = false;
    };
  }, [isStreaming, setUsage]);

  // 跟随滚动：流式输出时自动跟随到底部。用 useLayoutEffect 而非 useEffect——
  // 在浏览器绘制之前同步纠正 scrollTop，避免「先按旧内容绘制一帧、再跳到底部」
  // 造成的跟随漂移（任务48 scrollStability 实测 follow 漂移 103px）。
  const followRef = useRef(true);
  useLayoutEffect(() => {
    if (scrollRef.current && followRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, isStreaming]);

  // 运行报告：渲染视图始终是默认视图；只有后端真的报了条目才附上原始载荷与
  // Raw 切换，四类都未上报时保持纯渲染区域。
  const reportHasRaw = Boolean(runtimeReport && REPORT_SECTIONS.some(([key]) => (runtimeReport[key]?.length ?? 0) > 0));
  const reportBody = (
    <details>
      <summary className="cursor-pointer text-[var(--color-text-muted)]">{t('anchored.report.report_title')} · {runtimeReport?.completed?.length != null ? t('anchored.report.completed_items', { count: runtimeReport.completed.length }) : t('anchored.status.unreported')} · {runtimeReport?.risks?.length != null ? t('anchored.report.risk_items', { count: runtimeReport.risks.length }) : t('anchored.status.unreported')}</summary>
      <dl className="grid grid-cols-2 gap-[var(--space-2)] sm:grid-cols-4">
        {REPORT_SECTIONS.map(([key, labelKey]) => {
          const entries = runtimeReport?.[key];
          return <div key={key} className="min-w-0">
            <dt className="text-[var(--color-text-muted)]">{t(labelKey)}</dt>
            <dd>{entries === null || entries === undefined ? t('anchored.status.unreported') : entries.length === 0 ? t('anchored.report.empty') : <details>
              <summary className="cursor-pointer truncate" title={entries[0]}>{entries[0]}</summary>
              <ul className="max-h-[var(--space-24)] overflow-y-auto break-words">{entries.map((entry, index) => <li key={index}>{entry}</li>)}</ul>
            </details>}</dd>
          </div>;
        })}
      </dl>
    </details>
  );

  return (
    <section
      data-testid="anchored-chat-column"
      className="flex h-full min-w-0 flex-col bg-[var(--color-bg-page)]"
    >
      <header
        data-testid="anchored-title-bar"
        className="flex h-12 shrink-0 items-center gap-[var(--space-3)] border-b border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-1)] px-[var(--space-4)]"
      >
        {/* 管道面包屑：会话标题 → 当前阶段 */}
        <nav aria-label={t('anchored.status.label')} className="flex min-w-0 flex-1 items-center gap-[var(--space-1-5)]">
          <h2 className="min-w-0 max-w-[50%] truncate text-[length:var(--text-sm)] font-medium text-[var(--color-text-primary)]">
            {session?.title ?? t('chat.new_conversation')}
          </h2>
          <span aria-hidden="true" className="shrink-0 text-[var(--color-text-muted)]">
            /
          </span>
          <span data-testid="anchored-pipeline-stage" className="shrink-0 truncate text-[length:var(--text-xs)] text-[var(--color-text-muted)]">
            {t(`anchored.status.${agentState}`)}
          </span>
        </nav>
        {onToggleInfo && <button type="button" onClick={onToggleInfo} aria-label={t('anchored.panel.label')} className="flex items-center gap-[var(--space-1)] rounded-[var(--radius-sm)] px-[var(--space-2)] text-[length:var(--text-xs)] text-[var(--color-text-muted)] hover:bg-[var(--color-bg-surface-2)] focus-visible:shadow-[var(--focus-ring)]"><WorkbenchIcon name="preview" />{t('anchored.panel.label')}</button>}
        <TypewriterModeToggle />
      </header>

      <div
        ref={scrollRef}
        data-testid="anchored-message-scroll"
        onScroll={(event) => {
          const node = event.currentTarget;
          followRef.current = node.scrollHeight - node.scrollTop - node.clientHeight < 48;
        }}
        className={cn(
          'min-h-0 flex-1 overflow-y-auto px-[var(--space-4)] py-[var(--space-4)]',
          messages.length === 0 && 'flex items-center justify-center',
        )}
      >
        {messages.length === 0 ? (
          <ScrollReveal testId="anchored-welcome-reveal">
            <ChatEmptyState
              data-testid="anchored-welcome"
              title={t('anchored.welcome.title')}
              description={t('chat.empty_hint')}
              onSend={(content) => void sendMessage(content)}
              disabled={isStreaming || !sessionId}
            />
          </ScrollReveal>
        ) : (
          <ScrollReveal testId="anchored-conversation-reveal">
            <div data-testid="anchored-conversation" className="mx-auto w-full max-w-[800px]">
              <AnchoredMessageFlow messages={messages} activeMessageId={isStreaming ? lastMessage?.id : undefined} />
            </div>
          </ScrollReveal>
        )}
      </div>

      {deliverables && (
        <div className="mx-auto w-full max-w-[800px] shrink-0 px-[var(--space-3)] py-[var(--space-2)]">
          <ScrollReveal testId="anchored-deliverables-reveal">
            <DeliverablesCard entries={deliverables} onOpenFile={openDeliverableFile} />
          </ScrollReveal>
        </div>
      )}
      <LoopStatusPanel className="mx-auto w-full max-w-[800px] shrink-0 px-[var(--space-3)] py-[var(--space-2)]" />
      {runtimeReport && <section aria-label={t('anchored.report.report_title')} data-testid="runtime-report" className="mx-auto w-full max-w-[800px] shrink-0 px-[var(--space-3)] py-[var(--space-2)] text-[length:var(--text-xs)] text-[var(--color-text-secondary)]">
        <ScrollReveal testId="anchored-report-reveal">
          {reportHasRaw ? (
            <RawRenderedToggle
              rendered={reportBody}
              raw={runtimeReport}
              view={reportView}
              onViewChange={setReportView}
            />
          ) : reportBody}
        </ScrollReveal>
      </section>}
      {error && (
        <ChatStreamError
          className="shrink-0"
          message={error}
          onRetry={() => retry()}
          retryDisabled={isStreaming || !sessionId}
        />
      )}
      {inputs.length > 0 && <details className="shrink-0 border-t border-[var(--color-border-subtle)] px-[var(--space-3)] py-[var(--space-2)] text-[length:var(--text-xs)] text-[var(--color-text-secondary)]">
        <summary className="cursor-pointer">{t('anchored.queue.queue')} · {t('anchored.queue.queue_pending', { count: inputs.filter(item => !['completed', 'applied'].includes(item.status)).length })}</summary>
        <ul className="max-h-[var(--space-24)] overflow-y-auto">
          {inputs.map(item => <li key={item.client_request_id} className="flex items-start gap-[var(--space-2)] py-[var(--space-1)]">
            <span className="min-w-0 flex-1 break-words">{item.kind === 'steering' ? t('anchored.queue.kind_steering') : t('anchored.queue.kind_follow_up')} · {t(INPUT_STATUS_KEYS[item.status])} · {item.message}{item.error && ` · ${item.error}`}</span>
            {item.status === 'unconfirmed' && <Button size="xs" variant="outline" disabled={!isStreaming} onClick={() => void retryInput(item)}>{t('anchored.queue.retry_confirm')}</Button>}
          </li>)}
        </ul>
      </details>}
      {(inputs.some(item => item.status === 'blocked') || resumeFeedback) && <section aria-label={t('anchored.review.review_title')} className="shrink-0 border-t border-[var(--color-border-subtle)] px-[var(--space-3)] py-[var(--space-2)] text-[length:var(--text-xs)] text-[var(--color-text-secondary)]">
        {inputs.some(item => item.status === 'blocked') && <>
          <p>{t('anchored.review.review_hint')}</p>
          <label className="flex items-start gap-[var(--space-2)] py-[var(--space-2)]">
            <input type="checkbox" checked={!!sessionId && reviewedSession === sessionId} disabled={resumePending} onChange={event => setReviewedSession(event.target.checked ? sessionId : null)} />
            {t('anchored.review.review_check')}
          </label>
          <Button size="xs" variant="outline" disabled={!sessionId || reviewedSession !== sessionId || resumePending} onClick={() => { setReviewedSession(null); void resumeInputs(true); }}>
            {resumePending ? t('anchored.review.review_waiting') : t('anchored.review.review_confirm')}
          </Button>
        </>}
        {resumeFeedback && <p role="status" className="py-[var(--space-1)]">{resumeFeedback}</p>}
      </section>}
      {!isStreaming && inputs.some(item => item.kind === 'follow_up' && item.status === 'queued') && <section aria-label={t('anchored.start.start_title')} className="shrink-0 border-t border-[var(--color-border-subtle)] px-[var(--space-3)] py-[var(--space-2)] text-[length:var(--text-xs)] text-[var(--color-text-secondary)]">
        <p>{t('anchored.start.start_hint')}</p>
        <Button size="xs" variant="outline" disabled={!sessionId || resumePending} onClick={() => startInputs()}>{t('anchored.start.start_action')}</Button>
      </section>}
      {isStreaming && (
        <div className="mx-auto w-full max-w-[800px] shrink-0 px-[var(--space-3)] pb-[var(--space-1)] pt-[var(--space-2)]">
          <StatusIndicator
            isWorking
            inlineMessage={agentStateMessage}
            detailLines={runningToolName ? [runningToolName] : undefined}
          />
        </div>
      )}
      <AnchoredComposer key={sessionId} sessionId={sessionId} isStreaming={isStreaming} onSend={sendMessage} onStop={stopStreaming} onSubmitInput={submitInput} model={session?.modelConfig?.modelId ?? null} />
      <AnchoredStatusRail />
    </section>
  );
}
