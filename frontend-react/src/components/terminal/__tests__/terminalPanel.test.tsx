import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen, waitFor } from '@testing-library/react';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import type { ITerminalOptions, Terminal } from '@xterm/xterm';
import { TerminalPanel, TERMINAL_THEME_TOKENS } from '../TerminalPanel';

const { created } = vi.hoisted(() => ({ created: [] as unknown[] }));

// The real xterm with a subclass that records every instance, so a test can
// read the options the panel actually handed to the terminal.
vi.mock('@xterm/xterm', async () => {
  const actual = await vi.importActual<typeof import('@xterm/xterm')>('@xterm/xterm');
  class RecordedTerminal extends actual.Terminal {
    constructor(options?: ITerminalOptions) {
      super(options);
      created.push(this);
    }
  }
  return { ...actual, Terminal: RecordedTerminal };
});

const { Terminal: Xterm } = await import('@xterm/xterm');

afterEach(() => {
  cleanup();
  created.length = 0;
  vi.restoreAllMocks();
  document.documentElement.removeAttribute('data-theme');
});

const css = readFileSync(resolve(process.cwd(), 'src/index.css'), 'utf-8');

/** The literal value a token resolves to in one theme block. */
const tokenValue = (name: string, theme: 'dark' | 'light' = 'dark'): string | undefined => {
  const start = theme === 'dark' ? 0 : css.indexOf('[data-theme="light"] {');
  const end = theme === 'dark' ? css.indexOf('[data-theme="light"] {') : css.indexOf('\n}', start);
  return new RegExp(`${name}:\\s*([^;]+);`).exec(css.slice(start, end))?.[1]?.trim();
};

const channel = (value: number): number => {
  const ratio = value / 255;
  return ratio <= 0.03928 ? ratio / 12.92 : Math.pow((ratio + 0.055) / 1.055, 2.4);
};

const luminance = (hex: string): number =>
  0.2126 * channel(parseInt(hex.slice(1, 3), 16)) +
  0.7152 * channel(parseInt(hex.slice(3, 5), 16)) +
  0.0722 * channel(parseInt(hex.slice(5, 7), 16));

const contrast = (foreground: string, background: string): number => {
  const a = luminance(foreground);
  const b = luminance(background);
  return a < b ? (b + 0.05) / (a + 0.05) : (a + 0.05) / (b + 0.05);
};

const channels = (hex: string): [number, number, number] => [
  parseInt(hex.slice(1, 3), 16),
  parseInt(hex.slice(3, 5), 16),
  parseInt(hex.slice(5, 7), 16),
];

const toHex = (values: [number, number, number]): string =>
  `#${values.map(value => Math.max(0, Math.min(255, value)).toString(16).padStart(2, '0')).join('')}`;

/**
 * Mirrors xterm's own `Color.ensureContrastRatio`, which `minimumContrastRatio`
 * applies to every glyph: nudge the colour towards white in 10% steps, and
 * towards black if that is not enough, then keep whichever reaches the ratio.
 */
const contrastAfterLift = (foreground: string, background: string, ratio: number): number => {
  let best = contrast(foreground, background);
  for (const towardsLight of [true, false]) {
    let value = channels(foreground);
    let current = best;
    while (current < ratio && (towardsLight ? value.some(c => c < 255) : value.some(c => c > 0))) {
      value = value.map(c => (towardsLight
        ? Math.min(255, c + Math.ceil((255 - c) * 0.1))
        : Math.max(0, c - Math.ceil(c * 0.1)))) as [number, number, number];
      current = contrast(toHex(value), background);
      best = Math.max(best, current);
    }
    if (best >= ratio) break;
  }
  return best;
};

type PaintedTheme = {
  foreground: { css: string; rgba: number };
  ansi: Array<{ css: string; rgba: number }>;
};

