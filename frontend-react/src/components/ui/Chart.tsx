import React from 'react';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from 'recharts';
import { cn } from '../../lib/utils';

export interface ChartDataPoint {
  name: string;
  [key: string]: string | number;
}

export interface ChartSeries {
  key: string;
  color?: string;
  label?: string;
}

export interface ChartProps {
  type: 'line' | 'bar' | 'pie' | 'area';
  data: ChartDataPoint[];
  series: ChartSeries[];
  height?: number;
  className?: string;
  showGrid?: boolean;
  showLegend?: boolean;
  showTooltip?: boolean;
  xAxisKey?: string;
  stacked?: boolean;
  curved?: boolean;
  colors?: string[];
}

const DEFAULT_COLORS = ['#5E6AD2', '#6366F1', '#8B5CF6', '#A78BFA', '#C4B5FD', '#10B981', '#34D399', '#F59E0B', '#EF4444', '#EC4899'];

function Chart({
  type,
  data,
  series,
  height = 300,
  className,
  showGrid = true,
  showLegend = true,
  showTooltip = true,
  xAxisKey = 'name',
  stacked = false,
  curved = true,
  colors = DEFAULT_COLORS,
}: ChartProps) {
  const seriesColors = series.map((s, i) => s.color || colors[i % colors.length]);

  const renderChart = () => {
    switch (type) {
      case 'line':
        return (
          <LineChart data={data} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
            {showGrid && <CartesianGrid strokeDasharray="3 3" stroke="var(--border-subtle)" />}
            <XAxis dataKey={xAxisKey} tick={{ fill: 'var(--text-muted)', fontSize: 12 }} axisLine={{ stroke: 'var(--border-subtle)' }} />
            <YAxis tick={{ fill: 'var(--text-muted)', fontSize: 12 }} axisLine={{ stroke: 'var(--border-subtle)' }} />
            {showTooltip && <Tooltip contentStyle={{ backgroundColor: 'var(--surface-bg)', border: '1px solid var(--border-subtle)', borderRadius: '8px', color: 'var(--text-primary)' }} />}
            {showLegend && <Legend wrapperStyle={{ color: 'var(--text-secondary)', fontSize: 12 }} />}
            {series.map((s, i) => (
              <Line
                key={s.key}
                type={curved ? 'monotone' : 'linear'}
                dataKey={s.key}
                name={s.label || s.key}
                stroke={seriesColors[i]}
                strokeWidth={2}
                dot={{ fill: seriesColors[i], r: 4 }}
                activeDot={{ r: 6 }}
              />
            ))}
          </LineChart>
        );
      case 'bar':
        return (
          <BarChart data={data} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
            {showGrid && <CartesianGrid strokeDasharray="3 3" stroke="var(--border-subtle)" />}
            <XAxis dataKey={xAxisKey} tick={{ fill: 'var(--text-muted)', fontSize: 12 }} axisLine={{ stroke: 'var(--border-subtle)' }} />
            <YAxis tick={{ fill: 'var(--text-muted)', fontSize: 12 }} axisLine={{ stroke: 'var(--border-subtle)' }} />
            {showTooltip && <Tooltip contentStyle={{ backgroundColor: 'var(--surface-bg)', border: '1px solid var(--border-subtle)', borderRadius: '8px', color: 'var(--text-primary)' }} />}
            {showLegend && <Legend wrapperStyle={{ color: 'var(--text-secondary)', fontSize: 12 }} />}
            {series.map((s, i) => (
              <Bar
                key={s.key}
                dataKey={s.key}
                name={s.label || s.key}
                fill={seriesColors[i]}
                radius={[4, 4, 0, 0]}
                stackId={stacked ? 'stack' : undefined}
              />
            ))}
          </BarChart>
        );
      case 'area':
        return (
          <AreaChart data={data} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
            {showGrid && <CartesianGrid strokeDasharray="3 3" stroke="var(--border-subtle)" />}
            <XAxis dataKey={xAxisKey} tick={{ fill: 'var(--text-muted)', fontSize: 12 }} axisLine={{ stroke: 'var(--border-subtle)' }} />
            <YAxis tick={{ fill: 'var(--text-muted)', fontSize: 12 }} axisLine={{ stroke: 'var(--border-subtle)' }} />
            {showTooltip && <Tooltip contentStyle={{ backgroundColor: 'var(--surface-bg)', border: '1px solid var(--border-subtle)', borderRadius: '8px', color: 'var(--text-primary)' }} />}
            {showLegend && <Legend wrapperStyle={{ color: 'var(--text-secondary)', fontSize: 12 }} />}
            {series.map((s, i) => (
              <Area
                key={s.key}
                type={curved ? 'monotone' : 'linear'}
                dataKey={s.key}
                name={s.label || s.key}
                stroke={seriesColors[i]}
                fill={seriesColors[i]}
                fillOpacity={0.15}
                strokeWidth={2}
                stackId={stacked ? 'stack' : undefined}
              />
            ))}
          </AreaChart>
        );
      case 'pie':
        return (
          <PieChart>
            {showTooltip && <Tooltip contentStyle={{ backgroundColor: 'var(--surface-bg)', border: '1px solid var(--border-subtle)', borderRadius: '8px', color: 'var(--text-primary)' }} />}
            {showLegend && <Legend wrapperStyle={{ color: 'var(--text-secondary)', fontSize: 12 }} />}
            <Pie
              data={data}
              dataKey={series[0]?.key || 'value'}
              nameKey={xAxisKey}
              cx="50%"
              cy="50%"
              outerRadius={80}
              innerRadius={stacked ? 50 : 0}
              paddingAngle={2}
              label={({ name, percent }: { name?: string; percent?: number }) => `${name ?? ''} ${((percent ?? 0) * 100).toFixed(0)}%`}
            >
              {data.map((_, index) => (
                <Cell key={index} fill={colors[index % colors.length]} />
              ))}
            </Pie>
          </PieChart>
        );
    }
  };

  return (
    <div className={cn('w-full', className)} role="img" aria-label={`${type} chart`} style={{ height }}>
      <ResponsiveContainer width="100%" height="100%">
        {renderChart()}
      </ResponsiveContainer>
    </div>
  );
}

export { Chart };
