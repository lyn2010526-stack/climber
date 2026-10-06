import { useId } from 'react';
import { cn } from '../../lib/utils';
import { useI18n } from '../../i18n';

export interface ParamControlsValues {
  temperature: number;
  top_p: number;
  frequency_penalty: number;
  presence_penalty: number;
  max_tokens: number;
  response_format: string;
  stop: string;
}

export type ParamControlsChange = <K extends keyof ParamControlsValues>(
  key: K,
  value: ParamControlsValues[K],
) => void;

export interface ParamControlsProps {
  value: ParamControlsValues;
  onChange: ParamControlsChange;
  disabled?: boolean;
  /**
   * Keys the surrounding feature actually honours. When provided, every other
   * control renders disabled with a "not supported yet" marker instead of
   * letting the user tune a value nothing consumes.
   */
  supportedKeys?: readonly (keyof ParamControlsValues)[];
  className?: string;
  'data-testid'?: string;
}

interface SliderSpec {
  min: number;
  max: number;
  step: number;
}

interface ParamRow {
  key: keyof ParamControlsValues;
  labelKey: string;
  labelDefault: string;
  slider: SliderSpec;
}

const SLIDER_ROWS: ParamRow[] = [
  {
    key: 'temperature',
    labelKey: 'agent.params.temperature',
    labelDefault: 'Temperature',
    slider: { min: 0, max: 2, step: 0.01 },
  },
  {
    key: 'top_p',
    labelKey: 'agent.params.top_p',
    labelDefault: 'Top P',
    slider: { min: 0, max: 1, step: 0.01 },
  },
  {
    key: 'frequency_penalty',
    labelKey: 'agent.params.frequency_penalty',
    labelDefault: 'Frequency penalty',
    slider: { min: -2, max: 2, step: 0.01 },
  },
  {
    key: 'presence_penalty',
    labelKey: 'agent.params.presence_penalty',
    labelDefault: 'Presence penalty',
    slider: { min: -2, max: 2, step: 0.01 },
  },
];

const MAX_TOKENS: SliderSpec = { min: 1, max: 32768, step: 1 };

const RESPONSE_FORMATS = ['text', 'json_object'] as const;

const clamp = (value: number, spec: SliderSpec) => {
  if (Number.isNaN(value)) return spec.min;
  return Math.min(spec.max, Math.max(spec.min, value));
};

const formatReadout = (value: number, spec: SliderSpec) => {
  const decimals = spec.step < 1 ? 2 : 0;
  return value.toFixed(decimals);
};

