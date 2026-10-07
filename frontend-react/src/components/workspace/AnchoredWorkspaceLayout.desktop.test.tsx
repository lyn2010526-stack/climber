import { act, fireEvent, render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useRef, type ReactNode } from 'react';
import { AnchoredWorkspaceLayout } from './AnchoredWorkspaceLayout';
import { useWorkspaceStore } from '../../store/workspace';

function evaluateMediaQuery(media: string, width: number): boolean {
  const min = /min-width:\s*(\d+)px/.exec(media);
  const max = /max-width:\s*(\d+)px/.exec(media);
  if (!min && !max) return false;
  return (!min || width >= Number(min[1])) && (!max || width <= Number(max[1]));
}

const mediaQueryRegistry = new Map<string, FakeMediaQueryList>();

class FakeMediaQueryList {
  media: string;
  matches: boolean;
  onchange: ((event: { matches: boolean }) => void) | null = null;
  private listeners = new Set<(event: { matches: boolean }) => void>();

  constructor(media: string) {
    this.media = media;
    this.matches = evaluateMediaQuery(media, window.innerWidth);
  }

  addEventListener(type: string, cb: (event: { matches: boolean }) => void) {
    if (type === 'change') this.listeners.add(cb);
  }

  removeEventListener(type: string, cb: (event: { matches: boolean }) => void) {
    if (type === 'change') this.listeners.delete(cb);
  }

  addListener(cb: (event: { matches: boolean }) => void) { this.listeners.add(cb); }
  removeListener(cb: (event: { matches: boolean }) => void) { this.listeners.delete(cb); }
  dispatchEvent() { return false; }

  // Re-reads the live window width and notifies subscribers only on a real flip.
  sync() {
    const next = evaluateMediaQuery(this.media, window.innerWidth);
    if (next === this.matches) return;
    this.matches = next;
    const event = { matches: next };
    this.onchange?.(event);
    for (const cb of this.listeners) cb(event);
  }
}

// The shared test-setup pins matchMedia to a constant `matches: false`, which
// forces the workspace into the drawer layout. This stub resolves min-width /
// max-width queries against the live window width so the three-column branch
// (min-width: 1162px) is reachable.
vi.stubGlobal('matchMedia', (query: string) => {
  let mql = mediaQueryRegistry.get(query);
  if (!mql) {
    mql = new FakeMediaQueryList(query);
    mediaQueryRegistry.set(query, mql);
  }
  return mql;
});

// jsdom never emits matchMedia change events on resize, so forward the window
// resize to every registered query and let useMediaQuery re-read the breakpoint.
window.addEventListener('resize', () => {
  for (const mql of mediaQueryRegistry.values()) mql.sync();
});

const KEY = 'climber.workspace.desktop.v1';
const panels = vi.hoisted(() => new Map<string, {
  resize: (size: string) => void;
  onResize: (size: { inPixels: number; asPercentage: number }, id: string, previous: { inPixels: number; asPercentage: number }) => void;
}>());
vi.mock('../../hooks/useDefaultSession', () => ({ useDefaultSession: () => ({ sessionId: 'real-session-contract' }) }));
vi.mock('../../i18n', () => ({ useI18n: () => ({ t: (key: string) => key }) }));
vi.mock('./AnchoredLeftNav', () => ({ AnchoredLeftNav: ({ onCollapse }: { onCollapse: () => void }) => <nav><button onClick={onCollapse}>Collapse navigation</button></nav> }));
vi.mock('./AnchoredInfoPanel', () => ({ AnchoredInfoPanel: ({ sessionId }: { sessionId: string }) => <aside data-testid="inspect-content">{sessionId}</aside> }));
vi.mock('../agent/AnchoredChatColumn', () => ({ AnchoredChatColumn: ({ sessionId, onToggleInfo }: { sessionId: string; onToggleInfo: () => void }) => <main data-testid="chat"><span>{sessionId}</span><textarea aria-label="Draft" /><button onClick={onToggleInfo}>Inspect</button></main> }));
vi.mock('react-resizable-panels', () => ({
  Group: ({ children }: { children: ReactNode }) => <div>{children}</div>,
  Separator: (props: { className: string; onPointerDown: () => void; onKeyDown: () => void; disabled?: boolean; 'aria-label': string }) => <div role="separator" {...props} />,
  usePanelRef: () => useRef(null),
  Panel: ({ id, panelRef, defaultSize, minSize, maxSize, onResize, children, className }: {
    id: string; panelRef?: { current: unknown }; defaultSize?: string; minSize: string; maxSize?: string;
    onResize?: (size: { inPixels: number; asPercentage: number }, id: string, previous: { inPixels: number; asPercentage: number }) => void;
    children: ReactNode; className: string;
  }) => {
    const size = useRef(Number.parseFloat(defaultSize ?? '600px'));
    const resize = (value: string) => {
      const previous = size.current;
      size.current = Number.parseFloat(value);
      onResize?.({ inPixels: size.current, asPercentage: 0 }, id, { inPixels: previous, asPercentage: 0 });
    };
    if (panelRef) panelRef.current = { resize, collapse: () => resize(id === 'anchored-left' ? '60px' : '0px') };
    if (onResize) panels.set(id, { resize, onResize });
    return <div data-testid={id} data-default-size={defaultSize} data-min-size={minSize} data-max-size={maxSize} className={className}>{children}</div>;
  },
}));

