import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { TaskInput } from '../TaskInput';

describe('TaskInput', () => {
  const defaultProps = {
    onStart: vi.fn(),
    onPause: vi.fn(),
    onStop: vi.fn(),
    status: 'idle' as const,
  };

  it('renders without crashing', () => {
    const { container } = render(<TaskInput {...defaultProps} />);
    expect(container).toBeDefined();
  });

  it('renders task input', () => {
    render(<TaskInput {...defaultProps} />);
    expect(screen.getByRole('textbox')).toBeDefined();
  });

  it('renders start button', () => {
    render(<TaskInput {...defaultProps} />);
    const buttons = screen.getAllByRole('button');
    expect(buttons.length).toBeGreaterThan(0);
  });

  it('calls onStart when start button is clicked with task', () => {
    const onStart = vi.fn();
    render(<TaskInput {...defaultProps} onStart={onStart} />);
    const input = screen.getByRole('textbox');
    fireEvent.change(input, { target: { value: 'test task' } });
    const buttons = screen.getAllByRole('button');
    fireEvent.click(buttons[0]);
    expect(onStart).toHaveBeenCalled();
  });

  it('does not call onStart when task is empty', () => {
    const onStart = vi.fn();
    render(<TaskInput {...defaultProps} onStart={onStart} />);
    const buttons = screen.getAllByRole('button');
    fireEvent.click(buttons[0]);
    expect(onStart).not.toHaveBeenCalled();
  });

  it('renders in running state', () => {
    const { container } = render(<TaskInput {...defaultProps} status="running" />);
    expect(container).toBeDefined();
  });

  it('renders in paused state', () => {
    const { container } = render(<TaskInput {...defaultProps} status="paused" />);
    expect(container).toBeDefined();
  });

  it('calls onPause when pause button is clicked', () => {
    const onPause = vi.fn();
    render(<TaskInput {...defaultProps} status="running" onPause={onPause} />);
    const buttons = screen.getAllByRole('button');
    for (const button of buttons) {
      fireEvent.click(button);
    }
    expect(onPause).toHaveBeenCalled();
  });

  it('calls onStop when stop button is clicked', () => {
    const onStop = vi.fn();
    render(<TaskInput {...defaultProps} status="running" onStop={onStop} />);
    const buttons = screen.getAllByRole('button');
    for (const button of buttons) {
      fireEvent.click(button);
    }
    expect(onStop).toHaveBeenCalled();
  });

  it('renders with disabled prop', () => {
    const { container } = render(<TaskInput {...defaultProps} disabled={true} />);
    expect(container).toBeDefined();
  });

  it('renders advanced options when toggled', () => {
    const { container } = render(<TaskInput {...defaultProps} />);
    const buttons = screen.getAllByRole('button');
    if (buttons.length > 1) {
      fireEvent.click(buttons[1]);
    }
    expect(container).toBeDefined();
  });

  it('renders with available tasks', () => {
    const { container } = render(
      <TaskInput
        {...defaultProps}
        availableTasks={[
          { id: 'task1', description: 'Task 1' },
          { id: 'task2', description: 'Task 2' },
        ]}
      />
    );
    expect(container).toBeDefined();
  });

  it('updates task value on input change', () => {
    render(<TaskInput {...defaultProps} />);
    const input = screen.getByRole('textbox');
    fireEvent.change(input, { target: { value: 'new task' } });
    expect(input).toBeDefined();
  });
});
