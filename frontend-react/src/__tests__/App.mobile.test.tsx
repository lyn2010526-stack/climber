import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, act, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import App from '../App';
import i18n from '../i18n';
import { ThemeProvider } from '../hooks/useTheme.tsx';
import { ErrorBoundary } from '../components/ErrorBoundary';

function evaluateMedia(media: string, width: number): boolean {
  const min = /min-width:\s*(\d+)px/.exec(media);
  const max = /max-width:\s*(\d+)px/.exec(media);
  if (!min && !max) return false;
  return (!min || width >= Number(min[1])) && (!max || width <= Number(max[1]));
}

const mqlRegistry = new Map<string, FakeMediaQueryList>();

class FakeMediaQueryList {
  media: string;
  matches: boolean;
  private listeners = new Set<(event: { matches: boolean }) => void>();

  constructor(media: string, width: number) {
    this.media = media;
    this.matches = evaluateMedia(media, width);
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
  onchange: ((event: { matches: boolean }) => void) | null = null;

  _applyWidth(width: number) {
    const next = evaluateMedia(this.media, width);
    if (next !== this.matches) {
      this.matches = next;
      for (const cb of this.listeners) cb({ matches: next });
    }
  }
}

let viewportWidth = 1280;

function setViewport(width: number) {
  viewportWidth = width;
  act(() => {
    for (const mql of mqlRegistry.values()) mql._applyWidth(width);
  });
}

beforeEach(async () => {
  localStorage.clear();
  localStorage.setItem('i18next_lng', 'en');
  // The privacy lock gate reads this opt-out; shell tests target the chat
  // surface, not the first-run PIN setup.
  localStorage.setItem('climber.privacy.skipped', '1');
  await act(async () => { await i18n.changeLanguage('en'); });
  window.location.hash = '';
});

vi.stubGlobal('matchMedia', (query: string) => {
  let mql = mqlRegistry.get(query);
  if (!mql) {
    mql = new FakeMediaQueryList(query, viewportWidth);
    mqlRegistry.set(query, mql);
  }
  return mql;
});

vi.mock('../components/workspace/AnchoredWorkspaceLayout', () => ({
  AnchoredWorkspaceLayout: () => <div data-testid="desktop-workspace">Desktop Workspace</div>,
}));

vi.mock('../pages/MobileChatPage', () => ({
  MobileChatPage: () => <div>Mobile Chat</div>,
}));

vi.mock('../pages/mobile/MobileFactoryPage', () => ({
  MobileFactoryPage: () => <div>Mobile Factory</div>,
}));

vi.mock('../pages/mobile/MobileClusterPage', () => ({
  MobileClusterPage: () => <div>Mobile Cluster</div>,
}));

vi.mock('../pages/mobile/MobileTasksPage', () => ({
  MobileTasksPage: () => <div>Mobile Tasks</div>,
}));

vi.mock('../pages/AgentsPage', () => ({
  AgentsPage: () => <div>Agents Page</div>,
}));

vi.mock('../components/ios', () => ({
  IOsToaster: () => null,
}));

vi.mock('../components/LanguageSwitcher', () => ({
  LanguageSwitcher: () => null,
}));

function renderApp() {
  return render(
    <ThemeProvider>
      <ErrorBoundary>
        <App />
      </ErrorBoundary>
    </ThemeProvider>,
  );
}

describe('Desktop-first shell contract', () => {
  it.each(['Control', 'Meta'])('toggles the mobile command palette with %s+K and closes with Escape', async (modifier) => {
    const user = userEvent.setup();
    setViewport(390);
    renderApp();
    // Below the breakpoint the conversation entry is the anchored workbench
    // itself; there is no second mobile chat surface to mount.
    expect(await screen.findByTestId('desktop-workspace')).toBeInTheDocument();
    expect(screen.queryByText('Mobile Chat')).toBeNull();
    expect(document.querySelector('input[type="password"]')).toBeNull();

    await user.keyboard(`{${modifier}>}k{/${modifier}}`);
    expect(screen.getAllByRole('dialog')).toHaveLength(1);
    expect(screen.getByRole('combobox')).toHaveFocus();
    await user.keyboard(`{${modifier}>}k{/${modifier}}`);
    expect(screen.queryByRole('dialog')).toBeNull();

    await user.keyboard(`{${modifier}>}k{/${modifier}}`);
    await user.keyboard('{Escape}');
    expect(screen.queryByRole('dialog')).toBeNull();
  });

  it('navigates from the mobile command palette and closes it', async () => {
    const user = userEvent.setup();
    setViewport(390);
    renderApp();
    await user.keyboard('{Control>}k{/Control}');
    await user.type(screen.getByRole('combobox'), 'Agents');
    await user.keyboard('{Enter}');
    expect(await screen.findByText('Agents Page')).toBeInTheDocument();
    expect(window.location.hash).toBe('#agents');
    expect(screen.queryByRole('dialog')).toBeNull();
  });

  it('preserves global search across the mobile breakpoint and switches to commands exclusively', async () => {
    const user = userEvent.setup();
    setViewport(1280);
    renderApp();
    await screen.findByTestId('desktop-workspace');
    // The chat surface uses the command palette as its global search entry.
    await user.keyboard('{Control>}k{/Control}');
    const search = screen.getByRole('combobox');
    await user.type(search, 'a');

    setViewport(390);
    expect(screen.getAllByRole('dialog')).toHaveLength(1);
    expect(screen.getByRole('combobox')).toBe(search);
    expect(search).toHaveValue('a');
    // Reopen on mobile so the query starts fresh, mirroring the palette being
    // the commands-exclusive search entry.
    await user.keyboard('{Escape}');
    await user.keyboard('{Control>}k{/Control}');
    await user.type(screen.getByRole('combobox'), 'Agents');
    setViewport(1280);
    expect(screen.getAllByRole('dialog')).toHaveLength(1);
    expect(screen.getByRole('combobox')).toHaveValue('Agents');
    await user.keyboard('{Escape}');
    expect(screen.queryByRole('dialog')).toBeNull();
  });

  it('renders the shell immediately without any login gate or auth request', async () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockImplementation(async () => {
      throw new Error('unexpected network call');
    });
    setViewport(1440);
    renderApp();
    await waitFor(() => {
      expect(screen.getByTestId('desktop-workspace')).toBeInTheDocument();
    });
    expect(fetchSpy).not.toHaveBeenCalled();
    expect(document.querySelector('input[type="password"]')).toBeNull();
    fetchSpy.mockRestore();
  });

  it('defaults to chat when hash is missing', async () => {
    setViewport(1280);
    renderApp();
    await waitFor(() => {
      expect(screen.getByTestId('desktop-workspace')).toBeInTheDocument();
    });
    // The chat surface renders the anchored three-column workspace; the old
    // aside sidebar only exists on non-chat routes now.
    expect(document.querySelector('aside')).toBeNull();
  });

  it('falls back to chat for unknown hashes', async () => {
    window.location.hash = 'no-such-page';
    setViewport(1280);
    renderApp();
    await waitFor(() => {
      expect(screen.getByTestId('desktop-workspace')).toBeInTheDocument();
    });
  });

  it('falls back to chat for #login instead of rendering a login screen', async () => {
    window.location.hash = 'login';
    setViewport(1280);
    renderApp();
    await waitFor(() => {
      expect(screen.getByTestId('desktop-workspace')).toBeInTheDocument();
    });
    expect(document.querySelector('input[type="password"]')).toBeNull();
  });

  it('mounts the anchored chat below the breakpoint, outside the mobile shell', async () => {
    setViewport(375);
    renderApp();
    expect(await screen.findByTestId('desktop-workspace')).toBeInTheDocument();
    expect(screen.queryByText('Mobile Chat')).toBeNull();
  });

  it('lands a page the mobile shell cannot use on the anchored chat', async () => {
    window.location.hash = 'traces';
    setViewport(375);
    renderApp();
    // The shell redirects an unusable page to the conversation entry, so the
    // anchored workbench is what a reader reaches and the desktop page is not
    // rendered.
    expect(await screen.findByTestId('desktop-workspace')).toBeInTheDocument();
    expect(window.location.hash).toBe('#chat');
    expect(screen.queryByText('Traces Page')).toBeNull();
  });

  it('collapses the sidebar automatically on compact desktop (768px)', async () => {
    setViewport(768);
    window.location.hash = 'agents';
    renderApp();
    await waitFor(() => {
      expect(screen.getByText('Agents Page')).toBeInTheDocument();
    });
    const toggle = screen.getByRole('button', { name: 'Expand sidebar' });
    expect(toggle).toHaveAttribute('aria-expanded', 'false');
  });

  it('expands the sidebar by default on full desktop (1024px) with no stored choice', async () => {
    setViewport(1024);
    window.location.hash = 'agents';
    renderApp();
    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Collapse sidebar' })).toHaveAttribute('aria-expanded', 'true');
    });
  });

  it('restores the explicit sidebar choice across breakpoints', async () => {
    setViewport(1024);
    window.location.hash = 'agents';
    renderApp();
    await waitFor(() => {
      expect(screen.getByText('Agents Page')).toBeInTheDocument();
    });

    const toggle = () => screen.getByRole('button', { name: /sidebar/i });

    expect(toggle()).toHaveAttribute('aria-expanded', 'true');
    fireEvent.click(toggle());
    expect(toggle()).toHaveAttribute('aria-expanded', 'false');
    expect(localStorage.getItem('climber.sidebar')).toBe('0');

    setViewport(768);
    expect(toggle()).toHaveAttribute('aria-expanded', 'false');

    setViewport(1024);
    expect(toggle()).toHaveAttribute('aria-expanded', 'false');

    fireEvent.click(toggle());
    expect(localStorage.getItem('climber.sidebar')).toBe('1');

    setViewport(768);
    expect(toggle()).toHaveAttribute('aria-expanded', 'false');

    setViewport(1024);
    await waitFor(() => {
      expect(toggle()).toHaveAttribute('aria-expanded', 'true');
    });
  });

  it('keeps exactly one aria-current page marker on the active core nav item', async () => {
    setViewport(1280);
    window.location.hash = 'agents';
    renderApp();
    await waitFor(() => {
      expect(screen.getByText('Agents Page')).toBeInTheDocument();
    });
    expect(window.location.hash).toBe('#agents');
    const markers = document.querySelectorAll('aside [aria-current="page"]');
    expect(markers).toHaveLength(1);
    expect(markers[0].textContent).toContain('Agents');
  });
});
