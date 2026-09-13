import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, act, fireEvent } from '@testing-library/react';
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

vi.mock('../components/workspace/WorkspaceLayout', () => ({
  WorkspaceLayout: () => <div data-testid="desktop-workspace">Desktop Workspace</div>,
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

vi.mock('../components/workspace/GlobalSearch', () => ({
  GlobalSearch: () => null,
}));

vi.mock('../components/workspace/CommandPalette', () => ({
  default: () => null,
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
    const current = document.querySelector('aside [aria-current="page"]');
    expect(current?.textContent).toContain('Chat');
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

  it('renders the mobile shell at 767px', async () => {
    setViewport(375);
    renderApp();
    await waitFor(() => {
      expect(screen.getByText('Mobile Chat')).toBeInTheDocument();
    });
    expect(screen.queryByTestId('desktop-workspace')).toBeNull();
  });

  it('collapses the sidebar automatically on compact desktop (768px)', async () => {
    setViewport(768);
    renderApp();
    await waitFor(() => {
      expect(screen.getByTestId('desktop-workspace')).toBeInTheDocument();
    });
    const toggle = screen.getByRole('button', { name: 'Expand sidebar' });
    expect(toggle).toHaveAttribute('aria-expanded', 'false');
  });

  it('expands the sidebar by default on full desktop (1024px) with no stored choice', async () => {
    setViewport(1024);
    renderApp();
    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Collapse sidebar' })).toHaveAttribute('aria-expanded', 'true');
    });
  });

  it('restores the explicit sidebar choice across breakpoints', async () => {
    setViewport(1024);
    renderApp();
    await waitFor(() => {
      expect(screen.getByTestId('desktop-workspace')).toBeInTheDocument();
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
    renderApp();
    await waitFor(() => {
      expect(screen.getByTestId('desktop-workspace')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByRole('button', { name: 'Agents', expanded: undefined }));
    await waitFor(() => {
      expect(screen.getByText('Agents Page')).toBeInTheDocument();
    });
    expect(window.location.hash).toBe('#agents');
    const markers = document.querySelectorAll('aside [aria-current="page"]');
    expect(markers).toHaveLength(1);
    expect(markers[0].textContent).toContain('Agents');
  });
});
