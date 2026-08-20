import { forwardRef, useMemo } from 'react';
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '../../lib/utils';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';

const statCardVariants = cva(
  'rounded-2xl border p-5 transition-all duration-200',
  {
    variants: {
      variant: {
        default: 'border-white/[0.06] bg-white/[0.02]',
        elevated: 'border-white/[0.06] bg-white/[0.03] shadow-lg shadow-black/20',
        gradient: 'border-white/[0.06] bg-gradient-to-br from-white/[0.04] to-white/[0.01]',
      },
    },
    defaultVariants: {
      variant: 'default',
    },
  }
);

interface DataPoint {
  label: string;
  value: number;
  color?: string;
}

interface StatCardProps extends React.HTMLAttributes<HTMLDivElement>, VariantProps<typeof statCardVariants> {
  title: string;
  value: string | number;
  change?: number;
  changeLabel?: string;
  icon?: React.ReactNode;
  chartData?: DataPoint[];
  chartType?: 'bar' | 'line' | 'area' | 'sparkline';
  chartHeight?: number;
  chartColor?: string;
}

const StatCard = forwardRef<HTMLDivElement, StatCardProps>(
  ({ className, title, value, change, changeLabel, icon, chartData, chartType = 'sparkline', chartHeight = 48, chartColor = 'var(--color-accent)', variant, ...props }, ref) => {
    const trend = change === undefined ? null : change > 0 ? 'up' : change < 0 ? 'down' : 'flat';

    const chartPath = useMemo(() => {
      if (!chartData || chartData.length < 2) return '';
      const values = chartData.map(d => d.value);
      const max = Math.max(...values);
      const min = Math.min(...values);
      const range = max - min || 1;
      const width = 100;
      const height = chartHeight;
      const padding = 4;

      const points = values.map((v, i) => {
        const x = padding + (i / (values.length - 1)) * (width - padding * 2);
        const y = height - padding - ((v - min) / range) * (height - padding * 2);
        return { x, y };
      });

      if (chartType === 'bar') {
        const barWidth = (width - padding * 2) / values.length - 2;
        return points.map((p, i) => {
          const barHeight = height - padding - p.y;
          return { x: p.x, y: p.y, width: barWidth, height: barHeight, index: i };
        });
      }

      const linePath = points.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x} ${p.y}`).join(' ');

      if (chartType === 'area') {
        const lastPoint = points[points.length - 1];
        const firstPoint = points[0];
        if (!lastPoint || !firstPoint) return { line: linePath };
        const areaPath = `${linePath} L ${lastPoint.x} ${height} L ${firstPoint.x} ${height} Z`;
        return { line: linePath, area: areaPath };
      }

      return { line: linePath };
    }, [chartData, chartType, chartHeight]);

    return (
      <div ref={ref} className={cn(statCardVariants({ variant }), className)} {...props}>
        <div className="flex items-start justify-between mb-3">
          <div>
            <p className="text-sm text-white/50 mb-1">{title}</p>
            <div className="flex items-baseline gap-2">
              <span className="text-2xl font-semibold text-white">{value}</span>
              {trend !== null && (
                <span className={cn(
                  'inline-flex items-center gap-0.5 text-xs font-medium',
                  trend === 'up' && 'text-emerald-400',
                  trend === 'down' && 'text-red-400',
                  trend === 'flat' && 'text-white/40',
                )}>
                  {trend === 'up' && <TrendingUp className="h-3 w-3" />}
                  {trend === 'down' && <TrendingDown className="h-3 w-3" />}
                  {trend === 'flat' && <Minus className="h-3 w-3" />}
                  {change !== undefined && `${Math.abs(change)}%`}
                </span>
              )}
            </div>
            {changeLabel && <p className="text-xs text-white/30 mt-0.5">{changeLabel}</p>}
          </div>
          {icon && (
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-white/[0.05] text-white/60">
              {icon}
            </div>
          )}
        </div>

        {chartData && chartData.length >= 2 && (
          <div className="mt-2" style={{ height: chartHeight }}>
            <svg
              viewBox={`0 0 100 ${chartHeight}`}
              className="w-full h-full"
              preserveAspectRatio="none"
            >
              {chartType === 'bar' && Array.isArray(chartPath) && chartPath.map((bar, i) => (
                <rect
                  key={i}
                  x={bar.x}
                  y={bar.y}
                  width={bar.width}
                  height={bar.height}
                  rx={1}
                  fill={chartData[i]?.color || chartColor}
                  opacity={0.8}
                  className="transition-all duration-300 hover:opacity-100"
                />
              ))}
              {chartType === 'area' && typeof chartPath === 'object' && 'area' in chartPath && chartPath.area && chartPath.line && (
                <>
                  <defs>
                    <linearGradient id={`gradient-${title}`} x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor={chartColor} stopOpacity="0.3" />
                      <stop offset="100%" stopColor={chartColor} stopOpacity="0" />
                    </linearGradient>
                  </defs>
                  <path d={chartPath.area} fill={`url(#gradient-${title})`} />
                  <path d={chartPath.line} fill="none" stroke={chartColor} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                </>
              )}
              {(chartType === 'line' || chartType === 'sparkline') && typeof chartPath === 'object' && 'line' in chartPath && chartPath.line && (
                <>
                  <path d={chartPath.line} fill="none" stroke={chartColor} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                  {chartType === 'line' && (
                    <circle
                      cx={chartPath.line.split('L').pop()?.trim().split(' ')[0] ?? 0}
                      cy={chartPath.line.split('L').pop()?.trim().split(' ')[1] ?? 0}
                      r="2"
                      fill={chartColor}
                    />
                  )}
                </>
              )}
            </svg>
          </div>
        )}
      </div>
    );
  }
);
StatCard.displayName = 'StatCard';

