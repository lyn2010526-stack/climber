import { cn } from '../../lib/utils';
import { useId } from 'react';
import { useField } from './Field';

export interface SwitchProps {
  checked: boolean;
  onChange: (checked: boolean) => void;
  size?: 'sm' | 'md' | 'lg';
  label?: string;
  description?: string;
  disabled?: boolean;
  className?: string;
  id?: string;
  'aria-label'?: string;
  'aria-labelledby'?: string;
  'aria-describedby'?: string;
  required?: boolean;
}

/**
 * Every size is the same three-part recipe, so the ladder is arithmetic rather
 * than a set of numbers: a knob of `n`, a travel of `n`, and one spacing step
 * of slack at each end. Track width is `2n + 2s`, the checked offset is `n + s`
 * and the track height is `n + 2s`, with `s` one `--space-1`. That centres the
 * knob in both positions and keeps the three sizes genuinely proportional, with
 * no rung carrying a value the others cannot be derived from.
 *
 * Only the knob is written down; the track and the travel are computed from it,
 * because those are the values that have to agree for the knob to sit centred.
 * A measurement can only reach the DOM as a token, so the arithmetic resolves
 * back to the rung that holds it, and a value that lands between two rungs
 * throws here rather than shipping a switch whose knob has drifted off centre.
 */
interface SizeConfig {
  track: string;
  thumb: string;
  translate: string;
  rest: string;
  label: string;
  desc: string;
}

/** The knob rung per size. `--space-1` is a quarter of a rem, so each rung
 *  number counts quarter-rem steps, and `SLACK` below is one of those steps. */
const KNOB_RUNG: Record<'sm' | 'md' | 'lg', string> = {
  sm: 'var(--space-2)',
  md: 'var(--space-3)',
  lg: 'var(--space-4)',
};

const SLACK = 0.25;
const REM_PER_RUNG = 0.25;

/** The `--space-*` rungs by the measurement they resolve to, in rem. */
const SPACE_RUNG: Record<number, string> = {
  0: 'var(--space-0)',
  0.125: 'var(--space-0-5)',
  0.25: 'var(--space-1)',
  0.375: 'var(--space-1-5)',
  0.5: 'var(--space-2)',
  0.625: 'var(--space-2-5)',
  0.75: 'var(--space-3)',
  1: 'var(--space-4)',
  1.25: 'var(--space-5)',
  1.5: 'var(--space-6)',
  2: 'var(--space-8)',
  2.5: 'var(--space-10)',
  3: 'var(--space-12)',
  4: 'var(--space-16)',
  5: 'var(--space-20)',
};

const trackWidth = (knob: number) => 2 * knob + 2 * SLACK;
const trackHeight = (knob: number) => knob + 2 * SLACK;
const checkedOffset = (knob: number) => knob + SLACK;
const restingOffset = () => SLACK;

const rung = (rem: number) => {
  const token = SPACE_RUNG[rem];
  if (!token) throw new Error(`switch size recipe produced ${rem}rem, which is not a --space-* rung`);
  return token;
};

const sizeConfig = (size: 'sm' | 'md' | 'lg'): SizeConfig => {
  const knobToken = KNOB_RUNG[size];
  const knob = Number.parseFloat(/[\d.]+/.exec(knobToken)![0]) * REM_PER_RUNG;
  return {
    track: `w-[${rung(trackWidth(knob))}] h-[${rung(trackHeight(knob))}]`,
    thumb: `size-[${knobToken}]`,
    translate: `translate-x-[${rung(checkedOffset(knob))}]`,
    // The unchecked knob sits on the leading slack, which is the same gap the
    // checked position leaves behind it. Reading it from the recipe rather than
    // from a literal is what stops the two positions drifting apart.
    rest: `translate-x-[${rung(restingOffset())}]`,
    label: size === 'sm' ? 'text-[length:var(--text-xs)]' : 'text-[length:var(--text-sm)]',
    desc: size === 'sm' ? 'text-[length:var(--text-2xs)]' : 'text-[length:var(--text-xs)]',
  };
};

