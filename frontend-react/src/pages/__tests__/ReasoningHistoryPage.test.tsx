import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ReasoningHistoryPage } from '../ReasoningHistoryPage';

const apiMocks = vi.hoisted(() => ({
  listReasoningHistory: vi.fn(),
}));

vi.mock('../../api', () => ({ api: apiMocks }));

describe('ReasoningHistoryPage loading errors', () => {
  beforeEach(() => {
    apiMocks.listReasoningHistory.mockReset();
  });

  it('shows a retryable error instead of an empty history when loading fails', async () => {
    const user = userEvent.setup();
    apiMocks.listReasoningHistory
      .mockRejectedValueOnce(new Error('Service unavailable'))
      .mockResolvedValueOnce([]);

    render(<ReasoningHistoryPage />);

    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent('加载推理历史失败');
    expect(screen.queryByText('暂无推理历史。')).not.toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: '重试加载推理历史' }));

    expect(await screen.findByText('暂无推理历史。')).toBeInTheDocument();
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    expect(apiMocks.listReasoningHistory).toHaveBeenCalledTimes(2);
  });
});
