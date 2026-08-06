import { describe, it, expect, vi, beforeAll, afterAll } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import App from '../App';
import { ThemeProvider } from '../hooks/useTheme.tsx';
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

describe('App mobile routing', () => {
  const originalInnerWidth = window.innerWidth;

  beforeAll(() => {
    Object.defineProperty(window, 'innerWidth', { value: 375, writable: true });
  });

  afterAll(() => {
    Object.defineProperty(window, 'innerWidth', { value: originalInnerWidth, writable: true });
  });

  it('renders mobile layout on small screens', async () => {
    render(
      <ThemeProvider>
        <ErrorBoundary>
          <App />
        </ErrorBoundary>
      </ThemeProvider>
    );
    await waitFor(() => {
      expect(screen.getByText('Climber')).toBeDefined();
    });
  });

  it('renders mobile chat page by default', async () => {
    render(
      <ThemeProvider>
        <ErrorBoundary>
          <App />
        </ErrorBoundary>
      </ThemeProvider>
    );
    await waitFor(() => {
      expect(screen.getByText('Mobile Chat')).toBeDefined();
    });
  });
});
