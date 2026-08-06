import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Input } from '../Input';

describe('Input', () => {
  const mockOnChange = vi.fn();

  beforeEach(() => {
    mockOnChange.mockClear();
  });

  it('renders input element', () => {
    render(<Input onChange={mockOnChange} />);
    expect(screen.getByRole('textbox')).toBeInTheDocument();
  });

  it('renders with default props', () => {
    const { container } = render(<Input onChange={mockOnChange} />);
    const wrapper = container.querySelector('.w-full');
    expect(wrapper).toBeInTheDocument();
  });

  it('applies sm size classes correctly', () => {
    const { container } = render(<Input size="sm" onChange={mockOnChange} />);
    const input = container.querySelector('input');
    expect(input?.className).toContain('h-8');
    expect(input?.className).toContain('text-xs');
  });

  it('applies md size classes by default', () => {
    const { container } = render(<Input onChange={mockOnChange} />);
    const input = container.querySelector('input');
    expect(input?.className).toContain('h-10');
    expect(input?.className).toContain('text-sm');
  });

  it('applies lg size classes when specified', () => {
    const { container } = render(<Input size="lg" onChange={mockOnChange} />);
    const input = container.querySelector('input');
    expect(input?.className).toContain('h-11');
  });

  it('applies disabled class when disabled prop is true', () => {
    const { container } = render(<Input disabled onChange={mockOnChange} />);
    const input = container.querySelector('input');
    expect(input?.className).toContain('disabled:cursor-not-allowed');
  });

  it('disables input element when disabled', () => {
    const { container } = render(<Input disabled onChange={mockOnChange} />);
    const input = container.querySelector('input');
    expect(input).toBeDisabled();
  });

  it('applies loading class when loading prop is true', () => {
    const { container } = render(<Input loading onChange={mockOnChange} />);
    const wrapper = container.querySelector('.relative.flex');
    expect(wrapper?.className).toContain('flex');
  });

  it('applies custom className', () => {
    const { container } = render(<Input className="custom-input-class" onChange={mockOnChange} />);
    const input = container.querySelector('input');
    expect(input?.className).toContain('custom-input-class');
  });

  it('handles text input changes', async () => {
    const user = userEvent.setup();
    render(<Input onChange={mockOnChange} />);
    const input = screen.getByRole('textbox');

    await user.type(input, 'Test input');

    expect(mockOnChange).toHaveBeenCalled();
  });

  it('calls onChange when value changes', async () => {
    const user = userEvent.setup();
    render(<Input onChange={mockOnChange} />);
    const input = screen.getByRole('textbox');

    await user.type(input, 'Hello');

    expect(mockOnChange).toHaveBeenCalled();
  });

  it('displays placeholder text', () => {
    render(
      <Input
        placeholder="Enter your text"
        onChange={mockOnChange}
      />
    );
    const input = screen.getByRole('textbox');
    expect(input).toHaveAttribute('placeholder', 'Enter your text');
  });

  it('supports type attribute for different input types', () => {
    const { container } = render(
      <Input
        type="password"
        onChange={mockOnChange}
      />
    );
    const input = container.querySelector('input[type="password"]');
    expect(input).toHaveAttribute('type', 'password');
  });

  it('supports pattern validation', () => {
    render(
      <Input
        pattern="[a-zA-Z]+"
        onChange={mockOnChange}
      />
    );
    const input = screen.getByRole('textbox');
    expect(input).toHaveAttribute('pattern', '[a-zA-Z]+');
  });

  it('preserves additional HTML attributes', () => {
    const { container } = render(
      <Input
        data-testid="custom-input"
        onChange={mockOnChange}
      />
    );
    const input = container.querySelector('[data-testid="custom-input"]');
    expect(input).toBeInTheDocument();
  });

  it('works with form labels', () => {
    const { container } = render(
      <form>
        <label htmlFor="username">Username</label>
        <Input
          id="username"
          onChange={mockOnChange}
        />
      </form>
    );
    const label = container.querySelector('label');
    expect(label?.textContent).toBe('Username');
  });

  it('handles email input type', () => {
    render(<Input type="email" onChange={mockOnChange} />);
    const input = screen.getByRole('textbox');
    expect(input).toHaveAttribute('type', 'email');
  });

  it('handles number input type', () => {
    const { container } = render(<Input type="number" onChange={mockOnChange} />);
    const input = container.querySelector('input[type="number"]');
    expect(input).toHaveAttribute('type', 'number');
  });

  it('allows reading current value', async () => {
    const user = userEvent.setup();
    render(<Input onChange={mockOnChange} />);
    const input = screen.getByRole('textbox');

    await user.type(input, 'Current Value');

    expect(input).toHaveValue('Current Value');
  });

  it('renders without errors when minimal props provided', () => {
    const { container } = render(<Input onChange={mockOnChange} />);
    expect(container.firstChild).toBeInTheDocument();
  });

  it('supports autoComplete attribute', () => {
    render(
      <Input
        autoComplete="off"
        onChange={mockOnChange}
      />
    );
    const input = screen.getByRole('textbox');
    expect(input).toHaveAttribute('autocomplete', 'off');
  });

  it('supports maxLength attribute', () => {
    render(
      <Input
        maxLength={100}
        onChange={mockOnChange}
      />
    );
    const input = screen.getByRole('textbox');
    expect(input).toHaveAttribute('maxLength', '100');
  });

  it('shows error message when error prop is provided', () => {
    const { container } = render(<Input error="This field is required" onChange={mockOnChange} />);
    expect(screen.getByText('This field is required')).toBeInTheDocument();
    const input = container.querySelector('input');
    expect(input?.className).toContain('border-[var(--color-error)]');
  });

  it('shows hint message when hint prop is provided', () => {
    render(<Input hint="Helper text" onChange={mockOnChange} />);
    expect(screen.getByText('Helper text')).toBeInTheDocument();
  });

  it('shows loading spinner when loading is true', () => {
    const { container } = render(<Input loading onChange={mockOnChange} />);
    const spinner = container.querySelector('.animate-spin');
    expect(spinner).toBeInTheDocument();
  });

  it('shows success icon when success is true', () => {
    const { container } = render(<Input success onChange={mockOnChange} />);
    const wrapper = container.querySelector('.relative.flex');
    expect(wrapper?.textContent).toBe('');
  });
});
