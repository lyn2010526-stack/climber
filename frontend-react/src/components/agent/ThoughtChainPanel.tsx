import type { ElementType } from 'react';
import { Check, Wrench } from 'lucide-react';
import { useI18n } from '../../i18n';
import { cn } from '../../lib/utils';
import type { StatusTone } from '../../lib/icons';
import { StatusIcon } from '../ui/StatusIcon';

export type ThoughtStepStatus =
  | 'pending'
  | 'running'
  | 'success'
  | 'error'
  | 'skipped';

export interface ThoughtChainStep {
  id: string;
  label: string;
  status: ThoughtStepStatus;
  icon?: ElementType;
}

export interface ThoughtChainPanelProps {
  steps: ThoughtChainStep[];
  className?: string;
  'aria-label'?: string;
}

interface StatusDescriptor {
  tone: StatusTone;
  labelKey: string;
  labelDefault: string;
  spin?: boolean;
}

const STEP_STATUS: Record<ThoughtStepStatus, StatusDescriptor> = {
  pending: { tone: 'queued', labelKey: 'thought_chain.status_pending', labelDefault: 'Pending' },
  running: { tone: 'loading', labelKey: 'thought_chain.status_running', labelDefault: 'Running', spin: true },
  success: { tone: 'success', labelKey: 'thought_chain.status_success', labelDefault: 'Done' },
  error: { tone: 'error', labelKey: 'thought_chain.status_error', labelDefault: 'Failed' },
  skipped: { tone: 'unknown', labelKey: 'thought_chain.status_skipped', labelDefault: 'Skipped' },
};

const PILL_TONE: Record<StatusTone, string> = {
  error: 'border-[var(--color-error)]/40 text-[var(--color-error)]',
  success: 'border-[var(--color-success)]/40 text-[var(--color-success)]',
  warning: 'border-[var(--color-warning)]/40 text-[var(--color-warning)]',
  info: 'border-[var(--color-info)]/40 text-[var(--color-info)]',
  loading: 'border-[var(--color-border-strong)] text-[var(--color-text-primary)]',
  queued: 'border-[var(--color-border-default)] text-[var(--color-text-muted)]',
  approval: 'border-[var(--color-border-accent)] text-[var(--color-accent-foreground)]',
  unknown: 'border-[var(--color-border-subtle)] text-[var(--color-text-disabled)]',
};

export function ThoughtChainPanel({
  steps,
  className,
  'aria-label': ariaLabel,
}: ThoughtChainPanelProps) {
  const { t } = useI18n();

  if (steps.length === 0) return null;

  return (
    <ol
      data-testid="thought-chain"
      aria-label={ariaLabel ?? t('thought_chain.label', { defaultValue: 'Chain of thought' })}
      className={cn('m-0 flex list-none flex-col gap-0 p-0', className)}
    >
      {steps.map((step, index) => {
        const descriptor = STEP_STATUS[step.status];
        const Icon = step.icon ?? Wrench;
        const isLast = index === steps.length - 1;
        const statusLabel = t(descriptor.labelKey, { defaultValue: descriptor.labelDefault });

        return (
          <li key={step.id} data-testid={`thought-step-${step.id}`} data-status={step.status} className="flex gap-[var(--space-2)]">
            <div className="flex flex-col items-center">
              <span className="flex size-[var(--space-6)] shrink-0 items-center justify-center rounded-full border border-[var(--color-border-default)] bg-[var(--color-bg-surface-3)] font-mono text-[length:var(--text-2xs)] tabular-nums text-[var(--color-text-secondary)]">
                {index + 1}
              </span>
              {!isLast && (
                <span aria-hidden="true" className="my-[var(--space-0-5)] w-px flex-1 bg-[var(--color-border-subtle)]" />
              )}
            </div>

            <div className={cn('min-w-0 flex-1', !isLast && 'pb-[var(--space-3)]')}>
              <span
                className={cn(
                  'inline-flex max-w-full items-center gap-[var(--space-1-5)] rounded-full border px-[var(--space-2)] py-[var(--space-1)]',
                  PILL_TONE[descriptor.tone],
                )}
              >
                {step.status === 'success'
                  ? <Check size={12} aria-hidden="true" className="shrink-0" />
                  : <Icon size={12} aria-hidden="true" className="shrink-0" />}
                <span className="min-w-0 break-words text-[length:var(--text-xs)] font-medium">{step.label}</span>
                <span className="sr-only">{statusLabel}</span>
                <StatusIcon tone={descriptor.tone} size="xs" spin={descriptor.spin} className="shrink-0" />
              </span>
            </div>
          </li>
        );
      })}
    </ol>
  );
}

export default ThoughtChainPanel;
