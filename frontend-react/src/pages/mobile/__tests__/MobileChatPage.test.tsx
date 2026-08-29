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
  it('renders a clear session action when no session is selected', () => {
    render(<MobileChatPage />);
    expect(screen.getByText('需要先创建会话')).toBeDefined();
    expect(screen.getByRole('button', { name: '新建会话' })).toBeDefined();
  });

  it('hides conversation actions until a session is selected', () => {
    render(<MobileChatPage />);
    expect(screen.queryByText('帮我分析代码')).toBeNull();
    expect(screen.queryByRole('textbox', { name: '消息输入框' })).toBeNull();
  });
});
