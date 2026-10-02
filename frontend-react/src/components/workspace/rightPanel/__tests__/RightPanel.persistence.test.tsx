import { describe, it, expect, vi, beforeAll, beforeEach } from 'vitest';
import { act, render, screen, fireEvent, waitFor } from '@testing-library/react';
import { api } from '../../../../api';
import { useWorkspaceStore, type Session } from '../../../../store/workspace';
import { RightPanel } from '../../RightPanel';
import { INSPECTOR_LAYOUT_STORAGE_KEY, layoutContextKey } from '../persistedState';
import { warmSectionChunks } from './warmSectionChunks';

vi.mock('../../../../i18n', () => ({
  useI18n: () => ({
    t: (key: string, params?: Record<string, unknown>) =>
      params ? `${key}(${Object.values(params).join('|')})` : key,
  }),
}));

vi.mock('../../../../api', () => ({
  api: {
    getClusterStatus: vi.fn().mockResolvedValue({ nodes: [] }),
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
  activeSkills: [],
  activeTools: [],
  modelConfig: { provider: 'anthropic', modelId: 'claude-opus', temperature: 0.4, maxTokens: 8192 },
  tokenUsage: { used: 5000, limit: 10000 },
  createdAt: Date.now(),
  ...overrides,
});

/**
 * A revealed section resolves its own chunk and then its own data, so a case
 * that ends mid-flight leaves the last update outside the case that asked for
 * it. Waiting for the panel to come to rest keeps the render where it belongs.
 */
const settlePanel = () =>
  waitFor(
    () => {
      expect(screen.queryByTestId('inspector-section-fallback')).not.toBeInTheDocument();
      expect(screen.queryByRole('progressbar')).not.toBeInTheDocument();
    },
    { timeout: 10000 },
  );

const press = async (control: () => HTMLElement) => {
  fireEvent.click(control());
  await act(async () => {});
  await settlePanel();
};

const expandGroup = (name: string) => press(() => screen.getByRole('button', { name }));
const selectTab = (name: string) => press(() => screen.getByRole('tab', { name }));

const isExpanded = (name: string) =>
  screen.getByRole('button', { name }).getAttribute('aria-expanded');

const visiblePanel = () => screen.queryByRole('tabpanel')?.id;

const storedLayout = (sessionId: string | null) =>
  JSON.parse(localStorage.getItem(INSPECTOR_LAYOUT_STORAGE_KEY) ?? '{}')[layoutContextKey(sessionId)];

beforeAll(warmSectionChunks);

beforeEach(() => {
  vi.clearAllMocks();
  localStorage.clear();
  useWorkspaceStore.setState({
    sessions: [makeSession(), makeSession({ id: 's2', title: 'Second run' })],
    activeSessionId: 's1',
    rightPanelTab: 'config',
    rightPanelOpen: true,
  });
});

describe('inspector layout memory', () => {
  it('restores the expanded group and the selected tab of the active session', async () => {
    const view = render(<RightPanel />);
    await expandGroup('right_panel.groups.execution');
    await selectTab('right_panel.sections.trace');
    expect(visiblePanel()).toBe('inspector-panel-trace');
    view.unmount();

    render(<RightPanel />);
    expect(isExpanded('right_panel.groups.execution')).toBe('true');
    expect(visiblePanel()).toBe('inspector-panel-trace');
    await settlePanel();
  });

  it('gives every session its own arrangement', async () => {
    const view = render(<RightPanel />);
    await expandGroup('right_panel.groups.changes');
    expect(visiblePanel()).toBe('inspector-panel-diff');

    // s2 carries no arrangement yet, so it opens on the group its active tab owns.
    await act(async () => useWorkspaceStore.setState({ activeSessionId: 's2' }));
    expect(isExpanded('right_panel.groups.changes')).toBe('true');

    await expandGroup('right_panel.sections.reasoning');
    expect(isExpanded('right_panel.sections.reasoning')).toBe('true');
    expect(visiblePanel()).toBe('inspector-panel-reasoning');

    // s1 keeps the arrangement it was left with, unaffected by s2's.
    await act(async () => useWorkspaceStore.setState({ activeSessionId: 's1' }));
    expect(isExpanded('right_panel.groups.changes')).toBe('true');
    expect(visiblePanel()).toBe('inspector-panel-diff');
    await settlePanel();
    await act(async () => useWorkspaceStore.setState({ activeSessionId: 's2' }));
    expect(isExpanded('right_panel.sections.reasoning')).toBe('true');
    expect(visiblePanel()).toBe('inspector-panel-reasoning');
    await settlePanel();
    view.unmount();
  });

  it('keys its storage by conversation instead of a single shared slot', async () => {
    render(<RightPanel />);
    await expandGroup('right_panel.groups.execution');
    await act(async () => useWorkspaceStore.setState({ activeSessionId: 's2' }));
    await expandGroup('right_panel.groups.activity');

    const stored = JSON.parse(localStorage.getItem(INSPECTOR_LAYOUT_STORAGE_KEY) ?? '{}');
    expect(Object.keys(stored).sort()).toEqual(
      [layoutContextKey('s1'), layoutContextKey('s2')].sort(),
    );
    expect(stored[layoutContextKey('s1')].openGroup).toBe('execution');
    expect(stored[layoutContextKey('s2')].openGroup).toBe('activity');
  });

  it('drops a remembered group the current context cannot serve', async () => {
    localStorage.setItem(
      INSPECTOR_LAYOUT_STORAGE_KEY,
      JSON.stringify({
        [layoutContextKey(null)]: {
          openGroup: 'activity',
          selected: { activity: 'toolcalls', changes: 'diff' },
        },
      }),
    );
    useWorkspaceStore.setState({ sessions: [], activeSessionId: null, rightPanelTab: 'config' });
    render(<RightPanel />);
    // Without a run, activity has no reachable section, so the remembered entry
    // is pruned instead of restored as a dead group.
    expect(screen.getByRole('button', { name: 'right_panel.groups.activity' })).toBeDisabled();
    expect(isExpanded('right_panel.groups.activity')).toBe('false');
    expect(visiblePanel()).toBeUndefined();

    await expandGroup('right_panel.groups.changes');
    // A session-bound tab from the same pruned entry is replaced by the section
    // that works here, and the pruned key never comes back.
    expect(storedLayout(null)).toEqual({ openGroup: 'changes', selected: { changes: 'files' } });
  });

  it('ignores a selected tab the group no longer declares', async () => {
    localStorage.setItem(
      INSPECTOR_LAYOUT_STORAGE_KEY,
      JSON.stringify({
        [layoutContextKey('s1')]: { openGroup: 'overview', selected: { overview: 'toolcalls' } },
      }),
    );
    render(<RightPanel />);
    await expandGroup('right_panel.groups.execution');
    expect(storedLayout('s1').selected.overview).toBeUndefined();
  });
});

describe('inspector request handling', () => {
  it('keeps a manual collapse across closing and reopening the panel', async () => {
    render(<RightPanel />);
    await expandGroup('right_panel.groups.overview');
    expect(visiblePanel()).toBeUndefined();

    await act(async () => useWorkspaceStore.setState({ rightPanelOpen: false }));
    await act(async () => useWorkspaceStore.setState({ rightPanelOpen: true }));
    // Reopening is a view action, not a request: the arrangement survives it.
    expect(visiblePanel()).toBeUndefined();
    expect(isExpanded('right_panel.groups.overview')).toBe('false');
  });

  it('keeps a manual collapse after the panel is remounted', async () => {
    const view = render(<RightPanel />);
    await expandGroup('right_panel.groups.overview');
    view.unmount();

    render(<RightPanel />);
    expect(visiblePanel()).toBeUndefined();
  });

  it('reveals the group of an external tab request, once per request', async () => {
    render(<RightPanel />);
    await expandGroup('right_panel.groups.overview');
    expect(visiblePanel()).toBeUndefined();

    await act(async () => useWorkspaceStore.getState().setRightPanelTab('trace'));
    expect(visiblePanel()).toBe('inspector-panel-trace');

    // Asking for the tab already in view is a fresh request, and it lands again.
    await expandGroup('right_panel.groups.execution');
    expect(visiblePanel()).toBeUndefined();
    await act(async () => useWorkspaceStore.getState().setRightPanelTab('trace'));
    expect(visiblePanel()).toBe('inspector-panel-trace');
    expect(screen.getAllByRole('tabpanel')).toHaveLength(1);
  });

  it('restores a collapse when the session is revisited', async () => {
    render(<RightPanel />);
    await expandGroup('right_panel.groups.execution');
    await expandGroup('right_panel.groups.execution');
    expect(visiblePanel()).toBeUndefined();

    await act(async () => useWorkspaceStore.setState({ activeSessionId: 's2' }));
    expect(visiblePanel()).toBe('inspector-panel-dag');
    await act(async () => useWorkspaceStore.setState({ activeSessionId: 's1' }));
    // s1 still remembers that its group was collapsed.
    expect(visiblePanel()).toBeUndefined();
  });
});
