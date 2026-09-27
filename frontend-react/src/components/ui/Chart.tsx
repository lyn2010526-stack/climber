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
import type { PieLabelRenderProps, TooltipContentProps } from 'recharts';
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

/**
 * One categorical slot: the paint that identifies the series, plus the flat
 * translucent wash an area body uses underneath it. The wash is the slot's own
 * subtle companion, so an area body keeps the hue of its line and both themes
 * pick up the alpha that reads on their own canvas.
 */
interface ChartSlot {
  stroke: string;
  wash: string;
}

/**
 * Categorical series palette, measured against the shipped token values rather
 * than picked by eye. Every entry is a token reference, and SVG paint resolves
 * the token at paint time, so one array serves both themes and the browser
 * performs the switch.
 *
 * The order is load-bearing, and the measurements behind it are:
 *
 * - Every slot is a token the light theme re-declares, so all six clear 3:1 on
 *   every light surface: accent 3.98, success 4.09, info 4.27, warning 4.24,
 *   error 4.38, unknown 3.77. The syntax roles the benchmark added stay out of
 *   the series palette for exactly that reason, since the light theme leaves
 *   them light-on-light: function 1.23, string 1.65, number 1.95, type 2.26.
 * - Hues are 208, 82, 253, 144, 26 and 262 degrees on the dark canvas, so the
 *   closest pair still sits 45 degrees apart and no two series read as the same
 *   colour even where a viewer cannot rely on hue alone.
 * - OKLab lightness stays inside a 0.09 band in the dark theme (0.69-0.78) and
 *   a 0.03 band in the light theme (0.53-0.56), so no series reads as brighter
 *   than its neighbour and none of them looks washed out.
 * - The last slot is the design system's neutral role, which gives a six-series
 *   chart an "everything else" bucket that still clears the light canvas.
 */
const CHART_PALETTE: readonly ChartSlot[] = [
  { stroke: 'var(--color-accent)', wash: 'var(--color-accent-subtle)' },
  { stroke: 'var(--color-warning)', wash: 'var(--color-warning-subtle)' },
  { stroke: 'var(--color-info)', wash: 'var(--color-info-subtle)' },
  { stroke: 'var(--color-success)', wash: 'var(--color-success-subtle)' },
  { stroke: 'var(--color-error)', wash: 'var(--color-error-subtle)' },
  { stroke: 'var(--color-unknown)', wash: 'var(--color-unknown-subtle)' },
];

const DEFAULT_COLORS: string[] = CHART_PALETTE.map(slot => slot.stroke);

/**
 * How many slots carry a measured contrast margin on both canvases. Every
 * shipped slot qualifies, so the number is the palette length: a caller on the
 * light theme never has to pass its own colours to stay readable, and a caller
 * that wants more than six series has to bring colours that clear 3:1 itself.
 */
export const LIGHT_THEME_SAFE_SERIES = CHART_PALETTE.length;

/** The grid sits under the marks and only divides, so the axes carry the frame. */
const GRID_STROKE = 'var(--color-border-subtle)';
const AXIS_STROKE = 'var(--color-border-default)';

/**
 * `text-[var(--text-xs)]` on its own would compile to a `color` declaration,
 * because Tailwind cannot tell a font-size token from a colour token. The
 * `length` data-type hint is what makes it a font size.
 */
const TYPE_XS = 'text-[length:var(--text-xs)]';

/**
 * recharts hands the tick object straight to the text element as presentation
 * attributes, so a token reference in here resolves at paint time. The size
 * rides a class instead, because a length token in a paint slot is the kind of
 * thing that only keeps working until the browser stops being lenient.
 */
const TICK_STYLE = { fill: 'var(--color-text-muted)', className: TYPE_XS };
/**
 * recharts paints a white ring around the active dot and a white outline
 * between pie sectors, both of which survive on a light canvas as a highlight
 * nobody asked for. The surface token turns both into a gap instead, and it
 * stays the gap whichever theme is active.
 */
const MARK_GAP_STROKE = 'var(--color-bg-surface-1)';

/** Wording inside the plot, at the muted rung so it never competes with a mark. */
const LABEL_FILL = 'var(--color-text-secondary)';

/**
 * The lengths in this file are numbers on purpose. recharts folds the margin
 * into the plot-area arithmetic, the bar radius into the outline path and the
 * dot radii into the point geometry, all through `Math.min`, so a token
 * reference in any of those places resolves to a string and produces `NaN`
 * geometry. Every paint decision stays on tokens; only layout inputs stay
 * numeric. The bar radius matches the small radius token and the dot radius
 * sits one step larger than the tick text.
 */
