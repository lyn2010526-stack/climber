import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MobileDesktopFallback } from '../MobileDesktopFallback';

describe('MobileDesktopFallback', () => {
  it('explains why a desktop surface has a mobile fallback', () => {
    render(<MobileDesktopFallback title="任务监控" description="需要宽屏" />);
    expect(screen.getByRole('heading', { name: '任务监控' })).toBeInTheDocument();
    expect(screen.getByText('需要宽屏')).toBeInTheDocument();
    expect(screen.getByText(/底部导航/)).toBeInTheDocument();
  });
});
