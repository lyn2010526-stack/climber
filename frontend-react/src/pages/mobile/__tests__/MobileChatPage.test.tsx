import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MobileChatPage } from '../../MobileChatPage';

vi.mock('../../hooks/useChat', () => ({
  useChat: () => ({
    messages: [],
    isStreaming: false,
    error: null,
    sendMessage: vi.fn(),
    stopStreaming: vi.fn(),
  }),
}));

vi.mock('../../store/workspace', () => ({
  useWorkspaceStore: () => ({
    activeSessionId: 'test-session',
    sessions: [],
  }),
}));

describe('MobileChatPage', () => {
  it('renders chat interface', () => {
    render(<MobileChatPage />);
    expect(screen.getByText('开始新的对话')).toBeDefined();
  });

  it('renders suggestion chips', () => {
    render(<MobileChatPage />);
    expect(screen.getByText('帮我分析代码')).toBeDefined();
  });
});
