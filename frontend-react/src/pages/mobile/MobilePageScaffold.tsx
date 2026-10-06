import type { ReactNode } from 'react';
import { Button } from '../../components/ui/Button';
import { Card } from '../../components/ui/Card';
import { EmptyState } from '../../components/ui/EmptyState';
import { useI18n } from '../../i18n';
import { cn } from '../../lib/utils';

/**
 * The mobile page surfaces share one skeleton: a section that hands its page
 * title to `aria-labelledby`, then a column of cards at a single spacing rung.
 * The shell header owns the large title, so a page body never repeats it.
 */
export function MobilePageSection({ labelledBy, children, className }: {
  labelledBy: string;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section
      aria-labelledby={labelledBy}
      className={cn(
        'mobile-page-container flex w-full min-w-0 flex-col gap-[var(--space-3)] px-[var(--space-4)] pt-[var(--space-3)]',
        className,
      )}
    >
      {children}
    </section>
  );
}

/**
 * The one card shape every mobile surface opens with: an accent icon chip, one
 * labelled heading and a description. The heading id feeds the wrapping
 * section's `aria-labelledby`, so the page keeps exactly one named heading.
 */
export function MobileNoticeCard({ icon, title, titleId, description }: {
  icon: ReactNode;
  title: string;
  titleId: string;
  description: string;
}) {
  return (
    <Card variant="default" padding="md">
      <div className="flex items-start gap-[var(--space-3)]">
        <span
          aria-hidden="true"
          className="grid size-10 shrink-0 place-items-center rounded-full bg-[var(--color-accent-subtle)] text-[var(--color-accent-foreground)]"
        >
          {icon}
        </span>
        <div className="min-w-0">
          <h2 id={titleId} className="text-base font-semibold leading-[var(--leading-tight)] text-[var(--color-text-primary)]">
            {title}
          </h2>
          <p className="mt-[var(--space-1)] text-sm leading-6 text-[var(--color-text-secondary)]">{description}</p>
        </div>
      </div>
    </Card>
  );
}

/**
 * The standard body card under the notice: a shared EmptyState plus the open
 * chat action, so all four surfaces present the same shape and the same exit.
 */
export function MobileEmptyBodyCard({ emptyTitle, emptyDescription }: {
  emptyTitle: string;
  emptyDescription: string;
}) {
  return (
    <Card variant="default" padding="md">
      <EmptyState
        icon="inbox"
        title={emptyTitle}
        description={emptyDescription}
        className="min-h-0 px-0 py-[var(--space-2)]"
      />
      <MobileOpenChatButton />
    </Card>
  );
}

/**
 * The single action every mobile surface ends with: opening chat. It routes
 * through the same hash router the shell uses, so the way out keeps the
 * back-forward history consistent.
 */
export function MobileOpenChatButton({ className }: { className?: string }) {
  const { t } = useI18n();
  return (
    <Button
      variant="primary"
      className={cn('mt-[var(--space-2)] min-h-11 w-full', className)}
      onClick={() => { window.location.hash = 'chat'; }}
    >
      {t('mobile.open_chat')}
    </Button>
  );
}
