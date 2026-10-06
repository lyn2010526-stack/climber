import { describe, it, expect, beforeEach, vi } from 'vitest';
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { useWorkspaceStore, type Message, type Session } from '../../../store/workspace';
import { ControlBar } from '../ControlBar';
import i18n from '../../../i18n/config';

const message = (id: string): Message => ({ id, type: 'user', content: id, timestamp: 1 });

const makeSession = (overrides: Partial<Session> = {}): Session => ({
  id: 's1',
  title: '会话 Alpha',
  status: 'idle',
  messages: [message('m1'), message('m2')],
  activeSkills: [],
  activeTools: [],
  modelConfig: { provider: 'openai', modelId: 'gpt-4o', temperature: 0.7, maxTokens: 4096 },
  tokenUsage: { used: 0, limit: 200000 },
  createdAt: Date.now(),
  ...overrides,
});

/** A snapshot that recorded a transcript, i.e. one that can be restored. */
const restorableSnapshot = {
  id: 'snap-1', sessionId: 's1', timestamp: 1, label: 'Snapshot 1', messages: [message('m1')],
};

const rollbackButton = () => screen.queryByRole('button', { name: new RegExp(i18n.t('anchored.controlbar.restore_snapshot').replace(/[.*+?^${}()|[\]\\]/g, '\\$&')) });
const restoreNamed = (name: string) => i18n.t('anchored.controlbar.restore_named', { name });

beforeEach(async () => {
  await i18n.changeLanguage('zh-CN');
  useWorkspaceStore.setState({
    sessions: [],
    sessionsLoaded: false,
    loadingSessions: false,
    activeSessionId: null,
    rightPanelOpen: true,
    focusMode: false,
    expertMode: false,
    permissionMode: null,
    tasks: [],
    snapshots: [],
  });
  vi.restoreAllMocks();
});

describe('ControlBar snapshot rollback', () => {
  it('offers no rollback action until a snapshot carries a restorable transcript', () => {
    render(<ControlBar />);
    expect(rollbackButton()).toBeNull();

    useWorkspaceStore.setState({ sessions: [makeSession()], activeSessionId: 's1' });
    render(<ControlBar />);
    // A session with no snapshot has nothing to go back to.
    expect(screen.queryAllByRole('button', { name: /还原视图/ })).toHaveLength(0);

    // A marker without a transcript is not offered as a control that would fail.
    useWorkspaceStore.setState({
      snapshots: [{ id: 'snap-0', sessionId: 's1', timestamp: 1, label: 'Snapshot 1' }],
    });
    expect(screen.queryAllByRole('button', { name: /还原视图/ })).toHaveLength(0);
  });

  it('rolls a session back to the newest restorable snapshot of that session', async () => {
    useWorkspaceStore.setState({
      sessions: [makeSession()],
      activeSessionId: 's1',
      snapshots: [
        restorableSnapshot,
        { ...restorableSnapshot, id: 'snap-2', label: 'Snapshot 2', messages: [message('m1'), message('m2'), message('m3')] },
        { id: 'snap-other', sessionId: 's2', timestamp: 3, label: 'Other session', messages: [] },
      ],
    });
    render(<ControlBar />);

    // The newest complete snapshot of THIS session is the target.
    fireEvent.click(screen.getByRole('button', { name: restoreNamed('Snapshot 2') }));
    await waitFor(() => {
      expect(useWorkspaceStore.getState().sessions[0]!.messages.map(entry => entry.id))
        .toEqual(['m1', 'm2', 'm3']);
    });
  });

  it('captures the transcript with the snapshot it records', () => {
    useWorkspaceStore.setState({ sessions: [makeSession()], activeSessionId: 's1' });
    render(<ControlBar />);
    fireEvent.click(screen.getByRole('button', { name: i18n.t('anchored.controlbar.save_snapshot') }));
    expect(useWorkspaceStore.getState().snapshots[0]).toMatchObject({
      sessionId: 's1',
      messages: [{ id: 'm1' }, { id: 'm2' }],
    });
    // The snapshot it just wrote is immediately a rollback target.
    expect(screen.getByRole('button', { name: restoreNamed('Snapshot 1') })).toBeEnabled();
  });

  it('serialises rollback attempts and reports the outcome in place', async () => {
    let restore!: (value: void) => void;
    const restoreSnapshot = vi.fn(() => new Promise<void>((done) => { restore = done; }));
    useWorkspaceStore.setState({
      sessions: [makeSession()], activeSessionId: 's1', snapshots: [restorableSnapshot], restoreSnapshot,
    });
    render(<ControlBar />);
    const trigger = screen.getByRole('button', { name: restoreNamed('Snapshot 1') });

    fireEvent.click(trigger);
    fireEvent.click(trigger);
    // The ref mutex refuses the second activation before the bar re-renders.
    expect(restoreSnapshot).toHaveBeenCalledOnce();
    expect(trigger).toBeDisabled();
    expect(trigger).toHaveAttribute('aria-busy', 'true');
    expect(screen.getByRole('status')).toHaveTextContent(i18n.t('anchored.controlbar.rolling_back'));
    await act(async () => { restore(); });
    expect(screen.queryByRole('status')).not.toBeInTheDocument();
  });

  it('keeps a failed rollback on screen and offers the same action again', async () => {
    const restoreSnapshot = vi.fn()
      .mockRejectedValueOnce(new Error('Snapshot session no longer exists'))
      .mockResolvedValueOnce(undefined);
    useWorkspaceStore.setState({
      sessions: [makeSession()], activeSessionId: 's1', snapshots: [restorableSnapshot], restoreSnapshot,
    });
    render(<ControlBar />);
    const trigger = screen.getByRole('button', { name: restoreNamed('Snapshot 1') });

    await act(async () => { fireEvent.click(trigger); });
    expect(screen.getByRole('alert')).toHaveTextContent(i18n.t('anchored.controlbar.rollback_failed', { message: '' }).replace('{{message}}', '').trim());
    expect(screen.getByRole('alert')).toHaveTextContent('Snapshot session no longer exists');
    expect(trigger).toBeEnabled();

    await act(async () => { fireEvent.click(trigger); });
    expect(restoreSnapshot).toHaveBeenCalledTimes(2);
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });
});