const paint = (theme?: Record<string, string>): PaintedTheme => {
  const term = new (Xterm as unknown as new (options?: ITerminalOptions) => Terminal)(theme ? { theme } : {});
  const host = document.createElement('div');
  document.body.appendChild(host);
  term.open(host);
  const service = (term as unknown as { _core: { _themeService: { colors: PaintedTheme & Record<string, unknown> } } })._core._themeService;
  const snapshot: PaintedTheme = {
    foreground: { ...service.colors.foreground },
    ansi: service.colors.ansi.map(color => ({ ...color })),
  };
  term.dispose();
  host.remove();
  return snapshot;
};

/** Resolves the token layer the way the browser would, from the map under test. */
const tokenLayer = (theme: 'dark' | 'light'): Map<string, string> =>
  new Map(Object.values(TERMINAL_THEME_TOKENS).map(token => [token, tokenValue(token, theme)!]));

const stubTokenLayer = (values: Map<string, string>) => {
  const real = window.getComputedStyle.bind(window);
  vi.spyOn(window, 'getComputedStyle').mockImplementation((element, pseudo) => {
    const style = real(element, pseudo);
    return new Proxy(style, {
      get(target, property, receiver) {
        if (property === 'getPropertyValue') {
          return (name: string) => (values.has(name) ? values.get(name)! : target.getPropertyValue(name));
        }
        const value = Reflect.get(target, property, receiver);
        return typeof value === 'function' ? value.bind(target) : value;
      },
    });
  });
};

const lastTerminal = (): Terminal => created.at(-1) as unknown as Terminal;

/**
 * Slots whose token value alone lands under 4.5:1 on the terminal surface: the
 * three semantic roles and their bright variants, whose light-theme values are
 * pressed for a light page, plus the comment grey and the type mauve. The panel
 * covers them with xterm's `minimumContrastRatio`, so the legibility check runs
 * on the colour xterm ends up painting rather than on the raw token.
 */
const liftedByXterm = new Set([
  'magenta',
  'brightMagenta',
  'red',
  'green',
  'yellow',
  'brightRed',
  'brightGreen',
  'brightYellow',
  'brightBlack',
]);

/** `black` is the surface itself and `selectionBackground` is a low alpha tint,
 *  so neither is judged as body text. */
const notText = new Set(['background', 'cursorAccent', 'selectionBackground', 'black']);

describe('terminal palette', () => {
  it('drops a css variable instead of painting it, which is why the panel resolves tokens itself', () => {
    const withVariable = paint({ foreground: 'var(--color-syntax-operator)' });
    const withoutTheme = paint();

    // xterm could not read the variable, so the slot fell back to its default.
    expect(withVariable.foreground.css).not.toContain('var(');
    expect(withVariable.foreground.rgba).toBe(withoutTheme.foreground.rgba);

    // A resolved computed value is the format xterm does parse.
    const resolved = tokenValue('--color-syntax-operator')!;
    expect(paint({ foreground: resolved }).foreground.css).toBe(resolved);
  });

  it('maps every xterm slot to a token the theme block declares', () => {
    for (const [slot, token] of Object.entries(TERMINAL_THEME_TOKENS)) {
      expect(token.startsWith('--color-'), slot).toBe(true);
      for (const theme of ['dark', 'light'] as const) {
        expect(tokenValue(token, theme), `${slot} -> ${token} (${theme})`).toBeTruthy();
      }
    }
  });

  it('keeps every glyph slot legible on the terminal background in both themes', () => {
    for (const [slot, token] of Object.entries(TERMINAL_THEME_TOKENS)) {
      if (notText.has(slot)) continue;
      for (const theme of ['dark', 'light'] as const) {
        const background = tokenValue('--color-code-bg', theme)!;
        const ratio = contrastAfterLift(tokenValue(token, theme)!, background, 4.5);
        expect(ratio, `${slot} on ${theme}`).toBeGreaterThanOrEqual(4.5);
      }
    }
  });

  it('knows exactly which slots depend on the contrast lift', () => {
    const raw = (slot: string, theme: 'dark' | 'light') =>
      contrast(tokenValue(TERMINAL_THEME_TOKENS[slot as keyof typeof TERMINAL_THEME_TOKENS], theme)!, tokenValue('--color-code-bg', theme)!);

    const under = new Set(
      Object.keys(TERMINAL_THEME_TOKENS).filter(slot =>
        !notText.has(slot) && (['dark', 'light'] as const).some(theme => raw(slot, theme) < 4.5)),
    );
    expect(under).toEqual(liftedByXterm);
  });

  it('asks xterm to lift the slots that fall short of 4.5:1', () => {
    stubTokenLayer(tokenLayer('light'));
    render(<TerminalPanel readOnly />);
    expect(lastTerminal().options.minimumContrastRatio).toBe(4.5);
  });

  it('follows the code surface rather than the page surface', () => {
    const darkCode = tokenValue('--color-code-bg', 'dark')!;
    // On the dark page the code surface sits one step below the page.
    expect(luminance(darkCode)).toBeLessThanOrEqual(luminance(tokenValue('--color-bg-page', 'dark')!));

    // In the light theme the page turns light, while the terminal stays a dark
    // code surface, so the two cannot be the same colour.
    const lightCode = tokenValue('--color-code-bg', 'light')!;
    const lightPage = tokenValue('--color-bg-page', 'light')!;
    expect(luminance(lightCode)).toBeLessThan(0.05);
    expect(contrast(lightCode, lightPage)).toBeGreaterThan(3);
  });

  it('selects with a low opacity accent tint', () => {
    const alpha = Number(/rgba\([^,]+,[^,]+,[^,]+,\s*([\d.]+)\)/.exec(tokenValue('--color-accent-subtle')!)?.[1]);
    expect(alpha).toBeGreaterThan(0);
    expect(alpha).toBeLessThanOrEqual(0.2);
  });
});

