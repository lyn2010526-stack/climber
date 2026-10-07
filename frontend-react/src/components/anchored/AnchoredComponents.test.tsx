import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { api } from '../../api';
import { resetAnchoredStore, useAnchoredStore } from '../../store/anchored';
import { AnchoredPopupStack } from '../agent/AnchoredPopupStack';
import { AnchoredMessageFlow, ToolCallCard } from '../agent/AnchoredMessageFlow';
import { TaskTracePanel } from './TaskTracePanel';
import { ArtifactPreview } from './ArtifactPreview';
import { normalizeChatEvent } from '../../types/chatEvents';

vi.mock('../../api', () => ({ api: { resolvePermission: vi.fn(), listTasks: vi.fn(), listTraces: vi.fn() } }));
vi.mock('./taskApi', async importOriginal => ({
  ...await importOriginal<typeof import('./taskApi')>(),
  consumeTaskEvents: () => new Promise(() => {}),
  listTaskGroups: async () => [],
}));
vi.mock('../../i18n', () => ({ useI18n: () => ({ t: (key: string) => key }), useTranslation: () => ({ t: (key: string) => key }) }));

beforeEach(() => { vi.resetAllMocks(); resetAnchoredStore(); });

describe('anchored approvals', () => {
  it('keeps pending approval until acknowledgement and preserves newest-first order', async () => {
    let acknowledge!: (value: unknown) => void;
    vi.mocked(api.resolvePermission).mockImplementation(() => new Promise(resolve => { acknowledge = resolve; }));
    useAnchoredStore.getState().pushPopup({ kind: 'approval', title: 'older', payload: { toolCallId: 'a' } });
    useAnchoredStore.getState().pushPopup({ kind: 'approval', title: 'newer', payload: { toolCallId: 'b' } });
    render(<AnchoredPopupStack />);
    const dialogs = screen.getAllByRole('dialog');
    expect(within(dialogs[0]).getByText('newer')).toBeInTheDocument();
    fireEvent.click(within(dialogs[0]).getByText('anchored.popup.approve'));
    expect(api.resolvePermission).toHaveBeenCalledWith('b', 'allow');
    expect(screen.getAllByRole('dialog')).toHaveLength(2);
    expect(within(dialogs[0]).getByLabelText('anchored.popup.dismiss')).toBeDisabled();
    await act(async () => { acknowledge({ status: 'resolved' }); });
    expect(screen.getAllByRole('dialog')).toHaveLength(1);
  });

  it('retains failed requests and allows retrying a denial', async () => {
    vi.mocked(api.resolvePermission).mockRejectedValueOnce(new Error('offline')).mockResolvedValueOnce({});
    useAnchoredStore.getState().pushPopup({ kind: 'approval', title: 'request', payload: { toolCallId: 'a' } });
    render(<AnchoredPopupStack />);
    fireEvent.click(screen.getByText('anchored.popup.cancel'));
    expect(await screen.findByRole('alert')).toHaveTextContent('offline');
    expect(screen.getByRole('dialog')).toBeInTheDocument();
    fireEvent.click(screen.getByText('anchored.popup.cancel'));
    await waitFor(() => expect(screen.queryByRole('dialog')).toBeNull());
    expect(api.resolvePermission).toHaveBeenLastCalledWith('a', 'deny');
  });

  it('normalizes backend approval metadata', () => {
    expect(normalizeChatEvent({ event: 'tool_call', data: { id: 'x', name: 'edit', requires_approval: true, description: 'review', severity: 'high' } })).toMatchObject({ toolCall: { requiresApproval: true, description: 'review', severity: 'high' } });
  });
});

