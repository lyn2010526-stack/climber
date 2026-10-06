import { useRef, useState } from 'react';
import { Check, ShieldQuestion, X } from 'lucide-react';
import { cn } from '../../lib/utils';
import { useI18n } from '../../i18n';
import { Button } from '../ui/Button';

export interface HitlPanelProps {
  title: string;
  description?: string;
  onApprove: () => void | Promise<void>;
  onReject: () => void | Promise<void>;
  /** When given, an "always allow" action is offered alongside approve/reject. */
  onAlwaysAllow?: () => void | Promise<void>;
  /** When given, a dismiss control closes the panel without deciding. */
  onDismiss?: () => void | Promise<void>;
  /** Renders the bar only when true. Defaults to true so it can mount guarded. */
  show?: boolean;
  className?: string;
  /**
   * Optional wording overrides. A host that owns its own approval vocabulary
   * (the anchored popup stack) passes its keys so the panel and the surrounding
   * surface name the same decision the same way; left unset, the panel falls
   * back to the shared HITL wording.
   */
  approveLabel?: string;
  rejectLabel?: string;
  alwaysAllowLabel?: string;
  dismissLabel?: string;
}

type Decision = 'approve' | 'reject' | 'always';

export function HitlPanel({
  title,
  description,
  onApprove,
  onReject,
  onAlwaysAllow,
  onDismiss,
  show = true,
  className,
  approveLabel,
  rejectLabel,
  alwaysAllowLabel,
  dismissLabel,
}: HitlPanelProps) {
  const { t } = useI18n();
  const responding = useRef(false);
  const [pending, setPending] = useState<Decision | null>(null);
  const [error, setError] = useState<string>();

  if (!show) return null;

  const decide = async (decision: Decision) => {
    if (responding.current) return;
    const handler = decision === 'approve' ? onApprove : decision === 'reject' ? onReject : onAlwaysAllow;
    if (!handler) return;
    responding.current = true;
    setPending(decision);
    setError(undefined);
    try {
      await handler();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : t('common.error', { defaultValue: 'Something went wrong' }));
    } finally {
      responding.current = false;
      setPending(null);
    }
  };

  const busy = pending !== null;

  return (
    <aside
      role="dialog"
      aria-label={title}
      aria-busy={busy}
      className={cn(
        'fixed bottom-4 end-4 z-50 flex w-[min(24rem,calc(100vw-2rem))] flex-col gap-[var(--space-3)] rounded-[var(--radius-lg)] border border-[var(--color-border-default)] bg-[var(--color-bg-surface-1)] p-[var(--space-4)] shadow-[var(--shadow-lg)]',
        className,
      )}
    >
      <div className="flex items-start gap-[var(--space-2)]">
        <ShieldQuestion size={16} aria-hidden="true" className="mt-[var(--space-0-5)] shrink-0 text-[var(--color-accent)]" />
        <div className="min-w-0 flex-1">
          <h2 className="text-[length:var(--text-sm)] font-semibold text-[var(--color-text-primary)]">{title}</h2>
          {description && (
            <p className="mt-[var(--space-1)] break-words text-[length:var(--text-xs)] text-[var(--color-text-secondary)]">{description}</p>
          )}
        </div>
        {onDismiss && (
          <Button
            type="button"
            variant="ghost"
            size="icon-sm"
            aria-label={dismissLabel ?? t('hitl.dismiss', { defaultValue: 'Dismiss' })}
            disabled={busy}
            onClick={() => void onDismiss()}
            icon={<X size={12} aria-hidden="true" />}
          />
        )}
      </div>

      {error && (
        <p role="alert" className="break-words text-[length:var(--text-xs)] text-[var(--color-error)]">{error}</p>
      )}

      <div className="flex flex-wrap items-center justify-end gap-[var(--space-2)]">
        {onAlwaysAllow && (
          <Button
            type="button"
            variant="ghost"
            size="sm"
            disabled={busy}
            loading={pending === 'always'}
            onClick={() => void decide('always')}
          >
            {alwaysAllowLabel ?? t('hitl.always_allow', { defaultValue: 'Always allow' })}
          </Button>
        )}
        <Button
          type="button"
          variant="outline"
          size="sm"
          disabled={busy}
          loading={pending === 'reject'}
          onClick={() => void decide('reject')}
          icon={<X size={12} aria-hidden="true" />}
        >
          {rejectLabel ?? t('hitl.reject', { defaultValue: 'Reject' })}
        </Button>
        <Button
          type="button"
          variant="primary"
          size="sm"
          disabled={busy}
          loading={pending === 'approve'}
          onClick={() => void decide('approve')}
          icon={<Check size={12} aria-hidden="true" />}
        >
          {approveLabel ?? t('hitl.approve', { defaultValue: 'Approve' })}
        </Button>
      </div>
    </aside>
  );
}

export default HitlPanel;
