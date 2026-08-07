import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { RouteGuard } from '../components/route-guard/RouteGuard';
import { useAuthStore } from '../store/auth';
import { useCurrentPage } from '../store/page';

vi.mock('../store/auth', () => ({
  useAuthStore: vi.fn(),
}));

vi.mock('../store/page', () => ({
  useCurrentPage: vi.fn(),
}));

describe('RouteGuard', () => {
  const mockSetPage = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    (useCurrentPage as any).mockReturnValue(mockSetPage);
  });

  it('renders children when authenticated and requireAuth is true', () => {
    (useAuthStore as any).mockReturnValue(true);
    render(
      <RouteGuard requireAuth>
        <div data-testid="protected">Protected Content</div>
      </RouteGuard>
    );
    expect(screen.getByTestId('protected')).toBeDefined();
  });

  it('renders login redirect when not authenticated and requireAuth is true', () => {
    (useAuthStore as any).mockReturnValue(false);
    render(
      <RouteGuard requireAuth>
        <div data-testid="protected">Protected Content</div>
      </RouteGuard>
    );
    expect(screen.getByText('需要登录')).toBeDefined();
  });

  it('renders children when requireAuth is false and not authenticated', () => {
    (useAuthStore as any).mockReturnValue(false);
    render(
      <RouteGuard requireAuth={false}>
        <div data-testid="public">Public Content</div>
      </RouteGuard>
    );
    expect(screen.getByTestId('public')).toBeDefined();
  });

  it('redirects to chat when not authenticated', () => {
    (useAuthStore as any).mockReturnValue(false);
    render(
      <RouteGuard requireAuth>
        <div>Protected</div>
      </RouteGuard>
    );
    expect(mockSetPage).toHaveBeenCalledWith('chat');
  });

  it('renders return home button in redirect view', () => {
    (useAuthStore as any).mockReturnValue(false);
    render(
      <RouteGuard requireAuth>
        <div>Protected</div>
      </RouteGuard>
    );
    expect(screen.getByText('返回首页')).toBeDefined();
  });
});
