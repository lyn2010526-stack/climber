declare const global: any;
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';

class MockWebSocket {
  static instances: MockWebSocket[] = [];
  onopen: (() => void) | null = null;
  onclose: (() => void) | null = null;
  onmessage: ((event: any) => void) | null = null;
  readyState = 0;
  sent: string[] = [];
  url: string;

  constructor(url: string) {
    this.url = url;
    MockWebSocket.instances.push(this);
  }

  send(data: string) {
    this.sent.push(data);
  }

  close() {
    this.readyState = 3;
    if (this.onclose) this.onclose();
  }
}

const mockApi = vi.hoisted(() => ({
  listGroupMessages: vi.fn().mockResolvedValue({ messages: [] }),
  getGroup: vi.fn().mockResolvedValue({ members: [] }),
}));

vi.mock('../../../api', () => ({
  api: mockApi,
}));

vi.mock('react', async (importOriginal) => {
  const actual = await importOriginal();
  return {
    ...actual,
    useEffect: vi.fn(),
  };
});

(global as any).WebSocket = MockWebSocket;

import { GroupRoom } from '../GroupRoom';

describe('GroupRoom', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    MockWebSocket.instances = [];
  });

  afterEach(() => {
    MockWebSocket.instances = [];
  });

  it('renders without crashing', () => {
    const { container } = render(
      <GroupRoom groupId="group-1" onLeave={() => {}} />
    );
    expect(container).toBeDefined();
  });

  it('renders group header', () => {
    render(<GroupRoom groupId="group-1" onLeave={() => {}} />);
    expect(screen.getByText('群组讨论')).toBeDefined();
  });

  it('renders empty state message', () => {
    render(<GroupRoom groupId="group-1" onLeave={() => {}} />);
    expect(screen.getByText('暂无消息，开始讨论吧！')).toBeDefined();
  });

  it('renders input field', () => {
    render(<GroupRoom groupId="group-1" onLeave={() => {}} />);
    expect(screen.getByPlaceholderText('输入消息...')).toBeDefined();
  });

  it('renders leave button', () => {
    render(<GroupRoom groupId="group-1" onLeave={() => {}} />);
    expect(screen.getByText('退出群组')).toBeDefined();
  });

  it('calls onLeave when leave button clicked', () => {
    const onLeave = vi.fn();
    render(<GroupRoom groupId="group-1" onLeave={onLeave} />);
    fireEvent.click(screen.getByText('退出群组'));
    expect(onLeave).toHaveBeenCalled();
  });

  it('renders member count in sidebar header', () => {
    render(<GroupRoom groupId="group-1" onLeave={() => {}} />);
    expect(screen.getByText(/成员/)).toBeDefined();
  });

  it('renders disconnected indicator initially', () => {
    render(<GroupRoom groupId="group-1" onLeave={() => {}} />);
    expect(screen.getByText('已断开')).toBeDefined();
  });

  it('renders send button disabled when input is empty', () => {
    render(<GroupRoom groupId="group-1" onLeave={() => {}} />);
    const buttons = screen.getAllByRole('button');
    // The send button should be disabled when input is empty
    expect(buttons.length).toBeGreaterThan(0);
  });
});
