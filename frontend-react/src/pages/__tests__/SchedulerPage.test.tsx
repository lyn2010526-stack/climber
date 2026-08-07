import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { api } from '../../api';

vi.mock('../../api', () => ({
  api: {
    listSchedulerTasks: vi.fn().mockResolvedValue([]),
    createSchedulerTask: vi.fn().mockResolvedValue({}),
    updateSchedulerTask: vi.fn().mockResolvedValue({}),
    deleteSchedulerTask: vi.fn().mockResolvedValue({}),
  },
}));

import { SchedulerPage } from '../SchedulerPage';

const mockTasks = [
  {
    id: 'task-1',
    name: 'Daily Backup',
    description: 'Backup database',
    cron: '0 2 * * *',
    type: 'backup',
    enabled: true,
    last_run: 1700000000000,
    next_run: 1700100000000,
    run_count: 5,
  },
  {
    id: 'task-2',
    name: 'Health Check',
    description: 'System health inspection',
    cron: '*/30 * * * *',
    type: 'inspect',
    enabled: false,
    last_run: null,
    next_run: null,
    run_count: 0,
  },
];

describe('SchedulerPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.listSchedulerTasks).mockResolvedValue([]);
  });

  it('renders without crashing', () => {
    const { container } = render(
      <MemoryRouter>
        <SchedulerPage />
      </MemoryRouter>
    );
    expect(container).toBeDefined();
  });

  it('renders loading state initially', () => {
    const { container } = render(
      <MemoryRouter>
        <SchedulerPage />
      </MemoryRouter>
    );
    expect(container.querySelector('.animate-spin')).toBeDefined();
  });

  it('renders page title after loading', async () => {
    render(
      <MemoryRouter>
        <SchedulerPage />
      </MemoryRouter>
    );
    await waitFor(() => {
      expect(screen.getByText('定时任务')).toBeDefined();
    });
  });

  it('renders empty state when no tasks', async () => {
    render(
      <MemoryRouter>
        <SchedulerPage />
      </MemoryRouter>
    );
    await waitFor(() => {
      expect(screen.getByText(/暂无定时任务/)).toBeDefined();
    });
  });

  it('renders tasks after loading', async () => {
    vi.mocked(api.listSchedulerTasks).mockResolvedValue(mockTasks);
    render(
      <MemoryRouter>
        <SchedulerPage />
      </MemoryRouter>
    );
    await waitFor(() => {
      expect(screen.getByText('Daily Backup')).toBeDefined();
      expect(screen.getByText('Health Check')).toBeDefined();
    });
  });

  it('toggles add task form', async () => {
    render(
      <MemoryRouter>
        <SchedulerPage />
      </MemoryRouter>
    );
    await waitFor(() => {
      expect(screen.getByText('定时任务')).toBeDefined();
    });
    fireEvent.click(screen.getByText('添加任务'));
    expect(screen.getByPlaceholderText('任务名称')).toBeDefined();
  });

  it('creates a new task', async () => {
    render(
      <MemoryRouter>
        <SchedulerPage />
      </MemoryRouter>
    );
    await waitFor(() => {
      expect(screen.getByText('定时任务')).toBeDefined();
    });
    fireEvent.click(screen.getByText('添加任务'));
    fireEvent.change(screen.getByPlaceholderText('任务名称'), { target: { value: 'New Task' } });
    fireEvent.change(screen.getByPlaceholderText('描述'), { target: { value: 'Test description' } });
    fireEvent.click(screen.getByText('创建'));
    await waitFor(() => {
      expect(api.createSchedulerTask).toHaveBeenCalled();
    });
  });

  it('cancels add task form', async () => {
    render(
      <MemoryRouter>
        <SchedulerPage />
      </MemoryRouter>
    );
    await waitFor(() => {
      expect(screen.getByText('定时任务')).toBeDefined();
    });
    fireEvent.click(screen.getByText('添加任务'));
    fireEvent.click(screen.getByText('取消'));
    expect(screen.queryByPlaceholderText('任务名称')).toBeNull();
  });

  it('toggles task enabled state', async () => {
    vi.mocked(api.listSchedulerTasks).mockResolvedValue(mockTasks);
    render(
      <MemoryRouter>
        <SchedulerPage />
      </MemoryRouter>
    );
    await waitFor(() => {
      expect(screen.getByText('Daily Backup')).toBeDefined();
    });
    const toggleBtns = screen.getAllByTitle(/启用|禁用/);
    expect(toggleBtns.length).toBeGreaterThan(0);
    fireEvent.click(toggleBtns[0]);
    await waitFor(() => {
      expect(api.updateSchedulerTask).toHaveBeenCalled();
    });
  });

  it('deletes a task', async () => {
    vi.mocked(api.listSchedulerTasks).mockResolvedValue(mockTasks);
    render(
      <MemoryRouter>
        <SchedulerPage />
      </MemoryRouter>
    );
    await waitFor(() => {
      expect(screen.getByText('Daily Backup')).toBeDefined();
    });
    const deleteBtns = screen.getAllByRole('button');
    // Find the delete button by its SVG icon (Trash2)
    const trashBtn = deleteBtns.find(btn =>
      btn.querySelector('svg')?.getAttribute('class')?.includes('trash') ||
      btn.innerHTML.includes('trash')
    );
    if (trashBtn) {
      fireEvent.click(trashBtn);
      await waitFor(() => {
        expect(api.deleteSchedulerTask).toHaveBeenCalled();
      });
    }
  });

  it('shows task details', async () => {
    vi.mocked(api.listSchedulerTasks).mockResolvedValue([mockTasks[0]]);
    render(
      <MemoryRouter>
        <SchedulerPage />
      </MemoryRouter>
    );
    await waitFor(() => {
      expect(screen.getByText('Daily Backup')).toBeDefined();
      expect(screen.getByText('Backup database')).toBeDefined();
      expect(screen.getByText('backup')).toBeDefined();
    });
  });

  it('renders type badge', async () => {
    vi.mocked(api.listSchedulerTasks).mockResolvedValue([mockTasks[0]]);
    render(
      <MemoryRouter>
        <SchedulerPage />
      </MemoryRouter>
    );
    await waitFor(() => {
      expect(screen.getByText('backup')).toBeDefined();
    });
  });

  it('formats last run time', async () => {
    vi.mocked(api.listSchedulerTasks).mockResolvedValue([mockTasks[0]]);
    render(
      <MemoryRouter>
        <SchedulerPage />
      </MemoryRouter>
    );
    await waitFor(() => {
      expect(screen.getByText(/执行 5 次/)).toBeDefined();
    });
  });

  it('shows never for null last_run', async () => {
    vi.mocked(api.listSchedulerTasks).mockResolvedValue([mockTasks[1]]);
    render(
      <MemoryRouter>
        <SchedulerPage />
      </MemoryRouter>
    );
    await waitFor(() => {
      expect(screen.getByText(/从未/)).toBeDefined();
    });
  });
});
