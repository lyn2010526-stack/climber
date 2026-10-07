import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { ShimmerText } from './ShimmerText';

describe('ShimmerText — codex shimmer 移植', () => {
  it('渲染文本并挂上扫光 class', () => {
    render(<ShimmerText text="正在思考…" />);
    const el = screen.getByText('正在思考…');
    expect(el).toHaveClass('workbench-shimmer-text');
  });

  it('空文本渲染为空（codex 对空输入返回空）', () => {
    const { container } = render(<ShimmerText text="" />);
    expect(container.firstChild).toBeNull();
  });

  it('透传 className', () => {
    render(<ShimmerText text="加载中" className="extra" />);
    expect(screen.getByText('加载中')).toHaveClass('workbench-shimmer-text', 'extra');
  });
});
