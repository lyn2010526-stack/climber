/**
 * The single place that records where each colour came from.
 *
 * The tokens themselves live in `src/index.css` — this file carries no values,
 * only the provenance, so a future change to a hex can be traced back to the
 * benchmark that justified it. See
 * `.monkeycode/specs/2026-09-26-parity-codex-deepseek-opencode/benchmark.md`.
 */

export type ParitySource = 'codex' | 'opencode' | 'deepseek' | 'derived';

export interface TokenProvenance {
  token: string;
  value: string;
  source: ParitySource;
  role: string;
}

/** Codex CLI, measured from its actual terminal interface. */
const codex: Record<string, string> = {
  '--color-bg-page': '#20222E',
  '--color-bg-surface-1': '#262938',
  '--color-bg-surface-2': '#2A2D3E',
  '--color-bg-surface-3': '#31354A',
  '--color-bg-surface-4': '#3A3F57',
  '--color-text-primary': '#E9EBF0',
  '--color-text-secondary': '#C9CCD6',
  '--color-text-muted': '#8A8FA3',
  '--color-text-disabled': '#6C7182',
  '--color-accent': '#5BC8D8',
  '--color-success': '#7EC97E',
  '--color-warning': '#D9B26A',
  '--color-error': '#E07A72',
  '--color-info': '#8FB8E8',
  '--color-border-default': '#34374A',
  '--color-syntax-keyword': '#7EC97E',
  '--color-syntax-function': '#5BC8D8',
  '--color-syntax-string': '#8FB8E8',
  '--color-syntax-number': '#82A8E0',
  '--color-diff-added': '#7EC97E',
  '--color-diff-removed': '#E07A72',
  '--color-diff-hunk': '#5BC8D8',
};

/** OpenCode's published theme schema, whose role names Climber reuses. */
const opencode: Record<string, string> = {
  '--color-syntax-type': '#B48EAD',
  '--color-syntax-comment': '#6C7182',
  '--color-syntax-operator': '#C9CCD6',
  '--color-border-strong': '#4A4F66',
};

/** Light-theme surfaces: a single white canvas, Codex style. */
const lightSurfaces: Record<string, string> = {
  '--color-bg-page': '#FFFFFF',
  '--color-bg-surface-1': '#FFFFFF',
  '--color-bg-surface-2': '#F6F7F9',
  '--color-bg-surface-3': '#EEF0F4',
  '--color-bg-surface-4': '#E4E8EF',
  '--color-text-primary': '#2E3440',
  '--color-text-secondary': '#3B4252',
  '--color-text-muted': '#4C566A',
};

const roleOf: Record<string, string> = {
  '--color-bg-page': 'background',
  '--color-bg-surface-1': 'backgroundPanel',
  '--color-bg-surface-2': 'backgroundElement',
  '--color-bg-surface-3': 'backgroundElementHover',
  '--color-bg-surface-4': 'backgroundElementPressed',
  '--color-text-primary': 'text',
  '--color-text-secondary': 'textSecondary',
  '--color-text-muted': 'textMuted',
  '--color-text-disabled': 'textDisabled',
  '--color-accent': 'primary',
  '--color-accent-hover': 'primaryHover',
  '--color-accent-active': 'primaryActive',
  '--color-accent-foreground': 'accent',
  '--color-success': 'success',
  '--color-warning': 'warning',
  '--color-error': 'error',
  '--color-info': 'info',
  '--color-unknown': 'unknown',
  '--color-border-subtle': 'borderSubtle',
  '--color-border-default': 'border',
  '--color-border-strong': 'borderStrong',
  '--color-border-accent': 'borderActive',
  '--color-syntax-comment': 'syntaxComment',
  '--color-syntax-keyword': 'syntaxKeyword',
  '--color-syntax-function': 'syntaxFunction',
  '--color-syntax-string': 'syntaxString',
  '--color-syntax-number': 'syntaxNumber',
  '--color-syntax-type': 'syntaxType',
  '--color-syntax-operator': 'syntaxOperator',
  '--color-diff-added': 'diffAdded',
  '--color-diff-removed': 'diffRemoved',
  '--color-diff-hunk': 'diffHunkHeader',
};

export const darkTokenProvenance: TokenProvenance[] = Object.entries({
  ...codex,
  ...opencode,
}).map(([token, value]) => ({
  token,
  value,
  source: token in codex ? ('codex' as const) : ('opencode' as const),
  role: roleOf[token] ?? 'unclassified',
}));

export const lightTokenProvenance: TokenProvenance[] = Object.entries(lightSurfaces).map(
  ([token, value]) => ({
    token,
    value,
    source: 'opencode' as const,
    role: roleOf[token] ?? 'unclassified',
  }),
);

export const tokenProvenance = [...darkTokenProvenance, ...lightTokenProvenance];

/**
 * DeepSeek exposes a partial-override contract (`DEEPSEEKCODE_THEME_COLORS`)
 * rather than a fixed palette worth copying. Climber already matches that
 * mechanism: one token source, a light-theme override block, and a three-state
 * accent. Recorded here so the decision is traceable instead of implicit.
 */
export const deepseekContract = {
  partialOverride: 'DEEPSEEKCODE_THEME_COLORS',
  selectableThemes: ['dark', 'light', 'nord', 'dracula', 'monokai', 'one-dark', 'tokyo-night'],
  climberEquivalent: 'src/index.css @theme + [data-theme="light"] + --color-accent-{hover,active,subtle}',
} as const;
