import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { api } from '../../../../api';
import { useWorkspaceStore, type Session } from '../../../../store/workspace';
import { RightPanel } from '../../RightPanel';

/**
 * Section chunks are cached by `React.lazy` for the lifetime of a module
 * registry, so the placeholder is only observable in a file that renders a
 * section for the first time. Every case here is written around that first
 * render, and the waits allow for a cold module graph.
 */
vi.mock('../../../../i18n', () => ({
  useI18n: () => ({ t: (key: string) => key }),
}));

vi.mock('../../../../api', () => ({
  api: {
    getClusterStatus: vi.fn().mockResolvedValue({ nodes: [] }),
    listTraces: vi.fn().mockResolvedValue({ traces: [] }),
    listDocuments: vi.fn().mockResolvedValue([]),
    getSessionMessages: vi.fn().mockResolvedValue([]),
  },
}));

const CHUNK_TIMEOUT = { timeout: 10000 };

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

beforeEach(() => {
  vi.clearAllMocks();
  localStorage.clear();
  useWorkspaceStore.setState({
    sessions: [makeSession()],
    activeSessionId: 's1',
    rightPanelTab: 'config',
    rightPanelOpen: true,
  });
});

describe('inspector section loading', () => {
  it('asks for a section only once its chunk has landed', async () => {
    useWorkspaceStore.setState({ rightPanelTab: 'toolcalls' });
    render(<RightPanel />);
    // The chunk is still in flight: the placeholder holds the layout and the
    // section has issued no request, so a panel nobody opened stays silent.
    expect(screen.getByTestId('inspector-section-fallback')).toBeInTheDocument();
    expect(api.getSessionMessages).not.toHaveBeenCalled();

    await waitFor(
      () => expect(screen.queryByTestId('inspector-section-fallback')).not.toBeInTheDocument(),
      CHUNK_TIMEOUT,
    );
    await waitFor(() => expect(api.getSessionMessages).toHaveBeenCalledTimes(1), CHUNK_TIMEOUT);
  });

  it('leaves every section outside the open group unfetched', async () => {
    render(<RightPanel />);
    // Only the group the active tab owns is open, so no other section asks for
    // anything behind the collapsed headings.
    await waitFor(
      () => expect(screen.queryByTestId('inspector-section-fallback')).not.toBeInTheDocument(),
      CHUNK_TIMEOUT,
    );
    expect(api.getSessionMessages).not.toHaveBeenCalled();
    expect(api.getClusterStatus).not.toHaveBeenCalled();
    expect(api.listTraces).not.toHaveBeenCalled();
    expect(api.listDocuments).not.toHaveBeenCalled();
  });

  it('leaves a collapsed section out of the request budget', async () => {
    render(<RightPanel />);
    fireEvent.click(screen.getByRole('button', { name: 'right_panel.groups.changes' }));
    // Entering a group asks for exactly its own section, and collapsing it again
    // issues nothing new.
    await waitFor(() => expect(api.getSessionMessages).toHaveBeenCalledTimes(1), CHUNK_TIMEOUT);
    fireEvent.click(screen.getByRole('button', { name: 'right_panel.groups.changes' }));
    expect(api.getSessionMessages).toHaveBeenCalledTimes(1);
    expect(api.getClusterStatus).not.toHaveBeenCalled();
    expect(api.listTraces).not.toHaveBeenCalled();
  });
});
