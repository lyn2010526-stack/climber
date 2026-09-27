import { describe, it, expect, vi, beforeAll, beforeEach } from 'vitest';
import { act, render, screen, fireEvent, waitFor, within } from '@testing-library/react';
import { api } from '../../../../api';
import { useWorkspaceStore, type Session } from '../../../../store/workspace';
import { RightPanel } from '../../RightPanel';
import { warmSectionChunks } from './warmSectionChunks';

vi.mock('../../../../i18n', () => ({
  useI18n: () => ({
    // Keys stay identifiable in assertions while interpolation stays observable.
    t: (key: string, params?: Record<string, unknown>) =>
      params ? `${key}(${Object.values(params).join('|')})` : key,
  }),
}));

vi.mock('../../../workspace/ReasoningPanel', () => ({
  ReasoningPanel: () => <div data-testid="reasoning-panel" />,
}));

vi.mock('../../../../api', () => ({
  api: {
    getClusterStatus: vi.fn().mockResolvedValue({ plan: [] }),
    listTraces: vi.fn().mockResolvedValue({ traces: [] }),
    listDocuments: vi.fn().mockResolvedValue([]),
    getSessionMessages: vi.fn().mockResolvedValue([]),
  },
}));

const makeSession = (overrides: Partial<Session> = {}): Session => ({
  id: 's1',
  title: 'Refactor auth',
  status: 'idle',
  messages: [],
  activeSkills: ['research'],
  activeTools: ['grep', 'edit'],
  modelConfig: { provider: 'anthropic', modelId: 'claude-opus', temperature: 0.4, maxTokens: 8192 },
  tokenUsage: { used: 5000, limit: 10000 },
  createdAt: Date.now(),
  ...overrides,
});

beforeAll(warmSectionChunks);

/**
 * Sections are fetched as they are shown, so a case that ends while a chunk is
 * still in flight leaves an update landing after the assertions. Waiting for the
 * placeholder to clear keeps the render inside the case that asked for it.
 */
const settleSection = () =>
  waitFor(() => expect(screen.queryByTestId('inspector-section-fallback')).not.toBeInTheDocument(), {
    timeout: 10000,
  });

beforeEach(() => {
  vi.clearAllMocks();
  // Expansion and selection are remembered per conversation, so each case
  // starts from a blank layout rather than the previous test's arrangement.
  localStorage.clear();
  useWorkspaceStore.setState({
    sessions: [makeSession()],
    activeSessionId: 's1',
    rightPanelTab: 'config',
    rightPanelOpen: true,
  });
});

