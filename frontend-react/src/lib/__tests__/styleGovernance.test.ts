import { describe, it, expect } from 'vitest';
import { readFileSync, readdirSync, statSync } from 'node:fs';
import { join, relative, resolve } from 'node:path';

const root = resolve(process.cwd(), 'src');
const css = readFileSync(resolve(root, 'index.css'), 'utf-8');

const TOKEN_SOURCE = 'src/index.css';
// workbench.css carries a second sanctioned token layer: the Codex-parity
// `.workbench-theme` scope, the same block
// components/workspace/__tests__/anchored-spec-conformance.test.tsx requires to
// define its own colour tokens in. Only those declarations are tokens; the rest
// of the file is styling and stays governed, so the block is lifted out of the
// source instead of exempting the whole stylesheet.
const WORKBENCH_TOKENS = 'src/styles/workbench.css';
// Matches every `.workbench-theme` scope block: the plain scope, the light-theme
// overrides, and the layout-qualified desktop and three-column palettes. The
// qualifier class stops the match at `button:focus-visible` style rules, which
// are styling rather than tokens.
const WORKBENCH_TOKEN_BLOCK =
  /^[ \t]*(?:\[data-theme="light"\][ \t]*)?\.workbench-theme[\w.="\-[\]]*\s*\{[^}]*\}[^\n]*\n?/gm;
const TEST_FILE = /(?:^|[\\/])(?:__tests__[\\/])|\.(?:test|spec)\.[a-z0-9]+$/i;

// Documented exceptions from the style-governance rules. Each one names its
// reason, and `it('keeps every exception a real file')` fails if one goes away.
const DOCUMENTED_EXCEPTIONS: Record<string, string> = {
  'src/styles/rtl.css': 'only holds var() fallback values for the token layer',
  // The token source and its provenance record are the two places a hex is
  // allowed to exist. Both are checked against index.css by designTokens.test.ts.
  'src/lib/parityPalette.ts': 'records which benchmark each hex came from; holds no styling',
};

const TAILWIND_PALETTE =
  /\b(?:bg|text|border|ring|shadow|fill|stroke|outline|divide|from|via|to|accent|caret|decoration|placeholder)-(?:red|orange|amber|yellow|lime|green|emerald|teal|cyan|sky|blue|indigo|violet|purple|fuchsia|pink|rose|slate|gray|zinc|neutral|stone)-\d{2,3}\b/;
const HEX_LITERAL = /#(?:[0-9a-fA-F]{3,4}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})\b/;
const RGB_LITERAL = /\brgba?\((?![^)]*var\()/;
const SECOND_NAMESPACE = /^\s*(--(?!color-|text-|space-|radius-|shadow-|font-|ease-|duration-|z-|icon-|focus-|border-|surface-)[a-z0-9-]+)\s*:/gm;

const sourceFiles: string[] = [];
(function walk(dir: string) {
  for (const entry of readdirSync(dir)) {
    const full = join(dir, entry);
    if (statSync(full).isDirectory()) walk(full);
    else if (/\.(?:tsx?|css)$/.test(entry)) sourceFiles.push(full);
  }
})(root);

const toPosix = (file: string) => relative(process.cwd(), file).split('\\').join('/');

/** Source files that must consume tokens: everything except the token source itself,
 *  tests, and the documented third-party exceptions. */
const governedFiles = sourceFiles
  .map(toPosix)
  .filter(file => !file.endsWith(TOKEN_SOURCE))
  .filter(file => !TEST_FILE.test(file))
  .filter(file => !DOCUMENTED_EXCEPTIONS[file]);

/** The styling of a governed file, with any token-definition block blanked out.
 *  Newlines survive so a reported line number still points at the source. */
function governedSource(file: string): string {
  const source = readFileSync(resolve(process.cwd(), file), 'utf-8');
  return file === WORKBENCH_TOKENS
    ? source.replace(WORKBENCH_TOKEN_BLOCK, block => block.replace(/[^\n]/g, ''))
    : source;
}

const readLines = (file: string) => governedSource(file).split('\n');

const stripComment = (line: string) => line.replace(/\/\/.*$/, '');

const tokenBlocks = [
  css,
  readFileSync(resolve(process.cwd(), WORKBENCH_TOKENS), 'utf-8').match(WORKBENCH_TOKEN_BLOCK)?.join('') ?? '',
];

const declaredTokens = new Set(
  tokenBlocks.flatMap(block => [...block.matchAll(/(--[a-z0-9-]+)\s*:/g)].map(match => match[1]!)),
);

// A component may also declare a custom property in its own scope through a
// Tailwind arbitrary property (`[--fade-width:20px]`). That is a local
// declaration, not a missing token.
for (const file of governedFiles) {
  const source = readFileSync(resolve(process.cwd(), file), 'utf-8');
  for (const match of source.matchAll(/\[(--[a-z0-9-]+)\s*:/g)) declaredTokens.add(match[1]!);
}

describe('style governance', () => {
  it('keeps every exception a real file, so a stale whitelist entry gets noticed', () => {
    for (const file of Object.keys(DOCUMENTED_EXCEPTIONS)) {
      expect(() => readFileSync(resolve(process.cwd(), file), 'utf-8'), file).not.toThrow();
      expect(DOCUMENTED_EXCEPTIONS[file]!.length, file).toBeGreaterThan(10);
    }
  });

  it('keeps the governance scope non-empty so the gate cannot pass by scanning nothing', () => {
    expect(governedFiles.length).toBeGreaterThan(50);
  });

  it('never references a token that the theme block does not declare', () => {
    const dead: string[] = [];
    for (const file of governedFiles) {
      readLines(file).forEach((line, index) => {
        for (const match of stripComment(line).matchAll(/var\((--[a-z0-9-]+)\)/g)) {
          if (!declaredTokens.has(match[1]!)) dead.push(`${file}:${index + 1} ${match[1]}`);
        }
      });
    }
    expect(dead).toEqual([]);
  });

  it('rejects Tailwind palette utilities, which bypass the token layer entirely', () => {
    const hits: string[] = [];
    for (const file of governedFiles) {
      if (!file.endsWith('.tsx') && !file.endsWith('.ts')) continue;
      readLines(file).forEach((line, index) => {
        if (TAILWIND_PALETTE.test(stripComment(line))) hits.push(`${file}:${index + 1}`);
      });
    }
    expect(hits).toEqual([]);
  });

  it('rejects hex and rgb colour literals in components and pages', () => {
    const hits: string[] = [];
    for (const file of governedFiles) {
      readLines(file).forEach((line, index) => {
        const code = stripComment(line);
        if (HEX_LITERAL.test(code) || RGB_LITERAL.test(code)) hits.push(`${file}:${index + 1}`);
      });
    }
    expect(hits).toEqual([]);
  });

  it('confines new CSS variables to the declared token namespaces', () => {
    const hits: string[] = [];
    for (const file of governedFiles) {
      if (!file.endsWith('.css')) continue;
      for (const match of governedSource(file).matchAll(SECOND_NAMESPACE)) hits.push(`${file} ${match[1]}`);
    }
    expect(hits).toEqual([]);
  });
});
