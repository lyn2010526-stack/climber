import { act, cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { api } from '../../api';
import { ThinkingLevelSelect } from './ThinkingLevelSelect';

vi.mock('../../api', () => ({
  api: {
    getThinkingLevels: vi.fn().mockResolvedValue({ levels: [{ id: 'low' }, { id: 'medium' }, { id: 'high' }] }),
    getSessionThinkingLevel: vi.fn().mockResolvedValue({ level: 'medium' }),
    updateSessionThinkingLevel: vi.fn(),
  },
}));

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe('ThinkingLevelSelect', () => {
  it('shows the current level description and rolls back a failed optimistic update', async () => {
    vi.mocked(api.updateSessionThinkingLevel).mockRejectedValueOnce(new Error('save failed'));
    render(<ThinkingLevelSelect sessionId="session-1" />);

    await screen.findByText('Medium: balanced speed and depth (default)');
    expect(screen.getByRole('button', { name: 'Medium' })).toHaveAttribute('aria-pressed', 'true');

    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: 'High' }));
    });

    expect(screen.getByRole('button', { name: 'Medium' })).toHaveAttribute('aria-pressed', 'true');
    expect(screen.getByRole('alert')).toHaveTextContent('Failed to save the thinking level, try again');
  });
});
