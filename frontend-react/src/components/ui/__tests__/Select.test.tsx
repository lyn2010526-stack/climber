import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { Select } from '../Select';

describe('Select', () => {
  const mockOnChange = vi.fn();

  beforeEach(() => {
    mockOnChange.mockClear();
  });

  it('renders select element', () => {
    render(
      <Select
        value=""
        onChange={mockOnChange}
        options={[
          { value: '1', label: 'Option 1' },
          { value: '2', label: 'Option 2' },
        ]}
      />
    );
    expect(screen.getByText('请选择...')).toBeInTheDocument();
  });

  it('displays selected option', () => {
    render(
      <Select
        value="1"
        onChange={mockOnChange}
        options={[
          { value: '1', label: 'Option 1' },
          { value: '2', label: 'Option 2' },
        ]}
      />
    );
    expect(screen.getByText('Option 1')).toBeInTheDocument();
  });

  it('applies sm size classes correctly', () => {
    const { container } = render(
      <Select value="" size="sm" onChange={mockOnChange} options={[{ value: '1', label: 'Option' }]} />
    );
    const trigger = container.querySelector('.h-8');
    expect(trigger).toBeInTheDocument();
  });

  it('applies md size by default', () => {
    const { container } = render(
      <Select value="" onChange={mockOnChange} options={[{ value: '1', label: 'Option' }]} />
    );
    const trigger = container.querySelector('.h-10');
    expect(trigger).toBeInTheDocument();
  });

  it('applies lg size classes when specified', () => {
    const { container } = render(
      <Select value="" size="lg" onChange={mockOnChange} options={[{ value: '1', label: 'Option' }]} />
    );
    const trigger = container.querySelector('.h-11');
    expect(trigger).toBeInTheDocument();
  });

  it('applies disabled class when disabled prop is true', () => {
    const { container } = render(
      <Select
        value=""
        disabled
        onChange={mockOnChange}
        options={[{ value: '1', label: 'Option' }]}
      />
    );
    const trigger = container.querySelector('.opacity-50');
    expect(trigger).toBeInTheDocument();
  });

  it('applies custom className', () => {
    const { container } = render(
      <Select
        value=""
        className="custom-select-class"
        onChange={mockOnChange}
        options={[{ value: '1', label: 'Option' }]}
      />
    );
    const trigger = container.querySelector('.custom-select-class');
    expect(trigger).toBeInTheDocument();
  });

  it('opens dropdown when clicked', () => {
    render(
      <Select
        value=""
        onChange={mockOnChange}
        options={[
          { value: '1', label: 'Option 1' },
          { value: '2', label: 'Option 2' },
        ]}
      />
    );
    const trigger = screen.getByText('请选择...');
    fireEvent.click(trigger);
    expect(screen.getByText('Option 1')).toBeInTheDocument();
    expect(screen.getByText('Option 2')).toBeInTheDocument();
  });

  it('calls onChange when option is selected', () => {
    render(
      <Select
        value=""
        onChange={mockOnChange}
        options={[
          { value: '1', label: 'Option 1' },
          { value: '2', label: 'Option 2' },
        ]}
      />
    );
    const trigger = screen.getByText('请选择...');
    fireEvent.click(trigger);
    fireEvent.click(screen.getByText('Option 1'));
    expect(mockOnChange).toHaveBeenCalledWith('1');
  });

  it('renders with placeholder', () => {
    render(
      <Select value="" onChange={mockOnChange} placeholder="Pick one" options={[{ value: '1', label: 'Option 1' }]} />
    );
    expect(screen.getByText('Pick one')).toBeInTheDocument();
  });

  it('supports multiple selection', () => {
    render(
      <Select
        multiple
        value={[]}
        onChange={mockOnChange}
        options={[
          { value: '1', label: 'One' },
          { value: '2', label: 'Two' },
        ]}
      />
    );
    const trigger = screen.getByText('请选择...');
    fireEvent.click(trigger);
    fireEvent.click(screen.getByText('One'));
    expect(mockOnChange).toHaveBeenCalledWith(['1']);
  });

  it('renders with leftIcon', () => {
    const { container } = render(
      <Select
        value=""
        onChange={mockOnChange}
        leftIcon={<span data-testid="left-icon">Icon</span>}
        options={[{ value: '1', label: 'Option' }]}
      />
    );
    expect(container.querySelector('[data-testid="left-icon"]')).toBeInTheDocument();
  });

  it('shows error message when error prop is provided', () => {
    render(
      <Select value="" error="Required" onChange={mockOnChange} options={[{ value: '1', label: 'Option' }]} />
    );
    expect(screen.getByText('Required')).toBeInTheDocument();
  });

  it('shows hint message when hint prop is provided', () => {
    render(
      <Select value="" hint="Helper text" onChange={mockOnChange} options={[{ value: '1', label: 'Option' }]} />
    );
    expect(screen.getByText('Helper text')).toBeInTheDocument();
  });

  it('renders without errors when minimal props provided', () => {
    const { container } = render(<Select value="" onChange={mockOnChange} options={[{ value: '1', label: 'Option' }]} />);
    expect(container.firstChild).toBeInTheDocument();
  });

  it('supports grouped options', () => {
    render(
      <Select
        value=""
        onChange={mockOnChange}
        groups={[
          {
            label: 'Group 1',
            options: [
              { value: '1', label: 'Option 1' },
              { value: '2', label: 'Option 2' },
            ],
          },
        ]}
      />
    );
    const trigger = screen.getByText('请选择...');
    fireEvent.click(trigger);
    expect(screen.getByText('Group 1')).toBeInTheDocument();
    expect(screen.getByText('Option 1')).toBeInTheDocument();
  });
});
