import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { SessionSidebar } from '../SessionSidebar';

const mocks = vi.hoisted(() => ({
  refresh: vi.fn(),
  setActiveSession: vi.fn(),
  listAgents: vi.fn(),
  listModels: vi.fn(),
}));

vi.mock('../../../store/workspace', () => ({
  useWorkspaceStore: (selector: (state: object) => unknown) => selector({
    activeSessionId: null,
    setActiveSession: mocks.setActiveSession,
  }),
}));

vi.mock('../../../hooks/useSessions', () => ({
  useSessions: () => ({
    sessions: [],
    loading: false,
    error: 'Network request failed',
    createSession: vi.fn(),
    deleteSession: vi.fn(),
    renameSession: vi.fn(),
    refresh: mocks.refresh,
  }),
}));

vi.mock('../../../api', () => ({
  api: {
    listAgents: mocks.listAgents,
    listModels: mocks.listModels,
  },
}));

describe('SessionSidebar loading errors', () => {
  beforeEach(() => {
    mocks.refresh.mockReset();
    mocks.listAgents.mockResolvedValue([]);
    mocks.listModels.mockResolvedValue([]);
  });

  it('shows a retryable error instead of an empty state', async () => {
    const user = userEvent.setup();
    render(<SessionSidebar />);

    expect(await screen.findByText('加载会话失败')).toBeInTheDocument();
    expect(screen.queryByText('暂无会话')).not.toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: '重试加载会话' }));

    expect(mocks.refresh).toHaveBeenCalledTimes(1);
  });
});
