import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

// The chrome contract lives in the shared stylesheet, so it is read from disk
// the same way the navigation reserve contract reads it.
const css = readFileSync(resolve(process.cwd(), 'src/index.css'), 'utf-8');

describe('mobile chrome touch and focus contract', () => {
  it('keeps a global focus-visible ring for keyboard users', () => {
    const rule = /(^|\n):focus-visible\s*\{([^}]*)\}/.exec(css);
    expect(rule).toBeTruthy();
    expect(rule![2]).toContain('outline: 2px solid var(--color-accent-foreground)');
  });

  it('gives the header icon action a 44px touch floor', () => {
    const block = /\.mobile-icon-button\s*\{([^}]*)\}/.exec(css);
    expect(block).toBeTruthy();
    expect(block![1]).toMatch(/min-height:\s*44px/);
    expect(block![1]).toMatch(/min-width:\s*44px/);
  });

  it('gives every mobile page the shared safe-area paddings', () => {
    const top = /\.safe-area-top\s*\{([^}]*)\}/.exec(css);
    const bottom = /\.safe-area-bottom\s*\{([^}]*)\}/.exec(css);
    expect(top![1]).toMatch(/env\(safe-area-inset-top, 0px\)/);
    expect(bottom![1]).toMatch(/env\(safe-area-inset-bottom, 0px\)/);
  });
});