interface BarChartProps extends React.HTMLAttributes<HTMLDivElement> {
  data: DataPoint[];
  height?: number;
  showGrid?: boolean;
  showLabels?: boolean;
  color?: string;
}

const BarChart = forwardRef<HTMLDivElement, BarChartProps>(
  ({ className, data, height = 200, showGrid = true, showLabels = true, color = 'var(--color-accent)', ...props }, ref) => {
    const maxValue = Math.max(...data.map(d => d.value));
    const chartPadding = { top: 10, right: 10, bottom: showLabels ? 24 : 10, left: 10 };
    const chartWidth = 300;
    const chartH = height;
    const innerWidth = chartWidth - chartPadding.left - chartPadding.right;
    const innerHeight = chartH - chartPadding.top - chartPadding.bottom;
    const barWidth = innerWidth / data.length - 4;

    return (
      <div ref={ref} className={cn('w-full', className)} {...props}>
        <svg viewBox={`0 0 ${chartWidth} ${chartH}`} className="w-full" style={{ height: chartH }}>
          {showGrid && [0, 0.25, 0.5, 0.75, 1].map((ratio) => (
            <line
              key={ratio}
              x1={chartPadding.left}
              y1={chartPadding.top + innerHeight * (1 - ratio)}
              x2={chartWidth - chartPadding.right}
              y2={chartPadding.top + innerHeight * (1 - ratio)}
              stroke="rgba(255,255,255,0.04)"
              strokeWidth="0.5"
            />
          ))}
          {data.map((d, i) => {
            const barHeight = (d.value / maxValue) * innerHeight;
            const x = chartPadding.left + i * (innerWidth / data.length) + 2;
            const y = chartPadding.top + innerHeight - barHeight;
            return (
              <g key={i}>
                <rect
                  x={x}
                  y={y}
                  width={barWidth}
                  height={barHeight}
                  rx={2}
                  fill={d.color || color}
                  opacity={0.85}
                  className="transition-all duration-300 hover:opacity-100"
                />
                {showLabels && (
                  <text
                    x={x + barWidth / 2}
                    y={chartH - 4}
                    textAnchor="middle"
                    className="text-[8px] fill-white/40"
                  >
                    {d.label}
                  </text>
                )}
              </g>
            );
          })}
        </svg>
      </div>
    );
  }
);
BarChart.displayName = 'BarChart';

interface DonutChartProps extends React.HTMLAttributes<HTMLDivElement> {
  data: DataPoint[];
  size?: number;
  strokeWidth?: number;
  centerLabel?: string;
  centerValue?: string | number;
}

const DonutChart = forwardRef<HTMLDivElement, DonutChartProps>(
  ({ className, data, size = 120, strokeWidth = 12, centerLabel, centerValue, ...props }, ref) => {
    const total = data.reduce((sum, d) => sum + d.value, 0);
    const radius = (size - strokeWidth) / 2;
    const circumference = 2 * Math.PI * radius;
    const center = size / 2;

    let cumulativePercent = 0;

    return (
      <div ref={ref} className={cn('relative inline-flex items-center justify-center', className)} {...props}>
        <svg width={size} height={size} className="-rotate-90">
          {data.map((d, i) => {
            const percent = d.value / total;
            const dashLength = circumference * percent;
            const dashOffset = circumference * cumulativePercent;
            cumulativePercent += percent;
            return (
              <circle
                key={i}
                cx={center}
                cy={center}
                r={radius}
                fill="none"
                stroke={d.color || `hsl(${i * 360 / data.length}, 70%, 60%)`}
                strokeWidth={strokeWidth}
                strokeDasharray={`${dashLength} ${circumference - dashLength}`}
                strokeDashoffset={-dashOffset}
                strokeLinecap="round"
                className="transition-all duration-500"
              />
            );
          })}
        </svg>
        {(centerLabel || centerValue) && (
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            {centerValue && <span className="text-lg font-semibold text-white">{centerValue}</span>}
            {centerLabel && <span className="text-xs text-white/40">{centerLabel}</span>}
          </div>
        )}
      </div>
    );
  }
);
DonutChart.displayName = 'DonutChart';

export { StatCard, BarChart, DonutChart, statCardVariants };
export type { StatCardProps, BarChartProps, DonutChartProps, DataPoint };