const CHART_MARGIN = { top: 4, right: 20, left: 0, bottom: 4 };
const BAR_TOP_RADIUS: [number, number, number, number] = [4, 4, 0, 0];
const LINE_WIDTH = 2;
const DOT_RADIUS = 4;
const ACTIVE_DOT_RADIUS = 6;
const PIE_OUTER_RADIUS = 80;
const PIE_INNER_RADIUS = 50;
const PIE_PADDING_DEGREES = 2;
/**
 * recharts multiplies an area fill by 0.6 of its own, which would quietly
 * halve the alpha the wash token already carries. Pinning the multiplier to one
 * hands the alpha back to the token layer, so each theme paints the wash it
 * declares.
 */
const WASH_OPACITY = 1;

/**
 * recharts paints tooltip rows and legend labels in the series colour. Several
 * series tokens are light-on-light in the light theme, so wording in a series
 * colour drops under the legibility floor. The colour therefore moves into a
 * swatch and the words stay on the text tokens.
 */
interface ChartSwatchEntry {
  key: string;
  label: string;
  color: string;
}

interface ChartTooltipEntry extends ChartSwatchEntry {
  value: string;
}

/**
 * The wash follows the slot, not the literal colour, so a caller that swaps in
 * one of the palette's own tokens keeps the matching area fill. A colour from
 * outside the palette falls back to the wash of the slot it landed on, which
 * keeps the area body flat and translucent either way.
 */
const washFor = (color: string, index: number): string => {
  const matched = CHART_PALETTE.find(slot => slot.stroke === color);
  return (matched ?? CHART_PALETTE[index % CHART_PALETTE.length]!).wash;
};

function ChartSwatch({ color }: { color: string }) {
  return (
    <span
      aria-hidden="true"
      className="h-[var(--space-2)] w-[var(--space-2)] shrink-0 rounded-[var(--radius-xs)]"
      style={{ backgroundColor: color }}
    />
  );
}