export function Switch({
  checked,
  onChange,
  size = 'md',
  label,
  description,
  disabled = false,
  className,
  id,
  required,
  ...aria
}: SwitchProps) {
  const generatedId = useId();
  // Inside a FormField the switch adopts the id the field's label points at,
  // and the field's description paragraph id, because the field is what renders
  // that text: the control points at it rather than drawing its own copy.
  const field = useField();
  const controlId = field?.htmlFor ?? id ?? generatedId;
  const labelId = `${controlId}-label`;
  const descriptionId = field?.messageId ?? `${controlId}-description`;

  const config = sizeConfig(size);

  // An explicit aria-label from the caller wins over the visible label, which
  // is what an icon-only or externally-labelled switch needs.
  const labelledBy = aria['aria-labelledby'] ?? (label ? labelId : undefined);
  // Only a description the switch itself renders may be announced from here.
  // A description the surrounding `FormField` renders is wired to the control
  // by the field, so listing it again would read the same sentence twice.
  const describedBy = [
    aria['aria-describedby'],
    label && description && !field?.messageId ? descriptionId : undefined,
  ].filter(Boolean).join(' ') || undefined;

  // Four states, all carried by the track. Off is the top of the surface ramp,
  // on is the accent with the accent's own hover and press, focus is the shared
  // two-layer ring, and disabled is the recessed fill with a dropped label.
  // Disabled never reaches the accent, so a live switch and a locked one can
  // never both read as switched on.
  const trackStates = disabled
    ? 'bg-[var(--color-bg-disabled)] border-[var(--color-border-subtle)]'
    : checked
      ? 'bg-[var(--color-accent)] border-[var(--color-accent)] enabled:hover:bg-[var(--color-accent-hover)] enabled:active:bg-[var(--color-accent-active)]'
      : 'bg-[var(--color-bg-surface-4)] border-[var(--color-border-default)] enabled:hover:bg-[var(--color-border-strong)] enabled:active:bg-[var(--color-bg-surface-3)]';

  const switchElement = (
    <button
      type="button"
      role="switch"
      id={controlId}
      aria-checked={checked}
      aria-label={aria['aria-label']}
      aria-labelledby={labelledBy}
      aria-describedby={describedBy}
      aria-required={required || undefined}
      onClick={() => !disabled && onChange(!checked)}
      disabled={disabled}
      className={cn(
        'relative inline-flex shrink-0 items-center rounded-[var(--radius-pill)] border',
        'cursor-pointer transition-colors duration-150 motion-reduce:transition-none',
        'focus-visible:outline-none focus-visible:shadow-[var(--focus-ring)]',
        'disabled:cursor-not-allowed',
        config.track,
        trackStates,
        !label && className
      )}
    >
      <span
        className={cn(
          // The knob is the page colour with a hairline of its own, so it stays
          // the same object in both positions and the track colour alone carries
          // the state.
          'pointer-events-none inline-block rounded-[var(--radius-pill)] border border-[var(--color-border-default)] bg-[var(--color-bg-page)]',
          'transition-transform duration-150 motion-reduce:transition-none',
          config.thumb,
          checked ? config.translate : config.rest
        )}
      />
    </button>
  );

  if (!label) return switchElement;

  return (
    <div className={cn('flex items-center justify-between gap-[var(--space-3)]', className)}>
      <div className="min-w-0 flex-1">
        <div id={labelId} className={cn('font-medium', disabled ? 'text-[var(--color-text-disabled)]' : 'text-[var(--color-text-secondary)]', config.label)}>{label}</div>
        {description && <div id={descriptionId} className={cn('mt-[var(--space-0-5)]', disabled ? 'text-[var(--color-text-disabled)]' : 'text-[var(--color-text-muted)]', config.desc)}>{description}</div>}
      </div>
      {switchElement}
    </div>
  );
}
