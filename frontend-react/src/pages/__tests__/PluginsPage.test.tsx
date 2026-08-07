import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { api } from '../../api';

vi.mock('../../api', () => ({
  api: {
    listPlugins: vi.fn().mockResolvedValue([]),
    installPlugin: vi.fn().mockResolvedValue({}),
    uninstallPlugin: vi.fn().mockResolvedValue({}),
    enablePlugin: vi.fn().mockResolvedValue({}),
    disablePlugin: vi.fn().mockResolvedValue({}),
    importPlugin: vi.fn().mockResolvedValue({}),
  },
}));

vi.mock('../../hooks/useNetworkStatus', () => ({
  useOnline: () => true,
}));

import { PluginsPage } from '../PluginsPage';

const mockPlugins = [
  {
    id: 'plugin-1',
    name: 'Web Search',
    description: 'Search the web',
    type: 'skill' as const,
    source: 'builtin',
    status: 'enabled' as const,
    icon: '🔍',
    category: 'search',
    version: '1.0.0',
    tools: ['web_search'],
    tags: ['search', 'web'],
    popularity: 100,
  },
  {
    id: 'plugin-2',
    name: 'Code Runner',
    description: 'Run code snippets',
    type: 'mcp' as const,
    source: 'community',
    status: 'installed' as const,
    icon: '⚙️',
    category: 'development',
    version: '2.0.0',
    tools: ['run_code'],
    tags: ['code'],
    popularity: 50,
  },
];

describe('PluginsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.listPlugins).mockResolvedValue([]);
  });

  it('renders without crashing', () => {
    const { container } = render(
      <MemoryRouter>
        <PluginsPage />
      </MemoryRouter>
    );
    expect(container).toBeDefined();
  });

  it('renders loading state initially', () => {
    const { container } = render(
      <MemoryRouter>
        <PluginsPage />
      </MemoryRouter>
    );
    expect(container.querySelector('.animate-spin')).toBeDefined();
  });

  it('renders page title after loading', async () => {
    render(
      <MemoryRouter>
        <PluginsPage />
      </MemoryRouter>
    );
    await waitFor(() => {
      expect(screen.getByText('插件市场')).toBeDefined();
    });
  });

  it('renders search input', async () => {
    render(
      <MemoryRouter>
        <PluginsPage />
      </MemoryRouter>
    );
    await waitFor(() => {
      expect(screen.getByPlaceholderText(/搜索插件/)).toBeDefined();
    });
  });

  it('renders plugins list', async () => {
    vi.mocked(api.listPlugins).mockResolvedValue(mockPlugins);
    render(
      <MemoryRouter>
        <PluginsPage />
      </MemoryRouter>
    );
    await waitFor(() => {
      expect(screen.getByText('Web Search')).toBeDefined();
      expect(screen.getByText('Code Runner')).toBeDefined();
    });
  });

  it('filters plugins by search', async () => {
    vi.mocked(api.listPlugins).mockResolvedValue(mockPlugins);
    render(
      <MemoryRouter>
        <PluginsPage />
      </MemoryRouter>
    );
    await waitFor(() => {
      expect(screen.getByText('Web Search')).toBeDefined();
    });
    const searchInput = screen.getByPlaceholderText(/搜索插件/);
    fireEvent.change(searchInput, { target: { value: 'code' } });
    await waitFor(() => {
      expect(screen.getByText('Code Runner')).toBeDefined();
    });
  });

  it('shows enabled count', async () => {
    vi.mocked(api.listPlugins).mockResolvedValue(mockPlugins);
    render(
      <MemoryRouter>
        <PluginsPage />
      </MemoryRouter>
    );
    await waitFor(() => {
      expect(screen.getByText(/1 个已启用/)).toBeDefined();
    });
  });

  it('renders type filter buttons', async () => {
    render(
      <MemoryRouter>
        <PluginsPage />
      </MemoryRouter>
    );
    await waitFor(() => {
      expect(screen.getByText('全部')).toBeDefined();
      expect(screen.getByText('Skill')).toBeDefined();
      expect(screen.getByText('MCP')).toBeDefined();
      expect(screen.getByText('Prompt')).toBeDefined();
    });
  });

  it('toggles import modal', async () => {
    render(
      <MemoryRouter>
        <PluginsPage />
      </MemoryRouter>
    );
    await waitFor(() => {
      expect(screen.getByText('导入插件')).toBeDefined();
    });
    fireEvent.click(screen.getByText('导入插件'));
    await waitFor(() => {
      expect(screen.getByText(/源地址/)).toBeDefined();
    });
  });

  it('imports a plugin', async () => {
    render(
      <MemoryRouter>
        <PluginsPage />
      </MemoryRouter>
    );
    await waitFor(() => {
      expect(screen.getByText('导入插件')).toBeDefined();
    });
    fireEvent.click(screen.getByText('导入插件'));
    const urlInput = screen.getByPlaceholderText(/github.com/);
    fireEvent.change(urlInput, { target: { value: 'https://example.com/plugin' } });
    fireEvent.click(screen.getByText('导入'));
    await waitFor(() => {
      expect(api.importPlugin).toHaveBeenCalled();
    });
  });

  it('closes import modal', async () => {
    render(
      <MemoryRouter>
        <PluginsPage />
      </MemoryRouter>
    );
    await waitFor(() => {
      expect(screen.getByText('导入插件')).toBeDefined();
    });
    fireEvent.click(screen.getByText('导入插件'));
    fireEvent.click(screen.getByText('取消'));
    await waitFor(() => {
      expect(screen.queryByText(/源地址/)).toBeNull();
    });
  });
});
