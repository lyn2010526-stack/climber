import { Button } from '../ui/Button';
import { useI18n } from '../../i18n';
import { isActiveTaskStatus, reportedNumber, taskStatusLabel } from './taskStatus';

export interface TaskProgressProps {
  /** Status string exactly as reported by the backend; absent means not reported. */
  status?: string | null;
  progress?: number | null;
  totalSteps?: number | null;
  taskId?: string | null;
  objective?: string | null;
  result?: unknown;
  error?: string | null;
  onCancel?: () => void;
  cancelling?: boolean;
  onReset?: () => void;
  onRetry?: () => void;
}

function renderResult(result: unknown) {
  if (typeof result === 'string') return result;
  try {
    return JSON.stringify(result, null, 2);
  } catch {
    return String(result);
  }
}

export function TaskProgress({
  status,
  progress,
  totalSteps,
  taskId,
  objective,
  result,
  error,
  onCancel,
  cancelling,
  onReset,
  onRetry,
}: TaskProgressProps) {
  const { t } = useI18n();
  const started = !!taskId;
  // The one place that decides whether a run is still in flight: the sidebar
  // and this surface must never disagree about whether cancelling is offered.
  const active = started && isActiveTaskStatus(status);
  const cancellable = active && onCancel ? onCancel : undefined;

  return (
    <div className="min-w-0">
      <div
        role="status"
        aria-label={t('collaboration.aria.task_status')}
        className="flex flex-wrap items-center gap-x-4 gap-y-1 border-b border-[var(--color-border-subtle)] pb-3 text-xs text-[var(--color-text-secondary)]"
      >
        <span className="font-medium">{taskStatusLabel(status, t)}</span>
        <span>{t('collaboration.steps_progress', { done: reportedNumber(progress, t), total: reportedNumber(totalSteps, t) })}</span>
        {cancellable && (
          <Button
            variant="outline"
            size="xs"
            className="ml-auto"
            onClick={cancellable}
            disabled={cancelling}
          >
            {cancelling ? t('collaboration.cancel.cancelling') : t('collaboration.cancel.action')}
          </Button>
        )}
      </div>

      {!started && <p className="py-6 text-sm text-[var(--color-text-muted)]">{t('collaboration.no_run_yet')}</p>}

      {started && (
        <div className="min-w-0 space-y-4 py-4 text-sm">
          <div>
            <span className="text-[var(--color-text-muted)]">{t('collaboration.task_id_label')}</span>
            <p className="mt-1 break-all font-mono text-xs">{taskId}</p>
          </div>
          {objective && <p className="whitespace-pre-wrap break-words">{objective}</p>}
          {error && (
            <p role="alert" className="text-[var(--color-error)]">
              {error}
            </p>
          )}
          {result != null && (
            <div>
              <h3 className="mb-2 font-medium">{t('collaboration.result_heading')}</h3>
              <pre className="max-h-96 overflow-auto whitespace-pre-wrap break-words rounded-lg bg-[var(--color-bg-surface-2)] p-3 text-xs">
                {renderResult(result)}
              </pre>
            </div>
          )}
          {!active && status === 'failed' && onRetry && (
            <Button variant="outline" size="sm" onClick={onRetry}>
              {t('common.retry')}
            </Button>
          )}
          {!active && onReset && (
            <Button variant="ghost" size="sm" onClick={onReset}>
              {t('collaboration.new_task')}
            </Button>
          )}
        </div>
      )}

    </div>
  );
}