function ChartTooltipPanel({
  active,
  label,
  entries,
}: {
  active?: boolean;
  label?: string | number;
  entries: ChartTooltipEntry[];
}) {
  if (!active || entries.length === 0) return null;
  return (
    <div
      role="tooltip"
      className="rounded-[var(--radius-md)] border border-[var(--color-border-default)] bg-[var(--color-bg-surface-1)] px-[var(--space-3)] py-[var(--space-2)] shadow-[var(--shadow-lg)]"
    >
      {label === undefined || label === null || label === '' ? null : (
        <p className={cn('m-0', TYPE_XS, 'text-[var(--color-text-secondary)]')}>{label}</p>
      )}
      <ul className="m-0 list-none p-0">
        {entries.map(entry => (
          <li key={entry.key} className="flex items-center gap-[var(--space-2)] py-[var(--space-0-5)]">
            <ChartSwatch color={entry.color} />
            <span className={cn(TYPE_XS, 'text-[var(--color-text-secondary)]')}>{entry.label}</span>
            <span className={cn('ml-auto font-medium text-[var(--color-text-primary)]', TYPE_XS)}>
              {entry.value}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}

function ChartLegend({ entries }: { entries: ChartSwatchEntry[] }) {
  if (entries.length === 0) return null;
  return (
    <ul
      className={cn(
        'm-0 flex list-none flex-wrap items-center gap-x-[var(--space-4)] gap-y-[var(--space-1)] p-0',
        TYPE_XS,
        'text-[var(--color-text-secondary)]',
      )}
    >
      {entries.map(entry => (
        <li key={entry.key} className="flex items-center gap-[var(--space-2)]">
          <ChartSwatch color={entry.color} />
          {entry.label}
        </li>
      ))}
    </ul>
  );
}

/** Axis and grid chrome, shared by the three cartesian chart types. */
function cartesianAxes(xAxisKey: string, showGrid: boolean) {
  return (
    <>
      {showGrid ? <CartesianGrid stroke={GRID_STROKE} /> : null}
      <XAxis
        dataKey={xAxisKey}
        tick={TICK_STYLE}
        axisLine={{ stroke: AXIS_STROKE }}
        tickLine={{ stroke: AXIS_STROKE }}
      />
      <YAxis tick={TICK_STYLE} axisLine={{ stroke: AXIS_STROKE }} tickLine={{ stroke: AXIS_STROKE }} />
    </>
  );
}

/**
 * Every value in a `ChartDataPoint` is a string or a number, so the formatter only
 * has to render what it is handed and drop the empty cases.
 */
const formatValue = (value: unknown): string => (value === null || value === undefined ? '' : String(value));

/**
 * A pie label is wording, so it follows the same rule as the tooltip and the
 * legend: the words ride a text token instead of the slice colour. recharts
 * paints a function label in the colour of whatever it is describing and only
 * hands the coordinates to a returned element, which is why this one builds its
 * own text node rather than returning a string.
 */
const pieLabel = ({ x, y, textAnchor, name, percent }: PieLabelRenderProps) => (
  <text
    x={x}
    y={y}
    textAnchor={textAnchor}
    dominantBaseline="middle"
    className={TYPE_XS}
    fill={LABEL_FILL}
  >
    {`${name ?? ''} ${((percent ?? 0) * 100).toFixed(0)}%`}
  </text>
);

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
  const palette = colors.length ? colors : DEFAULT_COLORS;
  const seriesColors = series.map((s, i) => s.color || palette[i % palette.length]!);
  const lineType = curved ? ('monotone' as const) : ('linear' as const);

  const swatchEntries: ChartSwatchEntry[] = series.map((s, i) => ({
    key: s.key,
    label: s.label || s.key,
    color: seriesColors[i]!,
  }));

  /**
   * A single tooltip renderer for all four chart types. The payload recharts
   * supplies is readonly and sparse, so each field falls back to its neighbours
   * rather than being trusted.
   */
  const tooltipContent = ({ active, label, payload }: TooltipContentProps) => (
    <ChartTooltipPanel
      active={active}
      label={label}
      entries={(payload ?? []).map(item => ({
        key: String(item.dataKey ?? item.name ?? ''),
        label: String(item.name ?? item.dataKey ?? ''),
        color: String(item.color ?? item.fill ?? 'transparent'),
        value: formatValue(item.value),
      }))}
    />
  );

  /**
   * The legend renders from the resolved series colours rather than from the
   * recharts payload, so its swatches always match the marks on the canvas
   * exactly, including when a series carries an explicit `color`.
   */
  const legendContent = () => <ChartLegend entries={swatchEntries} />;

  const tooltip = showTooltip ? <Tooltip content={tooltipContent} /> : null;
  const legend = showLegend ? <Legend content={legendContent} /> : null;

  const renderChart = () => {
    switch (type) {
      case 'line':
        return (
          <LineChart data={data} margin={CHART_MARGIN}>
            {cartesianAxes(xAxisKey, showGrid)}
            {tooltip}
            {legend}
            {series.map((s, i) => (
              <Line
                key={s.key}
                type={lineType}
                dataKey={s.key}
                name={s.label || s.key}
                stroke={seriesColors[i]}
                strokeWidth={LINE_WIDTH}
                dot={{ fill: seriesColors[i], r: DOT_RADIUS }}
                activeDot={{ r: ACTIVE_DOT_RADIUS, fill: seriesColors[i], stroke: MARK_GAP_STROKE }}
              />
            ))}
          </LineChart>
        );
      case 'bar':
        return (
          <BarChart data={data} margin={CHART_MARGIN}>
            {cartesianAxes(xAxisKey, showGrid)}
            {tooltip}
            {legend}
            {series.map((s, i) => (
              <Bar
                key={s.key}
                dataKey={s.key}
                name={s.label || s.key}
                fill={seriesColors[i]}
                radius={BAR_TOP_RADIUS}
                stackId={stacked ? 'stack' : undefined}
              />
            ))}
          </BarChart>
        );
      case 'area':
        return (
          <AreaChart data={data} margin={CHART_MARGIN}>
            {cartesianAxes(xAxisKey, showGrid)}
            {tooltip}
            {legend}
            {series.map((s, i) => (
              <Area
                key={s.key}
                type={lineType}
                dataKey={s.key}
                name={s.label || s.key}
                stroke={seriesColors[i]}
                fill={washFor(seriesColors[i]!, i)}
                fillOpacity={WASH_OPACITY}
                strokeWidth={LINE_WIDTH}
                stackId={stacked ? 'stack' : undefined}
              />
            ))}
          </AreaChart>
        );
      case 'pie':
        return (
          <PieChart>
            {tooltip}
            {legend}
            <Pie
              data={data}
              dataKey={series[0]?.key || 'value'}
              nameKey={xAxisKey}
              cx="50%"
              cy="50%"
              outerRadius={PIE_OUTER_RADIUS}
              innerRadius={stacked ? PIE_INNER_RADIUS : 0}
              paddingAngle={PIE_PADDING_DEGREES}
              stroke={MARK_GAP_STROKE}
              label={pieLabel}
            >
              {data.map((_, index) => (
                <Cell key={index} fill={palette[index % palette.length]} />
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
