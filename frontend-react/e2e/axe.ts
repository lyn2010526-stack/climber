import { createRequire } from 'node:module';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
import type { Page } from '@playwright/test';

const require = createRequire(import.meta.url);
void require;

const AXE_PATH = path.join(path.dirname(fileURLToPath(import.meta.url)), '..', 'node_modules', 'axe-core', 'axe.min.js');

/** How long to wait after a dev-server reload before scanning again. */
const SETTLE_AFTER_RELOAD_MS = 900;

let cached: string | null = null;

/** axe-core source, read once and injected into every page under test. */
export function axeSource(): string {
  if (cached === null) cached = readFileSync(AXE_PATH, 'utf8');
  return cached;
}

export type AxeImpact = 'minor' | 'moderate' | 'serious' | 'critical';

export interface AxeViolationNode {
  target: string[];
  html: string;
  failureSummary: string;
}

export interface AxeViolation {
  id: string;
  impact: AxeImpact | null;
  tags: string[];
  help: string;
  helpUrl: string;
  nodes: AxeViolationNode[];
}

export interface AxeScan {
  route: string;
  theme: 'light' | 'dark';
  width: number;
  violations: AxeViolation[];
}

const IMPACT_ORDER: Record<AxeImpact, number> = { critical: 0, serious: 1, moderate: 2, minor: 3 };

export function impactRank(impact: AxeImpact | null): number {
  return IMPACT_ORDER[impact ?? 'minor'];
}

/** WCAG success-criterion tags only, so a rule maps to the criterion it fails. */
export function wcagTags(violation: AxeViolation): string[] {
  return violation.tags.filter(tag => /^wcag\d+/.test(tag));
}

export function isBlocking(violation: AxeViolation): boolean {
  return impactRank(violation.impact) <= IMPACT_ORDER.serious;
}

/** Stable ordering: severity, then rule id, then first node selector. */
export function sortViolations(violations: AxeViolation[]): AxeViolation[] {
  return [...violations].sort((a, b) => {
    const byImpact = impactRank(a.impact) - impactRank(b.impact);
    if (byImpact !== 0) return byImpact;
    if (a.id !== b.id) return a.id.localeCompare(b.id);
    return (a.nodes[0]?.target[0] ?? '').localeCompare(b.nodes[0]?.target[0] ?? '');
  });
}

/** Rule ids this axe-core build actually knows. */
export function knownRuleIds(): string[] {
  const require = createRequire(import.meta.url);
  return require('axe-core').getRules().map((rule: { ruleId: string }) => rule.ruleId);
}

/**
 * A rule id that does not exist makes `axe.run` throw rather than report, which
 * turns a typo into a confusing in-page error instead of a clear failure here.
 */
export function assertKnownRules(ids: readonly string[]): void {
  const known = new Set(knownRuleIds());
  const unknown = [...new Set(ids)].filter(id => !known.has(id));
  if (unknown.length > 0) {
    throw new Error(`axe-core ${require('axe-core/package.json').version} has no rule(s): ${unknown.join(', ')}`);
  }
}

export interface RunAxeOptions {
  /** Restrict the scan to a subtree; defaults to the whole document. */
  include?: string[];
  disableRules?: string[];
  enableRules?: string[];
  context?: unknown;
}

/** A dev-server reload can tear down the context between the wait and the run. */
function isLostContext(error: unknown): boolean {
  const message = error instanceof Error ? error.message : String(error);
  return /Execution context was destroyed|Target closed|navigation/i.test(message);
}

/**
 * Injects axe-core and returns the violation objects for the current DOM.
 * Colour contrast and target size are enabled explicitly because both are
 * best-practice-tagged rather than WCAG-tagged, and both were hand-fixed.
 */
export async function runAxe(page: Page, options: RunAxeOptions = {}): Promise<AxeViolation[]> {
  // Validated on this side of the boundary, where a bad id is a test bug with a
  // readable message rather than an in-page exception.
  assertKnownRules([...(options.enableRules ?? []), ...(options.disableRules ?? [])]);

  for (let attempt = 0; ; attempt += 1) {
    try {
      // The tag is a no-op when axe is already there. Injecting blind throws
      // away the rest of the run, and a hash change during a lazy route load is
      // enough to lose the race.
      await page.addScriptTag({ content: axeSource() }).catch(() => {});
      const violations = await page.evaluate(async opts => {
        const axe = (window as unknown as { axe: { run: (ctx: unknown, o: unknown) => Promise<{ violations: AxeViolation[] }> } }).axe;
        const rules: Record<string, { enabled: boolean }> = {
          'color-contrast': { enabled: true },
          'target-size': { enabled: true },
        };
        for (const id of opts.enableRules ?? []) rules[id] = { enabled: true };
        for (const id of opts.disableRules ?? []) rules[id] = { enabled: false };
        const result = await axe.run(opts.context ?? (opts.include ? { include: opts.include, exclude: [] } : document), { rules });
        return result.violations;
      }, options as RunAxeOptions);
      return sortViolations(violations);
    } catch (error) {
      // A vite reload during the scan is a dev-server artefact, not a finding.
      // One retry rides it out; a second failure is a real error worth showing.
      if (attempt >= 2 || !isLostContext(error)) throw error;
      await page.waitForLoadState('domcontentloaded');
      await page.waitForTimeout(SETTLE_AFTER_RELOAD_MS);
    }
  }
}

/** One line per offending node, for human-readable reports. */
export function formatViolations(violations: AxeViolation[]): string[] {
  return violations.flatMap(violation =>
    violation.nodes.map(node => {
      const tags = wcagTags(violation).join(', ') || 'best-practice';
      const summary = node.failureSummary?.replace(/\s+/g, ' ').trim() ?? '';
      return `[${violation.impact ?? 'unknown'}] ${violation.id} <${tags}> ${node.target.join(' ')} :: ${summary}`;
    }),
  );
}
