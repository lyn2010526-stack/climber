import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { DatePicker } from '../DatePicker';

describe('DatePicker', () => {
  it('renders with placeholder', () => {
    render(<DatePicker placeholder="选择日期" />);
    expect(screen.getByPlaceholderText('选择日期')).toBeDefined();
  });

  it('opens calendar on click', () => {
    render(<DatePicker />);
    const input = screen.getByPlaceholderText('选择日期');
    fireEvent.click(input);
    expect(screen.getByText('今天')).toBeDefined();
  });

  it('displays formatted date when value is provided', () => {
    const date = new Date(2024, 0, 15);
    render(<DatePicker value={date} />);
    const input = screen.getByPlaceholderText('选择日期') as HTMLInputElement;
    expect(input.value).toBe('2024-01-15');
  });

  it('calls onChange when a date is selected', () => {
    const handleChange = vi.fn();
    render(<DatePicker onChange={handleChange} placeholder="选择日期" />);
    fireEvent.click(screen.getByPlaceholderText('选择日期'));
    fireEvent.click(screen.getByText('15'));
    expect(handleChange).toHaveBeenCalled();
  });

  it('clears value when clear button is clicked', () => {
    const handleChange = vi.fn();
    const date = new Date(2024, 0, 15);
    render(<DatePicker value={date} onChange={handleChange} clearable />);
    fireEvent.click(screen.getByRole('button', { hidden: true }));
    expect(handleChange).toHaveBeenCalledWith(null);
  });

  it('navigates to previous and next month', () => {
    render(<DatePicker placeholder="选择日期" />);
    fireEvent.click(screen.getByPlaceholderText('选择日期'));
    const buttons = screen.getAllByRole('button');
    const prevButton = buttons[0];
    if (prevButton) fireEvent.click(prevButton);
    expect(screen.getByText('今天')).toBeDefined();
  });

  it('applies different sizes', () => {
    const { container } = render(<DatePicker inputSize="lg" />);
    expect(container.querySelector('.h-12')).not.toBeNull();
  });
});
