import { useCallback, useEffect, useId, useMemo, useRef, useState, type KeyboardEvent } from 'react';
import { useI18n } from '../../i18n';
import { cn } from '../../lib/utils';

/**
 * Codex 审批浮层（`approval_overlay.rs:296-325` 形态）：
 * 粗体标题 → 空行 → 说明 → mono `$ cmd` 块 → 编号选项 `› 1. Yes, proceed (y)`
 * → 页脚 `Press enter to confirm or esc to cancel`。
 *
 * 选中行用 `bg-surface-3 + 粗体` 表达 Codex 的 REVERSED 反白效果。
 * 与 FloatingPermissionDialog 并存：这是一个纯受控组件，不接入 ChatInterface，
 * 也不会替换现有对话框。
 */
export interface ApprovalOverlayOption {
  id: string;
  label: string;
  /** 触达该选项的按键（如 `y` / `a` / `esc`）。 */
  shortcut?: string;
}

export interface ApprovalOverlayProps {
  title: string;
  description?: string;
  /** 需要用户批准的原始命令，渲染为 mono `$ cmd` 块。 */
  command?: string;
  /** 选项列表；缺省使用 Codex 三项。 */
  options?: ApprovalOverlayOption[];
  /** 确认某个选项。 */
  onSelect: (id: string) => void;
  /** Esc / 取消回调。 */
  onCancel: () => void;
  className?: string;
}

export function ApprovalOverlay({
  title,
  description,
  command,
  options,
  onSelect,
  onCancel,
  className,
}: ApprovalOverlayProps) {
  const { t } = useI18n();
  const titleId = useId();
  const containerRef = useRef<HTMLDivElement>(null);
  const [selectedIndex, setSelectedIndex] = useState(0);

  const resolvedOptions = useMemo<ApprovalOverlayOption[]>(() => options ?? [
    { id: 'approve', label: t('approval.option.approve', { defaultValue: '允许执行' }), shortcut: 'y' },
    { id: 'approve_all', label: t('approval.option.approve_all', { defaultValue: '允许且不再询问' }), shortcut: 'a' },
    { id: 'deny', label: t('approval.option.deny', { defaultValue: '拒绝并说明原因' }), shortcut: 'esc' },
  ], [options, t]);

  // 键盘操作时把焦点拉到浮层本身，快捷键即可生效。
  useEffect(() => {
    containerRef.current?.focus();
  }, []);

  const move = useCallback((delta: number) => {
    setSelectedIndex((current) => {
      const count = resolvedOptions.length;
      if (count === 0) return 0;
      return (current + delta + count) % count;
    });
  }, [resolvedOptions.length]);

  const confirm = useCallback(() => {
    const option = resolvedOptions[selectedIndex];
    if (option) onSelect(option.id);
  }, [onSelect, resolvedOptions, selectedIndex]);

  const handleKeyDown = useCallback((event: KeyboardEvent<HTMLDivElement>) => {
    // 焦点陷阱：浮层内只有一个可聚焦区，Tab 不把焦点让出去。
    if (event.key === 'Tab') {
      event.preventDefault();
      containerRef.current?.focus();
      return;
    }
    if (event.key === 'ArrowDown') {
      event.preventDefault();
      move(1);
      return;
    }
    if (event.key === 'ArrowUp') {
      event.preventDefault();
      move(-1);
      return;
    }
    if (event.key === 'Escape') {
      event.preventDefault();
      onCancel();
      return;
    }
    if (event.key === 'Enter') {
      event.preventDefault();
      confirm();
      return;
    }
    const letter = event.key.toLowerCase();
    const shortcutOption = resolvedOptions.find((option) => option.shortcut?.toLowerCase() === letter);
    if (shortcutOption) {
      event.preventDefault();
      onSelect(shortcutOption.id);
    }
  }, [confirm, move, onCancel, onSelect, resolvedOptions]);

  return (
    <div
      ref={containerRef}
      data-testid="approval-overlay"
      role="dialog"
      aria-modal="true"
      aria-labelledby={titleId}
      tabIndex={-1}
      onKeyDown={handleKeyDown}
      className={cn(
        'flex min-w-0 flex-col rounded-[var(--radius-lg)] border border-[var(--color-border-default)] bg-[var(--color-bg-surface-1)] p-[var(--space-3)]',
        'text-[length:var(--text-xs)] leading-[var(--leading-normal)] focus-visible:outline-none focus-visible:shadow-[var(--focus-ring)]',
        className,
      )}
    >
      <h2 id={titleId} className="font-bold text-[var(--color-text-primary)]">
        {title}
      </h2>

      <div aria-hidden="true" className="h-[var(--space-2)]" />

      {description && <p className="break-words text-[var(--color-text-secondary)]">{description}</p>}

      {command && (
        <pre
          data-testid="approval-command"
          className="mt-[var(--space-2)] max-h-40 overflow-auto whitespace-pre-wrap break-words rounded-[var(--radius-md)] bg-[var(--color-bg-surface-3)] p-[var(--space-2)] font-mono text-[length:var(--text-2xs)] text-[var(--color-text-primary)]"
        >
          <span aria-hidden="true" className="text-[var(--color-text-muted)]">{'$ '}</span>
          {command}
        </pre>
      )}

      <ul role="listbox" aria-label={title} className="mt-[var(--space-3)] flex min-w-0 flex-col">
        {resolvedOptions.map((option, index) => {
          const selected = index === selectedIndex;
          return (
            <li
              key={option.id}
              role="option"
              aria-selected={selected}
              data-testid={`approval-option-${option.id}`}
              onClick={() => {
                if (selected) onSelect(option.id);
                else setSelectedIndex(index);
              }}
              className={cn(
                'flex min-w-0 cursor-pointer items-baseline gap-[var(--space-2)] px-[var(--space-2)] py-[var(--space-1)] font-mono transition-colors',
                selected
                  ? 'bg-[var(--color-bg-surface-3)] font-bold text-[var(--color-text-primary)]'
                  : 'text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-surface-2)]',
              )}
            >
              <span aria-hidden="true" className="w-[1ch] shrink-0 select-none">
                {selected ? '›' : ' '}
              </span>
              <span aria-hidden="true" className="shrink-0">{index + 1}.</span>
              <span className="min-w-0 truncate">{option.label}</span>
              {option.shortcut && (
                <span className="shrink-0 text-[var(--color-text-muted)]">({option.shortcut})</span>
              )}
            </li>
          );
        })}
      </ul>

      <p className="mt-[var(--space-3)] text-[length:var(--text-2xs)] text-[var(--color-text-muted)]">
        {t('approval.footer', { defaultValue: '按 enter 确认，按 esc 取消' })}
      </p>
    </div>
  );
}

export default ApprovalOverlay;