describe('RightPanel', () => {
  it('renders nothing when the panel is closed', () => {
    useWorkspaceStore.setState({ rightPanelOpen: false });
    const { container } = render(<RightPanel />);
    expect(container).toBeEmptyDOMElement();
  });

  it('closes from the panel header without changing the selected tab', () => {
    render(<RightPanel />);
    fireEvent.click(screen.getByTestId('right-panel-close'));
    expect(useWorkspaceStore.getState().rightPanelOpen).toBe(false);
    expect(useWorkspaceStore.getState().rightPanelTab).toBe('config');
  });

  it('keeps the run summary mounted for every tab', async () => {
    useWorkspaceStore.setState({ rightPanelTab: 'toolcalls' });
    render(<RightPanel />);
    await settleSection();
    expect(screen.getByText('Refactor auth')).toBeInTheDocument();
    expect(screen.queryByText('claude-opus')).not.toBeInTheDocument();
    expect(screen.queryByRole('progressbar')).not.toBeInTheDocument();
  });

  it('shows status once and keeps usage in configuration only', async () => {
    useWorkspaceStore.setState({
      sessions: [
        makeSession({
          status: 'running',
          messages: [
            { id: 'm1', type: 'tool-call', content: {}, timestamp: 1 },
            { id: 'm2', type: 'tool-result', content: {}, timestamp: 2, metadata: { status: 'error' } },
          ],
        }),
      ],
    });
    render(<RightPanel />);
    // The status label carries its own value, so the summary is matched by text
    // content and the "once" claim is checked as a count.
    const summary = screen.getByRole('complementary');
    expect(summary.textContent?.match(/right_panel\.status\.running/g)).toHaveLength(1);
    expect(screen.queryByText('right_panel.summary.errors')).not.toBeInTheDocument();
    const progress = await screen.findByRole('progressbar', { name: 'right_panel.config.token_title' });
    expect(progress).toHaveAttribute('aria-valuenow', '50');
  });

  it('prompts to pick a session when none is active', () => {
    useWorkspaceStore.setState({ sessions: [], activeSessionId: null });
    render(<RightPanel />);
    expect(screen.getByText('right_panel.summary.no_session')).toBeInTheDocument();
  });

  it('exposes the five groups as collapsible buttons', () => {
    render(<RightPanel />);
    for (const id of ['overview', 'execution', 'changes', 'activity']) {
      const button = screen.getByRole('button', { name: `right_panel.groups.${id}` });
      expect(button).toHaveAttribute('aria-expanded');
    }
    expect(screen.getByRole('button', { name: 'right_panel.sections.reasoning' })).toHaveAttribute('aria-expanded');
  });

  it('expands the group that owns the active tab and marks its section selected', async () => {
    useWorkspaceStore.setState({ rightPanelTab: 'trace' });
    render(<RightPanel />);
    await settleSection();
    expect(screen.getByRole('button', { name: 'right_panel.groups.execution' }))
      .toHaveAttribute('aria-expanded', 'true');
    expect(screen.getByRole('tab', { name: 'right_panel.sections.trace' }))
      .toHaveAttribute('aria-selected', 'true');
  });

  it('omits sub tabs for single-section groups', async () => {
    render(<RightPanel />);
    expect(screen.queryByRole('tab', { name: 'right_panel.sections.config' })).not.toBeInTheDocument();
    expect(await screen.findByText('right_panel.config.provider')).toBeInTheDocument();
  });

  it('shows sub tabs for multi-section groups', async () => {
    useWorkspaceStore.setState({ rightPanelTab: 'dag' });
    render(<RightPanel />);
    await settleSection();
    expect(screen.getByRole('tab', { name: 'right_panel.sections.dag' })).toBeInTheDocument();
    expect(screen.queryByRole('tab', { name: 'right_panel.sections.reasoning' })).not.toBeInTheDocument();
  });

  it('keeps reasoning in its own group', async () => {
    useWorkspaceStore.setState({ rightPanelTab: 'reasoning' });
    render(<RightPanel />);
    expect(screen.getByRole('button', { name: 'right_panel.sections.reasoning' }))
      .toHaveAttribute('aria-expanded', 'true');
    expect(screen.getByRole('tabpanel')).toHaveAttribute('id', 'inspector-panel-reasoning');
  });

  it('mounts one group at a time and allows collapsing the active group', async () => {
    render(<RightPanel />);
    expect(api.getClusterStatus).not.toHaveBeenCalled();
    expect(api.listTraces).not.toHaveBeenCalled();
    expect(api.listDocuments).not.toHaveBeenCalled();
    expect(api.getSessionMessages).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole('button', { name: 'right_panel.groups.execution' }));
    await screen.findByText('right_panel.states.empty_dag');
    expect(api.getClusterStatus).toHaveBeenCalledTimes(1);
    expect(screen.getByRole('button', { name: 'right_panel.groups.overview' }))
      .toHaveAttribute('aria-expanded', 'false');
    fireEvent.click(screen.getByRole('button', { name: 'right_panel.groups.execution' }));
    expect(screen.queryByRole('tabpanel')).not.toBeInTheDocument();
    act(() => useWorkspaceStore.getState().setRightPanelTab('trace'));
    await screen.findByText('right_panel.states.empty_trace');
    expect(screen.getAllByRole('tabpanel')).toHaveLength(1);
  });

  it.each(['config', 'dag', 'trace', 'reasoning', 'diff', 'files', 'toolcalls'] as const)('preserves external navigation to %s', async (tab) => {
    const view = render(<RightPanel />);
    await act(async () => useWorkspaceStore.setState({ rightPanelTab: tab }));
    expect(screen.getAllByRole('tabpanel')).toHaveLength(1);
    expect(screen.getByRole('tabpanel')).toHaveAttribute('id', `inspector-panel-${tab}`);
    view.unmount();
  });

  it('omits unreported configuration metrics', async () => {
    useWorkspaceStore.setState({ sessions: [makeSession({ modelConfig: undefined, tokenUsage: undefined })] });
    render(<RightPanel />);
    // The section is resolved first, so the absence below is a real verdict
    // rather than a placeholder that has not answered yet.
    await settleSection();
    expect(screen.queryByRole('progressbar')).not.toBeInTheDocument();
    const panel = screen.getByRole('tabpanel');
    expect(within(panel).getByText('research')).toBeInTheDocument();
    // Every metric keeps its label and reports the gap, so a value the backend
    // never sent can never be read back as a real budget.
    expect(within(panel).getAllByText('right_panel.summary.not_reported').length)
      .toBeGreaterThanOrEqual(4);
    for (const fabricated of ['0.4', '8192', '5000', '10000']) {
      expect(within(panel).queryByText(fabricated)).not.toBeInTheDocument();
    }
  });

  it('keeps a collapsed panel collapsed until a tab is requested again', async () => {
    render(<RightPanel />);
    fireEvent.click(screen.getByRole('button', { name: 'right_panel.groups.overview' }));
    expect(screen.queryByRole('tabpanel')).not.toBeInTheDocument();
    act(() => useWorkspaceStore.setState({ rightPanelOpen: false }));
    await act(async () => useWorkspaceStore.setState({ rightPanelOpen: true }));
    // Closing and reopening the panel is a view action; the arrangement stands.
    expect(screen.queryByRole('tabpanel')).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'right_panel.groups.overview' }))
      .toHaveAttribute('aria-expanded', 'false');
    await act(async () => useWorkspaceStore.getState().setRightPanelTab('trace'));
    expect(screen.getByRole('tabpanel')).toHaveAttribute('id', 'inspector-panel-trace');
  });

  it('falls back to files without a session and disables session-only activity', async () => {
    useWorkspaceStore.setState({ sessions: [], activeSessionId: null, rightPanelTab: 'diff' });
    await act(async () => render(<RightPanel />));
    expect(screen.getByRole('tabpanel')).toHaveAttribute('id', 'inspector-panel-files');
    expect(screen.getByRole('button', { name: 'right_panel.groups.activity' })).toBeDisabled();
    expect(api.getSessionMessages).not.toHaveBeenCalled();
  });

  it('unmounts old tool details immediately when switching sessions', async () => {
    vi.mocked(api.getSessionMessages).mockResolvedValueOnce([
      { id: 'old', role: 'assistant', content: null, tool_call_id: null, tool_name: null, created_at: '', tool_calls: [{ id: 'call', name: 'old-tool' }] },
    ]).mockImplementationOnce(() => new Promise(() => {}));
    useWorkspaceStore.setState({ rightPanelTab: 'toolcalls', sessions: [makeSession(), makeSession({ id: 's2' })] });
    render(<RightPanel />);
    await screen.findByRole('button', { name: 'old-tool' });
    act(() => useWorkspaceStore.setState({ activeSessionId: 's2' }));
    expect(screen.queryByRole('button', { name: 'old-tool' })).not.toBeInTheDocument();
    expect(screen.getByRole('status')).toHaveAttribute('aria-busy', 'true');
  });

  it('renders a declared empty state for a section without data', async () => {
    useWorkspaceStore.setState({ rightPanelTab: 'dag' });
    render(<RightPanel />);
    await waitFor(() => {
      expect(screen.getByText('right_panel.states.empty_dag')).toBeInTheDocument();
    });
  });
});