describe('TerminalPanel', () => {
  it('hands xterm the resolved token values', () => {
    stubTokenLayer(tokenLayer('dark'));
    render(<TerminalPanel readOnly />);

    const theme = lastTerminal().options.theme!;
    for (const [slot, token] of Object.entries(TERMINAL_THEME_TOKENS)) {
      expect(theme[slot as keyof typeof theme], slot).toBe(tokenValue(token, 'dark'));
    }
  });

  it('re-reads the palette when the theme switches', async () => {
    const values = tokenLayer('dark');
    stubTokenLayer(values);
    render(<TerminalPanel readOnly />);
    expect(lastTerminal().options.theme!.background).toBe(tokenValue('--color-code-bg', 'dark'));

    values.clear();
    for (const [token, value] of tokenLayer('light')) values.set(token, value);
    document.documentElement.setAttribute('data-theme', 'light');

    await waitFor(() => {
      const theme = lastTerminal().options.theme!;
      expect(theme.background).toBe(tokenValue('--color-code-bg', 'light'));
      expect(theme.green).toBe(tokenValue('--color-success', 'light'));
    });
  });

  it('paints the code surface behind the terminal instead of a second hardcoded panel', () => {
    stubTokenLayer(tokenLayer('dark'));
    render(<TerminalPanel readOnly />);

    const section = screen.getByLabelText('沙箱终端');
    const surfaces = [...section.querySelectorAll('div')].filter(node => node.className.includes('bg-[var(--color-code-bg)]'));
    expect(surfaces).toHaveLength(1);
  });

  it('keeps the panel free of colour literals, so this file needs no governance exception', () => {
    const source = readFileSync(resolve(process.cwd(), 'src/components/terminal/TerminalPanel.tsx'), 'utf-8')
      .replace(/\/\/.*$/gm, '');

    expect(source).not.toMatch(/#[0-9a-fA-F]{3,8}\b/);
    expect(source).not.toMatch(/\brgba?\(/);
  });

  it('runs a command through the resolved palette without touching the token layer', async () => {
    stubTokenLayer(tokenLayer('dark'));
    const onCommand = vi.fn().mockResolvedValue('done');
    render(<TerminalPanel onCommand={onCommand} />);
    expect(screen.getByRole('status')).toHaveTextContent('等待命令');
    expect(onCommand).not.toHaveBeenCalled();
  });
});
