import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';

vi.mock('../../useChat', () => ({
  useChat: () => ({
    messages: [],
    isStreaming: false,
    error: null,
    sendMessage: vi.fn(),
    stopStreaming: vi.fn(),
  }),
}));

vi.mock('../../store/workspace', () => ({
  useWorkspaceStore: vi.fn((selector: any) => {
    if (typeof selector === 'function') {
      return selector({ activeSessionId: 'session-1' });
    }
    return { activeSessionId: 'session-1' };
  }),
}));

import { ChatPage } from '../ChatPage';

describe('ChatPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders without crashing', () => {
    const { container } = render(
      <MemoryRouter>
        <ChatPage />
      </MemoryRouter>
    );
    expect(container).toBeDefined();
  });

  it('renders chat interface', () => {
    render(
      <MemoryRouter>
        <ChatPage />
      </MemoryRouter>
    );
    expect(screen.getByText('开始新的对话')).toBeDefined();
  });

  it('renders empty state description', () => {
    render(
      <MemoryRouter>
        <ChatPage />
      </MemoryRouter>
    );
    expect(screen.getByText('输入任何问题或任务，Climber 将为你自主执行。')).toBeDefined();
  });
});
