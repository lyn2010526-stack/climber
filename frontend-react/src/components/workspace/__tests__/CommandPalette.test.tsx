import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import CommandPalette from '../CommandPalette';

const mockNavigate = vi.fn();

describe('CommandPalette', () => {
  it('renders nothing when closed', () => {
    const { container } = render(<CommandPalette isOpen={false} onClose={() => {}} onNavigate={mockNavigate} />);
    expect(container.innerHTML).toBe('');
  });

  it('renders commands when open', () => {
    render(<CommandPalette isOpen={true} onClose={() => {}} onNavigate={mockNavigate} />);
    expect(screen.getByText('工作台')).toBeDefined();
    expect(screen.getByText('自主执行')).toBeDefined();
  });

  it('filters commands based on search', () => {
    render(<CommandPalette isOpen={true} onClose={() => {}} onNavigate={mockNavigate} />);
    const input = screen.getByPlaceholderText('搜索页面、功能...');
    fireEvent.change(input, { target: { value: '工作台' } });
    expect(screen.getByText('工作台')).toBeDefined();
  });

  it('calls onNavigate when command is clicked', () => {
    render(<CommandPalette isOpen={true} onClose={() => {}} onNavigate={mockNavigate} />);
    fireEvent.click(screen.getByText('工作台'));
    expect(mockNavigate).toHaveBeenCalledWith('chat');
  });
});
