import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MobileTasksPage } from '../MobileTasksPage';

vi.mock('../../TaskMonitorPage', () => ({
  default: () => <div>Tasks Content</div>,
}));

describe('MobileTasksPage', () => {
  it('renders the desktop fallback without mounting TaskMonitorPage', () => {
    render(<MobileTasksPage />);
    expect(screen.getByRole('region', { name: '任务监控' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: '任务监控' })).toBeInTheDocument();
    expect(screen.getByText('任务监控需要更宽的工作区，移动端保留清晰入口并避免压缩桌面控制台。')).toBeInTheDocument();
    expect(screen.getByText('使用底部导航打开聊天，或点击“更多”访问可用的移动端入口。')).toBeInTheDocument();
    expect(screen.queryByText('Tasks Content')).not.toBeInTheDocument();
  });
});
