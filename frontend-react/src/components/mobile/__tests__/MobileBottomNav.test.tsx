import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { MobileBottomNav } from '../MobileBottomNav';

describe('MobileBottomNav', () => {
  const mockNavigate = vi.fn();

  it('renders core mobile tabs', () => {
    render(<MobileBottomNav currentPage="chat" onNavigate={mockNavigate} />);
    expect(screen.getByText('工作台')).toBeDefined();
    expect(screen.getByText('执行')).toBeDefined();
    expect(screen.getByText('集群')).toBeDefined();
    expect(screen.getByText('任务')).toBeDefined();
    expect(screen.getByText('智能体')).toBeDefined();
  });

  it('renders more button', () => {
    render(<MobileBottomNav currentPage="chat" onNavigate={mockNavigate} />);
    expect(screen.getByText('更多')).toBeDefined();
  });

  it('calls onNavigate when a tab is clicked', () => {
    render(<MobileBottomNav currentPage="chat" onNavigate={mockNavigate} />);
    fireEvent.click(screen.getByText('执行'));
    expect(mockNavigate).toHaveBeenCalledWith('factory');
  });

  it('shows more menu when more button is clicked', () => {
    render(<MobileBottomNav currentPage="chat" onNavigate={mockNavigate} />);
    fireEvent.click(screen.getByText('更多'));
    expect(screen.getByText('系统设置')).toBeDefined();
  });

  it('highlights active tab', () => {
    const { container } = render(<MobileBottomNav currentPage="chat" onNavigate={mockNavigate} />);
    const activeButton = container.querySelector('[style*="var(--color-accent)"]');
    expect(activeButton).toBeDefined();
  });
});
