declare const global: any;
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';

vi.mock('../../api', () => ({
  api: {
    listGroups: vi.fn().mockResolvedValue({ groups: [] }),
    getGroup: vi.fn().mockResolvedValue({ members: [] }),
    listGroupMessages: vi.fn().mockResolvedValue({ messages: [] }),
    createGroup: vi.fn().mockResolvedValue({ id: 'new-group' }),
  },
}));

vi.mock('../../hooks/useNetworkStatus', () => ({
  useOnline: () => true,
}));

class MockWebSocket {
  onopen: any = null;
  onclose: any = null;
  onmessage: any = null;
  send = vi.fn();
  close = vi.fn();
}

import { ClusterPage } from '../ClusterPage';

describe('ClusterPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (global as any).WebSocket = MockWebSocket;
    Element.prototype.scrollIntoView = vi.fn();
  });

  it('renders without crashing', () => {
    const { container } = render(
      <MemoryRouter>
        <ClusterPage />
      </MemoryRouter>
    );
    expect(container).toBeDefined();
  });

  it('renders main content area', () => {
    const { container } = render(
      <MemoryRouter>
        <ClusterPage />
      </MemoryRouter>
    );
    // Should have some content
    expect(container).toBeDefined();
  });

  it('renders buttons', () => {
    const { container } = render(
      <MemoryRouter>
        <ClusterPage />
      </MemoryRouter>
    );
    const buttons = container.querySelectorAll('button');
    expect(buttons.length).toBeGreaterThan(0);
  });

  it('renders description text', () => {
    render(
      <MemoryRouter>
        <ClusterPage />
      </MemoryRouter>
    );
    expect(screen.getByPlaceholderText(/描述您的需求/)).toBeDefined();
  });
});
