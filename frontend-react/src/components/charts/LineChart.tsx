import React, { useMemo } from "react";

export interface LineChartSeries {
  name: string;
  data: { x: string | number; y: number }[];
  color?: string;
}

export interface LineChartProps {
  series: LineChartSeries[];
  height?: number;
  showDots?: boolean;
  showGrid?: boolean;
  showLegend?: boolean;
  smooth?: boolean;
  yAxisLabel?: string;
  fillArea?: boolean;
}

const seriesColors = ["#3B82F6", "#10B981", "#F59E0B", "#EF4444", "#8B5CF6", "#EC4899"];

export const LineChart: React.FC<LineChartProps> = ({
  series, height = 250, showDots = true, showGrid = true, showLegend = true, smooth: _smooth = true, yAxisLabel: _yAxisLabel, fillArea,
}) => {
  const allValues = series.flatMap((s) => s.data.map((d) => d.y));
  const maxY = Math.max(...allValues, 1);
  const minY = Math.min(...allValues, 0);
  const range = maxY - minY || 1;

  const padding = { top: 20, right: 20, bottom: 30, left: 40 };
  const chartWidth = 600;
  const chartHeight = height - padding.top - padding.bottom;

  const getScaledY = (value: number) => {
    return padding.top + chartHeight - ((value - minY) / range) * chartHeight;
  };

  const getPath = (data: { x: string | number; y: number }[]) => {
    if (data.length === 0) return "";
    const stepX = chartWidth / Math.max(data.length - 1, 1);
    return data
      .map((point, i) => {
        const x = padding.left + i * stepX;
        const y = getScaledY(point.y);
        return i === 0 ? `M ${x} ${y}` : `L ${x} ${y}`;
      })
      .join(" ");
  };

  const getAreaPath = (data: { x: string | number; y: number }[]) => {
    if (data.length === 0) return "";
    const linePath = getPath(data);
    const stepX = chartWidth / Math.max(data.length - 1, 1);
    const lastX = padding.left + (data.length - 1) * stepX;
    return `${linePath} L ${lastX} ${padding.top + chartHeight} L ${padding.left} ${padding.top + chartHeight} Z`;
  };

  const gridLines = useMemo(() => {
    const lines = [];
    const numLines = 5;
    for (let i = 0; i <= numLines; i++) {
      const value = minY + (range * i) / numLines;
      lines.push({ value, y: getScaledY(value) });
    }
    return lines;
  }, [minY, range]);

  return (
    <div className="w-full">
      {showLegend && (
        <div className="flex flex-wrap gap-4 mb-2">
          {series.map((s, i) => (
            <div key={i} className="flex items-center gap-1.5">
              <div className="w-3 h-3 rounded-full" style={{ backgroundColor: s.color || seriesColors[i % seriesColors.length] }} />
              <span className="text-xs text-gray-600">{s.name}</span>
            </div>
          ))}
        </div>
      )}
      <svg viewBox={`0 0 ${chartWidth} ${height}`} className="w-full" preserveAspectRatio="xMidYMid meet">
        {showGrid && gridLines.map((line, i) => (
          <g key={i}>
            <line x1={padding.left} y1={line.y} x2={chartWidth - padding.right} y2={line.y} stroke="#E5E7EB" strokeWidth="1" />
            <text x={padding.left - 5} y={line.y + 4} textAnchor="end" fontSize="10" fill="#9CA3AF">
              {line.value.toFixed(0)}
            </text>
          </g>
        ))}
        {series.map((s, i) => {
          const color = s.color || seriesColors[i % seriesColors.length];
          return (
            <g key={i}>
              {fillArea && (
                <path d={getAreaPath(s.data)} fill={color} opacity={0.1} />
              )}
              <path d={getPath(s.data)} fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
              {showDots && s.data.map((point, j) => {
                const stepX = chartWidth / Math.max(s.data.length - 1, 1);
                const x = padding.left + j * stepX;
                return <circle key={j} cx={x} cy={getScaledY(point.y)} r="3" fill={color} />;
              })}
            </g>
          );
        })}
      </svg>
    </div>
  );
};

export interface AreaChartProps {
  data: { x: string; y: number; y2?: number }[];
  height?: number;
  color?: string;
  gradient?: boolean;
  showDots?: boolean;
}

