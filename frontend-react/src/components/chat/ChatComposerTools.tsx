import { Eye, EyeOff } from 'lucide-react';
import { cn } from '../../lib/utils';
import { useI18n } from '../../i18n';
import { ThinkingLevelSelect } from './ThinkingLevelSelect';
import { ModelPickerButton } from './ModelPickerButton';
import type { ChatVisuals } from '../../hooks/useChatVisuals';

/**
 * One shared composer toolbar: session model (left) plus the thinking-level
 * selector and the transcript display switches (right).
 *
 * `ChatInterface` and `MobileChatInterface` mount the same component so the
 * controls never drift apart; `compact` adapts hit targets for the mobile
 * composer. The display switches are render gates only — permission dialogs
 * stay visible regardless of what is hidden here.
 */

interface ChatComposerToolsProps {
  sessionId: string | null;
  /** Mobile composer height; desktop uses the compact composer scale. */
  compact?: boolean;
  /** Disabled while a turn streams so the session model cannot shift mid-run. */
  disabled?: boolean;
  visuals: ChatVisuals;
  setShowToolCalls: (value: boolean) => void;
  setShowThinking: (value: boolean) => void;
  className?: string;
}

export function ChatComposerTools({
  sessionId,
  compact = false,
  disabled = false,
  visuals,
  setShowToolCalls,
  setShowThinking,
  className,
}: ChatComposerToolsProps) {
  const { t } = useI18n();

  const toggleClass = cn(
    'flex items-center gap-1 rounded-full px-2 transition-colors duration-150 text-[var(--color-text-muted)] hover:bg-[var(--color-bg-surface-2)] hover:text-[var(--color-text-secondary)] focus-visible:outline-none focus-visible:shadow-[var(--focus-ring)] disabled:cursor-not-allowed disabled:opacity-60 motion-reduce:transition-none',
    compact ? 'h-11 text-sm' : 'h-7 text-[length:var(--text-2xs)]',
  );

  return (
    <div className={cn('flex min-w-0 flex-wrap items-center justify-between gap-2', className)}>
      <ModelPickerButton sessionId={sessionId} disabled={disabled} compact={compact} />
      <div className="flex min-w-0 items-center gap-1.5">
        <ThinkingLevelSelect sessionId={sessionId} />
        <button
          type="button"
          aria-pressed={visuals.showToolCalls}
          disabled={compact && disabled}
          title={
            visuals.showToolCalls
              ? t('chat.tool_calls_hide_hint', { defaultValue: '隐藏工具调用卡片' })
              : t('chat.tool_calls_show_hint', { defaultValue: '显示工具调用卡片' })
          }
          onClick={() => setShowToolCalls(!visuals.showToolCalls)}
          className={toggleClass}
        >
          {visuals.showToolCalls ? (
            <Eye size={compact ? 16 : 12} aria-hidden="true" />
          ) : (
            <EyeOff size={compact ? 16 : 12} aria-hidden="true" />
          )}
          <span className="min-w-0 truncate">
            {t('chat.tool_calls_toggle', { defaultValue: '工具' })}
          </span>
        </button>
        <button
          type="button"
          aria-pressed={visuals.showThinking}
          disabled={compact && disabled}
          title={
            visuals.showThinking
              ? t('chat.thinking_hide_hint', { defaultValue: '隐藏思考过程' })
              : t('chat.thinking_show_hint', { defaultValue: '显示思考过程' })
          }
          onClick={() => setShowThinking(!visuals.showThinking)}
          className={toggleClass}
        >
          {visuals.showThinking ? (
            <Eye size={compact ? 16 : 12} aria-hidden="true" />
          ) : (
            <EyeOff size={compact ? 16 : 12} aria-hidden="true" />
          )}
          <span className="min-w-0 truncate">
            {t('chat.thinking_toggle', { defaultValue: '思考' })}
          </span>
        </button>
      </div>
    </div>
  );
}

export default ChatComposerTools;
