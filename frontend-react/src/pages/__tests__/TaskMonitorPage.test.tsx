declare const global: any;
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { api } from '../../api';

vi.mock('../../api', () => ({
  api: {
    listTasks: vi.fn().mockResolvedValue([]),
    getTask: vi.fn().mockResolvedValue({ steps: [] }),
    listGroups: vi.fn().mockResolvedValue([]),
    createTask: vi.fn().mockResolvedValue({ id: 'task-1' }),
    stopTask: vi.fn().mockResolvedValue({}),
  },
}));

class MockWebSocket {
  onopen: any = null;
  onclose: any = null;
  onmessage: any = null;
  send = vi.fn();
  close = vi.fn();
}

import TaskMonitorPage from '../TaskMonitorPage';

describe('TaskMonitorPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (global as any).WebSocket = MockWebSocket;
  });

  it('renders without crashing', () => {
    const { container } = render(
      <MemoryRouter>
        <TaskMonitorPage />
      </MemoryRouter>
    );
    expect(container).toBeDefined();
  });

  it('renders title', () => {
    const { container } = render(
      <MemoryRouter>
        <TaskMonitorPage />
      </MemoryRouter>
    );
    expect(container.querySelector('h2')?.textContent).toContain('自主任务');
  });

  it('renders empty state after loading', async () => {
    const { container } = render(
      <MemoryRouter>
        <TaskMonitorPage />
      </MemoryRouter>
    );
    await waitFor(() => {
      expect(container.textContent).toContain('暂无任务');
    });
  });

  it('fetches tasks on mount', async () => {
    render(
      <MemoryRouter>
        <TaskMonitorPage />
      </MemoryRouter>
    );
    await waitFor(() => {
      expect(api.listTasks).toHaveBeenCalled();
    });
  });
});