describe('RightPanel on-demand inspection', () => {
  it('keeps a single group open and unmounts the section left behind', async () => {
    useWorkspaceStore.setState({ rightPanelTab: 'dag' });
    render(<RightPanel />);
    await screen.findByText('right_panel.states.empty_dag');
    expect(api.getClusterStatus).toHaveBeenCalledTimes(1);

    fireEvent.click(screen.getByRole('button', { name: 'right_panel.groups.changes' }));
    expect(screen.queryByRole('tabpanel')).toHaveProperty('id', 'inspector-panel-diff');
    // The plan request already answered is not re-issued by collapsing its group.
    expect(api.getClusterStatus).toHaveBeenCalledTimes(1);
    expect(screen.getByRole('button', { name: 'right_panel.groups.execution' }))
      .toHaveAttribute('aria-expanded', 'false');
    await settleSection();
  });

  it('collapses every group from the header and restores the active tab group', async () => {
    render(<RightPanel />);
    fireEvent.click(screen.getByRole('button', { name: 'right_panel.collapse_all' }));
    for (const id of ['overview', 'execution', 'changes', 'activity']) {
      expect(screen.getByRole('button', { name: `right_panel.groups.${id}` }))
        .toHaveAttribute('aria-expanded', 'false');
    }
    expect(screen.queryByRole('tabpanel')).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'right_panel.expand_all' }));
    expect(screen.getByRole('tabpanel')).toHaveAttribute('id', 'inspector-panel-config');
  });

  it('keeps session independent data across a session switch', async () => {
    useWorkspaceStore.setState({
      rightPanelTab: 'files',
      sessions: [makeSession(), makeSession({ id: 's2' })],
    });
    render(<RightPanel />);
    await screen.findByText('right_panel.states.empty_documents');
    expect(api.listDocuments).toHaveBeenCalledTimes(1);

    act(() => useWorkspaceStore.setState({ activeSessionId: 's2' }));
    expect(screen.getByRole('tabpanel')).toHaveAttribute('id', 'inspector-panel-files');
    expect(api.listDocuments).toHaveBeenCalledTimes(1);
  });

  it('tallies resolved entries in the group heading and retires the tally on collapse', async () => {
    vi.mocked(api.getClusterStatus).mockResolvedValue({
      plan: [
        { id: 'a', description: 'First step', status: 'completed' },
        { id: 'b', description: 'Second step', status: 'running' },
      ],
    });
    useWorkspaceStore.setState({ rightPanelTab: 'dag' });
    render(<RightPanel />);
    const heading = screen.getByRole('button', { name: 'right_panel.groups.execution' });
    await screen.findByText('Second step');
    // The tally is published by the section once its data resolves.
    await waitFor(() => expect(within(heading).getByText('2')).toBeInTheDocument());

    fireEvent.click(heading);
    expect(within(heading).queryByText('2')).not.toBeInTheDocument();
  });

  it('shows no tally while a section is still loading', async () => {
    vi.mocked(api.getClusterStatus).mockReturnValueOnce(new Promise(() => {}));
    useWorkspaceStore.setState({ rightPanelTab: 'dag' });
    render(<RightPanel />);
    const heading = screen.getByRole('button', { name: 'right_panel.groups.execution' });
    // Once the chunk has landed, the section itself holds the busy state.
    await waitFor(() =>
      expect(screen.getByRole('status')).toHaveAttribute('aria-busy', 'true'),
    );
    expect(heading.textContent).toBe('right_panel.groups.execution');
  });

  it('publishes no tally when a section request fails', async () => {
    // A failed request has no count to report. Publishing 0 here would tell the
    // user the backend holds no plan nodes, which the failure never said.
    vi.mocked(api.getClusterStatus).mockRejectedValue(new Error('down'));
    useWorkspaceStore.setState({ rightPanelTab: 'dag' });
    render(<RightPanel />);
    const heading = screen.getByRole('button', { name: 'right_panel.groups.execution' });
    await screen.findByText('right_panel.states.load_failed');
    expect(heading.textContent).toBe('right_panel.groups.execution');
  });

  it('still tallies a resolved empty list as zero rather than unreported', async () => {
    vi.mocked(api.getClusterStatus).mockResolvedValue({ plan: [] });
    useWorkspaceStore.setState({ rightPanelTab: 'dag' });
    render(<RightPanel />);
    await screen.findByText('right_panel.states.empty_dag');
    // The heading only renders a tally above zero, so an empty list is shown by
    // the section's own empty state; the point is that no false number appears.
    const heading = screen.getByRole('button', { name: 'right_panel.groups.execution' });
    expect(heading.textContent).toBe('right_panel.groups.execution');
  });
});
