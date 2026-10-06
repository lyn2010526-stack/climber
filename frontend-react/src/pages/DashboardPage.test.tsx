import { beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import i18n from '../i18n';
import { api } from '../api';
import { DashboardPage } from './DashboardPage';
import type { TaskSummary } from '../api';

vi.mock('../api', () => ({
  api: {
    checkHealth: vi.fn(),
    listSessions: vi.fn(),
    listAgents: vi.fn(),
    listTasks: vi.fn(),
    listCostRecords: vi.fn(),
    getClusterStatus: vi.fn(),
    getCostQuota: vi.fn(),
  },
}));

const todayIso = () => new Date().toISOString();

const tasks: TaskSummary[] = [
  { task_id: 'task-1', objective: 'Refactor auth module', status: 'running', progress: 1, total_steps: 3, created_at: todayIso() },
  { task_id: 'task-2', objective: 'Write docs', status: 'completed', progress: 2, total_steps: 2, created_at: todayIso() },
];

function setUpData() {
  vi.mocked(api.listSessions).mockResolvedValue([
    { id: 's-1', title: 'Session one', status: 'idle' },
    { id: 's-2', title: 'Session two', status: 'running' },
    { id: 's-3', title: 'Session three', status: 'completed' },
  ] as any);
  vi.mocked(api.listAgents).mockResolvedValue([
    { id: 'a-1', name: 'writer' },
    { id: 'a-2', name: 'reviewer' },
  ] as any);
  vi.mocked(api.listTasks).mockResolvedValue(tasks as any);
  vi.mocked(api.listCostRecords).mockResolvedValue([
    { id: 'c-1', total_cost: 0.1, created_at: todayIso() },
    { id: 'c-2', total_cost: 0.2, created_at: todayIso() },
    { id: 'c-3', total_cost: 0.4, created_at: '2020-01-01T00:00:00Z' },
  ] as any);
  vi.mocked(api.getClusterStatus).mockResolvedValue({
    status: 'ok',
    total_nodes: 2,
    online_nodes: 1,
    nodes: [
      { id: 'n-1', name: 'node-a', status: 'online', role: 'worker' },
      { id: 'n-2', name: 'node-b', status: 'offline', role: 'worker' },
    ],
  } as any);
  vi.mocked(api.checkHealth).mockResolvedValue(true);
  vi.mocked(api.getCostQuota).mockResolvedValue({
    max_requests_per_day: 200,
    requests_today: 50,
  });
}

beforeEach(async () => {
  vi.resetAllMocks();
  await i18n.changeLanguage('en');
  setUpData();
});

describe('DashboardPage', () => {
  it('renders live metrics from every data source and the recent task list', async () => {
    render(<DashboardPage />);

    expect(await screen.findByText('API request succeeded')).toBeDefined();
    expect(screen.getByText('Total sessions')).toBeDefined();
    expect(screen.getByText('Active agents')).toBeDefined();
    expect(screen.getByText("Today's cost")).toBeDefined();
    expect(screen.getByText('Cluster nodes')).toBeDefined();

    expect(screen.getByText('3')).toBeDefined();
    expect(screen.getByText('2')).toBeDefined();
    expect(screen.getByText('$0.3000')).toBeDefined();
    expect(screen.getByText('1 of 2 online')).toBeDefined();

    expect(screen.getByText('Recent tasks')).toBeDefined();
    expect(screen.getByText('Refactor auth module')).toBeDefined();
    expect(screen.getByText('1 of 3 steps')).toBeDefined();
    expect(screen.getByText('Completed')).toBeDefined();
  });

  it('shows loading placeholders until every source settles', async () => {
    let release!: (value: unknown) => void;
    const pendingCost = new Promise((resolve) => { release = resolve; });
    vi.mocked(api.listCostRecords).mockReturnValueOnce(pendingCost as any);

    render(<DashboardPage />);

    expect(screen.getAllByText('…').length).toBeGreaterThanOrEqual(3);
    expect(screen.getAllByRole('status').length).toBeGreaterThan(0);

    release([{ id: 'c-1', total_cost: 0.5, created_at: todayIso() }]);
    expect(await screen.findByText('$0.5000')).toBeDefined();
  });

  it('surfaces failed sections with a retry that reloads the dashboard', async () => {
    vi.mocked(api.listSessions).mockRejectedValueOnce(new Error('sessions down'));
    vi.mocked(api.getClusterStatus).mockRejectedValueOnce(new Error('cluster down'));

    render(<DashboardPage />);

    expect(await screen.findByText(/Failed to load: sessions, cluster status/)).toBeDefined();
    expect(screen.getAllByText('—').length).toBeGreaterThanOrEqual(2);

    fireEvent.click(screen.getByRole('button', { name: 'Retry' }));
    await waitFor(() => expect(api.listSessions).toHaveBeenCalledTimes(2));
    expect(await screen.findByText('3')).toBeDefined();
    expect(screen.queryByText(/Failed to load/)).toBeNull();
  });

  it('renders friendly placeholders when every collection is empty', async () => {
    vi.mocked(api.listSessions).mockResolvedValue([]);
    vi.mocked(api.listAgents).mockResolvedValue([]);
    vi.mocked(api.listTasks).mockResolvedValue([]);
    vi.mocked(api.listCostRecords).mockResolvedValue([]);
    vi.mocked(api.getClusterStatus).mockResolvedValue({ status: 'ok', total_nodes: 0, online_nodes: 0, nodes: [] } as any);

    render(<DashboardPage />);

    expect(await screen.findByText('No tasks yet')).toBeDefined();
    expect(screen.getByText('No cluster nodes reported')).toBeDefined();
    expect(screen.getByText('$0.0000')).toBeDefined();
    expect(screen.getByText('API request succeeded')).toBeDefined();
  });

  it('shows an offline health banner when the health endpoint reports failure', async () => {
    vi.mocked(api.checkHealth).mockResolvedValue(false);

    render(<DashboardPage />);

    expect(await screen.findByText('API request failed')).toBeDefined();
  });

  it('keeps the quick actions visible after the data loads', async () => {
    render(<DashboardPage />);

    expect(await screen.findByText('API request succeeded')).toBeDefined();
    expect(screen.getByRole('button', { name: /Create an agent/i })).toBeDefined();
    expect(screen.getByRole('button', { name: /Start a task/i })).toBeDefined();
    expect(screen.queryByText('Welcome back')).toBeNull();
  });

  it('mounts the hero above the health banner and routes its primary CTA to chat', async () => {
    render(<DashboardPage />);

    const hero = screen.getByRole('region', { name: 'Climber hero section' });
    expect(hero).toHaveAttribute('data-hero-intro', expect.stringMatching(/^(play|instant)$/));
    expect(screen.getByRole('heading', { level: 1, name: 'Climber' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Start a conversation' })).toBeInTheDocument();

    const healthBanner = await screen.findByText('API request succeeded');
    expect(hero.compareDocumentPosition(healthBanner) & Node.DOCUMENT_POSITION_FOLLOWING).toBe(Node.DOCUMENT_POSITION_FOLLOWING);

    fireEvent.click(screen.getByRole('button', { name: 'Start a conversation' }));
    expect(window.location.hash).toBe('#chat');
    window.history.replaceState(null, '', '/');

    expect(screen.getByText('Refactor auth module')).toBeDefined();
  });
});
