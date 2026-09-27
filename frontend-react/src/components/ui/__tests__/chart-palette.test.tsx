import { afterAll, afterEach, beforeAll, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, waitFor } from '@testing-library/react';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { Global } from 'recharts';
import { Chart, LIGHT_THEME_SAFE_SERIES } from '../Chart';

afterEach(cleanup);

const source = readFileSync(resolve(process.cwd(), 'src/components/ui/Chart.tsx'), 'utf-8');
const theme = readFileSync(resolve(process.cwd(), 'src/index.css'), 'utf-8');

/**
 * `ResponsiveContainer` refuses to draw until a `ResizeObserver` reports a
 * non-zero content box, and the shared test stub is an inert class that never
 * fires. Reporting a real size is what turns these into assertions about the
 * rendered marks rather than about the wrapper.
 */
const CHART_BOX = { width: 640, height: 320 };

class MeasuredResizeObserver implements ResizeObserver {
  constructor(private readonly callback: ResizeObserverCallback) {}

  observe(target: Element) {
    const rect = { ...CHART_BOX, top: 0, left: 0, right: CHART_BOX.width, bottom: CHART_BOX.height, x: 0, y: 0, toJSON: () => ({}) };
    const entry = { target, contentRect: rect, borderBoxSize: [], contentBoxSize: [], devicePixelContentBoxSize: [] } as unknown as ResizeObserverEntry;
    setTimeout(() => this.callback([entry], this), 0);
  }

  unobserve() {}
  disconnect() {}
}

beforeAll(() => {
  vi.stubGlobal('ResizeObserver', MeasuredResizeObserver);
  // Line and bar marks are revealed on a timer, so a synchronous assertion would
  // otherwise see an empty surface. The switch is test-only; the component keeps
  // its default motion.
  Global.isAnimationActive = false;
});

afterAll(() => {
  vi.unstubAllGlobals();
  Global.isAnimationActive = true;
});

const DATA = [
  { name: 'mon', requests: 12, errors: 3, latency: 40 },
  { name: 'tue', requests: 20, errors: 5, latency: 30 },
  { name: 'wed', requests: 15, errors: 2, latency: 55 },
];

const seriesColors = (...keys: string[]) => keys.map(key => `var(--${key})`);

/**
 * `ResponsiveContainer` draws nothing until the stubbed `ResizeObserver` has
 * reported a size, and the report lands on a later tick. A synchronous read of
 * the tree therefore sees the wrapper and nothing inside it, so every test that
 * asserts on a mark waits for recharts to actually paint.
 */
const settle = async (container: HTMLElement) => {
  await waitFor(() => {
    expect(container.querySelector('.recharts-wrapper'), 'recharts wrapper').not.toBeNull();
  });
  await waitFor(
    () => {
      expect(container.querySelector('.recharts-surface'), 'recharts surface').not.toBeNull();
    },
    { timeout: 5000 },
  );
};

/** The palette block, read out of the source so the order stays asserted. */
const paletteBlock = source.slice(
  source.indexOf('const CHART_PALETTE'),
  source.indexOf('const DEFAULT_COLORS'),
);

const paletteEntries = (): { stroke: string; wash: string }[] =>
  [...paletteBlock.matchAll(/stroke: 'var\((--[a-z0-9-]+)\)', wash: 'var\((--[a-z0-9-]+)\)'/g)].map(
    match => ({ stroke: match[1]!, wash: match[2]! }),
  );

/**
 * The token values as the theme file declares them. A contrast assertion that
 * hardcoded the numbers would only prove that somebody once measured them; this
 * one re-measures, so a token change that costs legibility fails here.
 *
 * The dark values are the Tailwind theme block, which is the first thing in the
 * file; the light values are the theme override that follows it. Comments come
 * out first, because the token layer mentions the light selector in prose before
 * it declares it.
 */
