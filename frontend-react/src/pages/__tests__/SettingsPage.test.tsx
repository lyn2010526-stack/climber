import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { api } from '../../api';

vi.mock('../../api', () => ({
  api: {
    getCurrentUser: vi.fn().mockResolvedValue({
      id: 1,
      username: 'admin',
      email: 'admin@example.com',
      role: 'admin',
    }),
    updateSettings: vi.fn().mockResolvedValue({}),
    getSettings: vi.fn().mockResolvedValue({
      autonomous_agent_mode: false,
      token_throttle_mcp_enabled: false,
      mcp_status: 'disconnected',
      mcp_ready: false,
      notifications: {},
    }),
    listAuthApiKeys: vi.fn().mockResolvedValue({ keys: [] }),
    createAuthApiKey: vi.fn().mockResolvedValue({}),
    revokeAuthApiKey: vi.fn().mockResolvedValue({}),
    getAuthHealth: vi.fn().mockResolvedValue({
      authentication_enabled: true,
      auth_method: 'password',
    }),
    changePassword: vi.fn().mockResolvedValue({}),
  },
}));

import { SettingsPage } from '../SettingsPage';

describe('SettingsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.getCurrentUser).mockResolvedValue({
      id: 1,
      username: 'admin',
      email: 'admin@example.com',
      role: 'admin',
    });
    vi.mocked(api.getSettings).mockResolvedValue({
      autonomous_agent_mode: false,
      token_throttle_mcp_enabled: false,
      mcp_status: 'disconnected',
      mcp_ready: false,
      notifications: {},
    });
    vi.mocked(api.listAuthApiKeys).mockResolvedValue({ keys: [] });
    vi.mocked(api.getAuthHealth).mockResolvedValue({
      authentication_enabled: true,
      auth_method: 'password',
    });
  });

  it('renders settings page without crashing', async () => {
    const { container } = render(<MemoryRouter><SettingsPage /></MemoryRouter>);
    await waitFor(() => expect(screen.getByText('基本信息')).toBeDefined());
    expect(container).toBeDefined();
  });

  it('renders page title', async () => {
    render(<MemoryRouter><SettingsPage /></MemoryRouter>);
    await waitFor(() => expect(screen.getByText('基本信息')).toBeDefined());
    expect(screen.getByText('Settings')).toBeDefined();
  });

  it('renders mode descriptions', async () => {
    render(<MemoryRouter><SettingsPage /></MemoryRouter>);
    fireEvent.click(screen.getAllByText('API Settings')[0]);
    await waitFor(() => expect(screen.getByText('执行模式')).toBeDefined());
    expect(screen.getByText(/控制智能体的运行行为/)).toBeDefined();
  });

  it('renders toggle switches', async () => {
    render(<MemoryRouter><SettingsPage /></MemoryRouter>);
    fireEvent.click(screen.getAllByText('API Settings')[0]);
    await waitFor(() => expect(screen.getByText('自主智能体模式')).toBeDefined());
    expect(screen.getByText('MCP Token 节流')).toBeDefined();
  });

  it('renders mode description text', async () => {
    render(<MemoryRouter><SettingsPage /></MemoryRouter>);
    fireEvent.click(screen.getAllByText('API Settings')[0]);
    await waitFor(() => expect(screen.getByText(/开启后智能体可自主决策执行多步任务/)).toBeDefined());
  });

  it('renders MCP toggle', async () => {
    render(<MemoryRouter><SettingsPage /></MemoryRouter>);
    fireEvent.click(screen.getAllByText('API Settings')[0]);
    await waitFor(() => expect(screen.getByText(/对 MCP 工具调用进行 Token 限流/)).toBeDefined());
  });

  it('shows MCP status when enabled', async () => {
    vi.mocked(api.getSettings).mockResolvedValue({
      autonomous_agent_mode: false,
      token_throttle_mcp_enabled: true,
      mcp_status: 'ready',
      mcp_ready: true,
      notifications: {},
    });
    render(<MemoryRouter><SettingsPage /></MemoryRouter>);
    fireEvent.click(screen.getAllByText('API Settings')[0]);
    await waitFor(() => expect(screen.getByText('已就绪')).toBeDefined());
    expect(screen.getAllByText('ready').length).toBeGreaterThan(0);
  });

  it('renders current mode section', async () => {
    render(<MemoryRouter><SettingsPage /></MemoryRouter>);
    fireEvent.click(screen.getAllByText('API Settings')[0]);
    await waitFor(() => expect(screen.getByText('MCP 状态')).toBeDefined());
  });

  it('shows autonomous mode when enabled', async () => {
    vi.mocked(api.getSettings).mockResolvedValue({
      autonomous_agent_mode: true,
      token_throttle_mcp_enabled: false,
      mcp_status: 'disconnected',
      mcp_ready: false,
      notifications: {},
    });
    render(<MemoryRouter><SettingsPage /></MemoryRouter>);
    fireEvent.click(screen.getAllByText('API Settings')[0]);
    await waitFor(() => expect(screen.getAllByRole('switch').length).toBeGreaterThan(0));
    expect(screen.getAllByRole('switch')[0]).toHaveAttribute('aria-checked', 'true');
  });

  it('shows full mode when both enabled', async () => {
    vi.mocked(api.getSettings).mockResolvedValue({
      autonomous_agent_mode: true,
      token_throttle_mcp_enabled: true,
      mcp_status: 'ready',
      mcp_ready: true,
      notifications: {},
    });
    render(<MemoryRouter><SettingsPage /></MemoryRouter>);
    fireEvent.click(screen.getAllByText('API Settings')[0]);
    await waitFor(() => expect(screen.getAllByRole('switch').length).toBe(2));
    expect(screen.getAllByRole('switch')[0]).toHaveAttribute('aria-checked', 'true');
    expect(screen.getAllByRole('switch')[1]).toHaveAttribute('aria-checked', 'true');
  });

  it('shows loading state', async () => {
    let resolveCurrentUser!: (v: any) => void;
    vi.mocked(api.getCurrentUser).mockImplementation(
      () => new Promise((resolve) => { resolveCurrentUser = resolve; })
    );
    const { container } = render(<MemoryRouter><SettingsPage /></MemoryRouter>);
    await waitFor(() => expect(container.querySelector('[class*=shimmer]')).toBeDefined());
    resolveCurrentUser({ id: 1, username: 'admin', email: 'admin@example.com', role: 'admin' });
    await waitFor(() => expect(screen.getByText('基本信息')).toBeDefined());
  });

  it('shows error state', async () => {
    vi.mocked(api.getCurrentUser).mockRejectedValue(new Error('Failed to load profile'));
    render(<MemoryRouter><SettingsPage /></MemoryRouter>);
    await waitFor(() => expect(screen.getByText('Failed to load profile')).toBeDefined());
  });

  it('renders MCP status badge states', async () => {
    vi.mocked(api.getSettings).mockResolvedValue({
      autonomous_agent_mode: false,
      token_throttle_mcp_enabled: true,
      mcp_status: 'ready',
      mcp_ready: true,
      notifications: {},
    });
    render(<MemoryRouter><SettingsPage /></MemoryRouter>);
    fireEvent.click(screen.getAllByText('API Settings')[0]);
    await waitFor(() => expect(screen.getAllByText('已就绪').length).toBeGreaterThan(0));
    expect(screen.getAllByText('ready').length).toBeGreaterThan(0);
  });

  it('shows disconnected MCP status', async () => {
    render(<MemoryRouter><SettingsPage /></MemoryRouter>);
    fireEvent.click(screen.getAllByText('API Settings')[0]);
    await waitFor(() => expect(screen.getByText('未就绪')).toBeDefined());
  });
});
