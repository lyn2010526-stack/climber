import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { ApprovalOverlay } from './ApprovalOverlay';

function renderOverlay(overrides: Partial<Parameters<typeof ApprovalOverlay>[0]> = {}) {
  const onSelect = vi.fn();
  const onCancel = vi.fn();
  render(
    <ApprovalOverlay
      title="需要批准"
      description="将运行以下命令"
      command="rm -rf build"
      onSelect={onSelect}
      onCancel={onCancel}
      {...overrides}
    />,
  );
  return { onSelect, onCancel };
}

describe('ApprovalOverlay', () => {
  it('renders the codex shape: bold title, command block and numbered options', () => {
    renderOverlay();
    const overlay = screen.getByTestId('approval-overlay');
    expect(overlay).toHaveAttribute('role', 'dialog');
    expect(screen.getByRole('heading', { level: 2 })).toHaveTextContent('需要批准');
    expect(screen.getByTestId('approval-command')).toHaveTextContent('$ rm -rf build');
    const first = screen.getByTestId('approval-option-approve');
    expect(first).toHaveTextContent('1.');
    expect(first).toHaveTextContent('(y)');
    expect(first).toHaveAttribute('aria-selected', 'true');
    expect(screen.getByTestId('approval-option-deny')).toHaveTextContent('(esc)');
  });

  it('uses surface-3 + bold as the REVERSED selected-row equivalent', () => {
    renderOverlay();
    expect(screen.getByTestId('approval-option-approve')).toHaveClass('bg-[var(--color-bg-surface-3)]', 'font-bold');
    expect(screen.getByTestId('approval-option-approve_all')).not.toHaveClass('font-bold');
  });

  it('moves selection with arrow keys and confirms with enter', () => {
    const { onSelect } = renderOverlay();
    const overlay = screen.getByTestId('approval-overlay');
    fireEvent.keyDown(overlay, { key: 'ArrowDown' });
    expect(screen.getByTestId('approval-option-approve_all')).toHaveAttribute('aria-selected', 'true');
    fireEvent.keyDown(overlay, { key: 'ArrowUp' });
    expect(screen.getByTestId('approval-option-approve')).toHaveAttribute('aria-selected', 'true');
    fireEvent.keyDown(overlay, { key: 'Enter' });
    expect(onSelect).toHaveBeenCalledWith('approve');
  });

  it('honours y/a shortcuts and esc cancel', () => {
    const { onSelect, onCancel } = renderOverlay();
    const overlay = screen.getByTestId('approval-overlay');
    fireEvent.keyDown(overlay, { key: 'a' });
    expect(onSelect).toHaveBeenCalledWith('approve_all');
    fireEvent.keyDown(overlay, { key: 'y' });
    expect(onSelect).toHaveBeenCalledWith('approve');
    fireEvent.keyDown(overlay, { key: 'Escape' });
    expect(onCancel).toHaveBeenCalledTimes(1);
  });

  it('traps tab focus inside the overlay and focuses it on mount', () => {
    renderOverlay();
    const overlay = screen.getByTestId('approval-overlay');
    expect(overlay).toHaveFocus();
    fireEvent.keyDown(overlay, { key: 'Tab' });
    expect(overlay).toHaveFocus();
  });

  it('accepts caller-supplied options', () => {
    const { onSelect } = renderOverlay({
      options: [{ id: 'only', label: '继续', shortcut: 'c' }],
    });
    fireEvent.keyDown(screen.getByTestId('approval-overlay'), { key: 'c' });
    expect(onSelect).toHaveBeenCalledWith('only');
  });
});
