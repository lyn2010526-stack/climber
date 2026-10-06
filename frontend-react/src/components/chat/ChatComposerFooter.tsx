import { useI18n } from '../../i18n';
import { cn } from '../../lib/utils';

/**
 * Codex 规格 §3.2 的 composer footer：输入区之下、缩进 2 列的一行提示。
 * 空输入时给出发送/换行快捷键（`? for shortcuts` 语义的本地版）；
 * 有草稿时 Codex 会收起快捷键提示——这里用 `hiddenWhenDraft` 让调用方
 * 按同一规则隐藏。纯展示：键位文案沿用既有 i18n 键，不新增 locale 条目。
 */
interface ChatComposerFooterProps {
  hasDraft?: boolean;
  /** 附加在右侧的上下文信息（如权限模式、模型名），与提示之间用 `·` 分隔。 */
  trailing?: React.ReactNode;
  className?: string;
  'data-testid'?: string;
}

export function ChatComposerFooter({
  hasDraft = false,
  trailing,
  className,
  'data-testid': testId,
}: ChatComposerFooterProps) {
  const { t } = useI18n();
  return (
    <p
      data-testid={testId ?? 'chat-composer-footer'}
      className={cn(
        'flex min-w-0 flex-wrap items-center gap-x-[var(--space-2)] gap-y-[var(--space-1)]',
        'px-[var(--space-6)] text-[length:var(--text-2xs)] leading-normal text-[var(--color-text-muted)]',
        className,
      )}
    >
      {!hasDraft && (
        <>
          <span className="shrink-0">{t('anchored.welcome.enter_hint')}</span>
          <span aria-hidden="true" className="shrink-0">
            ·
          </span>
          <span className="shrink-0">{t('anchored.welcome.shift_hint')}</span>
        </>
      )}
      {trailing && (
        <>
          {!hasDraft && (
            <span aria-hidden="true" className="shrink-0">
              ·
            </span>
          )}
          <span className="min-w-0 truncate">{trailing}</span>
        </>
      )}
    </p>
  );
}

export default ChatComposerFooter;
