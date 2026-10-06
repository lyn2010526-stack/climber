import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { ChatStreamError, ChatStreamSkeleton } from '../ChatStreamStates';

describe('ChatStreamSkeleton', () => {
  it('renders the requested number of skeleton rows as a busy status region', () => {
    render(<ChatStreamSkeleton rows={4} />);
    const region = screen.getByRole('status');
    expect(region).toHaveAttribute('aria-busy', 'true');
    expect(screen.getAllByTestId('chat-skeleton-row')).toHaveLength(4);
  });

  it('defaults to three rows and honours a custom testid', () => {
    render(<ChatStreamSkeleton data-testid="my-skeleton" />);
    expect(screen.getByTestId('my-skeleton')).toBeInTheDocument();
    expect(screen.getAllByTestId('chat-skeleton-row')).toHaveLength(3);
  });
});

describe('ChatStreamError', () => {
  it('announces the message as an alert and renders the status dot', () => {
    render(<ChatStreamError message="stream failed" />);
    const alert = screen.getByRole('alert');
    expect(alert).toHaveTextContent('stream failed');
    expect(alert.querySelector('[class*=statusDot]')).not.toBeNull();
  });

  it('fires the retry callback unless disabled', async () => {
    const user = userEvent.setup();
    const onRetry = vi.fn();
    const { rerender } = render(<ChatStreamError message="boom" onRetry={onRetry} />);
    await user.click(screen.getByRole('button', { name: /重试|Retry/i }));
    expect(onRetry).toHaveBeenCalledTimes(1);
    rerender(<ChatStreamError message="boom" onRetry={onRetry} retryDisabled />);
    expect(screen.getByRole('button', { name: /重试|Retry/i })).toBeDisabled();
  });

  it('omits the retry button when no callback is given', () => {
    render(<ChatStreamError message="boom" />);
    expect(screen.queryByRole('button')).toBeNull();
  });
});
