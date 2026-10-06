import { useEffect, useId, useState, type ReactNode } from 'react';
import { cn } from '../../lib/utils';
import { useI18n } from '../../i18n';
import { Modal } from '../ui/Modal';

export interface SettingsTab {
  id: string;
  label: string;
  content: ReactNode;
}

export interface SettingsModalProps {
  open: boolean;
  onClose: () => void;
  tabs: SettingsTab[];
  title?: string;
  className?: string;
  'data-testid'?: string;
}

export function SettingsModal({
  open,
  onClose,
  tabs,
  title,
  className,
  'data-testid': testId = 'settings-modal',
}: SettingsModalProps) {
  const { t } = useI18n();
  const baseId = useId();
  const [activeId, setActiveId] = useState<string>(tabs[0]?.id ?? '');

  useEffect(() => {
    if (!tabs.some((tab) => tab.id === activeId)) {
      setActiveId(tabs[0]?.id ?? '');
    }
  }, [tabs, activeId]);

  const activeTab = tabs.find((tab) => tab.id === activeId) ?? tabs[0];
  const resolvedTitle =
    title ?? t('agent.settings.title', { defaultValue: 'Settings' });

  return (
    <Modal
      open={open}
      onClose={onClose}
      centered
      size="xl"
      title={resolvedTitle}
      className={className}
      data-testid={testId}
    >
      <div className="flex min-h-[24rem] gap-[var(--space-4)]">
        <nav
          role="tablist"
          aria-label={resolvedTitle}
          aria-orientation="vertical"
          data-testid={`${testId}-rail`}
          className="flex w-[10rem] shrink-0 flex-col gap-[var(--space-1)]"
        >
          {tabs.map((tab) => {
            const selected = tab.id === activeTab?.id;
            return (
              <button
                key={tab.id}
                type="button"
                role="tab"
                id={`${baseId}-tab-${tab.id}`}
                aria-selected={selected}
                aria-controls={`${baseId}-panel-${tab.id}`}
                data-testid={`${testId}-tab-${tab.id}`}
                onClick={() => setActiveId(tab.id)}
                className={cn(
                  'flex h-[var(--control-height-md)] items-center rounded-[var(--radius-md)] px-[var(--space-3)] text-left text-[length:var(--text-sm)] font-medium',
                  'transition-colors motion-reduce:transition-none',
                  'focus-visible:outline-none focus-visible:shadow-[var(--focus-ring)]',
                  selected
                    ? 'bg-[var(--color-accent-subtle)] font-semibold text-[var(--color-accent-foreground)]'
                    : 'text-[var(--color-text-muted)] hover:bg-[var(--color-bg-surface-2)] hover:text-[var(--color-text-primary)]',
                )}
              >
                {tab.label}
              </button>
            );
          })}
        </nav>

        <section
          role="tabpanel"
          id={`${baseId}-panel-${activeTab?.id ?? ''}`}
          aria-labelledby={`${baseId}-tab-${activeTab?.id ?? ''}`}
          tabIndex={0}
          data-testid={`${testId}-content-${activeTab?.id ?? ''}`}
          className="min-w-0 flex-1 focus-visible:outline-none focus-visible:shadow-[var(--focus-ring)]"
        >
          {activeTab?.content}
        </section>
      </div>
    </Modal>
  );
}

export default SettingsModal;
