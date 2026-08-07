import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { Radio, RadioGroup } from '../Radio';

describe('Radio', () => {
  const mockOnChange = vi.fn();

  beforeEach(() => {
    mockOnChange.mockClear();
  });

  it('renders a radio input', () => {
    render(<Radio checked={false} onChange={mockOnChange} />);
    expect(screen.getByRole('radio')).toBeInTheDocument();
  });

  it('renders label content', () => {
    render(<Radio checked={false} onChange={mockOnChange} label="Radio Label" />);
    expect(screen.getByText('Radio Label')).toBeInTheDocument();
  });

  it('renders description content', () => {
    render(<Radio checked={false} onChange={mockOnChange} description="Radio Description" />);
    expect(screen.getByText('Radio Description')).toBeInTheDocument();
  });

  it('does not render label block when label and description are absent', () => {
    render(<Radio checked={false} onChange={mockOnChange} />);
    expect(screen.queryByText('Radio Label')).not.toBeInTheDocument();
  });

  it('disables the actual radio input when disabled', () => {
    const { container } = render(<Radio checked={false} onChange={mockOnChange} disabled />);
    const radio = container.querySelector('input[type="radio"]');
    expect(radio).toBeDisabled();
  });

  it('applies disabled styling class', () => {
    const { container } = render(<Radio checked={false} onChange={mockOnChange} disabled />);
    expect(container.querySelector('label')?.className).toContain('opacity-50');
  });

  it('applies custom className', () => {
    const { container } = render(
      <Radio checked={false} onChange={mockOnChange} className="custom-radio-class" />
    );
    expect(container.querySelector('label')?.className).toContain('custom-radio-class');
  });

  it('handles change events when clicked', () => {
    render(<Radio checked={false} onChange={mockOnChange} />);
    const radio = screen.getByRole('radio');
    fireEvent.click(radio);
    expect(mockOnChange).toHaveBeenCalledWith(true);
  });

  it('renders as unchecked when checked is false', () => {
    render(<Radio checked={false} onChange={mockOnChange} />);
    expect(screen.getByRole('radio')).not.toBeChecked();
  });

  it('renders as checked when checked is true', () => {
    render(<Radio checked onChange={mockOnChange} />);
    expect(screen.getByRole('radio')).toBeChecked();
  });

  it('shows filled indicator when checked', () => {
    const { container } = render(<Radio checked onChange={mockOnChange} />);
    const border = container.querySelector('.rounded-full');
    expect(border?.className).toContain('bg-[var(--color-accent)]');
  });

  it('shows empty indicator when unchecked', () => {
    const { container } = render(<Radio checked={false} onChange={mockOnChange} />);
    const border = container.querySelector('.rounded-full');
    expect(border?.className).toContain('bg-transparent');
  });
});

describe('RadioGroup', () => {
  const options = [
    { value: 'a', label: 'Option A' },
    { value: 'b', label: 'Option B', description: 'B description' },
  ];

  it('renders all options', () => {
    render(<RadioGroup options={options} value="a" onChange={() => {}} />);
    expect(screen.getAllByRole('radio')).toHaveLength(2);
    expect(screen.getByText('Option A')).toBeInTheDocument();
    expect(screen.getByText('Option B')).toBeInTheDocument();
  });

  it('checks the option matching the value', () => {
    render(<RadioGroup options={options} value="b" onChange={() => {}} />);
    const radios = screen.getAllByRole('radio');
    expect(radios[0]).not.toBeChecked();
    expect(radios[1]).toBeChecked();
  });

  it('calls onChange with option value when selected', () => {
    const handleChange = vi.fn();
    render(<RadioGroup options={options} value="a" onChange={handleChange} />);
    fireEvent.click(screen.getAllByRole('radio')[1]);
    expect(handleChange).toHaveBeenCalledWith('b');
  });
});
