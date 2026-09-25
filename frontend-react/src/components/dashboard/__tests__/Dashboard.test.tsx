import { afterEach, describe, expect, it } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';
import { Dashboard } from '../Dashboard';

afterEach(cleanup);

describe('Dashboard supplied statistics', () => {
  it('announces missing data without demo metrics', () => {
    const { container } = render(<Dashboard />);
    expect(screen.getByRole('status')).toHaveTextContent('统计数据未加载');
    expect(container.textContent).not.toMatch(/12|45\.2K|1\.2GB|34%|活跃会话/);
  });

  it('distinguishes a loaded empty result from missing data', () => {
    render(<Dashboard stats={[]} />);
    expect(screen.getByRole('status')).toHaveTextContent('暂无统计数据');
    expect(screen.queryByText('统计数据未加载')).not.toBeInTheDocument();
  });

  it('renders supplied zero and trend values without inventing other metrics', () => {
    render(<Dashboard stats={[
      { title: 'Completed tasks', value: 0 },
      { title: 'Reported tokens', value: '123', change: { value: -4, trend: 'down' } },
    ]} />);
    expect(screen.getByText('0')).toBeInTheDocument();
    expect(screen.getByText('123')).toBeInTheDocument();
    expect(screen.getByText('4%')).toHaveClass('text-rose-400');
    expect(screen.queryByRole('status')).not.toBeInTheDocument();
    expect(screen.queryByText('CPU 负载')).not.toBeInTheDocument();
  });

  it('updates from missing data to supplied data and back', () => {
    const { rerender } = render(<Dashboard />);
    rerender(<Dashboard stats={[{ title: 'Reported sessions', value: 7 }]} />);
    expect(screen.getByText('7')).toBeInTheDocument();
    expect(screen.queryByRole('status')).not.toBeInTheDocument();
    rerender(<Dashboard />);
    expect(screen.queryByText('7')).not.toBeInTheDocument();
    expect(screen.getByRole('status')).toHaveTextContent('统计数据未加载');
  });
});
