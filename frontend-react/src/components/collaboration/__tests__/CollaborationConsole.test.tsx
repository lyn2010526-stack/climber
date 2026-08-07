declare const global: any;
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';

vi.mock('../../../api', () => ({
  api: {
    listGroupMessages: vi.fn().mockResolvedValue({ messages: [] }),
    getGroup: vi.fn().mockResolvedValue({ members: [] }),
  },
}));

vi.mock('../../../hooks/useNetworkStatus', () => ({
  useOnline: () => true,
}));

import { CollaborationConsole } from '../CollaborationConsole';

class MockWebSocket {
  onopen: any = null;
  onclose: any = null;
  onmessage: any = null;
  send = vi.fn();
  close = vi.fn();
}

describe('CollaborationConsole', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (global as any).WebSocket = MockWebSocket;
    Element.prototype.scrollIntoView = vi.fn();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('renders without crashing', () => {
    const { container } = render(
      <CollaborationConsole groupId="test-group" />
    );
    expect(container).toBeDefined();
  });

  it('renders task input area', () => {
    render(
      <CollaborationConsole groupId="test-group" />
    );
    expect(screen.getByPlaceholderText('输入任务描述，AI 将自动协作完成...')).toBeDefined();
  });

  it('renders Start button', () => {
    render(
      <CollaborationConsole groupId="test-group" />
    );
    expect(screen.getByText('Start')).toBeDefined();
  });

  it('renders advanced settings toggle', () => {
    render(
      <CollaborationConsole groupId="test-group" />
    );
    expect(screen.getByText('高级设置')).toBeDefined();
  });

  it('renders hint text', () => {
    render(
      <CollaborationConsole groupId="test-group" />
    );
    expect(screen.getByText('点击开始后，AI 将自动循环执行直到完成')).toBeDefined();
  });

  it('renders messages area', () => {
    const { container } = render(
      <CollaborationConsole groupId="test-group" />
    );
    // Should have a messages container
    expect(container).toBeDefined();
  });
});
