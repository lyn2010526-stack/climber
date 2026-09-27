import { useState } from 'react';
import { Play } from 'lucide-react';
import { useTranslation } from '../../i18n';
import { Button } from '../ui/Button';

export interface TaskSubmitFormProps {
  onSubmit: (objective: string, maxSteps: number) => void;
  disabled?: boolean;
  submitting?: boolean;
}

const DEFAULT_MAX_STEPS = 5;
const MIN_MAX_STEPS = 1;
const MAX_MAX_STEPS = 20;

/**
 * The single place a group task is created. It only exposes fields the task
 * submit contract actually accepts.
 */
export function TaskSubmitForm({ onSubmit, disabled, submitting }: TaskSubmitFormProps) {
  const { t } = useTranslation();
  const [objective, setObjective] = useState('');
  const [maxSteps, setMaxSteps] = useState(DEFAULT_MAX_STEPS);
  const locked = !!disabled || !!submitting;

  return (
    <form
      className="space-y-2"
      onSubmit={event => {
        event.preventDefault();
        if (locked || !objective.trim()) return;
        onSubmit(objective.trim(), maxSteps);
      }}
    >
      <label className="block text-xs text-[var(--color-text-secondary)]">
        {t('collaboration.task.objective_label')}
        <textarea
          aria-label={t('collaboration.task.objective_label')}
          value={objective}
          disabled={locked}
          onChange={event => setObjective(event.target.value)}
          placeholder={t('collaboration.task.objective_placeholder')}
          rows={3}
          className="mt-1.5 w-full resize-y rounded-lg border border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-1)] p-2 text-xs text-[var(--color-text-primary)]"
        />
      </label>
      <div className="flex items-center justify-between gap-2">
        <label className="flex items-center gap-1.5 text-[10px] text-[var(--color-text-muted)]">
          {t('collaboration.task.max_steps')}
          <input
            type="number"
            min={MIN_MAX_STEPS}
            max={MAX_MAX_STEPS}
            aria-label={t('collaboration.task.max_steps')}
            value={maxSteps}
            disabled={locked}
            onChange={event =>
              setMaxSteps(
                Math.max(
                  MIN_MAX_STEPS,
                  Math.min(MAX_MAX_STEPS, Number(event.target.value) || MIN_MAX_STEPS),
                ),
              )
            }
            className="w-14 rounded border border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-1)] p-1"
          />
        </label>
        <Button
          type="submit"
          size="xs"
          disabled={locked || !objective.trim()}
          icon={<Play size={12} />}
        >
          {submitting ? t('collaboration.task.submitting') : t('collaboration.task.submit')}
        </Button>
      </div>
    </form>
  );
}
