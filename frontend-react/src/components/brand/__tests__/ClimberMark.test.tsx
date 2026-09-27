import { describe, it, expect } from 'vitest';
import { render } from '@testing-library/react';
import { CLIMBER_MARK, ClimberMark } from '../ClimberMark';

const geometry = () => {
  const { container } = render(<ClimberMark />);
  const svg = container.querySelector('svg')!;
  return {
    svg,
    polyline: svg.querySelector('polyline')!,
    node: svg.querySelector('circle')!,
  };
};

/** Every vertex of the single ascent polyline, as [x, y] pairs. */
const vertices = (points: string) =>
  points
    .trim()
    .split(/\s+/)
    .reduce<Array<[number, number]>>((pairs, value, index, all) => {
      if (index % 2 === 0) pairs.push([Number(value), Number(all[index + 1])]);
      return pairs;
    }, []);

describe('ClimberMark', () => {
  it('renders an inline svg marked aria-hidden', () => {
    const { svg } = geometry();
    expect(svg).toBeTruthy();
    expect(svg).toHaveAttribute('aria-hidden', 'true');
    expect(svg).toHaveAttribute('focusable', 'false');
  });

  it('applies default 16px size and honours a custom size on the 24-unit grid', () => {
    const { container: def } = render(<ClimberMark />);
    const defSvg = def.querySelector('svg')!;
    expect(defSvg).toHaveAttribute('width', '16');
    expect(defSvg).toHaveAttribute('height', '16');

    const { container } = render(<ClimberMark size={24} />);
    const svg = container.querySelector('svg')!;
    expect(svg).toHaveAttribute('width', '24');
    expect(svg).toHaveAttribute('height', '24');
    expect(svg).toHaveAttribute('viewBox', '0 0 24 24');
    expect(svg).toHaveAttribute('viewBox', CLIMBER_MARK.viewBox);
  });

  it('keeps the whole drawing inside the 24-unit box at the default weight', () => {
    const { polyline, node } = geometry();
    const half = CLIMBER_MARK.strokeWidth / 2;
    const { cx, cy, r } = CLIMBER_MARK.node;
    const bounds = [
      ...vertices(polyline.getAttribute('points')!).flatMap(([x, y]) => [x - half, x + half, y - half, y + half]),
      cx - r - half,
      cx + r + half,
      cy - r - half,
      cy + r + half,
    ];
    // Round caps and joins grow the ink past the last vertex, so the geometry
    // is checked against the stroke box, not the raw points.
    expect(Math.min(...bounds)).toBeGreaterThan(0);
    expect(Math.max(...bounds)).toBeLessThan(24);
    // The node is a circle of the same weight, so it lands on the same grid.
    expect(Number(node.getAttribute('r'))).toBeGreaterThan(0);
  });

  it('holds one optical weight and lets callers raise it', () => {
    const { svg } = geometry();
    expect(svg).toHaveAttribute('stroke-width', '1.75');
    expect(CLIMBER_MARK.strokeWidth).toBe(1.75);

    const { container } = render(<ClimberMark strokeWidth={2} />);
    expect(container.querySelector('svg')).toHaveAttribute('stroke-width', '2');
  });

  it('rounds every cap and join so vertices keep one thickness at any weight', () => {
    const { svg } = geometry();
    expect(svg).toHaveAttribute('stroke-linecap', 'round');
    expect(svg).toHaveAttribute('stroke-linejoin', 'round');
  });

  it('forwards className and inherits the surrounding colour by default', () => {
    const { container } = render(<ClimberMark className="workspace-mark-icon" />);
    const svg = container.querySelector('svg')!;
    expect(svg).toHaveClass('workspace-mark-icon');
    expect(svg).toHaveAttribute('stroke', 'currentColor');
  });

  it('accepts a token reference as the colour, never a literal', () => {
    const { container } = render(<ClimberMark color="var(--color-accent)" />);
    expect(container.querySelector('svg')).toHaveAttribute('stroke', 'var(--color-accent)');
  });

  it('draws one ascending polyline aimed at a summit node', () => {
    const { polyline, node } = geometry();
    expect(polyline).toBeTruthy();
    expect(node).toBeTruthy();

    const points = vertices(polyline.getAttribute('points')!);
    expect(points.length).toBe(4);
    // Ascent reads left to right and bottom to top: every step gains height,
    // and the last vertex sits below-left of the summit.
    for (let i = 1; i < points.length; i += 1) {
      expect(points[i]![1]).toBeLessThan(points[i - 1]![1]);
    }
    expect(points.at(-1)![0]).toBeLessThan(CLIMBER_MARK.node.cx);
    expect(points.at(-1)![1]).toBeGreaterThan(CLIMBER_MARK.node.cy);
  });

  it('keeps the summit a circle of the same weight as the ridge, not a filled block', () => {
    const { svg, node } = geometry();
    expect(node.getAttribute('r')).toBe(String(CLIMBER_MARK.node.r));
    expect(Number(node.getAttribute('r'))).toBeGreaterThan(0);
    // The node inherits the root stroke, so it carries no colour of its own.
    expect(node.getAttribute('stroke')).toBeNull();
    expect(node.getAttribute('fill')).toBeNull();
    expect(svg.getAttribute('fill')).toBe('none');
  });

  it('holds a visible gap between the ridge and the summit at 16px', () => {
    const { polyline } = geometry();
    const end = vertices(polyline.getAttribute('points')!).at(-1)!;
    const { cx, cy, r } = CLIMBER_MARK.node;
    const reach =
      Math.hypot(cx - end[0], cy - end[1]) -
      r -
      CLIMBER_MARK.strokeWidth / 2 -
      CLIMBER_MARK.strokeWidth / 2;
    // Rendered gap at the 16px shell size, in CSS pixels.
    const gapAt16 = (reach * 16) / 24;
    expect(gapAt16).toBeGreaterThan(0.8);
    expect(gapAt16).toBeLessThan(2);
  });

  it('strokes in one colour with no fill, gradient or decorative layer', () => {
    const { svg } = geometry();
    expect(svg).toHaveAttribute('fill', 'none');
    expect(svg.querySelector('linearGradient')).toBeNull();
    expect(svg.querySelector('radialGradient')).toBeNull();
    expect(svg.querySelector('mask')).toBeNull();
    expect(svg.querySelector('filter')).toBeNull();
    expect(svg.querySelector('defs')).toBeNull();
    expect(svg.querySelectorAll('path')).toHaveLength(0);
    // No glyph carries its own paint: the root stroke is the only colour.
    for (const shape of Array.from(svg.children)) {
      expect(shape.getAttribute('fill')).toBeNull();
      expect(shape.getAttribute('stroke')).toBeNull();
    }
    // Two shapes only: the ridge and the summit. Everything else would not
    // survive the 15px rung.
    expect(svg.children).toHaveLength(2);
  });
});
