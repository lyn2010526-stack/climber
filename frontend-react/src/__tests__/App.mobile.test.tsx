import { describe, it, expect, vi, beforeAll, afterAll, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import App from '../App';
import { ThemeProvider } from '../hooks/useTheme';
import { ErrorBoundary } from '../components/ErrorBoundary';

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

vi.mock('../pages/mobile/MobileAgentsPage', () => ({
  MobileAgentsPage: () => <div>Mobile Agents</div>,
}));

vi.mock('../pages/PluginsPage', () => ({
  PluginsPage: () => <div>Mobile Plugins</div>,
}));

describe('App mobile routing', () => {
  const originalInnerWidth = window.innerWidth;

  beforeAll(() => {
    Object.defineProperty(window, 'innerWidth', { value: 375, writable: true });
  });

  afterAll(() => {
    Object.defineProperty(window, 'innerWidth', { value: originalInnerWidth, writable: true });
  });

  beforeEach(() => {
    window.history.replaceState(null, '', window.location.pathname);
  });

  it('renders mobile layout on small screens', async () => {
    render(
      <ThemeProvider>
        <ErrorBoundary>
          <App />
        </ErrorBoundary>
      </ThemeProvider>
    );
    expect(await screen.findByRole('heading', { name: 'Climber' }, { timeout: 5000 })).toBeDefined();
  });

  it('renders mobile chat page by default', async () => {
    render(
      <ThemeProvider>
        <ErrorBoundary>
          <App />
        </ErrorBoundary>
      </ThemeProvider>
    );
    expect(await screen.findByText('Mobile Chat', {}, { timeout: 5000 })).toBeDefined();
  });

  it('renders shared responsive pages for valid mobile hashes', async () => {
    window.location.hash = '#plugins';

    render(
      <ThemeProvider>
        <ErrorBoundary>
          <App />
        </ErrorBoundary>
      </ThemeProvider>
    );

    expect(await screen.findByText('Mobile Plugins', {}, { timeout: 5000 })).toBeDefined();
  });
});
