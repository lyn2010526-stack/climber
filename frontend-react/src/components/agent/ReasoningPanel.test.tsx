import { act, cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { ReasoningPanel } from './ReasoningPanel';

beforeEach(() => {
  vi.useFakeTimers();
  vi.setSystemTime(new Date('2026-01-01T00:00:00Z'));
});

afterEach(() => {
  cleanup();
  vi.useRealTimers();
  vi.restoreAllMocks();
});

describe('ReasoningPanel', () => {
  it('opens itself while streaming and follows the text', () => {
    render(<ReasoningPanel text="step one" active />);
    expect(screen.getByTestId('reasoning-content')).toHaveTextContent('step one');
    expect(screen.getByTestId('reasoning-label')).toHaveTextContent('Thinking...');
  });

  it('records the duration and collapses once streaming ends', () => {
    const { rerender } = render(<ReasoningPanel text="step one" active />);
    act(() => vi.advanceTimersByTime(3000));

    rerender(<ReasoningPanel text="step one step two" active={false} />);
    expect(screen.getByTestId('reasoning-content')).toBeInTheDocument();
    expect(screen.getByTestId('reasoning-label')).toHaveTextContent('Thought for 3 seconds');

    act(() => vi.advanceTimersByTime(1000));
    expect(screen.queryByTestId('reasoning-content')).not.toBeInTheDocument();
    expect(screen.getByTestId('reasoning-label')).toHaveTextContent('Thought for 3 seconds');
  });

  it('has a collapsed aria state that tracks the toggle', () => {
    render(<ReasoningPanel text="thought" active={false} defaultOpen />);
    const trigger = screen.getByRole('button');
    expect(trigger).toHaveAttribute('aria-expanded', 'true');
    fireEvent.click(trigger);
    expect(screen.getByRole('button')).toHaveAttribute('aria-expanded', 'false');
  });

  it('respects an explicit closed default while still measuring', () => {
    const { rerender } = render(<ReasoningPanel text="t" active defaultOpen={false} />);
    expect(screen.queryByTestId('reasoning-content')).not.toBeInTheDocument();
    act(() => vi.advanceTimersByTime(2000));
    rerender(<ReasoningPanel text="t done" active={false} defaultOpen={false} />);
    expect(screen.getByTestId('reasoning-label')).toHaveTextContent('Thought for 2 seconds');
  });

  it('falls back to a durationless label when the run was too short to measure', () => {
    render(<ReasoningPanel text="t" active={false} defaultOpen />);
    expect(screen.getByTestId('reasoning-label')).toHaveTextContent('Thought for a few seconds');
  });
});
