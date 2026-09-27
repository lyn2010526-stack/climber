import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

// `*?raw` returns an empty string under Vite 8 (the Tailwind plugin consumes
// the stylesheet before the raw loader runs), so the file is read from disk —
// the same approach as the presentation contract test.
const css = readFileSync(resolve(process.cwd(), 'src/index.css'), 'utf-8');

const customProperty = (name: string): string => {
  const match = new RegExp(`${name}:\\s*([^;]+);`).exec(css);
  if (!match?.[1]) throw new Error(`${name} is not declared in index.css`);
  return match[1].trim();
};

const declaration = (selector: string, property: string): string => {
  const block = new RegExp(`\\${selector}\\s*\\{([^}]*)\\}`).exec(css);
  const value = block?.[1] && new RegExp(`${property}:\\s*([^;]+);`).exec(block[1]);
  if (!value?.[1]) throw new Error(`${selector} does not declare ${property}`);
  return value[1].trim();
};

const pixels = (value: string): number => {
  const match = /^(\d+(?:\.\d+)?)px$/.exec(value);
  if (!match?.[1]) throw new Error(`expected a px length, received ${value}`);
  return Number(match[1]);
};

const reserve = customProperty('--mobile-nav-reserve');
const navHeight = pixels(customProperty('--mobile-nav-height'));
const itemMinHeight = pixels(customProperty('--mobile-nav-item-min-height'));

/** The reserve as a device without a home indicator resolves it. */
const reserved = (): number => {
  const substituted = reserve
    .replace(/var\(--mobile-nav-height\)/g, `${navHeight}px`)
    .replace(/env\(safe-area-inset-bottom,\s*0px\)/g, '0px');
  const match = /^calc\(\s*([\d.]+)px\s*\+\s*max\(\s*([\d.]+)px\s*,\s*([\d.]+)px\s*\)\s*\)$/.exec(substituted);
  if (!match) throw new Error(`reserve is not a strip plus a safe-area max: ${reserve}`);
  return Number(match[1]) + Math.max(Number(match[2]), Number(match[3]));
};

describe('mobile navigation reserve', () => {
  it('reserves the navigation strip plus the safe area from one declaration', () => {
    // The reserve exists so the strip height, the home-indicator inset and the
    // gap below the last row are decided in exactly one place.
    expect(reserve).toContain('var(--mobile-nav-height)');
    expect(reserve).toMatch(/max\(\s*12px\s*,\s*env\(safe-area-inset-bottom,\s*0px\)\s*\)/);
  });

  it.each(['.mobile-content', '.mobile-main'])('pads %s with the shared reserve', (selector) => {
    expect(declaration(selector, 'padding-bottom')).toBe('var(--mobile-nav-reserve)');
  });

  it('keeps a single reserve so neither shell can drift behind the navigation', () => {
    // A second hand-rolled calc is how the two reserves drifted apart before.
    expect(css.match(/padding-bottom:[^;]*var\(--mobile-nav-height\)[^;]*/g) ?? []).toEqual([]);
    expect(css.match(/--mobile-nav-reserve:/g)).toHaveLength(1);
  });

  it('reserves at least the navigation height plus a gap the last row scrolls into', () => {
    // The navigation is fixed over the content area, so the padding covers the
    // strip and the breathing room, on a device with and without a home
    // indicator alike.
    expect(reserved()).toBeGreaterThanOrEqual(navHeight + 12);
    expect(reserve).toContain('env(safe-area-inset-bottom, 0px)');
  });

  it('keeps the strip at least as tall as the tap targets it holds', () => {
    expect(itemMinHeight).toBeGreaterThanOrEqual(48);
    expect(navHeight).toBeGreaterThanOrEqual(itemMinHeight);
  });

  it('binds the navigation to the heights the reserve accounts for', () => {
    expect(declaration('.mobile-nav-item', 'min-height')).toBe('var(--mobile-nav-item-min-height)');
    expect(declaration('.mobile-bottom-nav', 'min-height')).toBe('var(--mobile-nav-height)');
    // The strip carries the safe area as padding, hence content-box.
    expect(declaration('.mobile-bottom-nav', 'box-sizing')).toBe('content-box');
    expect(declaration('.mobile-bottom-nav', 'padding-bottom')).toBe('env(safe-area-inset-bottom, 0px)');
  });
});