export const AreaChart: React.FC<AreaChartProps> = ({
  data, height = 200, color = "#3B82F6", gradient = true, showDots = false,
}) => {
  const maxY = Math.max(...data.map((d) => Math.max(d.y, d.y2 || 0)), 1);
  const padding = { top: 10, right: 10, bottom: 20, left: 10 };
  const width = 600;
  const chartHeight = height - padding.top - padding.bottom;

  const getY = (val: number) => padding.top + chartHeight - (val / maxY) * chartHeight;
  const stepX = (width - padding.left - padding.right) / Math.max(data.length - 1, 1);

  const areaPath = data
    .map((point, i) => {
      const x = padding.left + i * stepX;
      const y = getY(point.y);
      return i === 0 ? `M ${x} ${y}` : `L ${x} ${y}`;
    })
    .join(" ");

  const closedPath = `${areaPath} L ${padding.left + (data.length - 1) * stepX} ${padding.top + chartHeight} L ${padding.left} ${padding.top + chartHeight} Z`;

  return (
    <svg viewBox={`0 0 ${width} ${height}`} className="w-full">
      <defs>
        <linearGradient id="areaGradient" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity={gradient ? 0.3 : 0} />
          <stop offset="100%" stopColor={color} stopOpacity={0} />
        </linearGradient>
      </defs>
      <path d={closedPath} fill="url(#areaGradient)" />
      <path d={areaPath} fill="none" stroke={color} strokeWidth="2" />
      {showDots && data.map((point, i) => (
        <circle key={i} cx={padding.left + i * stepX} cy={getY(point.y)} r="3" fill={color} />
      ))}
    </svg>
  );
};

export interface PieChartProps {
  data: { label: string; value: number; color?: string }[];
  size?: number;
  donut?: boolean;
  showLabels?: boolean;
}

export const PieChart: React.FC<PieChartProps> = ({ data, size = 200, donut = false, showLabels = true }) => {
  const total = data.reduce((sum, d) => sum + d.value, 0);
  const center = size / 2;
  const radius = size / 2 - 10;
  const innerRadius = donut ? radius * 0.6 : 0;

  let currentAngle = -Math.PI / 2;

  const slices = data.map((item, index) => {
    const angle = (item.value / total) * 2 * Math.PI;
    const startAngle = currentAngle;
    const endAngle = currentAngle + angle;
    currentAngle = endAngle;

    const x1 = center + radius * Math.cos(startAngle);
    const y1 = center + radius * Math.sin(startAngle);
    const x2 = center + radius * Math.cos(endAngle);
    const y2 = center + radius * Math.sin(endAngle);

    const ix1 = center + innerRadius * Math.cos(endAngle);
    const iy1 = center + innerRadius * Math.sin(endAngle);
    const ix2 = center + innerRadius * Math.cos(startAngle);
    const iy2 = center + innerRadius * Math.sin(startAngle);

    const largeArc = angle > Math.PI ? 1 : 0;

    const path = donut
      ? `M ${x1} ${y1} A ${radius} ${radius} 0 ${largeArc} 1 ${x2} ${y2} L ${ix1} ${iy1} A ${innerRadius} ${innerRadius} 0 ${largeArc} 0 ${ix2} ${iy2} Z`
      : `M ${center} ${center} L ${x1} ${y1} A ${radius} ${radius} 0 ${largeArc} 1 ${x2} ${y2} Z`;

    return { path, color: item.color || seriesColors[index % seriesColors.length], label: item.label, value: item.value };
  });

  return (
    <div className="flex items-center gap-4">
      <svg width={size} height={size}>
        {slices.map((slice, i) => (
          <path key={i} d={slice.path} fill={slice.color} stroke="white" strokeWidth="2" />
        ))}
      </svg>
      {showLabels && (
        <div className="space-y-1">
          {slices.map((slice, i) => (
            <div key={i} className="flex items-center gap-2 text-xs">
              <div className="w-3 h-3 rounded" style={{ backgroundColor: slice.color }} />
              <span className="text-gray-600">{slice.label}</span>
              <span className="text-gray-400">({((slice.value / total) * 100).toFixed(1)}%)</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
