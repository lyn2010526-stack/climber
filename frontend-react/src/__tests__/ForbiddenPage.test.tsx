import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { ForbiddenPage } from '../pages/ForbiddenPage';
import { useCurrentPage } from '../store/page';

vi.mock('../store/page', () => ({
  useCurrentPage: vi.fn(),
}));

describe('ForbiddenPage', () => {
  const mockSetPage = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    (useCurrentPage as any).mockReturnValue(mockSetPage);
  });

  it('renders 403 title', () => {
    render(<ForbiddenPage />);
    expect(screen.getByText('访问被拒绝')).toBeDefined();
  });

  it('renders 403 description', () => {
    render(<ForbiddenPage />);
    expect(screen.getByText('您没有权限访问此页面，请联系管理员获取相应权限')).toBeDefined();
  });

  it('navigates to home when clicking home button', () => {
    render(<ForbiddenPage />);
    fireEvent.click(screen.getByText('返回首页'));
    expect(mockSetPage).toHaveBeenCalledWith('chat');
    expect(window.location.hash).toBe('#chat');
  });

  it('renders back button', () => {
    render(<ForbiddenPage />);
    expect(screen.getByText('返回上页')).toBeDefined();
  });
});
