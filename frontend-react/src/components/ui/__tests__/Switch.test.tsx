import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { Switch } from '../Switch';

describe('Switch', () => {
  const mockOnChange = vi.fn();

  beforeEach(() => {
    mockOnChange.mockClear();
  });

  it('renders switch without label when label is not provided', () => {
    const { container } = render(<Switch checked={false} onChange={mockOnChange} />);
    expect(container.querySelector('button')).toBeInTheDocument();
    expect(container.querySelector('[role="switch"]')).toBeInTheDocument();
  });

  it('applies correct classes for unchecked state', () => {
    const { container } = render(<Switch checked={false} onChange={mockOnChange} />);
    const button = container.querySelector('button');
    expect(button?.classList).toContain('bg-[var(--color-bg-surface-4)]');
    expect(button?.getAttribute('aria-checked')).toBe('false');
  });

  it('applies correct classes for checked state', () => {
    const { container } = render(<Switch checked={true} onChange={mockOnChange} />);
    const button = container.querySelector('button');
    expect(button?.classList).toContain('bg-[var(--color-accent)]');
    expect(button?.getAttribute('aria-checked')).toBe('true');
  });

  it('toggles checked state when clicked', () => {
    render(<Switch checked={false} onChange={mockOnChange} />);
    const button = screen.getByRole('switch');
    fireEvent.click(button);
    expect(mockOnChange).toHaveBeenCalledWith(true);
  });

  it('calls onChange with true when switching on', () => {
    render(<Switch checked={false} onChange={mockOnChange} />);
    const button = screen.getByRole('switch');
    fireEvent.click(button);
    expect(mockOnChange).toHaveBeenCalledTimes(1);
    expect(mockOnChange).toHaveBeenCalledWith(true);
  });

  it('calls onChange with false when switching off', () => {
    render(<Switch checked={true} onChange={mockOnChange} />);
    const button = screen.getByRole('switch');
    fireEvent.click(button);
    expect(mockOnChange).toHaveBeenCalledTimes(1);
    expect(mockOnChange).toHaveBeenCalledWith(false);
  });

  it('applies sm size classes', () => {
    const { container } = render(<Switch checked={false} onChange={mockOnChange} size="sm" />);
    const button = container.querySelector('button');
    expect(button?.classList).toContain('w-7');
    expect(button?.classList).toContain('h-4');
  });

  it('applies md size classes', () => {
    const { container } = render(<Switch checked={false} onChange={mockOnChange} size="md" />);
    const button = container.querySelector('button');
    expect(button?.classList).toContain('w-9');
    expect(button?.classList).toContain('h-5');
  });

  it('applies lg size classes', () => {
    const { container } = render(<Switch checked={false} onChange={mockOnChange} size="lg" />);
    const button = container.querySelector('button');
    expect(button?.classList).toContain('w-11');
    expect(button?.classList).toContain('h-6');
  });

  it('renders with label when label is provided', () => {
    render(<Switch checked={false} onChange={mockOnChange} label="Test Label" />);
    expect(screen.getByText('Test Label')).toBeInTheDocument();
  });

  it('renders description when provided', () => {
    render(<Switch 
      checked={false} 
      onChange={mockOnChange} 
      label="Test Label"
      description="Test Description" 
    />);
    expect(screen.getByText('Test Description')).toBeInTheDocument();
  });

  it('applies disabled class when disabled prop is true', () => {
    const { container } = render(<Switch checked={false} onChange={mockOnChange} disabled />);
    const button = container.querySelector('button');
    expect(button?.classList).toContain('opacity-40');
    expect(button?.classList).toContain('cursor-not-allowed');
  });

  it('does not call onChange when disabled', () => {
    render(<Switch checked={false} onChange={mockOnChange} disabled />);
    const button = screen.getByRole('switch');
    fireEvent.click(button);
    expect(mockOnChange).not.toHaveBeenCalled();
  });

  it('applies custom className', () => {
    const { container } = render(
      <Switch 
        checked={false} 
        onChange={mockOnChange} 
        label="Test"
        className="custom-class"
      />
    );
    const div = container.querySelector('div');
    expect(div?.classList).toContain('custom-class');
  });

  it('uses default size md when not specified', () => {
    const { container } = render(<Switch checked={false} onChange={mockOnChange} />);
    const button = container.querySelector('button');
    expect(button?.classList).toContain('w-9');
    expect(button?.classList).toContain('h-5');
  });

  it('properly positions thumb when checked', () => {
    const { container } = render(<Switch checked={true} onChange={mockOnChange} />);
    const thumb = container.querySelector('.pointer-events-none');
    expect(thumb?.classList).toContain('translate-x-4');
  });

  it('positions thumb at start when unchecked', () => {
    const { container } = render(<Switch checked={false} onChange={mockOnChange} />);
    const thumb = container.querySelector('.pointer-events-none');
    expect(thumb?.classList).toContain('translate-x-0');
  });
});
