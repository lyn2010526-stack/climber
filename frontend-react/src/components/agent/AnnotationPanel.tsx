import { useMemo, useState } from 'react';
import { ImageOff, Send } from 'lucide-react';
import { useI18n } from '../../i18n';
import { cn } from '../../lib/utils';
import { Button } from '../ui/Button';

export interface Annotation {
  index: number;
  note: string;
  x: number;
  y: number;
}

export interface AnnotationFeedback {
  source: string;
  annotations: Annotation[];
}

export interface AnnotationPanelProps {
  imageUrl?: string;
  annotations: Annotation[];
  source?: string;
  onSubmit: (feedback: AnnotationFeedback) => void;
  className?: string;
  'aria-label'?: string;
}

export function buildAnnotationFeedback(
  source: string,
  annotations: Annotation[],
): AnnotationFeedback {
  return {
    source,
    annotations: annotations.map((annotation) => ({
      index: annotation.index,
      note: annotation.note,
      x: annotation.x,
      y: annotation.y,
    })),
  };
}

function AnnotationMarker({ index, x, y }: { index: number; x: number; y: number }) {
  const left = `${Math.max(0, Math.min(1, x)) * 100}%`;
  const top = `${Math.max(0, Math.min(1, y)) * 100}%`;
  return (
    <span
      aria-hidden="true"
      data-testid={`annotation-marker-${index}`}
      style={{ left, top }}
      className="absolute flex size-[var(--space-5)] -translate-x-1/2 -translate-y-1/2 items-center justify-center rounded-full border border-[var(--color-accent-text)] bg-[var(--color-accent)] font-mono text-[length:var(--text-2xs)] font-medium tabular-nums text-[var(--color-accent-text)]"
    >
      {index}
    </span>
  );
}

export function AnnotationPanel({
  imageUrl,
  annotations,
  source = 'screenshot',
  onSubmit,
  className,
  'aria-label': ariaLabel,
}: AnnotationPanelProps) {
  const { t } = useI18n();
  const [draft, setDraft] = useState<Record<number, string>>({});

  const sorted = useMemo(
    () => [...annotations].sort((a, b) => a.index - b.index),
    [annotations],
  );

  const notesFor = (annotation: Annotation) => draft[annotation.index] ?? annotation.note;

  const handleSubmit = () => {
    const merged = sorted.map((annotation) => ({ ...annotation, note: notesFor(annotation) }));
    onSubmit(buildAnnotationFeedback(source, merged));
  };

  return (
    <div
      data-testid="annotation-panel"
      aria-label={ariaLabel ?? t('annotation.panel_label', { defaultValue: 'Screenshot annotations' })}
      className={cn(
        'flex min-w-0 flex-col gap-[var(--space-3)] rounded-[var(--radius-md)] border border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-2)] p-[var(--space-3)]',
        className,
      )}
    >
      <div className="relative min-h-[var(--space-32)] w-full overflow-hidden rounded-[var(--radius-md)] border border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-3)]">
        {imageUrl ? (
          <img
            src={imageUrl}
            alt={t('annotation.image_alt', { defaultValue: 'Annotated screenshot' })}
            className="block max-h-72 w-full object-contain"
          />
        ) : (
          <div className="flex min-h-[var(--space-32)] flex-col items-center justify-center gap-[var(--space-2)] text-[var(--color-text-muted)]">
            <ImageOff size={20} aria-hidden="true" />
            <span className="text-[length:var(--text-2xs)]">{t('annotation.no_image', { defaultValue: 'No screenshot attached' })}</span>
          </div>
        )}
        {imageUrl && sorted.map((annotation) => (
          <AnnotationMarker key={annotation.index} index={annotation.index} x={annotation.x} y={annotation.y} />
        ))}
      </div>

      <ul className="flex list-none flex-col gap-[var(--space-2)] p-0">
        {sorted.map((annotation) => (
          <li
            key={annotation.index}
            data-testid={`annotation-card-${annotation.index}`}
            className="flex items-start gap-[var(--space-2)] rounded-[var(--radius-sm)] border border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-1)] p-[var(--space-2)]"
          >
            <span className="flex size-[var(--space-5)] shrink-0 items-center justify-center rounded-full bg-[var(--color-accent)] font-mono text-[length:var(--text-2xs)] font-medium tabular-nums text-[var(--color-accent-text)]">
              {annotation.index}
            </span>
            <label className="min-w-0 flex-1">
              <span className="sr-only">{t('annotation.note_label', { defaultValue: 'Annotation note' })}</span>
              <textarea
                value={notesFor(annotation)}
                onChange={(event) => setDraft((prev) => ({ ...prev, [annotation.index]: event.target.value }))}
                placeholder={t('annotation.note_placeholder', { defaultValue: 'Describe the change…' })}
                rows={2}
                className="w-full resize-y rounded-[var(--radius-sm)] border border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-2)] p-[var(--space-1-5)] text-[length:var(--text-xs)] text-[var(--color-text-primary)] focus-visible:outline-none focus-visible:shadow-[var(--focus-ring)]"
              />
              <span className="mt-[var(--space-0-5)] block font-mono text-[length:var(--text-2xs)] tabular-nums text-[var(--color-text-muted)]">
                {`x: ${annotation.x}, y: ${annotation.y}`}
              </span>
            </label>
          </li>
        ))}
      </ul>

      <div className="flex justify-end">
        <Button
          size="sm"
          variant="primary"
          icon={<Send size={12} aria-hidden="true" />}
          onClick={handleSubmit}
        >
          {t('annotation.submit', { defaultValue: 'Submit feedback' })}
        </Button>
      </div>
    </div>
  );
}

export default AnnotationPanel;
