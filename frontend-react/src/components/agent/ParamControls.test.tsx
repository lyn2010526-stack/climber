import { fireEvent, render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useState } from 'react';
import {
  ParamControls,
  type ParamControlsValues,
} from './ParamControls';

const DEFAULTS: ParamControlsValues = {
  temperature: 0.7,
  top_p: 1,
  frequency_penalty: 0,
  presence_penalty: 0,
  max_tokens: 4096,
  response_format: 'text',
  stop: '',
};

function Harness({ onChange }: { onChange?: (k: keyof ParamControlsValues, v: unknown) => void }) {
  const [value, setValue] = useState<ParamControlsValues>(DEFAULTS);
  return (
    <ParamControls
      value={value}
      onChange={(key, next) => {
        setValue((previous) => ({ ...previous, [key]: next }));
        onChange?.(key, next);
      }}
    />
  );
}

describe('ParamControls', () => {
  beforeEach(() => vi.clearAllMocks());

  it('renders a labelled slider and numeric readout for each parameter', () => {
    render(<ParamControls value={DEFAULTS} onChange={vi.fn()} />);
    for (const key of ['temperature', 'top_p', 'frequency_penalty', 'presence_penalty', 'max_tokens']) {
      expect(screen.getByTestId(`param-row-${key}`)).toBeVisible();
      expect(screen.getByTestId(`param-value-${key}`)).toBeVisible();
    }
    expect(screen.getByLabelText('Temperature')).toHaveAttribute('type', 'range');
    expect(screen.getByTestId('param-value-temperature')).toHaveTextContent('0.70');
    expect(screen.getByTestId('param-value-top_p')).toHaveTextContent('1.00');
  });

  it('reports the numeric value through onChange when a slider moves', () => {
    const onChange = vi.fn();
    render(<Harness onChange={onChange} />);
    fireEvent.change(screen.getByLabelText('Temperature'), { target: { value: '1.25' } });
    expect(onChange).toHaveBeenCalledWith('temperature', 1.25);
    expect(screen.getByTestId('param-value-temperature')).toHaveTextContent('1.25');
  });

  it('clamps a reported value into the parameter range', () => {
    const onChange = vi.fn();
    render(<ParamControls value={DEFAULTS} onChange={onChange} />);
    const topP = screen.getByLabelText('Top P');
    expect(topP).toHaveAttribute('min', '0');
    expect(topP).toHaveAttribute('max', '1');
    // The control owns the bounds; a hostile value cannot reach the caller.
    fireEvent.change(topP, { target: { value: '0.42' } });
    expect(onChange).toHaveBeenCalledWith('top_p', 0.42);
  });

  it('exposes selects for common parameters and reports changes', () => {
    const onChange = vi.fn();
    render(<ParamControls value={DEFAULTS} onChange={onChange} />);
    const format = screen.getByTestId('param-select-response_format');
    fireEvent.change(format, { target: { value: 'json_object' } });
    expect(onChange).toHaveBeenCalledWith('response_format', 'json_object');
  });

  it('is fully controlled: it only reports, never mutates its own value', () => {
    const onChange = vi.fn();
    render(<ParamControls value={DEFAULTS} onChange={onChange} />);
    fireEvent.change(screen.getByTestId('param-input-stop'), { target: { value: 'END' } });
    expect(onChange).toHaveBeenCalledWith('stop', 'END');
    expect(screen.getByTestId('param-input-stop')).toHaveValue('');
  });

  it('disables every control when disabled', () => {
    render(<ParamControls value={DEFAULTS} onChange={vi.fn()} disabled />);
    expect(screen.getByLabelText('Temperature')).toBeDisabled();
    expect(screen.getByTestId('param-select-response_format')).toBeDisabled();
    expect(screen.getByTestId('param-input-stop')).toBeDisabled();
  });
});
