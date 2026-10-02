import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen, within } from '@testing-library/react';
import i18n from '../../i18n';
import { api } from '../../api';
import { useWorkspaceStore } from '../../store/workspace';
import { SessionSidebar } from '../../components/workspace/SessionSidebar';
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

describe('SessionSidebar distinguishes a failed list from an empty list', () => {
  it('reports the count as unreported when the session request fails', async () => {
    vi.mocked(api.listSessions).mockRejectedValue(new Error('backend down') as never);

    render(<SessionSidebar />);

    expect(await screen.findByText('会话列表未上报')).toBeInTheDocument();
    // The heading count must not claim the backend holds no sessions.
    const heading = screen.getByRole('heading', { name: i18n.t('navigation.sessions') });
    expect(heading.parentElement?.textContent).not.toMatch(/^Sessions0/);
  });

  it('keeps a real empty list distinct from a missing one', async () => {
    render(<SessionSidebar />);

    // `common.no_data` only appears once the list has actually resolved empty.
    expect(await screen.findByText(i18n.t('common.no_data'))).toBeInTheDocument();
    expect(screen.queryByText('会话列表未上报')).not.toBeInTheDocument();
  });

  it('reports the agent list as unreported instead of "no agents available"', async () => {
    vi.mocked(api.listAgents).mockRejectedValue(new Error('boom') as never);

    render(<SessionSidebar />);

    // The select offers a "not reported" option and refuses to be used, so a
    // failed read can never be resolved into "pick an agent" with no agents.
    const option = await screen.findByText('智能体列表未上报');
    expect(option.closest('select')).toBeDisabled();
  });
});

describe('PluginsPage reports statuses the backend never declared', () => {
  it('labels an unrecognised status as not reported rather than installed', async () => {
    vi.mocked(api.listPlugins).mockResolvedValue([
      { ...basePlugin, status: 'quarantined' },
    ] as never);

    render(<PluginsPage />);

    expect(within(await screen.findByRole('status')).getByText(i18n.t('plugins.status.unknown', { defaultValue: 'Unreported' }))).toBeInTheDocument();
    expect(screen.queryByText(i18n.t('plugins.status.installed', { defaultValue: 'Installed' }))).not.toBeInTheDocument();
  });

  it('keeps a missing status field on the not-reported path', async () => {
    vi.mocked(api.listPlugins).mockResolvedValue([
      { ...basePlugin, status: undefined },
    ] as never);

    render(<PluginsPage />);

    expect(within(await screen.findByRole('status')).getByText(i18n.t('plugins.status.unknown', { defaultValue: 'Unreported' }))).toBeInTheDocument();
  });

  it('still names the statuses the backend does declare', async () => {
    vi.mocked(api.listPlugins).mockResolvedValue([
      { ...basePlugin, id: 'p1', status: 'enabled' },
      { ...basePlugin, id: 'p2', name: 'Disabled one', status: 'disabled' },
    ] as never);

    render(<PluginsPage />);

    expect(await screen.findByText(i18n.t('plugins.status.enabled', { defaultValue: 'Enabled' }))).toBeInTheDocument();
    expect(screen.getByText(i18n.t('plugins.status.disabled', { defaultValue: 'Disabled' }))).toBeInTheDocument();
    expect(screen.queryByText(i18n.t('plugins.status.unknown', { defaultValue: 'Unreported' }))).not.toBeInTheDocument();
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

    expect(await screen.findByText(i18n.t('workflows.status.never_run'))).toBeInTheDocument();
    expect(document.querySelector('[data-workflow-status="never_run"]')).not.toBeNull();
  });

  it('reports a status outside the known vocabulary as not reported', async () => {
    vi.mocked(api.listWorkflows).mockResolvedValue([workflow({ last_status: 'teleported' })] as never);

    render(<WorkflowsPage />);

    expect(await screen.findByText(i18n.t('workflows.status.unknown'))).toBeInTheDocument();
    expect(document.querySelector('[data-workflow-status="teleported"]')).not.toBeNull();
  });

  it('reports an absent run count instead of rendering zero runs', async () => {
    vi.mocked(api.listWorkflows).mockResolvedValue([workflow({ last_status: 'completed' })] as never);

    render(<WorkflowsPage />);

    expect(await screen.findByText(i18n.t('workflows.status.completed'))).toBeInTheDocument();
    expect(screen.queryByText('0 runs')).not.toBeInTheDocument();
    expect(screen.getByText(i18n.t('collaboration.not_reported'))).toBeInTheDocument();
  });
});
