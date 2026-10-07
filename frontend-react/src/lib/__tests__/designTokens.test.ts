import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import {
  icons,
  iconSize,
  iconSizes,
  statusIconFor,
  statusTones,
  type SemanticIconName,
} from '../icons';
import { tokenProvenance, darkTokenProvenance, lightTokenProvenance } from '../parityPalette';

const css = readFileSync(resolve(process.cwd(), 'src/index.css'), 'utf-8');
const statusIconSource = readFileSync(resolve(process.cwd(), 'src/components/ui/StatusIcon.tsx'), 'utf-8');

const themeStart = css.indexOf('@theme');
const lightStart = css.indexOf('[data-theme="light"] {');
const lightEnd = css.indexOf('\n}', lightStart);

const themeBlock = css.slice(themeStart, css.indexOf(':root'));
const lightBlock = css.slice(lightStart, lightEnd);

const declarations = (block: string) =>
  new Map([...block.matchAll(/(--[a-z0-9-]+):\s*([^;]+);/g)].map(match => [match[1]!, match[2]!.trim()]));

const declaredIn = (block: string, name: string) => new RegExp(`${name}:\\s*[^;]+;`).test(block);

const themeTokens = declarations(themeBlock);
const lightTokens = declarations(lightBlock);

describe('design token single source', () => {
  it('keeps colour, type, spacing, radius, shadow, motion and focus in one @theme block', () => {
    for (const name of ['--color-bg-page', '--color-accent', '--color-accent-active', '--color-unknown', '--text-2xs', '--space-4', '--radius-xs', '--radius-pill', '--shadow-md', '--focus-ring']) {
      expect(declaredIn(themeBlock, name), name).toBe(true);
    }
  });

  it('mirrors every token that carries its own value into the light theme', () => {
    // A token whose dark value is another token is an alias and resolves itself
    // per theme. A token with a literal value must be restated for light,
    // otherwise switching themes leaves a dark value on screen.
    const literals = [...themeTokens].filter(([name, value]) =>
      (name.startsWith('--color-') || name.startsWith('--shadow-')) && !value.startsWith('var('),
    );
    const missing = literals.map(([name]) => name).filter(name => !lightTokens.has(name));
    expect(missing).toEqual([]);
  });

  it('restates the accent trio and every semantic colour for light', () => {
    for (const name of [
      '--color-accent',
      '--color-accent-hover',
      '--color-accent-active',
      '--color-accent-foreground',
      '--color-accent-text',
      '--color-accent-subtle',
      '--color-success',
      '--color-warning',
      '--color-error',
      '--color-info',
      '--color-unknown',
    ]) {
      expect(lightTokens.get(name), name).toBeTruthy();
    }
  });

  it('exposes the full state vocabulary so pages never invent a value', () => {
    for (const name of [
      '--color-accent-hover',
      '--color-accent-active',
      '--color-accent-subtle',
      '--color-accent-foreground',
      '--color-accent-text',
      '--color-success',
      '--color-warning',
      '--color-error',
      '--color-info',
      '--color-unknown',
      '--color-bg-disabled',
    ]) {
      expect(declaredIn(themeBlock, name), name).toBe(true);
    }
  });

  it('keeps the four-rung icon ladder and the 24px radius ladder', () => {
    for (const name of ['--icon-xs', '--icon-sm', '--icon-md', '--icon-lg']) {
      expect(declaredIn(themeBlock, name), name).toBe(true);
    }
    expect(declaredIn(themeBlock, '--radius-xs')).toBe(true);
    expect(declaredIn(themeBlock, '--radius-pill')).toBe(true);
  });

  it('gives code and diff their own roles instead of borrowing the semantic colours', () => {
    // A diff and a stack trace are the two densest places a reviewer reads
    // coloured text. Reusing `--color-success` for an added line would put a
    // prose-tuned value under a small monospace font, so each gets its own.
    for (const name of [
      '--color-syntax-comment',
      '--color-syntax-keyword',
      '--color-syntax-function',
      '--color-syntax-string',
      '--color-syntax-number',
      '--color-syntax-type',
      '--color-syntax-operator',
      '--color-diff-added',
      '--color-diff-removed',
      '--color-diff-hunk',
      '--color-diff-added-bg',
      '--color-diff-removed-bg',
    ]) {
      expect(declaredIn(themeBlock, name), name).toBe(true);
      expect(lightTokens.has(name), `${name} in light`).toBe(true);
    }
  });

  it('keeps a code surface dark in both themes and pins its text colour', () => {
    // The code block rule lives outside the token blocks, so it is checked by
    // reading the rule itself: a code surface that follows the page surface
    // would render dark-on-dark the moment the light theme is selected.
    const codeRule = css.slice(css.indexOf('.code-block {'), css.indexOf('}', css.indexOf('.code-block {')));
    expect(codeRule).toContain('var(--color-code-bg)');
    expect(codeRule).not.toMatch(/#[0-9a-fA-F]{3,8}/);
  });
});

describe('parity palette provenance', () => {
  it('records the exact hex each benchmark value landed on', () => {
    // Looked up per theme: a token such as `--color-bg-page` has a different
    // value in each, so the merged list cannot be keyed by token alone.
    const dark = new Map(darkTokenProvenance.map(entry => [entry.token, entry]));
    const light = new Map(lightTokenProvenance.map(entry => [entry.token, entry]));
    expect(dark.get('--color-bg-page')?.value).toBe('#20222E');
    expect(dark.get('--color-accent')?.value).toBe('#5BC8D8');
    expect(dark.get('--color-diff-added')?.value).toBe('#7EC97E');
    // Light is a single white canvas, so page and surface-1
    // share #FFFFFF and depth comes from borders.
    expect(light.get('--color-bg-page')?.value).toBe('#FFFFFF');
    expect(light.get('--color-text-primary')?.value).toBe('#2E3440');
    expect(tokenProvenance.length).toBe(darkTokenProvenance.length + lightTokenProvenance.length);
  });

  it('never leaves a tracked token without a benchmark role', () => {
    for (const entry of tokenProvenance) {
      expect(entry.role, entry.token).not.toBe('unclassified');
      expect(['dark-reference', 'syntax-reference', 'deepseek', 'derived']).toContain(entry.source);
    }
  });

  it('keeps every tracked dark value identical to the token block', () => {
    for (const entry of darkTokenProvenance) {
      expect(themeTokens.get(entry.token)?.toUpperCase(), entry.token).toBe(entry.value);
    }
  });

  it('keeps every tracked light value identical to the light block', () => {
    for (const entry of lightTokenProvenance) {
      expect(lightTokens.get(entry.token)?.toUpperCase(), entry.token).toBe(entry.value);
    }
  });
});

describe('semantic icon system', () => {
  /** One window per name, so each key is only ever judged on its own line. */
  const lineOf = (name: string) => statusIconSource.split('\n').find(line => line.includes(name));

  it('ships only the four rungs of the size ladder', () => {
    expect(iconSizes).toEqual({ xs: 12, sm: 14, md: 16, lg: 20 });
    expect(Object.keys(iconSizes)).toHaveLength(4);
    for (const pixels of Object.values(iconSizes)) expect(Number.isInteger(pixels)).toBe(true);
    expect(iconSize('xs')).toBe(12);
    expect(iconSize('lg')).toBe(20);
    // An unrecognised rung falls back to the body size instead of rendering
    // nothing, so a control can never end up with a glyph of no size.
    expect(iconSize('xxl' as unknown as keyof typeof iconSizes)).toBe(iconSizes.md);
    expect(iconSize()).toBe(iconSizes.md);
  });

  it('gives every status tone a distinct icon, so no two states share a drawing', () => {
    expect(statusTones).toHaveLength(8);
    for (const tone of statusTones) {
      const name = statusIconFor(tone);
      expect(name, tone).not.toBeNull();
      expect(icons[name as SemanticIconName], tone).toBeTruthy();
    }
    // A shared glyph would collapse two states into one at a glance, which is
    // the failure the vocabulary exists to prevent.
    const drawn = statusTones.map(tone => statusIconFor(tone));
    expect(new Set(drawn).size).toBe(statusTones.length);
  });

  it('keeps an unreported value distinct from loading and from a failure', () => {
    const unknown = statusIconFor('unknown');
    expect(unknown).not.toBe(statusIconFor('loading'));
    expect(unknown).not.toBe(statusIconFor('error'));
    // Queued and in flight are both greys, so their drawings are what separates
    // them once motion is taken away.
    expect(statusIconFor('queued')).not.toBe(statusIconFor('loading'));
    expect(statusIconFor('queued')).not.toBe(unknown);
  });

  it('reports no icon when a control carries no status', () => {
    expect(statusIconFor(undefined)).toBeNull();
    expect(statusIconFor(null)).toBeNull();
    // The renderer honours the same rule instead of substituting a neutral
    // glyph, so an absent status and a healthy one cannot look alike.
    expect(statusIconSource).toMatch(/if \(!tone\) return null;/);
  });

  it('renders every tone through StatusIcon, on the same name the library reports', () => {
    for (const tone of statusTones) {
      const semantic = statusIconFor(tone) as SemanticIconName;
      // The single renderer names the icon instead of looking it up, and both
      // tables have to agree: a new tone with a glyph here and a different name
      // in the library is a drift this catches.
      expect(lineOf(`${tone}: icons.${semantic},`), tone).toBeDefined();
    }
  });

  it('paints every tone from a colour token, and never from a literal', () => {
    const colourOf = (tone: string) => lineOf(`${tone}: 'text-[var(`);
    for (const tone of statusTones) {
      expect(colourOf(tone), tone).toMatch(/^\s*[\w]+: 'text-\[var\(--color-[\w-]+\)\]',$/);
    }
    // Every arbitrary value the renderer asks Tailwind for is a colour token,
    // and the tone class is the only thing painting the glyph: the drawing
    // itself can only pick the colour up as `currentColor`.
    const arbitrary = [...statusIconSource.matchAll(/-\[([^\]]+)\]/g)].map(match => match[1]!);
    expect(arbitrary.length).toBe(statusTones.length);
    for (const value of arbitrary) expect(value, value).toMatch(/^var\(--color-[\w-]+\)$/);
    expect(statusIconSource).not.toMatch(/#[0-9a-fA-F]{3,8}\b|rgba?\(/);
    expect(statusIconSource).not.toMatch(/stroke=|fill=/);
  });

  it('lets only the running status move', () => {
    expect(statusIconSource).toMatch(/tone === 'loading' && spin !== false/);
    expect(statusIconSource).toContain('motion-reduce:animate-none');
  });

  it('keeps the status glyph decorative, since the label carries the meaning', () => {
    expect(statusIconSource).toContain('aria-hidden="true"');
    expect(statusIconSource).toContain('focusable="false"');
  });
});
