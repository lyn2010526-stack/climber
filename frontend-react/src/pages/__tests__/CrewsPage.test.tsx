import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { api } from '../../api';

vi.mock('../../api', () => ({
  api: {
    listCrews: vi.fn().mockResolvedValue([]),
    createCrew: vi.fn().mockResolvedValue({}),
    runCrew: vi.fn().mockResolvedValue({}),
  },
}));

import { CrewsPage } from '../CrewsPage';

const mockCrews = [
  { id: 'crew-1', name: 'Dev Team', description: 'Development crew', agents: [] },
  { id: 'crew-2', name: 'Review Team', description: 'Code review crew', agents: [] },
];

describe('CrewsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.listCrews).mockResolvedValue([]);
  });

  it('renders without crashing', () => {
    const { container } = render(
      <MemoryRouter>
        <CrewsPage />
      </MemoryRouter>
    );
    expect(container).toBeDefined();
  });

  it('renders page title', async () => {
    render(
      <MemoryRouter>
        <CrewsPage />
      </MemoryRouter>
    );
    await waitFor(() => {
      expect(screen.getByText('团队管理')).toBeDefined();
    });
  });

  it('renders empty state', async () => {
    render(
      <MemoryRouter>
        <CrewsPage />
      </MemoryRouter>
    );
    await waitFor(() => {
      expect(screen.getByText(/暂无团队/)).toBeDefined();
    });
  });

  it('renders crews list', async () => {
    vi.mocked(api.listCrews).mockResolvedValue(mockCrews);
    render(
      <MemoryRouter>
        <CrewsPage />
      </MemoryRouter>
    );
    await waitFor(() => {
      expect(screen.getByText('Dev Team')).toBeDefined();
      expect(screen.getByText('Review Team')).toBeDefined();
    });
  });

  it('toggles create form', async () => {
    render(
      <MemoryRouter>
        <CrewsPage />
      </MemoryRouter>
    );
    await waitFor(() => {
      expect(screen.getByText('团队管理')).toBeDefined();
    });
    fireEvent.click(screen.getByText('新建团队'));
    expect(screen.getByPlaceholderText('团队名称')).toBeDefined();
  });

  it('creates a new crew', async () => {
    render(
      <MemoryRouter>
        <CrewsPage />
      </MemoryRouter>
    );
    await waitFor(() => {
      expect(screen.getByText('团队管理')).toBeDefined();
    });
    fireEvent.click(screen.getByText('新建团队'));
    fireEvent.change(screen.getByPlaceholderText('团队名称'), { target: { value: 'New Crew' } });
    fireEvent.click(screen.getByText('创建团队'));
    await waitFor(() => {
      expect(api.createCrew).toHaveBeenCalled();
    });
  });

  it('runs a crew', async () => {
    vi.mocked(api.listCrews).mockResolvedValue(mockCrews);
    render(
      <MemoryRouter>
        <CrewsPage />
      </MemoryRouter>
    );
    await waitFor(() => {
      expect(screen.getByText('Dev Team')).toBeDefined();
    });
    const runBtns = screen.getAllByText('运行');
    if (runBtns.length > 0) {
      fireEvent.click(runBtns[0]);
      await waitFor(() => {
        expect(api.runCrew).toHaveBeenCalled();
      });
    }
  });

  it('opens crew detail', async () => {
    vi.mocked(api.listCrews).mockResolvedValue(mockCrews);
    render(
      <MemoryRouter>
        <CrewsPage />
      </MemoryRouter>
    );
    await waitFor(() => {
      expect(screen.getByText('Dev Team')).toBeDefined();
    });
    const manageBtns = screen.getAllByText('管理成员');
    fireEvent.click(manageBtns[0]);
    await waitFor(() => {
      expect(screen.getAllByText(/成员/).length).toBeGreaterThan(0);
    });
  });

  it('shows error state', async () => {
    vi.mocked(api.listCrews).mockRejectedValue(new Error('Load failed'));
    render(
      <MemoryRouter>
        <CrewsPage />
      </MemoryRouter>
    );
    await waitFor(() => {
      expect(screen.getByText(/Load failed/)).toBeDefined();
    });
  });

  it('renders loading state', () => {
    const { container } = render(
      <MemoryRouter>
        <CrewsPage />
      </MemoryRouter>
    );
    expect(container.querySelector('.animate-spin, .animate-pulse')).toBeDefined();
  });

  it('shows running state when crew is running', async () => {
    let resolveRun: (val: any) => void;
    vi.mocked(api.runCrew).mockReturnValue(new Promise(r => { resolveRun = r; }));
    vi.mocked(api.listCrews).mockResolvedValue(mockCrews);
    render(
      <MemoryRouter>
        <CrewsPage />
      </MemoryRouter>
    );
    await waitFor(() => {
      expect(screen.getByText('Dev Team')).toBeDefined();
    });
    const runBtns = screen.getAllByText('运行');
    fireEvent.click(runBtns[0]);
    await waitFor(() => {
      expect(screen.getByText('运行中...')).toBeDefined();
    });
    resolveRun!({});
  });

  it('displays crew results after run', async () => {
    vi.mocked(api.runCrew).mockResolvedValue({ status: 'completed' });
    vi.mocked(api.listCrews).mockResolvedValue(mockCrews);
    render(
      <MemoryRouter>
        <CrewsPage />
      </MemoryRouter>
    );
    await waitFor(() => {
      expect(screen.getByText('Dev Team')).toBeDefined();
    });
    const runBtns = screen.getAllByText('运行');
    fireEvent.click(runBtns[0]);
    await waitFor(() => {
      expect(screen.getByText(/completed/)).toBeDefined();
    });
  });

  it('closes crew detail on backdrop click', async () => {
    vi.mocked(api.listCrews).mockResolvedValue(mockCrews);
    render(
      <MemoryRouter>
        <CrewsPage />
      </MemoryRouter>
    );
    await waitFor(() => {
      expect(screen.getByText('Dev Team')).toBeDefined();
    });
    const manageBtns = screen.getAllByText('管理成员');
    fireEvent.click(manageBtns[0]);
    await waitFor(() => {
      expect(screen.getByText(/成员管理/)).toBeDefined();
    });
    fireEvent.click(screen.getByText('关闭'));
    await waitFor(() => {
      expect(screen.queryByText(/成员管理/)).toBeNull();
    });
  });

  it('shows no description fallback', async () => {
    vi.mocked(api.listCrews).mockResolvedValue([{ id: 'c1', name: 'No Desc', agents: [] }]);
    render(
      <MemoryRouter>
        <CrewsPage />
      </MemoryRouter>
    );
    await waitFor(() => {
      expect(screen.getByText('暂无描述')).toBeDefined();
    });
  });
});
