import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MobileFactoryPage } from '../MobileFactoryPage';

vi.mock('../../FactoryModePage', () => ({
  FactoryModePage: () => <div>Factory Content</div>,
}));

describe('MobileFactoryPage', () => {
  it('renders the desktop fallback without mounting FactoryModePage', () => {
    render(<MobileFactoryPage />);
    expect(screen.getByRole('region', { name: '工厂模式' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: '工厂模式' })).toBeInTheDocument();
    expect(screen.getByText('工厂模式包含复杂的多栏编辑器，移动端提供可用回退，桌面端继续保留完整工作台。')).toBeInTheDocument();
    expect(screen.getByText('使用底部导航打开聊天，或点击“更多”访问可用的移动端入口。')).toBeInTheDocument();
    expect(screen.queryByText('Factory Content')).not.toBeInTheDocument();
  });
});
