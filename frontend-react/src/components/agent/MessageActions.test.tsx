import { act, cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { MessageActions } from './MessageActions';

const writeText = vi.fn().mockResolvedValue(undefined);

beforeEach(() => {
  writeText.mockClear();
  Object.defineProperty(navigator, 'clipboard', {
    configurable: true,
    value: { writeText },
  });
});

afterEach(() => {
  cleanup();
  vi.useRealTimers();
  vi.restoreAllMocks();
});

describe('MessageActions', () => {
  it('copies the message content to the clipboard', () => {
    render(<MessageActions content="hello world" />);
    fireEvent.click(screen.getByRole('button', { name: 'Copy' }));
    expect(writeText).toHaveBeenCalledWith('hello world');
  });

  it('shows a checkmark for two seconds and then reverts', () => {
    vi.useFakeTimers();
    render(<MessageActions content="hello" />);
    fireEvent.click(screen.getByRole('button', { name: 'Copy' }));
    expect(screen.getByTestId('message-copy-check')).toBeInTheDocument();

    act(() => vi.advanceTimersByTime(1999));
    expect(screen.getByTestId('message-copy-check')).toBeInTheDocument();

    act(() => vi.advanceTimersByTime(1));
    expect(screen.queryByTestId('message-copy-check')).not.toBeInTheDocument();
  });

  it('renders edit and regenerate only when their callbacks are given', () => {
    const onEdit = vi.fn();
    const onRegenerate = vi.fn();
    const { rerender } = render(<MessageActions content="x" />);
    expect(screen.queryByRole('button', { name: 'Edit' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Regenerate' })).not.toBeInTheDocument();

    rerender(<MessageActions content="x" onEdit={onEdit} onRegenerate={onRegenerate} />);
    fireEvent.click(screen.getByRole('button', { name: 'Edit' }));
    fireEvent.click(screen.getByRole('button', { name: 'Regenerate' }));
    expect(onEdit).toHaveBeenCalledTimes(1);
    expect(onRegenerate).toHaveBeenCalledTimes(1);
  });

  it('reveals the row on hover through the group contract', () => {
    render(<MessageActions content="x" data-testid="actions" />);
    expect(screen.getByTestId('actions').className).toContain('group-hover/message:opacity-100');
  });

  it('clears its revert timer on unmount', () => {
    vi.useFakeTimers();
    const { unmount } = render(<MessageActions content="x" />);
    fireEvent.click(screen.getByRole('button', { name: 'Copy' }));
    unmount();
    expect(vi.getTimerCount()).toBe(0);
  });

  it('still confirms when the clipboard is blocked', () => {
    writeText.mockImplementationOnce(() => {
      throw new Error('denied');
    });
    render(<MessageActions content="x" />);
    fireEvent.click(screen.getByRole('button', { name: 'Copy' }));
    expect(screen.getByTestId('message-copy-check')).toBeInTheDocument();
  });
});
