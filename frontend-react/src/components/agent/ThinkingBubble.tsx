import { useId, useState } from 'react';
import { ChevronDown, ChevronRight } from 'lucide-react';
import { useI18n } from '../../i18n';
import { cn } from '../../lib/utils';
import { useTypewriterReveal } from '../../hooks/useTypewriterReveal';
import { MarkdownRenderer } from '../chat/MarkdownRenderer';
import { WorkbenchIcon } from '../ui/WorkbenchIcon';
import { ReasoningPanel } from './ReasoningPanel';
import { MessageActions } from './MessageActions';
import { isTypewriterActive, typewriterPresetFor, useTypewriterMode } from './typewriterConfig';
import type { Message } from '../../useChat';

/**
 * Agent 消息单元（样式 2 的宿主）：正文、以 `failed` 报告的失败、活动态指示、
 * 公开推理摘要的披露，以及 hover / focus 才出现的操作条。
 *
 * 只承载公开事实：正文、公开的 `reasoning` 摘要、以及以 `failed` 报告的失败。
 * 绝不渲染 `thinking` / `reasoning_content` 等未公开推理字段。
 *
 * `group/message` 是操作条的显示契约：MessageActions 用 `group-hover/message`
 * 与 `focus-within` 显形，所以这个单元不为此付任何 React state。
 */

/**
 * ReasoningPanel 自带触发按钮，而这份 transcript 已经有一个了：披露按钮以
 * `anchored.messages.public_reasoning` 命名，读者据此区分"公开摘要"与私有
 * 思维链。因此这里只用它的正文呈现（流式跟随滚动、高度上限、克制的边框与
 * 排版），并把它自己的触发按钮移出无障碍树，保证界面上只有一个披露控件。
 */
const REASONING_BODY_CLASS = '[&>button]:hidden';

/** 正文为空时操作条没有可复制的内容，整条隐藏。 */
function hasCopyableContent(content: string): boolean {
  return content.trim().length > 0;
}

export function ThinkingBubble({ message, active }: { message: Message; active: boolean }) {
  const { t } = useI18n();
  const [reasoningOpen, setReasoningOpen] = useState(false);
  const reasoningId = useId();
  const typewriterMode = useTypewriterMode();
  const typewriterEnabled = isTypewriterActive(typewriterMode);

  const content = useTypewriterReveal(message.content, {
    active,
    preset: typewriterPresetFor(typewriterMode),
    enabled: typewriterEnabled,
  });
  const reasoningStatus = message.failed ? 'error' : message.interrupted ? 'paused' : active ? 'active' : 'complete';

  return (
    <div
      data-testid="anchored-thinking-bubble"
      className="group/message flex w-full min-w-0 flex-col items-start gap-[var(--space-2)]"
    >
      {message.failed && (
        <p role="alert" className="flex items-center gap-[var(--space-1-5)] text-[length:var(--text-xs)] font-medium text-[var(--color-error)]">
          <span aria-hidden="true" data-testid="anchored-thinking-icon-error" className="size-[6px] shrink-0 rounded-[var(--radius-pill)] bg-[var(--color-error)]" />
          {t('anchored.messages.agent_error', { defaultValue: '异常' })}
        </p>
      )}
      {content && (
        <div className="codex-agent-message max-w-[85%] text-[length:var(--text-sm)] leading-relaxed text-[var(--color-text-primary)]">
          <MarkdownRenderer content={content} />
        </div>
      )}
      <span className="flex min-w-0 items-center gap-[var(--space-1-5)] text-[length:var(--text-2xs)] text-[var(--color-text-muted)]">
        <WorkbenchIcon name="agent" size={12} className="shrink-0 text-[var(--color-text-muted)]" />
          <span
          aria-hidden="true"
          data-testid="anchored-thinking-icon"
          className={cn(
            'size-[6px] shrink-0 rounded-[var(--radius-pill)]',
            active
              ? 'bg-[var(--color-info)] motion-safe:animate-pulse'
              : message.failed
                ? 'bg-[var(--color-error)]'
                : message.interrupted
                  ? 'bg-[var(--color-warning)]'
                  : 'bg-[var(--color-success)]',
          )}
        />
        <span className={cn(
          'truncate',
          active && 'text-[var(--color-info)]',
          message.failed && 'text-[var(--color-error)]',
          message.interrupted && 'text-[var(--color-warning)]',
          !active && !message.failed && !message.interrupted && 'text-[var(--color-success)]',
        )}>
          {t(
            message.failed ? 'anchored.status.thinking_error' : message.interrupted ? 'anchored.status.thinking_paused' : active ? 'anchored.status.thinking' : 'anchored.status.thinking_complete',
            { defaultValue: message.failed ? 'Thinking failed' : message.interrupted ? 'Thinking paused' : active ? 'Thinking' : 'Thinking complete' },
          )}
        </span>
      </span>
      {message.reasoning && (
        <div className="w-full min-w-0">
          <button
            type="button"
            aria-expanded={reasoningOpen}
            aria-controls={reasoningId}
            onClick={() => setReasoningOpen((value) => !value)}
            className="flex items-center gap-[var(--space-1)] text-[length:var(--text-2xs)] text-[var(--color-text-muted)] transition-colors hover:text-[var(--color-text-primary)] focus-visible:outline-none focus-visible:shadow-[var(--focus-ring)]"
          >
            {reasoningOpen ? <ChevronDown size={12} aria-hidden="true" /> : <ChevronRight size={12} aria-hidden="true" />}
            {t('anchored.messages.public_reasoning', { defaultValue: '公开推理摘要' })}
          </button>
          <div id={reasoningId} hidden={!reasoningOpen} className="mt-[var(--space-1)] min-w-0">
            {reasoningOpen && (
              <ReasoningPanel
                text={message.reasoning}
                active={active}
                status={reasoningStatus}
                defaultOpen
                className={REASONING_BODY_CLASS}
              />
            )}
          </div>
        </div>
      )}
      {/* 悬停/聚焦才显形的操作条。复制接了（navigator.clipboard + message.copied
          反馈态由 MessageActions 承担）；编辑与重发在 transcript 里没有后端能力，
          所以不传回调，对应按钮由组件自身隐去。放在推理披露之后，让键盘顺序
          保持"先读内容、再取操作"。 */}
      {hasCopyableContent(message.content) && (
        <MessageActions content={message.content} data-testid="anchored-message-actions" className="self-end" />
      )}
    </div>
  );
}
