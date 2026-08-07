import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { Checkbox } from '../Checkbox';

describe('Checkbox', () => {
  const mockOnChange = vi.fn();

  beforeEach(() => {
    mockOnChange.mockClear();
  });

  it('renders checkbox element', () => {
    const { container } = render(
      <Checkbox
        checked={false}
        onChange={mockOnChange}
      />
    );
    const checkbox = container.querySelector('.w-4.h-4');
    expect(checkbox).toBeInTheDocument();
  });

  it('renders with default label', () => {
    render(<Checkbox checked={false} onChange={mockOnChange} label="Default" />);
    expect(screen.getByText('Default')).toBeInTheDocument();
  });

  it('renders with custom label', () => {
    render(<Checkbox
      checked={false}
      onChange={mockOnChange}
      label="Custom Label"
    />);
    expect(screen.getByText('Custom Label')).toBeInTheDocument();
  });

  it('renders description when provided', () => {
    render(
      <Checkbox checked={false} onChange={mockOnChange} label="Label" description="Description text" />
    );
    expect(screen.getByText('Description text')).toBeInTheDocument();
  });

  it('applies custom className', () => {
    const { container } = render(
      <Checkbox
        checked={false}
        onChange={mockOnChange}
        label="Label"
        className="custom-checkbox-class"
      />
    );
    const wrapper = container.querySelector('.custom-checkbox-class');
    expect(wrapper).toBeInTheDocument();
  });

  it('toggles checked state when clicked', () => {
    const { container } = render(<Checkbox checked={false} onChange={mockOnChange} />);
    const checkbox = container.querySelector('.w-4.h-4')!;
    fireEvent.click(checkbox);
    expect(mockOnChange).toHaveBeenCalledWith(true);
  });

  it('calls onChange with new checked state', () => {
    const { container } = render(<Checkbox checked={false} onChange={mockOnChange} />);
    const checkbox = container.querySelector('.w-4.h-4')!;
    fireEvent.click(checkbox);
    expect(mockOnChange).toHaveBeenCalledTimes(1);
    expect(mockOnChange).toHaveBeenCalledWith(true);
  });

  it('renders checked visual state when checked is true', () => {
    const { container } = render(<Checkbox checked={true} onChange={mockOnChange} />);
    const checkbox = container.querySelector('.w-4.h-4')!;
    expect(checkbox.className).toContain('bg-[var(--color-accent)]');
  });

  it('renders unchecked visual state when checked is false', () => {
    const { container } = render(<Checkbox checked={false} onChange={mockOnChange} />);
    const checkbox = container.querySelector('.w-4.h-4')!;
    expect(checkbox.className).toContain('border-[var(--color-border-default)]');
  });

  it('handles label click to toggle checkbox', () => {
    const { container } = render(
      <Checkbox
        checked={false}
        onChange={mockOnChange}
        label="Test Checkbox"
      />
    );
    const checkbox = container.querySelector('.w-4.h-4')!;
    fireEvent.click(checkbox);
    expect(mockOnChange).toHaveBeenCalledWith(true);
  });

  it('renders without errors when no props provided', () => {
    const { container } = render(
      <Checkbox checked={false} onChange={mockOnChange} />
    );
    expect(container.firstChild).toBeInTheDocument();
  });

  it('renders without label when label is not provided', () => {
    const { container } = render(
      <Checkbox
        checked={false}
        onChange={mockOnChange}
      />
    );
    const wrapper = container.querySelector('.w-4.h-4');
    expect(wrapper).toBeInTheDocument();
    expect(container.textContent).toBe('');
  });

  it('renders indeterminate state when indeterminate is true', () => {
    const { container } = render(
      <Checkbox checked={false} onChange={mockOnChange} indeterminate={true} />
    );
    const icon = container.querySelector('svg');
    expect(icon).toBeInTheDocument();
  });

  it('disables checkbox when disabled is true', () => {
    const { container } = render(
      <Checkbox checked={false} onChange={mockOnChange} disabled={true} />
    );
    const checkbox = container.querySelector('.w-4.h-4')!;
    expect(checkbox.className).toContain('opacity-40');
  });
});
