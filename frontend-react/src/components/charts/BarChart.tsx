import React from "react";

export interface BarChartData {
  label: string;
  value: number;
  color?: string;
}

export interface BarChartProps {
  data: BarChartData[];
  height?: number;
  showValues?: boolean;
  horizontal?: boolean;
  colorScheme?: string[];
  theme?: 'dark' | 'light';
}

const defaultDarkColors = ["#5E6AD2", "#60A5FA", "#34D399", "#FBBF24", "#F87171", "#8B5CF6", "#EC4899", "#06B6D4"];
const defaultLightColors = ["#4F46E5", "#2563EB", "#059669", "#D97706", "#DC2626", "#7C3AED", "#DB2777", "#0891B2"];

export const BarChart: React.FC<BarChartProps> = ({
  data, 
  height = 200, 
  showValues = true, 
  horizontal = false, 
  colorScheme,
  theme = 'dark'
}) => {
  const maxValue = Math.max(...data.map((d) => d.value), 1);
  const colors = theme === 'dark' ? (colorScheme || defaultDarkColors) : (colorScheme || defaultLightColors);

  if (horizontal) {
    return (
      <div className="space-y-2">
        {data.map((item, index) => (
          <div key={index} className="flex items-center gap-2">
            <span className={`text-sm w-24 truncate ${theme === 'dark' ? 'text-[var(--color-text-muted)]' : 'text-gray-600'}`}>
              {item.label}
            </span>
            <div className="flex-1 bg-[var(--color-bg-surface-2)] rounded-full h-6 overflow-hidden border border-[var(--color-border-subtle)]">
              <div
                className="h-full rounded-full transition-all duration-500 flex items-center justify-end pr-2"
                style={{
                  width: `${(item.value / maxValue) * 100}%`,
                  backgroundColor: item.color || colors[index % colors.length],
                }}
              >
                {showValues && (
                  <span className={`text-xs font-medium ${theme === 'dark' ? 'text-white' : 'text-white'}`}>
                    {item.value}
                  </span>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>
    );
  }

  return (
    <div className="flex items-end gap-2" style={{ height }}>
      {data.map((item, index) => (
        <div key={index} className="flex-1 flex flex-col items-center gap-1">
          {showValues && (
            <span className={`text-xs ${theme === 'dark' ? 'text-[var(--color-text-muted)]' : 'text-gray-600'}`}>
              {item.value}
            </span>
          )}
          <div className={`w-full rounded-t overflow-hidden flex-1 flex items-end border-t border-x ${theme === 'dark' ? 'border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-2)]' : 'bg-gray-100'}`}>
            <div
              className="w-full rounded-t transition-all duration-500"
              style={{
                height: `${(item.value / maxValue) * 100}%`,
                backgroundColor: item.color || colors[index % colors.length],
                minHeight: item.value > 0 ? "4px" : "0",
              }}
            />
          </div>
          <span className={`text-xs truncate max-w-full ${theme === 'dark' ? 'text-[var(--color-text-muted)]' : 'text-gray-600'}`}>
            {item.label}
          </span>
        </div>
      ))}
    </div>
  );
};

export interface StackedBarChartProps {
  data: { label: string; values: { name: string; value: number; color?: string }[] }[];
  height?: number;
  showLegend?: boolean;
}

export const StackedBarChart: React.FC<StackedBarChartProps> = ({ data, height = 200, showLegend = true }) => {
  const maxValue = Math.max(...data.map((d) => d.values.reduce((sum, v) => sum + v.value, 0)), 1);
  const allSeries = [...new Set(data.flatMap((d) => d.values.map((v) => v.name)))];
  const colors = defaultDarkColors;

  return (
    <div className="space-y-4">
      {showLegend && (
        <div className="flex flex-wrap gap-4">
          {allSeries.map((series) => {
            const firstWithValue = data.find((d) => d.values.find((v) => v.name === series));
            const valueItem = firstWithValue?.values.find((v) => v.name === series);
            return (
              <div key={series} className="flex items-center gap-1">
                <div className="w-3 h-3 rounded" style={{ backgroundColor: valueItem?.color || colors[allSeries.indexOf(series) % colors.length] }} />
                <span className="text-xs text-gray-600">{series}</span>
              </div>
            );
          })}
        </div>
      )}
      <div className="flex items-end gap-2" style={{ height }}>
        {data.map((bar, index) => {
          return (
            <div key={index} className="flex-1 flex flex-col items-center gap-1">
              <div className="w-full bg-gray-100 rounded-t overflow-hidden flex-1 flex flex-col-reverse">
                {bar.values.map((segment, segIndex) => (
                  <div
                    key={segIndex}
                    className="w-full transition-all duration-500"
                    style={{
                      height: `${(segment.value / maxValue) * 100}%`,
                      backgroundColor: segment.color || colors[segIndex % colors.length],
                      minHeight: segment.value > 0 ? "2px" : "0",
                    }}
                  />
                ))}
              </div>
              <span className="text-xs text-gray-600 truncate max-w-full">{bar.label}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export interface ProgressBarProps {
  value: number;
  max?: number;
  showLabel?: boolean;
  color?: string;
  size?: "sm" | "md" | "lg";
  animated?: boolean;
  striped?: boolean;
}

const progressSizes = { sm: "h-1.5", md: "h-3", lg: "h-5" };

export const ProgressBar: React.FC<ProgressBarProps> = ({
  value, max = 100, showLabel, color = "#3B82F6", size = "md", animated, striped,
}) => {
  const percentage = Math.min(100, Math.max(0, (value / max) * 100));

  return (
    <div className="w-full">
      <div className={cn("w-full bg-gray-200 rounded-full overflow-hidden", progressSizes[size])}>
        <div
          className={cn("rounded-full transition-all duration-500", progressSizes[size], striped && "bg-stripes")}
          style={{
            width: `${percentage}%`,
            backgroundColor: color,
            ...(striped && { backgroundImage: "linear-gradient(45deg, rgba(255,255,255,.15) 25%, transparent 25%, transparent 50%, rgba(255,255,255,.15) 50%, rgba(255,255,255,.15) 75%, transparent 75%, transparent)" }),
            ...(animated && striped && { animation: "progress-stripes 1s linear infinite" }),
          }}
        />
      </div>
      {showLabel && <span className="text-xs text-gray-500 mt-1 block text-right">{percentage.toFixed(1)}%</span>}
    </div>
  );
};

export interface MetricCardProps {
  title: string;
  value: string | number;
  change?: number;
  changeLabel?: string;
  icon?: React.ReactNode;
  color?: string;
}

export const MetricCard: React.FC<MetricCardProps> = ({ title, value, change, changeLabel, icon, color = "blue" }) => {
  const colorMap: Record<string, string> = {
    blue: "bg-blue-50 text-blue-600",
    green: "bg-green-50 text-green-600",
    red: "bg-red-50 text-red-600",
    yellow: "bg-yellow-50 text-yellow-600",
    purple: "bg-purple-50 text-purple-600",
  };

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-4">
      <div className="flex items-center justify-between">
        <span className="text-sm text-gray-500">{title}</span>
        {icon && <div className={cn("p-2 rounded-lg", colorMap[color])}>{icon}</div>}
      </div>
      <div className="mt-2 flex items-end gap-2">
        <span className="text-2xl font-bold text-gray-900">{value}</span>
        {change !== undefined && (
          <span className={cn("text-sm font-medium pb-0.5", change >= 0 ? "text-green-600" : "text-red-600")}>
            {change >= 0 ? "+" : ""}{change}%
          </span>
        )}
      </div>
      {changeLabel && <span className="text-xs text-gray-400 mt-1 block">{changeLabel}</span>}
    </div>
  );
};

function cn(...classes: (string | boolean | undefined)[]) {
  return classes.filter(Boolean).join(" ");
}
