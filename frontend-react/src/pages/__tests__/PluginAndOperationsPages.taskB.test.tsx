import { beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import i18n from '../../i18n';
import { api } from '../../api';
import { DashboardPage } from '../DashboardPage';
import { PluginsPage } from '../PluginsPage';
import { StatsPage } from '../StatsPage';

vi.mock('../../api', () => ({
  api: {
    checkHealth: vi.fn(),
    listPlugins: vi.fn(),
    enablePlugin: vi.fn(),
    disablePlugin: vi.fn(),
    installPlugin: vi.fn(),
    uninstallPlugin: vi.fn(),
    importPlugin: vi.fn(),
    getPluginCategories: vi.fn(),
    getStats: vi.fn(),
  },
}));

const plugin = {
  id: 'plugin-1',
  name: 'Filesystem',
  description: 'Filesystem tools',
  type: 'mcp',
  source: 'builtin',
  status: 'enabled',
  icon: '',
  category: 'Tools',
  version: '1.2.0',
  tools: ['read_file'],
  tags: ['files'],
  config: {},
};

beforeEach(async () => {
  vi.resetAllMocks();
  await i18n.changeLanguage('en');
  vi.mocked(api.checkHealth).mockResolvedValue(true);
  vi.mocked(api.listPlugins).mockResolvedValue([plugin] as any);
  vi.mocked(api.getPluginCategories).mockResolvedValue(['Tools'] as any);
  vi.mocked(api.getStats).mockResolvedValue({
    total_users: 4,
    total_agents: 2,
    total_sessions: 13,
    total_api_keys: 1,
  });
});

describe('Task B operations pages', () => {
  it('reports the live health response and keeps quick actions compact', async () => {
    render(<DashboardPage />);
    expect(await screen.findByText(i18n.t('home.api_online'))).toBeDefined();
    expect(screen.getByRole('button', { name: i18n.t('home.create_agent') })).toBeDefined();
    expect(screen.queryByText('Welcome back')).toBeNull();
  });

  it('filters plugins by search and calls the existing toggle contract', async () => {
    render(<PluginsPage />);
    expect(await screen.findByText('Filesystem')).toBeDefined();
    fireEvent.change(screen.getByRole('textbox', { name: i18n.t('common.search') }), { target: { value: 'missing' } });
    expect(screen.getByText(i18n.t('plugins.empty_title'))).toBeDefined();
    fireEvent.change(screen.getByRole('textbox', { name: i18n.t('common.search') }), { target: { value: 'file' } });
    fireEvent.click(screen.getByRole('button', { name: i18n.t('plugins.disable', { defaultValue: 'Disable' }) }));
    await waitFor(() => expect(api.disablePlugin).toHaveBeenCalledWith('plugin-1'));
  });

  it('renders API statistics from the returned payload and retries after failure', async () => {
    vi.mocked(api.getStats).mockRejectedValueOnce(new Error('Stats offline'));
    render(<StatsPage />);
    expect(await screen.findByText('Stats offline')).toBeDefined();
    vi.mocked(api.getStats).mockResolvedValueOnce({
      total_users: 4,
      total_agents: 2,
      total_sessions: 13,
      total_api_keys: 1,
    });
    fireEvent.click(screen.getByRole('button', { name: '重试' }));
    expect(await screen.findByText('13')).toBeDefined();
  });
});
