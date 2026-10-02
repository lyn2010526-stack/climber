import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MobileClusterPage } from '../MobileClusterPage';

vi.mock('../../ClusterPage', () => ({
  ClusterPage: () => <div>Cluster Content</div>,
}));

describe('MobileClusterPage', () => {
  it('renders the desktop fallback without mounting ClusterPage', () => {
    render(<MobileClusterPage />);
    expect(screen.getByRole('region', { name: '集群' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: '集群' })).toBeInTheDocument();
    expect(screen.getByText('集群管理依赖宽屏表格和多栏详情，移动端提供稳定回退，避免出现横向滚动和遮挡。')).toBeInTheDocument();
    expect(screen.getByText('使用底部导航打开聊天，或点击“更多”访问可用的移动端入口。')).toBeInTheDocument();
    expect(screen.queryByText('Cluster Content')).not.toBeInTheDocument();
  });
});
