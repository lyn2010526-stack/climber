import { beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import i18n from '../../i18n';
import { api } from '../../api';
import { MCPPage } from '../MCPPage';
import { PluginsPage } from '../PluginsPage';
import PluginPage from '../PluginPage';

vi.mock('../../api', () => ({ api: {
  listMCPServers: vi.fn(),
  listMCPCategories: vi.fn(),
  installMCPServer: vi.fn(),
  deleteMCPServer: vi.fn(),
  listPlugins: vi.fn(),
  installPlugin: vi.fn(),
  uninstallPlugin: vi.fn(),
  enablePlugin: vi.fn(),
  disablePlugin: vi.fn(),
  importPlugin: vi.fn(),
} }));

const servers = [
  { id: 'mcp-1', name: 'Filesystem', description: 'Read and write files', category: 'Tools', author: 'acme', is_builtin: true, is_installed: true, tags: ['files'], install_config: { root: '/tmp' }, popularity: 5, status: 'connected', tools_count: 1, resources_count: 1, tools: [{ name: 'read_file', description: 'Read a file' }], resources: [{ name: 'workspace', uri: 'file:///workspace' }] },
  { id: 'mcp-2', name: 'Postgres', description: 'Query the database', category: 'Data', author: 'globex', is_builtin: false, is_installed: false, tags: ['sql'], install_config: {}, popularity: 9 },
];

const plugins = [
  { id: 'plugin-1', name: 'Filesystem', description: 'Filesystem tools', type: 'mcp', source: 'builtin', status: 'enabled', icon: '', category: 'Tools', version: '1.2.0', tools: ['read_file'], tags: ['files'], config: { root: '/tmp' } },
  { id: 'plugin-2', name: 'Summarizer', description: 'Summarize long text', type: 'prompt', source: 'market', status: 'installed', icon: '', category: 'Writing', version: '0.4.0', tools: [], tags: [], config: {} },
];

function rows() {
  return document.querySelectorAll('li');
}

beforeEach(async () => {
  vi.resetAllMocks();
  await i18n.changeLanguage('en');
  vi.mocked(api.listMCPServers).mockResolvedValue(servers as any);
  vi.mocked(api.listMCPCategories).mockResolvedValue(['Tools', 'Data'] as any);
  vi.mocked(api.listPlugins).mockResolvedValue(plugins as any);
});

describe('MCP compact list', () => {
  it('renders one row per server with an icon plus text status label', async () => {
    render(<MCPPage />);
    await screen.findByText('Filesystem');
    expect(rows()).toHaveLength(2);
    const installed = document.querySelector('[data-mcp-installed="installed"]');
    const available = document.querySelector('[data-mcp-installed="available"]');
    expect(installed?.textContent).toContain('Installed');
    expect(available?.textContent).toContain('Not installed');
    expect(installed?.querySelector('svg')).not.toBeNull();
    expect(available?.querySelector('svg')).not.toBeNull();
  });

  it('search, category and installed-only filters all narrow the list', async () => {
    render(<MCPPage />);
    await screen.findByText('Filesystem');

    fireEvent.change(screen.getByRole('textbox', { name: 'Search' }), { target: { value: 'postgres' } });
    expect(screen.queryByText('Filesystem')).toBeNull();
    expect(screen.getByText('Postgres')).toBeDefined();

    fireEvent.change(screen.getByRole('textbox', { name: 'Search' }), { target: { value: '' } });
    fireEvent.change(screen.getByRole('combobox', { name: 'Filter' }), { target: { value: 'Data' } });
    expect(screen.queryByText('Filesystem')).toBeNull();
    expect(screen.getByText('Postgres')).toBeDefined();

    fireEvent.change(screen.getByRole('combobox', { name: 'Filter' }), { target: { value: '' } });
    fireEvent.click(screen.getByRole('checkbox'));
    expect(screen.queryByText('Postgres')).toBeNull();
    expect(screen.getByText('Filesystem')).toBeDefined();
  });

  it('shows a no-results state that clears every active filter', async () => {
    render(<MCPPage />);
    await screen.findByText('Filesystem');
    fireEvent.change(screen.getByRole('textbox', { name: 'Search' }), { target: { value: 'nothing-matches' } });
    expect(screen.getByText('No results')).toBeDefined();
    fireEvent.click(screen.getByRole('button', { name: 'Clear' }));
    expect(rows()).toHaveLength(2);
  });

  it('reports an empty catalog separately from a filtered miss', async () => {
    vi.mocked(api.listMCPServers).mockResolvedValue([] as any);
    render(<MCPPage />);
    expect(await screen.findByText('No data available')).toBeDefined();
    expect(screen.queryByText('No results')).toBeNull();
  });

  it('keeps the install and uninstall contracts and surfaces failures', async () => {
    vi.mocked(api.installMCPServer).mockRejectedValueOnce(new Error('Install unavailable'));
    render(<MCPPage />);
    await screen.findByText('Postgres');
    fireEvent.click(screen.getByRole('button', { name: 'Install' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Install unavailable');
    expect(api.installMCPServer).toHaveBeenCalledWith('mcp-2', {});

    vi.mocked(api.deleteMCPServer).mockResolvedValue({} as any);
    fireEvent.click(screen.getByRole('button', { name: 'Uninstall Filesystem' }));
    await waitFor(() => expect(api.deleteMCPServer).toHaveBeenCalledWith('mcp-1'));
    await waitFor(() => expect(screen.queryByRole('alert')).toBeNull());
  });

  it('expands the install configuration fields on demand', async () => {
    render(<MCPPage />);
    await screen.findByText('Filesystem');
    const toggle = screen.getAllByRole('button', { name: /Install configuration/ })[0]!;
    expect(toggle.getAttribute('aria-expanded')).toBe('false');
    fireEvent.click(toggle);
    expect(toggle.getAttribute('aria-expanded')).toBe('true');
    const panel = document.getElementById('mcp-config-mcp-1')!;
    expect(within(panel).getByText(/root/)).toBeDefined();
  });

  it('keeps MCP server, tool, and resource levels distinguishable', async () => {
    render(<MCPPage />);
    await screen.findByText('Filesystem');
    fireEvent.click(screen.getAllByRole('button', { name: /Install configuration/ })[0]!);
    const panel = document.getElementById('mcp-config-mcp-1')!;
    expect(within(panel).getByText('Server')).toBeDefined();
    expect(within(panel).getAllByText('Tools').length).toBeGreaterThan(0);
    expect(within(panel).getAllByText('Resources').length).toBeGreaterThan(0);
    expect(within(panel).getByText(/read_file/)).toBeDefined();
    expect(within(panel).getByText(/workspace/)).toBeDefined();
  });

  it('retries a failed catalog load from the error banner', async () => {
    vi.mocked(api.listMCPServers).mockRejectedValueOnce(new Error('Catalog offline'));
    render(<MCPPage />);
    expect(await screen.findByRole('alert')).toHaveTextContent('Catalog offline');
    fireEvent.click(screen.getByRole('button', { name: /Retry/ }));
    expect(await screen.findByText('Filesystem')).toBeDefined();
    expect(api.listMCPServers).toHaveBeenCalledTimes(2);
  });
});

describe('Plugins compact list', () => {
  it('renders one row per plugin with an icon plus text status label', async () => {
    render(<PluginsPage />);
    await screen.findByText('Filesystem');
    expect(rows()).toHaveLength(2);
    const enabled = document.querySelector('[data-plugin-status="enabled"]');
    const installed = document.querySelector('[data-plugin-status="installed"]');
    expect(enabled?.textContent).toContain('Enabled');
    expect(installed?.textContent).toContain('Installed');
    expect(enabled?.querySelector('svg')).not.toBeNull();
  });

  it('filters by type and by enabled category with real counts', async () => {
    render(<PluginsPage />);
    await screen.findByText('Filesystem');
    fireEvent.click(screen.getByRole('button', { name: 'Skill' }));
    expect(screen.getByText(i18n.t('plugins.empty_description'))).toBeDefined();
    const [typeFilter, categoryFilter] = screen.getAllByRole('group', { name: i18n.t('common.filter') });
    fireEvent.click(within(typeFilter).getByRole('button', { name: i18n.t('common.all') }));
    fireEvent.click(within(categoryFilter).getByRole('button', { name: new RegExp(i18n.t('plugins.category_installed').split(' ')[0]) }));
    expect(screen.getByText('Filesystem')).toBeDefined();
    expect(screen.getByText('Summarizer')).toBeDefined();
  });

  it('never offers uninstall for builtin sources but toggles normally', async () => {
    vi.mocked(api.disablePlugin).mockResolvedValue({} as any);
    render(<PluginsPage />);
    await screen.findByText('Filesystem');
    expect(screen.queryByRole('button', { name: 'Remove Filesystem' })).toBeNull();
    fireEvent.click(screen.getByRole('button', { name: 'Disable' }));
    await waitFor(() => expect(api.disablePlugin).toHaveBeenCalledWith('plugin-1'));
  });

  it('keeps a failed plugin action visible and retries it from the row', async () => {
    vi.mocked(api.disablePlugin).mockRejectedValueOnce(new Error('Disable unavailable')).mockResolvedValueOnce({} as any);
    render(<PluginsPage />);
    await screen.findByText('Filesystem');
    fireEvent.click(screen.getByRole('button', { name: 'Disable' }));
    expect((await screen.findAllByRole('alert'))[0]).toHaveTextContent('Disable unavailable');
    expect(screen.getByText('Filesystem')).toBeDefined();
    const row = screen.getByText('Filesystem').closest('li')!;
    fireEvent.click(within(row).getByRole('button', { name: 'Retry' }));
    await waitFor(() => expect(api.disablePlugin).toHaveBeenCalledTimes(2));
  });

  it('exposes details and configuration fields behind a single disclosure', async () => {
    render(<PluginsPage />);
    await screen.findByText('Filesystem');
    const toggle = screen.getAllByRole('button', { name: new RegExp(i18n.t('plugins.details_action')) })[0]!;
    expect(document.getElementById('plugin-detail-plugin-1')).toBeNull();
    fireEvent.click(toggle);
    const panel = document.getElementById('plugin-detail-plugin-1')!;
    expect(within(panel).getByText('Source')).toBeDefined();
    expect(within(panel).getByText(/root/)).toBeDefined();
  });

  it('imports a plugin from the header entry with the existing payload contract', async () => {
    vi.mocked(api.importPlugin).mockResolvedValue({} as any);
    render(<PluginsPage />);
    await screen.findByText('Filesystem');
    fireEvent.click(screen.getByRole('button', { name: 'Import plugin' }));
    const dialog = screen.getByRole('dialog');
    fireEvent.change(within(dialog).getByLabelText(i18n.t('plugins.import_url_label')), { target: { value: 'https://example.test/plugin.json' } });
    fireEvent.change(within(dialog).getByLabelText('Type'), { target: { value: 'prompt' } });
    fireEvent.click(within(dialog).getByRole('button', { name: 'Import' }));
    await waitFor(() => expect(api.importPlugin).toHaveBeenCalledWith('https://example.test/plugin.json', '', 'prompt'));
    await waitFor(() => expect(screen.queryByRole('dialog')).toBeNull());
  });
});

describe('Plugin management compact list', () => {
  it('keeps the import form reachable from the page header', async () => {
    vi.mocked(api.importPlugin).mockResolvedValue({} as any);
    render(<PluginPage />);
    await screen.findByText('Filesystem');
    fireEvent.click(screen.getByRole('button', { name: 'Import plugin' }));
    const dialog = screen.getByRole('dialog');
    fireEvent.change(within(dialog).getByLabelText(i18n.t('plugins.import_source_label')), { target: { value: 'https://example.test/p.json' } });
    fireEvent.click(within(dialog).getByRole('button', { name: 'Import' }));
    await waitFor(() => expect(api.importPlugin).toHaveBeenCalledWith('https://example.test/p.json', ''));
  });

  it('toggles and uninstalls with the existing plugin contracts', async () => {
    vi.mocked(api.enablePlugin).mockResolvedValue({} as any);
    vi.mocked(api.uninstallPlugin).mockResolvedValue({} as any);
    render(<PluginPage />);
    await screen.findByText('Filesystem');
    fireEvent.click(screen.getByRole('button', { name: 'Enable' }));
    await waitFor(() => expect(api.enablePlugin).toHaveBeenCalledWith('plugin-2'));
    fireEvent.click(screen.getByRole('button', { name: 'Disable' }));
    await waitFor(() => expect(api.disablePlugin).toHaveBeenCalledWith('plugin-1'));
    fireEvent.click(screen.getByRole('button', { name: 'Remove Summarizer' }));
    await waitFor(() => expect(api.uninstallPlugin).toHaveBeenCalledWith('plugin-2'));
    expect(rows()).toHaveLength(1);
  });

  it('separates a filtered miss from an empty install list', async () => {
    render(<PluginPage />);
    await screen.findByText('Filesystem');
    fireEvent.change(screen.getByRole('textbox', { name: 'Search' }), { target: { value: 'zzz' } });
    expect(screen.getByText('No matching plugins')).toBeDefined();
    vi.mocked(api.listPlugins).mockResolvedValue([] as any);
    fireEvent.click(screen.getByRole('button', { name: 'Clear' }));
    fireEvent.click(screen.getByRole('button', { name: /Refresh/ }));
    expect(await screen.findByText('No plugins installed')).toBeDefined();
  });
});