export function ParamControls({
  value,
  onChange,
  disabled = false,
  supportedKeys,
  className,
  'data-testid': testId = 'param-controls',
}: ParamControlsProps) {
  const { t } = useI18n();

  const isSupported = (key: keyof ParamControlsValues) =>
    !supportedKeys || supportedKeys.includes(key);

  const unsupportedBadge = (
    <span className="ml-[var(--space-1)] rounded-[var(--radius-sm)] bg-[var(--color-bg-surface-3)] px-1 py-0.5 text-[length:var(--text-2xs)] text-[var(--color-text-muted)]">
      {t('agent.params.not_supported', { defaultValue: 'Not supported yet' })}
    </span>
  );

  const renderSlider = (row: ParamRow) => {
    const controlId = `${testId}-${row.key}`;
    const current = value[row.key] as number;
    const supported = isSupported(row.key);
    return (
      <div
        key={row.key}
        data-testid={`param-row-${row.key}`}
        className="grid grid-cols-[minmax(0,7rem)_1fr_3.5rem] items-center gap-[var(--space-3)]"
      >
        <label
          htmlFor={controlId}
          className="truncate text-[length:var(--text-sm)] text-[var(--color-text-secondary)]"
        >
          {t(row.labelKey, { defaultValue: row.labelDefault })}
          {!supported && unsupportedBadge}
        </label>
        <input
          id={controlId}
          type="range"
          min={row.slider.min}
          max={row.slider.max}
          step={row.slider.step}
          value={current}
          disabled={disabled || !supported}
          aria-valuetext={formatReadout(current, row.slider)}
          onChange={(event) => {
            const next = clamp(Number(event.target.value), row.slider);
            onChange(row.key, next as ParamControlsValues[typeof row.key]);
          }}
          className={cn(
            'h-[var(--control-height-xs)] w-full cursor-pointer appearance-none rounded-[var(--radius-pill)] bg-[var(--color-bg-surface-3)]',
            'accent-[var(--color-accent)]',
            'focus-visible:outline-none focus-visible:shadow-[var(--focus-ring)]',
            'disabled:cursor-not-allowed disabled:bg-[var(--color-bg-disabled)]',
          )}
        />
        <output
          htmlFor={controlId}
          data-testid={`param-value-${row.key}`}
          className="rounded-[var(--radius-sm)] bg-[var(--color-bg-surface-2)] px-[var(--space-2)] py-[var(--space-1)] text-center font-mono text-[length:var(--text-xs)] tabular-nums text-[var(--color-text-primary)]"
        >
          {formatReadout(current, row.slider)}
        </output>
      </div>
    );
  };

  const selectId = useId();
  const stopId = useId();

  return (
    <div
      data-testid={testId}
      className={cn('flex flex-col gap-[var(--space-3)]', className)}
    >
      {SLIDER_ROWS.map(renderSlider)}

      <div
        data-testid="param-row-max_tokens"
        className="grid grid-cols-[minmax(0,7rem)_1fr_3.5rem] items-center gap-[var(--space-3)]"
      >
        <label
          htmlFor={`${testId}-max_tokens`}
          className="truncate text-[length:var(--text-sm)] text-[var(--color-text-secondary)]"
        >
          {t('agent.params.max_tokens', { defaultValue: 'Max tokens' })}
          {!isSupported('max_tokens') && unsupportedBadge}
        </label>
        <input
          id={`${testId}-max_tokens`}
          type="range"
          min={MAX_TOKENS.min}
          max={MAX_TOKENS.max}
          step={MAX_TOKENS.step}
          value={value.max_tokens}
          disabled={disabled || !isSupported('max_tokens')}
          aria-valuetext={String(value.max_tokens)}
          onChange={(event) => {
            onChange('max_tokens', clamp(Number(event.target.value), MAX_TOKENS));
          }}
          className={cn(
            'h-[var(--control-height-xs)] w-full cursor-pointer appearance-none rounded-[var(--radius-pill)] bg-[var(--color-bg-surface-3)]',
            'accent-[var(--color-accent)]',
            'focus-visible:outline-none focus-visible:shadow-[var(--focus-ring)]',
            'disabled:cursor-not-allowed disabled:bg-[var(--color-bg-disabled)]',
          )}
        />
        <output
          htmlFor={`${testId}-max_tokens`}
          data-testid="param-value-max_tokens"
          className="rounded-[var(--radius-sm)] bg-[var(--color-bg-surface-2)] px-[var(--space-2)] py-[var(--space-1)] text-center font-mono text-[length:var(--text-xs)] tabular-nums text-[var(--color-text-primary)]"
        >
          {value.max_tokens}
        </output>
      </div>

      <div className="grid grid-cols-[minmax(0,7rem)_1fr] items-center gap-[var(--space-3)]">
        <label
          htmlFor={selectId}
          className="truncate text-[length:var(--text-sm)] text-[var(--color-text-secondary)]"
        >
          {t('agent.params.response_format', { defaultValue: 'Response format' })}
          {!isSupported('response_format') && unsupportedBadge}
        </label>
        <select
          id={selectId}
          data-testid="param-select-response_format"
          value={value.response_format}
          disabled={disabled || !isSupported('response_format')}
          onChange={(event) => onChange('response_format', event.target.value)}
          className={cn(
            'h-[var(--control-height-sm)] w-full rounded-[var(--radius-md)] border border-[var(--color-border-default)] bg-[var(--color-bg-surface-2)] px-[var(--space-3)] text-[length:var(--text-sm)] text-[var(--color-text-primary)]',
            'transition-colors hover:border-[var(--color-border-strong)]',
            'focus-visible:outline-none focus-visible:border-[var(--color-border-accent)] focus-visible:shadow-[var(--focus-ring)]',
            'disabled:cursor-not-allowed disabled:bg-[var(--color-bg-disabled)] disabled:text-[var(--color-text-disabled)]',
          )}
        >
          {RESPONSE_FORMATS.map((format) => (
            <option key={format} value={format}>
              {format}
            </option>
          ))}
        </select>
      </div>

      <div className="grid grid-cols-[minmax(0,7rem)_1fr] items-center gap-[var(--space-3)]">
        <label
          htmlFor={stopId}
          className="truncate text-[length:var(--text-sm)] text-[var(--color-text-secondary)]"
        >
          {t('agent.params.stop', { defaultValue: 'Stop sequences' })}
          {!isSupported('stop') && unsupportedBadge}
        </label>
        <input
          id={stopId}
          data-testid="param-input-stop"
          type="text"
          value={value.stop}
          disabled={disabled || !isSupported('stop')}
          placeholder={t('agent.params.stop_placeholder', { defaultValue: 'Comma separated' })}
          onChange={(event) => onChange('stop', event.target.value)}
          className={cn(
            'h-[var(--control-height-sm)] w-full rounded-[var(--radius-md)] border border-[var(--color-border-default)] bg-[var(--color-bg-surface-2)] px-[var(--space-3)] text-[length:var(--text-sm)] text-[var(--color-text-primary)]',
            'placeholder:text-[var(--color-text-muted)]',
            'transition-colors hover:border-[var(--color-border-strong)]',
            'focus-visible:outline-none focus-visible:border-[var(--color-border-accent)] focus-visible:shadow-[var(--focus-ring)]',
            'disabled:cursor-not-allowed disabled:bg-[var(--color-bg-disabled)] disabled:text-[var(--color-text-disabled)]',
          )}
        />
      </div>
    </div>
  );
}

export default ParamControls;