beforeEach(() => {
  localStorage.removeItem(KEY);
  panels.clear();
  mediaQueryRegistry.clear();
  vi.restoreAllMocks();
  Object.defineProperty(window, 'innerWidth', { configurable: true, value: 1280 });
});

describe('Desktop anchored workspace (panel API mocked)', () => {
  it.each([1280, 1440, 1600])('keeps desktop navigation and a collapsed inspect at %ipx', width => {
    Object.defineProperty(window, 'innerWidth', { configurable: true, value: width });
    render(<AnchoredWorkspaceLayout />);
    expect(screen.getByTestId('anchored-workspace')).toHaveAttribute('data-layout', 'three-column');
    expect(screen.getByTestId('anchored-left')).toHaveAttribute('data-default-size', '240px');
    expect(screen.getByTestId('anchored-center')).toHaveAttribute('data-min-size', '600px');
    expect(screen.getByTestId('anchored-right')).toHaveAttribute('data-default-size', '0px');
    expect(screen.getByTestId('anchored-right')).toBeInTheDocument();
    expect(screen.queryByTestId('inspect-content')).toBeNull();
    expect(screen.queryByRole('dialog')).toBeNull();
  });

  it('toggles the default inspect panel and preserves the chat and draft across resize', () => {
    render(<AnchoredWorkspaceLayout />);
    const draft = screen.getByRole('textbox');
    fireEvent.change(draft, { target: { value: 'Keep current SSE session' } });
    expect(screen.queryByTestId('inspect-content')).toBeNull();
    fireEvent.click(screen.getByRole('button', { name: 'Inspect' }));
    expect(screen.getByTestId('inspect-content')).toHaveTextContent('real-session-contract');
    act(() => { Object.defineProperty(window, 'innerWidth', { configurable: true, value: 1280 }); window.dispatchEvent(new Event('resize')); });
    expect(screen.getByRole('textbox')).toBe(draft);
    fireEvent.click(screen.getByLabelText('anchored.layout.collapse_right'));
    expect(screen.queryByTestId('inspect-content')).toBeNull();
    expect(draft).toHaveValue('Keep current SSE session');
  });

  it('exposes forgiving resize targets for both rail boundaries', () => {
    render(<AnchoredWorkspaceLayout />);
    expect(screen.getByTestId('anchored-left-separator')).toHaveClass('workbench-desktop-separator');
    expect(screen.getByTestId('anchored-right-separator')).toHaveClass('workbench-desktop-inspect-separator');
    fireEvent.pointerDown(screen.getByTestId('anchored-right-separator'));
    act(() => panels.get('anchored-right')!.resize('360px'));
    fireEvent.pointerUp(window);
    expect(JSON.parse(localStorage.getItem(KEY)!)).toMatchObject({ rightWidth: 360 });
  });

  it('persists dragged widths and both collapse preferences across remounts', () => {
    const view = render(<AnchoredWorkspaceLayout />);
    fireEvent.pointerDown(screen.getAllByRole('separator')[0]);
    act(() => panels.get('anchored-left')!.resize('280px'));
    fireEvent.pointerUp(window);
    expect(screen.queryByTestId('inspect-content')).toBeNull();
    fireEvent.keyDown(screen.getAllByRole('separator')[1], { key: 'ArrowLeft' });
    act(() => panels.get('anchored-right')!.resize('350px'));
    fireEvent.keyUp(window, { key: 'ArrowLeft' });
    fireEvent.click(screen.getByText('Collapse navigation'));
    view.unmount();
    render(<AnchoredWorkspaceLayout />);
    expect(screen.getByTestId('anchored-left')).toHaveAttribute('data-default-size', '60px');
    expect(screen.getByTestId('anchored-right')).toHaveAttribute('data-default-size', '350px');
    fireEvent.click(screen.getByLabelText('anchored.layout.expand_left'));
    expect(JSON.parse(localStorage.getItem(KEY)!)).toMatchObject({ leftWidth: 280, rightWidth: 350, leftCollapsed: false, rightCollapsed: false });
  });

  it('keeps preferred widths while fitting inspect into a narrower desktop window', () => {
    localStorage.setItem(KEY, JSON.stringify({ leftWidth: 360, rightWidth: 480 }));
    Object.defineProperty(window, 'innerWidth', { configurable: true, value: 1162 });
    render(<AnchoredWorkspaceLayout />);
    expect(JSON.parse(localStorage.getItem(KEY)!)).toMatchObject({ leftWidth: 360, rightWidth: 480 });
    expect(screen.getByTestId('anchored-right')).toHaveAttribute('data-max-size', '380px');
  });

  it.each(['invalid JSON', 'null', '[]', '{"leftWidth":"280","rightCollapsed":"false"}'])('recovers from invalid storage: %s', value => {
    localStorage.setItem(KEY, value);
    render(<AnchoredWorkspaceLayout />);
    expect(screen.getByTestId('anchored-left')).toHaveAttribute('data-default-size', '240px');
    expect(screen.queryByTestId('inspect-content')).toBeNull();
  });

  it('clamps saved dimensions and tolerates storage read and write failures', () => {
    localStorage.setItem(KEY, '{"leftWidth":9999,"rightWidth":-1,"rightCollapsed":false}');
    const view = render(<AnchoredWorkspaceLayout />);
    expect(screen.getByTestId('anchored-left')).toHaveAttribute('data-default-size', '360px');
    expect(screen.getByTestId('anchored-right')).toHaveAttribute('data-default-size', '240px');
    view.unmount();
    vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => { throw new Error('Unavailable'); });
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => { throw new Error('Quota'); });
    render(<AnchoredWorkspaceLayout />);
    expect(screen.queryByTestId('inspect-content')).toBeNull();
  });

  it('exits focus mode with Escape while leaving text-field Escape untouched', () => {
    useWorkspaceStore.setState({ focusMode: true });
    render(<AnchoredWorkspaceLayout />);
    // Escape inside a text field never leaves focus mode.
    fireEvent.keyDown(screen.getByRole('textbox'), { key: 'Escape' });
    expect(useWorkspaceStore.getState().focusMode).toBe(true);
    // Escape anywhere else exits, matching the slim bar's aria-keyshortcuts.
    fireEvent.keyDown(document.body, { key: 'Escape' });
    expect(useWorkspaceStore.getState().focusMode).toBe(false);
  });

  it('collapses both side rails in focus mode and restores the prior layout on exit', () => {
    useWorkspaceStore.setState({ focusMode: false });
    render(<AnchoredWorkspaceLayout />);
    const section = screen.getByTestId('anchored-workspace');
    // The inspect rail starts collapsed and opens only on explicit user action.
    expect(screen.queryByTestId('inspect-content')).toBeNull();
    expect(screen.getByText('Collapse navigation')).toBeInTheDocument();
    expect(section).toHaveAttribute('data-focus', 'false');
    expect(section).toHaveAttribute('data-inspect-open', 'false');

    fireEvent.click(screen.getByLabelText('anchored.controlbar.enter_focus'));

    expect(section).toHaveAttribute('data-focus', 'true');
    // Both rails yield to the canvas: the navigation collapses to its rail
    // button and the inspect panel remains closed.
    expect(screen.queryByText('Collapse navigation')).toBeNull();
    expect(screen.getByLabelText('anchored.layout.expand_left')).toBeInTheDocument();
    expect(screen.queryByTestId('inspect-content')).toBeNull();
    expect(section).toHaveAttribute('data-inspect-open', 'false');

    fireEvent.click(screen.getByLabelText('anchored.controlbar.exit_focus'));

    expect(section).toHaveAttribute('data-focus', 'false');
    expect(screen.getByText('Collapse navigation')).toBeInTheDocument();
    expect(screen.queryByTestId('inspect-content')).toBeNull();
    expect(section).toHaveAttribute('data-inspect-open', 'false');
    // The mode never rewrites the user's own collapse preferences.
    expect(JSON.parse(localStorage.getItem(KEY)!)).toMatchObject({ leftCollapsed: false, rightCollapsed: true });
  });

  it('closes the side drawers in focus mode and restores them on exit', () => {
    Object.defineProperty(window, 'innerWidth', { configurable: true, value: 900 });
    useWorkspaceStore.setState({ focusMode: false });
    render(<AnchoredWorkspaceLayout />);
    const section = screen.getByTestId('anchored-workspace');
    expect(section).toHaveAttribute('data-layout', 'drawers');
    fireEvent.click(screen.getByLabelText('anchored.layout.expand_left'));
    expect(screen.getByTestId('anchored-left-drawer')).toBeInTheDocument();

    fireEvent.click(screen.getByLabelText('anchored.controlbar.enter_focus'));

    expect(section).toHaveAttribute('data-focus', 'true');
    expect(screen.queryByTestId('anchored-left-drawer')).toBeNull();

    fireEvent.click(screen.getByLabelText('anchored.controlbar.exit_focus'));

    expect(section).toHaveAttribute('data-focus', 'false');
    expect(screen.getByTestId('anchored-left-drawer')).toBeInTheDocument();
  });
});
