import { act, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { ReactNode } from 'react';
import App from '../App';
import { AnchoredWorkspaceLayout, ANCHORED_LAYOUT_GEOMETRY } from '../components/workspace/AnchoredWorkspaceLayout';
import { AdaptiveMobileLayout } from '../components/layout/AdaptiveMobileLayout';

let width = 390;
const listeners = new Set<() => void>();
vi.stubGlobal('matchMedia', (query: string) => ({
  get matches() {
    const min = /min-width:\s*(\d+)px/.exec(query);
    const max = /max-width:\s*(\d+)px/.exec(query);
    return (!min || width >= Number(min[1])) && (!max || width <= Number(max[1]));
  },
  addEventListener: (_: string, cb: () => void) => listeners.add(cb),
  removeEventListener: (_: string, cb: () => void) => listeners.delete(cb),
}));
vi.mock('../hooks/useDefaultSession', () => ({ useDefaultSession: () => ({ sessionId: 'shared-session' }) }));
vi.mock('../components/workspace/AnchoredLeftNav', () => ({ AnchoredLeftNav: ({ onCollapse }: { onCollapse: () => void }) => <nav data-testid="left-nav"><a href="#settings">Settings</a><button onClick={onCollapse}>Collapse</button></nav> }));
vi.mock('../components/workspace/AnchoredInfoPanel', () => ({ AnchoredInfoPanel: ({ sessionId }: { sessionId: string }) => <div data-testid="info-panel">{sessionId}<button>Last info action</button></div> }));
vi.mock('../components/agent/AnchoredChatColumn', () => ({ AnchoredChatColumn: ({ sessionId, onToggleInfo }: { sessionId: string; onToggleInfo: () => void }) => <div data-testid="anchored-chat-column">{sessionId}<textarea aria-label="Composer" /><button onClick={onToggleInfo}>Info</button></div> }));
vi.mock('react-resizable-panels', () => ({
  Group: ({ children }: { children: ReactNode }) => <div>{children}</div>,
  Panel: ({ children, id, minSize }: { children: ReactNode; id: string; minSize: string }) => <div data-testid={id} data-min-size={minSize}>{children}</div>,
  Separator: () => <div role="separator" />,
  usePanelRef: () => ({ current: { collapse: vi.fn(), expand: vi.fn() } }),
}));
vi.mock('../components/privacy', () => ({ AppLockGate: ({ children }: { children: ReactNode }) => children }));
vi.mock('../components/shell/BootSplash', () => ({ BootSplash: () => null }));
vi.mock('../components/ios', () => ({ IOsToaster: () => null }));
vi.mock('../pages/SettingsPage', () => ({ SettingsPage: () => <div>Actual settings route</div> }));

beforeEach(() => {
  width = 390;
  window.location.hash = '#chat';
});

describe('Anchored responsive entry', () => {
  it.each([390, 768, 1280])('mounts the anchored entry at %ipx with one chat and one navigation', async value => {
    width = value;
    render(<App />);
    expect(await screen.findByTestId('anchored-workspace')).toHaveAttribute('data-layout', value >= 1162 ? 'three-column' : 'drawers');
    expect(screen.getAllByTestId('anchored-chat-column')).toHaveLength(1);
    expect(document.querySelector('.mobile-bottom-nav')).toBeNull();
    expect(document.querySelector('.mobile-context-bar')).toBeNull();
    expect(screen.getByTestId('anchored-center')).toHaveAttribute('data-min-size', value >= 1162 ? '600px' : '0px');
  });

  it('keeps the chat and draft mounted while resizing and opening either drawer', async () => {
    const user = userEvent.setup();
    width = 1280;
    render(<AnchoredWorkspaceLayout />);
    const composer = screen.getByRole('textbox');
    await user.type(composer, 'preserved draft');
    act(() => { width = 390; listeners.forEach(cb => cb()); });
    expect(screen.getByRole('textbox')).toBe(composer);
    const trigger = screen.getByRole('button', { name: /展开|expand/i });
    await user.click(trigger);
    const dialog = screen.getByRole('dialog');
    expect(dialog).toHaveAttribute('aria-modal', 'true');
    expect(trigger).toHaveAttribute('aria-expanded', 'true');
    await user.keyboard('{Shift>}{Tab}{/Shift}');
    expect(dialog.contains(document.activeElement)).toBe(true);
    await user.keyboard('{Escape}');
    await waitFor(() => expect(screen.queryByRole('dialog')).toBeNull());
    expect(trigger).toHaveFocus();
    await user.click(screen.getByRole('button', { name: 'Info' }));
    expect(screen.getByTestId('info-panel')).toHaveTextContent('shared-session');
    await user.click(document.querySelector('.modal-overlay')!);
    await waitFor(() => expect(screen.queryByRole('dialog')).toBeNull());
    expect(screen.getByRole('button', { name: 'Info' })).toHaveFocus();
    expect(composer).toHaveValue('preserved draft');
  });

  it('renders settings content through the mobile shell and the App hash route', async () => {
    const view = render(<AdaptiveMobileLayout currentPage="settings" onNavigate={vi.fn()}><div>Settings content</div></AdaptiveMobileLayout>);
    expect(screen.getByText('Settings content')).toBeInTheDocument();
    view.unmount();
    window.location.hash = '#settings';
    render(<App />);
    expect(await screen.findByText('Actual settings route')).toBeInTheDocument();
  });

  it.each(['Control', 'Meta'])('keeps %s+K and settings navigation working in the mobile anchored entry', async modifier => {
    const user = userEvent.setup();
    render(<App />);
    await screen.findByTestId('anchored-workspace');
    await user.keyboard(`{${modifier}>}k{/${modifier}}`);
    expect(screen.getByRole('combobox')).toHaveFocus();
    await user.keyboard('{Escape}');
    expect(screen.queryByRole('dialog')).toBeNull();
    await user.keyboard(`{${modifier}>}k{/${modifier}}`);
    await user.type(screen.getByRole('combobox'), 'Settings');
    await user.keyboard('{Enter}');
    expect(await screen.findByText('Actual settings route')).toBeInTheDocument();
    expect(window.location.hash).toBe('#settings');
    expect(screen.queryByRole('dialog')).toBeNull();
  });

  it('clamps chat and drawers to the visual viewport and releases listeners', async () => {
    const visual = new EventTarget();
    Object.assign(visual, { height: 420, offsetTop: 12, scale: 1 });
    vi.stubGlobal('visualViewport', visual);
    const view = render(<AnchoredWorkspaceLayout />);
    expect(screen.getByTestId('anchored-workspace')).toHaveStyle({ height: '420px', top: '12px' });
    await userEvent.click(screen.getByRole('button', { name: 'Info' }));
    expect(screen.getByRole('dialog')).toHaveStyle({ height: '420px', top: '12px' });
    act(() => { Object.assign(visual, { height: 300 }); visual.dispatchEvent(new Event('resize')); });
    expect(screen.getByTestId('anchored-workspace')).toHaveStyle({ height: '300px' });
    view.unmount();
    vi.stubGlobal('visualViewport', undefined);
  });

  it('retains anchored desktop geometry', () => {
    expect(ANCHORED_LAYOUT_GEOMETRY).toMatchObject({ LEFT_DEFAULT: 240, LEFT_MIN: 180, LEFT_MAX: 360, LEFT_COLLAPSED: 60, CENTER_MIN: 600, RIGHT_DEFAULT: 320, RIGHT_MIN: 240, RIGHT_MAX: 480, RIGHT_COLLAPSED: 0, THREE_COLUMN_MIN: 1162 });
  });
});
