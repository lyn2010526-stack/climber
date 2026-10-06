import { act, cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { AnchoredLeftNav } from './AnchoredLeftNav';
import { CLIMBER_MARK } from '../brand/ClimberMark';
import { api } from '../../api';
import { useWorkspaceStore, type Session } from '../../store/workspace';

vi.mock('../../api', () => ({ api: { listSkills: vi.fn().mockResolvedValue([]), createSession: vi.fn(), deleteSession: vi.fn(), toggleSkill: vi.fn() } }));
vi.mock('../../lib/api-client', () => ({ apiClient: { get: vi.fn().mockResolvedValue({ username: 'tester' }) } }));
vi.mock('../../i18n', () => ({ useI18n: () => ({ t: (key: string) => key }) }));
vi.mock('../../i18n/utils', () => ({ formatTime: (value: number) => `t:${value}` }));
const session = (id: string, title = id, createdAt = 1): Session => ({ id, title, createdAt, status: 'idle', messages: [], activeSkills: [], activeTools: [] });
beforeEach(() => {
  vi.clearAllMocks();
  localStorage.removeItem('anchored.pinned-sessions');
  useWorkspaceStore.setState({ sessions: [session('first'), session('second', 'Second', 2)], activeSessionId: 'first' });
  vi.mocked(api.listSkills).mockResolvedValue([]);
});
afterEach(() => { cleanup(); vi.restoreAllMocks(); });

function openMenu(id = 'first') {
  fireEvent.contextMenu(screen.getByRole('button', { name: id }), { clientX: 20, clientY: 40 });
}

describe('anchored settings entry', () => {
  it('keeps sessions primary and settings collapsed at the bottom', async () => {
    const collapse = vi.fn();
    render(<AnchoredLeftNav onCollapse={collapse} />);
    await waitFor(() => expect(screen.getByText('tester')).toBeInTheDocument());
    const settings = screen.getByRole('button', { name: 'settings.title' });
    expect(settings).toHaveAttribute('aria-expanded', 'false');
    expect(settings.querySelector('svg')).toHaveAttribute('data-workbench-icon', 'settings');
    expect(screen.getByTestId('anchored-logo').querySelector('polyline')).toHaveAttribute('points', CLIMBER_MARK.ridge);
    const header = screen.getByTestId('anchored-logo').parentElement!;
    expect(within(header).queryByRole('link')).toBeNull();
    fireEvent.click(within(header).getByRole('button', { name: 'anchored.layout.collapse_left' }));
    expect(collapse).toHaveBeenCalledOnce();
    const nav = screen.getByTestId('anchored-left-nav');
    const sessions = screen.getByTestId('anchored-sessions');
    expect(screen.queryByTestId('anchored-skills')).toBeNull();
    fireEvent.click(settings);
    const skills = screen.getByTestId('anchored-skills');
    expect(within(skills).getByRole('button')).toHaveAttribute('aria-expanded', 'false');
    expect(within(screen.getByTestId('anchored-profiles')).getByRole('button')).toHaveAttribute('aria-expanded', 'false');
    expect(screen.getByRole('link', { name: 'anchored.nav.open_settings' })).toHaveAttribute('href', '#settings');
    expect(nav.contains(sessions)).toBe(true);
    expect(sessions.compareDocumentPosition(skills) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });

  it('brand reuses the active or first existing session without creating', () => {
    render(<AnchoredLeftNav />);
    fireEvent.click(screen.getByTestId('anchored-logo'));
    fireEvent.click(screen.getByTestId('anchored-logo'));
    expect(useWorkspaceStore.getState().activeSessionId).toBe('first');
    act(() => useWorkspaceStore.setState({ activeSessionId: null }));
    fireEvent.click(screen.getByTestId('anchored-logo'));
    expect(useWorkspaceStore.getState().activeSessionId).toBe('first');
    act(() => useWorkspaceStore.setState({ sessions: [], activeSessionId: null }));
    fireEvent.click(screen.getByTestId('anchored-logo'));
    expect(api.createSession).not.toHaveBeenCalled();
  });

  it('creates once while pending and preserves the backend status', async () => {
    let resolve!: (value: unknown) => void;
    vi.mocked(api.createSession).mockReturnValue(new Promise((done) => { resolve = done; }));
    render(<AnchoredLeftNav />);
    const create = screen.getByRole('button', { name: 'anchored.nav.new_session' });
    fireEvent.click(create);
    fireEvent.click(create);
    expect(create).toBeDisabled();
    expect(api.createSession).toHaveBeenCalledExactlyOnceWith({ title: 'anchored.nav.default_title' });
    expect(useWorkspaceStore.getState().sessions).toHaveLength(2);
    await act(async () => resolve({ id: 'new', title: 'Server title', status: 'pending', created_at: '2026-10-01T00:00:00Z' }));
    expect(useWorkspaceStore.getState().activeSessionId).toBe('new');
    expect(useWorkspaceStore.getState().sessions.find((item) => item.id === 'new')).toMatchObject({ title: 'Server title', status: 'pending', createdAt: Date.parse('2026-10-01T00:00:00Z') });
  });

  it.each([new Error('503 unavailable'), null])('shows creation failure and keeps the current session (%s)', async (cause) => {
    if (cause) vi.mocked(api.createSession).mockRejectedValueOnce(cause);
    else vi.mocked(api.createSession).mockResolvedValueOnce({ title: 'missing id' });
    render(<AnchoredLeftNav />);
    fireEvent.click(screen.getByRole('button', { name: 'anchored.nav.new_session' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('anchored.nav.create_failed');
    expect(useWorkspaceStore.getState().sessions).toHaveLength(2);
    expect(useWorkspaceStore.getState().activeSessionId).toBe('first');
    expect(screen.getByRole('button', { name: 'anchored.nav.new_session' })).toBeEnabled();
  });

  it('offers no rename action while no backend write contract exists', () => {
    render(<AnchoredLeftNav />);
    openMenu();
    expect(screen.queryByRole('menuitem', { name: 'anchored.nav.rename_session' })).not.toBeInTheDocument();
  });

  it('cancelling confirmation leaves the backend and local session untouched', () => {
    const confirm = vi.spyOn(window, 'confirm').mockReturnValue(false);
    render(<AnchoredLeftNav />);
    openMenu();
    fireEvent.click(screen.getByRole('menuitem', { name: 'anchored.nav.delete_session' }));
    expect(confirm).toHaveBeenCalledWith(expect.stringContaining('anchored.nav.delete_confirm'));
    expect(api.deleteSession).not.toHaveBeenCalled();
    expect(useWorkspaceStore.getState().sessions).toHaveLength(2);
  });

  it('keeps the session and selection when confirmed deletion fails', async () => {
    vi.spyOn(window, 'confirm').mockReturnValue(true);
    vi.mocked(api.deleteSession).mockRejectedValueOnce(new Error('403 forbidden'));
    render(<AnchoredLeftNav />);
    openMenu();
    fireEvent.click(screen.getByRole('menuitem', { name: 'anchored.nav.delete_session' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('anchored.nav.delete_failed');
    expect(useWorkspaceStore.getState().sessions).toHaveLength(2);
    expect(useWorkspaceStore.getState().activeSessionId).toBe('first');
  });

  it('removes a confirmed session only after backend success', async () => {
    vi.spyOn(window, 'confirm').mockReturnValue(true);
    let resolve!: (value: unknown) => void;
    vi.mocked(api.deleteSession).mockReturnValueOnce(new Promise((done) => { resolve = done; }));
    render(<AnchoredLeftNav />);
    openMenu();
    fireEvent.click(screen.getByRole('menuitem', { name: 'anchored.nav.delete_session' }));
    expect(api.deleteSession).toHaveBeenCalledExactlyOnceWith('first');
    expect(useWorkspaceStore.getState().sessions).toHaveLength(2);
    await act(async () => resolve({ success: true }));
    expect(useWorkspaceStore.getState().sessions.map((item) => item.id)).toEqual(['second']);
    expect(useWorkspaceStore.getState().activeSessionId).toBe('second');
  });

  it('filters sessions, selects results, and provides a keyboard-accessible menu', () => {
    render(<AnchoredLeftNav />);
    fireEvent.change(screen.getByRole('textbox', { name: 'anchored.nav.search_sessions' }), { target: { value: 'SECOND' } });
    expect(screen.queryByRole('button', { name: 'first' })).toBeNull();
    fireEvent.click(screen.getByRole('button', { name: 'Second' }));
    expect(useWorkspaceStore.getState().activeSessionId).toBe('second');
    fireEvent.click(screen.getByRole('button', { name: 'anchored.nav.session_menu: Second' }));
    fireEvent.click(screen.getByRole('menuitem', { name: 'anchored.nav.pin' }));
    expect(JSON.parse(localStorage.getItem('anchored.pinned-sessions')!)).toEqual(['second']);
    fireEvent.change(screen.getByRole('textbox', { name: 'anchored.nav.search_sessions' }), { target: { value: 'unmatched' } });
    expect(screen.getByText('anchored.nav.no_matching_sessions')).toBeInTheDocument();
  });

  it('closes the session menu with Escape', () => {
    render(<AnchoredLeftNav />);
    openMenu();
    expect(screen.getByRole('menu')).toBeInTheDocument();
    fireEvent.keyDown(window, { key: 'Escape' });
    expect(screen.queryByRole('menu')).toBeNull();
  });
});

describe('anchored session list spec', () => {
  const startOfToday = (() => {
    const date = new Date();
    date.setHours(0, 0, 0, 0);
    return date.getTime();
  })();

  it('renders 40px rows with icon, title and the latest activity time', () => {
    const message = (timestamp: number) => ({ id: String(timestamp), type: 'user' as const, content: '', timestamp });
    useWorkspaceStore.setState({
      sessions: [
        { ...session('latest'), createdAt: startOfToday, messages: [message(startOfToday), message(startOfToday + 3_600_000)] },
      ],
      activeSessionId: 'latest',
    });
    render(<AnchoredLeftNav />);
    const row = screen.getByRole('button', { name: 'latest' });
    expect(row).toHaveClass('h-10');
    expect(row.querySelector('[data-workbench-icon]')).toBeNull();
    expect(row.querySelector('svg')).toBeTruthy();
    // The newest message timestamp is the right-hand value; the time is hidden
    // from the accessible name so the row still announces just the title.
    expect(row.textContent).toContain(`t:${startOfToday + 3_600_000}`);
  });

  it('groups sessions into today, yesterday and earlier', () => {
    const dayMs = 24 * 60 * 60 * 1000;
    useWorkspaceStore.setState({
      sessions: [
        session('today', 'Today', startOfToday),
        session('yesterday', 'Yesterday', startOfToday - dayMs),
        session('older', 'Older', startOfToday - 5 * dayMs),
      ],
      activeSessionId: 'today',
    });
    render(<AnchoredLeftNav />);
    expect(screen.getByRole('heading', { name: '今天' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: '昨天' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: '更早' })).toBeInTheDocument();
  });

  it('highlights the active row with the primary accent', () => {
    render(<AnchoredLeftNav />);
    const active = screen.getByRole('button', { name: 'first' });
    expect(active).toHaveAttribute('aria-current', 'true');
    expect(active.className).toContain('--color-accent-subtle');
  });
});