const css = theme.replace(/\/\*[\s\S]*?\*\//g, '');

function blockBody(selector: string): string {
  const start = css.indexOf(selector);
  expect(start, `theme block ${selector}`).toBeGreaterThan(-1);
  // Walk the braces rather than slicing to the first one, since the rule that
  // follows the selector can hold nested blocks of its own.
  const open = css.indexOf('{', start);
  let depth = 0;
  let close = open;
  for (; close < css.length; close++) {
    if (css[close] === '{') depth++;
    else if (css[close] === '}' && --depth === 0) break;
  }
  return css.slice(open + 1, close);
}

const LIGHT_SELECTOR = '[data-theme="light"]';
const DARK_BODY = css.slice(0, css.indexOf(LIGHT_SELECTOR));
const LIGHT_BODY = blockBody(LIGHT_SELECTOR);

const readTokens = (body: string): Map<string, string> => {
  const tokens = new Map<string, string>();
  for (const match of body.matchAll(/(--[a-z0-9-]+)\s*:\s*([^;]+);/g)) {
    // A token that a later block overrides keeps the first value, which is the
    // one the base theme paints with.
    if (!tokens.has(match[1]!)) tokens.set(match[1]!, match[2]!.trim());
  }
  return tokens;
};

const THEMES: [string, Map<string, string>][] = [
  ['dark', readTokens(DARK_BODY)],
  ['light', readTokens(LIGHT_BODY)],
];

const hexToRgb = (value: string): [number, number, number] => {
  const match = /^#([0-9a-f]{3}|[0-9a-f]{6})$/i.exec(value);
  expect(match, `hex value ${value}`).not.toBeNull();
  const digits = match![1]!.length === 3 ? match![1]!.split('').map(c => c + c).join('') : match![1]!;
  return [0, 2, 4].map(offset => parseInt(digits.slice(offset, offset + 2), 16)) as [number, number, number];
};

const channelToLinear = (channel: number) => {
  const c = channel / 255;
  return c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
};

const luminance = ([r, g, b]: [number, number, number]) =>
  0.2126 * channelToLinear(r) + 0.7152 * channelToLinear(g) + 0.0722 * channelToLinear(b);

const contrast = (a: [number, number, number], b: [number, number, number]) => {
  const [x, y] = [luminance(a), luminance(b)];
  return (Math.max(x, y) + 0.05) / (Math.min(x, y) + 0.05);
};

const CANVASES = [
  '--color-bg-page',
  '--color-bg-surface-1',
  '--color-bg-surface-2',
  '--color-bg-surface-3',
  '--color-bg-surface-4',
];

describe('chart series palette', () => {
  it('pairs every stroke token with its own translucent wash, in one order', () => {
    const found = paletteEntries();
    // The order is the readability decision, so it is pinned: teal first because
    // it is the brand identity, then the widest hue spread the status roles can
    // offer, with the neutral role last so it reads as the leftover bucket.
    expect(found.map(entry => entry.stroke)).toEqual([
      '--color-accent',
      '--color-warning',
      '--color-info',
      '--color-success',
      '--color-error',
      '--color-unknown',
    ]);
    for (const entry of found) {
      expect(entry.wash, entry.stroke).toBe(`${entry.stroke}-subtle`);
    }
  });

  it('offers between six and eight slots, and no two of them the same colour', () => {
    const found = paletteEntries();
    expect(found.length).toBeGreaterThanOrEqual(6);
    expect(found.length).toBeLessThanOrEqual(8);
    for (const [name, declared] of THEMES) {
      const values = found.map(entry => declared.get(entry.stroke));
      expect(new Set(values).size, name).toBe(found.length);
    }
  });

  it('declares every stroke and wash token in both themes', () => {
    for (const [name, declared] of THEMES) {
      for (const entry of paletteEntries()) {
        expect(declared.has(entry.stroke), `${name} ${entry.stroke}`).toBe(true);
        expect(declared.has(entry.wash), `${name} ${entry.wash}`).toBe(true);
      }
    }
  });

  it('clears the non-text contrast floor on every surface of both themes', () => {
    for (const [name, declared] of THEMES) {
      for (const entry of paletteEntries()) {
        const colour = hexToRgb(declared.get(entry.stroke)!);
        for (const canvas of CANVASES) {
          const ratio = contrast(colour, hexToRgb(declared.get(canvas)!));
          expect(ratio, `${name} ${entry.stroke} on ${canvas}`).toBeGreaterThanOrEqual(3);
        }
      }
    }
  });

  it('keeps the slots inside one luminance band so no series outweighs another', () => {
    for (const [name, declared] of THEMES) {
      const values = paletteEntries().map(entry => luminance(hexToRgb(declared.get(entry.stroke)!)));
      const brightest = Math.max(...values);
      const dimmest = Math.min(...values);
      // 1.8 is the measured spread plus headroom: the dark theme sits at 1.75
      // and the light theme at 1.22.
      expect(brightest / dimmest, name).toBeLessThanOrEqual(1.8);
    }
  });

  it('publishes the light-safe ceiling as the whole palette', () => {
    // Every shipped slot clears the floor above in both themes, so the ceiling is
    // the palette length rather than a subset that callers have to police.
    expect(LIGHT_THEME_SAFE_SERIES).toBe(paletteEntries().length);
  });

  it('never reaches for a raw colour, a gradient or a palette utility class', () => {
    expect(source).not.toMatch(/#[0-9a-fA-F]{3,8}\b/);
    expect(source).not.toMatch(/\brgba?\(/);
    expect(source).not.toMatch(/gradient/i);
    expect(source).not.toMatch(
      /\b(?:bg|text|border|ring|fill|stroke)-(?:red|orange|amber|yellow|lime|green|emerald|teal|cyan|sky|blue|indigo|violet|purple|fuchsia|pink|rose|slate|gray|zinc|neutral|stone)-\d{2,3}\b/,
    );
  });

  it('leaves the area translucency to the wash token instead of a second alpha', () => {
    // recharts would otherwise multiply the wash by its own 0.6, so the pin has
    // to stay at one and no other opacity may appear in the file.
    expect(source).toContain('const WASH_OPACITY = 1;');
    expect(source).toContain('fillOpacity={WASH_OPACITY}');
    const opacities = [...source.matchAll(/(?:fillOpacity|fill-opacity|opacity)[:=]\s*{?([\d.]+)}?/g)].map(m => m[1]);
    expect(opacities.every(value => value === '1')).toBe(true);
  });
});

describe('chart axis, grid and tooltip tokens', () => {
  it('splits the structural roles across the tokens the design system defines', () => {
    expect(source).toContain("const GRID_STROKE = 'var(--color-border-subtle)'");
    expect(source).toContain("const AXIS_STROKE = 'var(--color-border-default)'");
    expect(source).toContain("fill: 'var(--color-text-muted)'");
    expect(source).toContain("const TYPE_XS = 'text-[length:var(--text-xs)]'");
    expect(source).toContain('className: TYPE_XS');
  });

  it('paints the tooltip panel with surface-1, border-default and shadow-lg', () => {
    expect(source).toContain('bg-[var(--color-bg-surface-1)]');
    expect(source).toContain('border-[var(--color-border-default)]');
    expect(source).toContain('shadow-[var(--shadow-lg)]');
    expect(source).toContain('rounded-[var(--radius-md)]');
  });

  it('keeps tooltip, legend and pie wording on the text tokens', () => {
    // recharts paints these in the series colour otherwise, and the light theme
    // puts the status roles between 3.9:1 and 4.4:1, which is short of the floor
    // for text.
    expect(source).toContain('text-[var(--color-text-secondary)]');
    expect(source).toContain('text-[var(--color-text-primary)]');
    expect(source).toContain("const LABEL_FILL = 'var(--color-text-secondary)'");
    expect(source).toContain('label={pieLabel}');
  });

  it('builds the pie label as a positioned text node, because jsdom never draws a wedge', () => {
    // recharts resolves the pie geometry from a real SVG measurement taken during
    // layout, so the wedges come out empty in jsdom however the observer reports.
    // A rendered assertion would therefore be a silently skipped one, and the
    // contract is asserted where it is decided: the label function recharts hands
    // the wedge coordinates to.
    expect(source).toContain('const pieLabel = ({ x, y, textAnchor, name, percent }: PieLabelRenderProps)');
    expect(source).toContain('fill={LABEL_FILL}');
    expect(source).toContain('textAnchor={textAnchor}');
    expect(source).toContain('dominantBaseline="middle"');
    // Wording goes to the node itself, never to a pie-supplied `labelList` prop,
    // which recharts would render in the slice colour.
    expect(source).toContain("`${name ?? ''} ${((percent ?? 0) * 100).toFixed(0)}%`");
    expect(source).not.toContain('labelList');
  });

  it('replaces the recharts defaults that hardcode a colour', () => {
    // DefaultTooltipContent ships an opaque white background and a grey border,
    // the legend wrapper ships its own colour, the active dot ships a white ring
    // and the pie ships a white outline between sectors. Each of those has to be
    // replaced or themed, and none of them may reach the DOM.
    expect(source).toContain('ChartTooltipPanel');
    expect(source).toContain('ChartLegend');
    expect(source).toContain('content={tooltipContent}');
    expect(source).toContain('content={legendContent}');
    expect(source).not.toMatch(/contentStyle|wrapperStyle|itemStyle|labelStyle/);
    expect(source).toContain("const MARK_GAP_STROKE = 'var(--color-bg-surface-1)'");
    expect(source).toContain('stroke={MARK_GAP_STROKE}');
    expect(source).toContain(
      'activeDot={{ r: ACTIVE_DOT_RADIUS, fill: seriesColors[i], stroke: MARK_GAP_STROKE }}',
    );
  });
});

describe('chart rendering', () => {
  it('renders every chart type and labels the figure for assistive tech', async () => {
    for (const type of ['line', 'bar', 'area', 'pie'] as const) {
      const { container, unmount } = render(
        <Chart
          type={type}
          data={DATA}
          series={[
            { key: 'requests', label: 'requests' },
            { key: 'errors', label: 'errors' },
          ]}
        />,
      );
      expect(container.querySelector(`[aria-label="${type} chart"]`), type).toBeInTheDocument();
      await settle(container);
      unmount();
    }
  });

  it('puts the series tokens straight onto the line marks, grid and axis', async () => {
    const { container } = render(
      <Chart
        type="line"
        data={DATA}
        series={[
          { key: 'requests', label: 'requests' },
          { key: 'errors', label: 'errors' },
        ]}
      />,
    );
    await settle(container);
    const strokes = [...container.querySelectorAll('.recharts-line-curve')].map(node => node.getAttribute('stroke'));
    expect(strokes).toEqual(['var(--color-accent)', 'var(--color-warning)']);

    const grid = container.querySelector('.recharts-cartesian-grid line');
    expect(grid?.getAttribute('stroke')).toBe('var(--color-border-subtle)');

    const axisLine = container.querySelector('.recharts-cartesian-axis-line');
    expect(axisLine?.getAttribute('stroke')).toBe('var(--color-border-default)');

    const tick = container.querySelector('.recharts-cartesian-axis-tick-value');
    expect(tick?.getAttribute('fill')).toBe('var(--color-text-muted)');
    expect(tick?.getAttribute('class')).toContain('text-[length:var(--text-xs)]');
  });

  it('fills an area with the wash token and leaves its own alpha alone', async () => {
    const { container } = render(
      <Chart
        type="area"
        data={DATA}
        series={[
          { key: 'requests', label: 'requests' },
          { key: 'errors', label: 'errors' },
        ]}
      />,
    );
    await settle(container);
    const areas = [...container.querySelectorAll('.recharts-area-area')];
    expect(areas.map(node => node.getAttribute('fill'))).toEqual([
      'var(--color-accent-subtle)',
      'var(--color-warning-subtle)',
    ]);
    expect(areas.map(node => node.getAttribute('fill-opacity'))).toEqual(['1', '1']);
    // recharts splits the area in two: the wash path and the outline path.
    const curves = [...container.querySelectorAll('.recharts-area-curve')];
    expect(curves.map(node => node.getAttribute('stroke'))).toEqual([
      'var(--color-accent)',
      'var(--color-warning)',
    ]);
  });

  it('keeps a caller colour on the wash it already pairs with', async () => {
    const { container } = render(
      <Chart
        type="area"
        data={DATA}
        series={[{ key: 'requests', label: 'requests', color: 'var(--color-info)' }]}
      />,
    );
    await settle(container);
    const area = container.querySelector('.recharts-area-area');
    expect(area?.getAttribute('fill')).toBe('var(--color-info-subtle)');
    expect(container.querySelector('.recharts-area-curve')?.getAttribute('stroke')).toBe('var(--color-info)');
  });

  it('wires the grid and the axis chrome only when asked', () => {
    const { container } = render(
      <Chart type="bar" data={DATA} series={[{ key: 'requests' }]} showGrid={false} showLegend={false} showTooltip={false} />,
    );
    expect(container.querySelector('.recharts-cartesian-grid')).toBeNull();
    expect(container.querySelector('.recharts-legend-wrapper')).toBeNull();
    expect(container.querySelector('.recharts-tooltip-wrapper')).toBeNull();
  });

  it('resolves a per-series colour before a caller palette, by series index', async () => {
    // Each series takes the palette slot for its own index unless it names a
    // colour itself, so an override on one series never shifts its neighbours.
    const { container } = render(
      <Chart
        type="line"
        data={DATA}
        series={[
          { key: 'requests', label: 'requests', color: 'var(--color-syntax-type)' },
          { key: 'errors', label: 'errors' },
          { key: 'latency', label: 'latency' },
        ]}
        colors={seriesColors('color-accent', 'color-info', 'color-success')}
      />,
    );
    await settle(container);
    const swatches = [...container.querySelectorAll('li span[aria-hidden="true"]')].map(node =>
      node.getAttribute('style'),
    );
    expect(swatches).toHaveLength(3);
    expect(swatches[0]).toContain('var(--color-syntax-type)');
    expect(swatches[1]).toContain('var(--color-info)');
    expect(swatches[2]).toContain('var(--color-success)');
  });

  it('wraps a short caller palette rather than running out of colours', async () => {
    const { container } = render(
      <Chart
        type="line"
        data={DATA}
        series={[
          { key: 'requests', label: 'requests' },
          { key: 'errors', label: 'errors' },
          { key: 'latency', label: 'latency' },
        ]}
        colors={seriesColors('color-accent', 'color-info')}
      />,
    );
    await settle(container);
    const swatches = [...container.querySelectorAll('li span[aria-hidden="true"]')].map(node =>
      node.getAttribute('style'),
    );
    expect(swatches[0]).toContain('var(--color-accent)');
    expect(swatches[1]).toContain('var(--color-info)');
    expect(swatches[2]).toContain('var(--color-accent)');
  });

  it('falls back to the shipped palette when the caller passes an empty one', async () => {
    const { container } = render(
      <Chart type="line" data={DATA} series={[{ key: 'requests', label: 'requests' }]} colors={[]} />,
    );
    await settle(container);
    const swatch = container.querySelector('li span[aria-hidden="true"]');
    expect(swatch?.getAttribute('style')).toContain('var(--color-accent)');
  });

  it('shows the legend on token-backed chrome with a series-coloured swatch', async () => {
    const { container } = render(
      <Chart type="line" data={DATA} series={[{ key: 'requests', label: 'requests' }]} />,
    );
    await settle(container);
    const list = [...container.querySelectorAll('ul')].find(node => node.textContent === 'requests');
    expect(list, 'legend list').toBeDefined();
    // The wording rides the text token, and only the swatch carries the series
    // colour, which is what keeps the label legible on a light canvas.
    expect(list?.className).toContain('text-[var(--color-text-secondary)]');
    const swatch = list?.querySelector('span[aria-hidden="true"]');
    expect(swatch?.getAttribute('style')).toContain('var(--color-accent)');
  });

  it('paints the tooltip panel with surface-1, border-default and shadow-lg', async () => {
    const { container } = render(
      <Chart type="line" data={DATA} series={[{ key: 'requests', label: 'requests' }]} />,
    );
    await settle(container);
    const wrapper = container.querySelector('.recharts-wrapper');
    expect(wrapper).not.toBeNull();
    fireEvent.mouseMove(wrapper!, { clientX: 120, clientY: 160 });

    // recharts settles the hover through a microtask, so the panel is not in the
    // tree within the same tick as the event.
    const tooltip = await waitFor(() => {
      const found = container.querySelector('[role="tooltip"]');
      expect(found, 'tooltip panel after hover').not.toBeNull();
      return found!;
    });
    expect(tooltip.className).toContain('bg-[var(--color-bg-surface-1)]');
    expect(tooltip.className).toContain('border-[var(--color-border-default)]');
    expect(tooltip.className).toContain('shadow-[var(--shadow-lg)]');
    // The swatch carries the series colour, the wording stays on a text token.
    expect(
      tooltip.querySelector('span[aria-hidden="true"]')?.getAttribute('style'),
    ).toContain('var(--color-accent)');
    expect(tooltip.querySelector('span.ml-auto')?.className).toContain('text-[var(--color-text-primary)]');
  });

  it('rings the active dot with the surface token so the hover mark stays readable', async () => {
    const { container } = render(
      <Chart type="line" data={DATA} series={[{ key: 'requests', label: 'requests' }]} />,
    );
    await settle(container);
    const wrapper = container.querySelector('.recharts-wrapper')!;
    fireEvent.mouseMove(wrapper, { clientX: 120, clientY: 160 });
    // recharts resolves the hovered index through a microtask.
    const activeDot = await waitFor(() => {
      const found = container.querySelector('.recharts-active-dot circle');
      expect(found, 'active dot after hover').not.toBeNull();
      return found!;
    });
    expect(activeDot.getAttribute('fill')).toBe('var(--color-accent)');
    expect(activeDot.getAttribute('stroke')).toBe('var(--color-bg-surface-1)');
  });

  it('survives a chart with no series', () => {
    const { container } = render(<Chart type="line" data={DATA} series={[]} />);
    expect(container.querySelector('[aria-label="line chart"]')).toBeInTheDocument();
  });
});
