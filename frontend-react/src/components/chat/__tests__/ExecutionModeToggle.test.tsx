import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { ExecutionModeToggle } from '../ExecutionModeToggle';

describe('ExecutionModeToggle', () => {
  it('renders active mode label', () => {
    render(<ExecutionModeToggle mode="plan" onChange={vi.fn()} />);
    expect(screen.getByText('Plan')).toBeDefined();
  });

  it('opens dropdown on click', () => {
    render(<ExecutionModeToggle mode="plan" onChange={vi.fn()} />);
    fireEvent.click(screen.getByText('Plan'));
    expect(screen.getByText('Act')).toBeDefined();
    expect(screen.getByText('Auto')).toBeDefined();
  });

  it('calls onChange when mode is selected', () => {
    const onChange = vi.fn();
    render(<ExecutionModeToggle mode="plan" onChange={onChange} />);
    fireEvent.click(screen.getByText('Plan'));
    fireEvent.click(screen.getByText('Act'));
    expect(onChange).toHaveBeenCalledWith('act');
  });

  it('displays mode descriptions', () => {
    render(<ExecutionModeToggle mode="plan" onChange={vi.fn()} />);
    fireEvent.click(screen.getByText('Plan'));
    expect(screen.getByText('先规划后执行，需确认')).toBeDefined();
    expect(screen.getByText('自主执行，无需确认')).toBeDefined();
  });
});