describe('anchored tool and activity panels', () => {
  it('selects real file outputs, preserves change markers and closes the last artifact', () => {
    useAnchoredStore.getState().openFilePreview({ name: 'first.ts', path: '/first.ts', lines: [{ marker: 'add', text: 'first output' }] });
    useAnchoredStore.getState().openFilePreview({ name: 'second.ts', path: '/second.ts', lines: [{ marker: 'del', text: 'second output' }] });
    render(<ArtifactPreview />);
    expect(screen.getByText('first output').closest('[data-line-marker]')).toHaveAttribute('data-line-marker', 'add');
    expect(screen.getByRole('tab', { name: 'first.ts' }).querySelector('svg')).toHaveAttribute('data-workbench-icon', 'preview');
    expect(screen.getByText('first output').parentElement?.querySelector('.workbench-line-number')).toHaveTextContent('1');
    expect(screen.getByText('first output').parentElement?.querySelector('.workbench-line-sign')).toHaveTextContent('+');
    fireEvent.click(screen.getByRole('tab', { name: 'second.ts' }));
    expect(screen.getByText('second output').closest('[data-line-marker]')).toHaveAttribute('data-line-marker', 'del');
    fireEvent.click(screen.getByText('anchored.preview.close · second.ts'));
    fireEvent.click(screen.getByText('anchored.preview.close · first.ts'));
    expect(screen.queryByRole('tabpanel')).toBeNull();
    expect(screen.getByText('anchored.preview.empty')).toBeInTheDocument();
  });
  it('renders three tool states and opens error-only output inline', () => {
    const call = { id: 'x', name: 'read', arguments: {} };
    const { rerender } = render(<ToolCallCard call={{ ...call, status: 'running' }} active defaultExpanded={false} />);
    expect(screen.getByTestId('anchored-tool-card')).toHaveAttribute('data-tool-status', 'running');
    expect(screen.getByTestId('anchored-tool-card').querySelector('svg')).toHaveAttribute('data-workbench-icon', 'tool');
    rerender(<ToolCallCard call={{ ...call, status: 'success', result: 'ok' }} active={false} defaultExpanded={false} />);
    expect(screen.queryByText('ok')).toBeNull();
    rerender(<ToolCallCard call={{ ...call, status: 'error', error: 'broken' }} active={false} defaultExpanded={false} />);
    expect(screen.getByText('broken')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button'));
    expect(screen.queryByText('broken')).toBeNull();
  });

  it('mounts separate user, agent and tool visual surfaces in the transcript', () => {
    render(<AnchoredMessageFlow messages={[
      { id: 'u', role: 'user', content: 'request' },
      { id: 'a', role: 'assistant', content: 'response', reasoning: 'reasoning' },
    ]} />);
    expect(screen.getByText('request').parentElement).toHaveClass('codex-user-message');
    expect(screen.getByTestId('anchored-thinking-bubble').querySelector('.codex-agent-message')).toBeInTheDocument();
    expect(screen.getByTestId('anchored-thinking-bubble').querySelector('svg')).toHaveAttribute('data-workbench-icon', 'agent');
  });

  it('shows account task lanes and isolates traces to the selected session', async () => {
    vi.mocked(api.listTasks).mockResolvedValue([{ task_id: 't', objective: 'real task', status: 'running', progress: 1, total_steps: 2 }]);
    const { unmount } = render(<TaskTracePanel kind="tasks" sessionId="a" />);
    expect(await screen.findByText('real task')).toBeInTheDocument();
    expect(screen.getAllByRole('region')).toHaveLength(3);
    unmount();
    vi.mocked(api.listTraces).mockResolvedValue([
      { id: 'one', session_id: 'a', name: 'mine', status: 'success', duration_ms: 4, spans: [] },
      { id: 'two', session_id: 'b', name: 'other', status: 'success', duration_ms: 8, spans: [] },
    ]);
    render(<TaskTracePanel kind="traces" sessionId="a" />);
    expect(await screen.findByText(/mine/)).toBeInTheDocument();
    expect(screen.queryByText(/other/)).toBeNull();
  });

  it('upserts subtask status without accumulating duplicate nodes', () => {
    useAnchoredStore.getState().expandForSubTask({ id: 'x', name: 'agent', status: 'running' });
    useAnchoredStore.getState().expandForSubTask({ id: 'x', name: 'agent', status: 'error', detail: 'failed' });
    expect(useAnchoredStore.getState().subAgentTree).toHaveLength(1);
    expect(useAnchoredStore.getState().subAgentTree[0].status).toBe('error');
  });

  it('ignores a stale trace response after switching sessions', async () => {
    let resolveOld!: (value: unknown) => void;
    vi.mocked(api.listTraces).mockImplementationOnce(() => new Promise(resolve => { resolveOld = resolve; })).mockResolvedValueOnce([
      { id: 'new', session_id: 'b', name: 'new session trace', status: 'running', duration_ms: null, spans: [] },
    ]);
    const { rerender } = render(<TaskTracePanel kind="traces" sessionId="a" />);
    rerender(<TaskTracePanel kind="traces" sessionId="b" />);
    expect(await screen.findByText(/new session trace/)).toBeInTheDocument();
    await act(async () => { resolveOld([{ id: 'old', session_id: 'a', name: 'stale trace', status: 'success', spans: [] }]); });
    expect(screen.queryByText(/stale trace/)).toBeNull();
    expect(screen.getByText(/new session trace/)).toBeInTheDocument();
  });

  it('shows snapshot errors and reloads through the retry control', async () => {
    vi.mocked(api.listTasks).mockRejectedValueOnce(new Error('server unavailable')).mockResolvedValueOnce([]);
    render(<TaskTracePanel kind="tasks" />);
    expect(await screen.findByRole('alert')).toHaveTextContent('server unavailable');
    fireEvent.click(screen.getByText('anchored.trace.retry'));
    expect(await screen.findByText('anchored.trace.empty')).toBeInTheDocument();
    expect(api.listTasks).toHaveBeenCalledTimes(2);
  });

  it('clears the previous trace error when no session is selected', async () => {
    vi.mocked(api.listTraces).mockRejectedValueOnce(new Error('old session unavailable'));
    const { rerender } = render(<TaskTracePanel kind="traces" sessionId="a" />);
    expect(await screen.findByRole('alert')).toHaveTextContent('old session unavailable');
    rerender(<TaskTracePanel kind="traces" sessionId={null} />);
    expect(screen.queryByRole('alert')).toBeNull();
    expect(screen.getByText('anchored.trace.empty')).toBeInTheDocument();
    expect(api.listTraces).toHaveBeenCalledTimes(1);
  });
});
