import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Textarea } from '../Textarea';

describe('Textarea', () => {
  const mockOnChange = vi.fn();

  beforeEach(() => {
    mockOnChange.mockClear();
  });

  it('renders textarea element', () => {
    render(<Textarea onChange={mockOnChange} />);
    expect(screen.getByRole('textbox')).toBeInTheDocument();
  });

  it('renders with default props', () => {
    const { container } = render(<Textarea onChange={mockOnChange} />);
    const wrapper = container.querySelector('.w-full');
    expect(wrapper).toBeInTheDocument();
  });

  it('applies custom className', () => {
    const { container } = render(<Textarea className="custom-textarea-class" onChange={mockOnChange} />);
    const textarea = container.querySelector('textarea');
    expect(textarea?.className).toContain('custom-textarea-class');
  });

  it('handles text input changes', async () => {
    const user = userEvent.setup();
    render(<Textarea onChange={mockOnChange} />);
    const textarea = screen.getByRole('textbox');

    await user.type(textarea, 'Test input');

    expect(mockOnChange).toHaveBeenCalled();
  });

  it('calls onChange when value changes', async () => {
    const user = userEvent.setup();
    render(<Textarea onChange={mockOnChange} />);
    const textarea = screen.getByRole('textbox');

    await user.type(textarea, 'Hello');

    expect(mockOnChange).toHaveBeenCalled();
  });

  it('displays placeholder text', () => {
    render(
      <Textarea
        placeholder="Enter your message"
        onChange={mockOnChange}
      />
    );
    const textarea = screen.getByRole('textbox');
    expect(textarea).toHaveAttribute('placeholder', 'Enter your message');
  });

  it('supports rows attribute', () => {
    const { container } = render(
      <Textarea
        rows={5}
        onChange={mockOnChange}
      />
    );
    const textarea = container.querySelector('textarea');
    expect(textarea?.getAttribute('rows')).toBe('5');
  });

  it('disables textarea input when disabled', () => {
    const { container } = render(<Textarea disabled onChange={mockOnChange} />);
    const textarea = container.querySelector('textarea');
    expect(textarea).toBeDisabled();
  });

  it('preserves additional HTML attributes', () => {
    const { container } = render(
      <Textarea
        data-testid="custom-textarea"
        onChange={mockOnChange}
      />
    );
    const textarea = container.querySelector('[data-testid="custom-textarea"]');
    expect(textarea).toBeInTheDocument();
  });

  it('works with form labels', () => {
    const { container } = render(
      <form>
        <label htmlFor="message">Message</label>
        <Textarea
          id="message"
          onChange={mockOnChange}
        />
      </form>
    );
    const label = container.querySelector('label');
    expect(label?.textContent).toBe('Message');
  });

  it('handles multiline text input', async () => {
    const user = userEvent.setup();
    render(<Textarea onChange={mockOnChange} />);
    const textarea = screen.getByRole('textbox');

    await user.type(textarea, 'Line 1\nLine 2\nLine 3');

    expect(textarea).toHaveValue('Line 1\nLine 2\nLine 3');
  });

  it('allows reading current value', async () => {
    const user = userEvent.setup();
    render(<Textarea onChange={mockOnChange} />);
    const textarea = screen.getByRole('textbox');

    await user.type(textarea, 'Current Value');

    expect(textarea).toHaveValue('Current Value');
  });

  it('renders without errors when no props provided except onChange', () => {
    const { container } = render(<Textarea onChange={mockOnChange} />);
    expect(container.firstChild).toBeInTheDocument();
  });

  it('shows error message when error prop is provided', () => {
    render(<Textarea error="Required field" onChange={mockOnChange} />);
    expect(screen.getByText('Required field')).toBeInTheDocument();
  });

  it('shows hint message when hint prop is provided', () => {
    render(<Textarea hint="Helper text" onChange={mockOnChange} />);
    expect(screen.getByText('Helper text')).toBeInTheDocument();
  });

  it('renders with autoSize prop', () => {
    const { container } = render(<Textarea autoSize onChange={mockOnChange} />);
    const textarea = container.querySelector('textarea');
    expect(textarea).toBeInTheDocument();
  });

  it('renders with custom minRows and maxRows', () => {
    const { container } = render(<Textarea minRows={2} maxRows={8} onChange={mockOnChange} />);
    const textarea = container.querySelector('textarea');
    expect(textarea?.getAttribute('rows')).toBe('2');
  });
});
