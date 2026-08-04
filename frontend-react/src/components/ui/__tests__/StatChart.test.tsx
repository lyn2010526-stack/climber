import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { StatCard, BarChart, DonutChart } from '../StatChart';

describe('StatCard', () => {
  it('renders title and value', () => {
    render(<StatCard title="总用户" value="1,234" />);
    expect(screen.getByText('总用户')).toBeDefined();
    expect(screen.getByText('1,234')).toBeDefined();
  });

  it('renders positive change indicator', () => {
    render(<StatCard title="收入" value="$12,345" change={12.5} changeLabel="较上月" />);
    expect(screen.getByText('12.5%')).toBeDefined();
    expect(screen.getByText('较上月')).toBeDefined();
  });

  it('renders negative change indicator', () => {
    render(<StatCard title="跳出率" value="23%" change={-5.2} />);
    expect(screen.getByText('5.2%')).toBeDefined();
  });

  it('renders icon', () => {
    render(<StatCard title="活跃用户" value="567" icon={<span>icon</span>} />);
    expect(screen.getByText('icon')).toBeDefined();
  });

  it('renders chart data as sparkline', () => {
    const data = [
      { label: 'Mon', value: 10 },
      { label: 'Tue', value: 20 },
      { label: 'Wed', value: 15 },
    ];
    const { container } = render(<StatCard title="趋势" value="45" chartData={data} chartType="sparkline" />);
    expect(container.querySelector('svg')).not.toBeNull();
  });

  it('renders bar chart type', () => {
    const data = [
      { label: 'A', value: 30 },
      { label: 'B', value: 50 },
      { label: 'C', value: 20 },
    ];
    const { container } = render(<StatCard title="分布" value="100" chartData={data} chartType="bar" />);
    expect(container.querySelector('rect')).not.toBeNull();
  });
});

describe('BarChart', () => {
  it('renders bars for each data point', () => {
    const data = [
      { label: 'A', value: 30 },
      { label: 'B', value: 50 },
      { label: 'C', value: 20 },
    ];
    const { container } = render(<BarChart data={data} />);
    const bars = container.querySelectorAll('rect');
    expect(bars.length).toBe(3);
  });

  it('renders labels when showLabels is true', () => {
    const data = [
      { label: '一月', value: 30 },
      { label: '二月', value: 50 },
    ];
    render(<BarChart data={data} showLabels />);
    expect(screen.getByText('一月')).toBeDefined();
    expect(screen.getByText('二月')).toBeDefined();
  });

  it('hides labels when showLabels is false', () => {
    const data = [
      { label: '一月', value: 30 },
      { label: '二月', value: 50 },
    ];
    render(<BarChart data={data} showLabels={false} />);
    expect(screen.queryByText('一月')).toBeNull();
  });
});

describe('DonutChart', () => {
  it('renders donut segments', () => {
    const data = [
      { label: 'A', value: 30, color: '#3B82F6' },
      { label: 'B', value: 50, color: '#8B5CF6' },
      { label: 'C', value: 20, color: '#10B981' },
    ];
    const { container } = render(<DonutChart data={data} />);
    const circles = container.querySelectorAll('circle');
    expect(circles.length).toBe(3);
  });

  it('renders center label and value', () => {
    const data = [
      { label: 'A', value: 50 },
      { label: 'B', value: 50 },
    ];
    render(<DonutChart data={data} centerValue="100" centerLabel="总计" />);
    expect(screen.getByText('100')).toBeDefined();
    expect(screen.getByText('总计')).toBeDefined();
  });
});
