import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import i18n from '../../i18n';
import { api } from '../../api';
import { useWorkspaceStore } from '../../store/workspace';
import { PluginsPage } from '../PluginsPage';
import { WorkflowsPage } from '../WorkflowsPage';

/**
 * Every surface below used to answer a question the backend never answered.
 * A request that failed, a field the payload omitted and a real value of zero
 * all rendered as the same confident number or label. These tests pin the
 * distinction: reported stays reported, unknown says so, and only a resolved
 * empty list reads as empty.
 */
vi.mock('../../api', () => ({
  api: {
    listSessions: vi.fn(),
    createSession: vi.fn(),
    deleteSession: vi.fn(),
    listAgents: vi.fn(),
    listModels: vi.fn(),
    listPlugins: vi.fn(),
    enablePlugin: vi.fn(),
    disablePlugin: vi.fn(),
    installPlugin: vi.fn(),
    uninstallPlugin: vi.fn(),
    importPlugin: vi.fn(),
    getPluginCategories: vi.fn(),
    listWorkflows: vi.fn(),
    runWorkflow: vi.fn(),
  },
}));

const basePlugin = {
  id: 'plugin-1',
  name: 'Filesystem',
  description: 'Filesystem tools',
  type: 'mcp',
  source: 'builtin',
  icon: '',
  category: 'Tools',
  version: '1.2.0',
  tools: [],
  tags: [],
  config: {},
};

beforeEach(async () => {
  vi.clearAllMocks();
  await i18n.changeLanguage('en');
  // The sidebar only asks for the agent list once it knows who the user is.
  vi.stubGlobal('fetch', vi.fn(async (url: string) => {
    if (url === '/api/v1/auth/me') return Response.json({ id: 'owner-a' });
    throw new Error(`Unexpected request: ${url}`);
  }));
  useWorkspaceStore.setState({
    sessions: [],
    sessionsLoaded: false,
    loadingSessions: false,
    activeSessionId: null,
    tasks: [],
    snapshots: [],
  });
  vi.mocked(api.listAgents).mockResolvedValue([] as never);
  vi.mocked(api.listModels).mockResolvedValue([] as never);
  vi.mocked(api.listSessions).mockResolvedValue([] as never);
  vi.mocked(api.listPlugins).mockResolvedValue([{ ...basePlugin, status: 'enabled' }] as never);
  vi.mocked(api.listWorkflows).mockResolvedValue([] as never);
});

describe('PluginsPage reports statuses the backend never declared', () => {
  it.each([
    ['en', 'Enabled', 'Status not reported'],
    ['zh-CN', '已启用', '状态未上报'],
  ])('uses the selected %s language for reported and unknown statuses', async (language, enabled, unknown) => {
    await i18n.changeLanguage(language);
    vi.mocked(api.listPlugins).mockResolvedValue([
      { ...basePlugin, status: 'enabled' },
      { ...basePlugin, id: 'unknown', name: 'Unknown', status: 'quarantined' },
    ] as never);
    render(<PluginsPage />);
    expect(await screen.findByText(enabled)).toBeInTheDocument();
    expect(screen.getByText(unknown, { selector: '[role="status"]' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: `${unknown}: Unknown` })).toBeDisabled();
  });
  it('labels an unrecognised status as not reported rather than installed', async () => {
    vi.mocked(api.listPlugins).mockResolvedValue([
      { ...basePlugin, status: 'quarantined' },
    ] as never);

    render(<PluginsPage />);

    expect(await screen.findByText('Status not reported', { selector: '[role="status"]' })).toBeInTheDocument();
    expect(screen.queryByText('Installed', { selector: '[role="status"]' })).not.toBeInTheDocument();
  });

  it('keeps a missing status field on the not-reported path', async () => {
    vi.mocked(api.listPlugins).mockResolvedValue([
      { ...basePlugin, status: undefined },
    ] as never);

    render(<PluginsPage />);

    expect(await screen.findByText('Status not reported', { selector: '[role="status"]' })).toBeInTheDocument();
  });

  it('still names the statuses the backend does declare', async () => {
    vi.mocked(api.listPlugins).mockResolvedValue([
      { ...basePlugin, id: 'p1', status: 'enabled' },
      { ...basePlugin, id: 'p2', name: 'Disabled one', status: 'disabled' },
    ] as never);

    render(<PluginsPage />);

    expect(await screen.findByText('Enabled')).toBeInTheDocument();
    expect(screen.getByText('Disabled')).toBeInTheDocument();
    expect(screen.queryByText('Status not reported')).not.toBeInTheDocument();
  });
});

describe('WorkflowsPage stops painting every status as a success', () => {
  const workflow = (overrides: Record<string, unknown>) => ({
    id: 'wf-1',
    name: 'Release',
    nodes: [],
    edges: [],
    ...overrides,
  });

  it('shows a workflow that has never run as never run', async () => {
    vi.mocked(api.listWorkflows).mockResolvedValue([workflow({ last_status: 'never_run' })] as never);

    render(<WorkflowsPage />);

    expect(await screen.findByText('Never run')).toBeInTheDocument();
    expect(document.querySelector('[data-workflow-status="never_run"]')).not.toBeNull();
  });

  it('reports a status outside the known vocabulary as not reported', async () => {
    vi.mocked(api.listWorkflows).mockResolvedValue([workflow({ last_status: 'teleported' })] as never);

    render(<WorkflowsPage />);

    expect(await screen.findByText('Status not reported')).toBeInTheDocument();
    expect(document.querySelector('[data-workflow-status="teleported"]')).not.toBeNull();
  });

  it('reports an absent run count instead of rendering zero runs', async () => {
    vi.mocked(api.listWorkflows).mockResolvedValue([workflow({ last_status: 'completed' })] as never);

    render(<WorkflowsPage />);

    expect(await screen.findByText('Completed')).toBeInTheDocument();
    expect(screen.queryByText('0 runs')).not.toBeInTheDocument();
    expect(screen.getByText('Not reported')).toBeInTheDocument();
  });
});
