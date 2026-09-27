import { mkdirSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import { expect, test } from '@playwright/test';
import { formatViolations, isBlocking, runAxe, wcagTags, type AxeScan } from './axe';
import { ROUTES, THEMES, VIEWPORTS, describeUnscannable, openRoute } from './a11y-matrix';

function summarise(scans: AxeScan[]): string[] {
  const byRule = new Map<string, { count: number; impacts: Set<string>; tags: Set<string>; targets: Set<string> }>();
  for (const scan of scans) {
    for (const violation of scan.violations) {
      const entry = byRule.get(violation.id) ?? { count: 0, impacts: new Set(), tags: new Set(), targets: new Set() };
      entry.count += violation.nodes.length;
      entry.impacts.add(violation.impact ?? 'unknown');
      for (const tag of wcagTags(violation)) entry.tags.add(tag);
      for (const node of violation.nodes) entry.targets.add(node.target.join(' '));
      byRule.set(violation.id, entry);
    }
  }
  return [...byRule.entries()]
    .sort((a, b) => b[1].count - a[1].count)
    .map(([id, entry]) => {
      const tags = [...entry.tags].join(', ') || 'best-practice';
      const targets = [...entry.targets].slice(0, 6).join('\n        ');
      return `  ${id} x${entry.count} impact=${[...entry.impacts].join('/')} wcag=${tags}\n        ${targets}`;
    });
}

/**
 * Report-only sweep. Writes every finding to `artifacts/a11y/a11y-report.json`
 * and prints a grouped summary. It never fails, so it can be run at any time to
 * produce a real violation list for the current tree.
 *
 * The report lives under `artifacts/` rather than `test-results/`, which
 * Playwright clears on every run: a report that only lives until the next
 * invocation is not something anyone can diff against.
 */
test.describe('axe audit report', () => {
  test('full route x theme x viewport sweep', async ({ page }, testInfo) => {
    test.setTimeout(15 * 60_000);
    const scans: AxeScan[] = [];
    const unstable: string[] = [];

    for (const theme of THEMES) {
      for (const viewport of VIEWPORTS) {
        for (const route of ROUTES) {
          const cause = await openRoute(page, route, theme, viewport.width);
          if (cause) unstable.push(`#${route} [${theme}/${viewport.width}px]: ${describeUnscannable(cause)}`);
          const violations = await runAxe(page);
          scans.push({ route, theme, width: viewport.width, violations });
        }
      }
    }

    const reportDir = path.join(process.cwd(), 'artifacts', 'a11y');
    mkdirSync(reportDir, { recursive: true });
    const file = path.join(reportDir, 'a11y-report.json');
    writeFileSync(file, JSON.stringify(scans, null, 2), 'utf8');
    const finalReport = path.join(reportDir, 'final-a11y.md');
    const blockingFindings = scans.flatMap(scan => scan.violations.filter(isBlocking).map(violation =>
      `- ${scan.route} / ${scan.theme} / ${scan.width}px: ${violation.id} (${violation.impact ?? 'unknown'})\n  - ${violation.nodes.map(node => node.target.join(' ')).join('\n  - ')}`,
    ));
    const markdown = [
      '# Final Accessibility Audit',
      '',
      `- Scans: ${scans.length}`,
      `- Routes: ${ROUTES.length}`,
      '- Themes: light, dark',
      '- Viewports: 1440px, 390px',
      `- Total violation nodes: ${totalViolationNodes(scans)}`,
      `- Blocking violations: ${blockingFindings.length}`,
      '',
      '## Blocking Findings',
      '',
      ...(blockingFindings.length > 0 ? blockingFindings : ['No serious or critical violations detected.']),
      '',
      '## Rule Summary',
      '',
      ...(summarise(scans).length > 0 ? summarise(scans) : ['No violations detected.']),
      '',
      'Raw data: `a11y-report.json`',
      '',
    ].join('\n');
    writeFileSync(finalReport, markdown, 'utf8');
    await testInfo.attach('a11y-report.json', { body: JSON.stringify(scans, null, 2), contentType: 'application/json' });

    const total = totalViolationNodes(scans);
    const blocking = scans.flatMap(s => s.violations.filter(isBlocking).map(v => `${s.route}/${s.theme}/${s.width} ${v.id}`));

    // eslint-disable-next-line no-console
    console.log(`\n=== axe audit: ${scans.length} scans, ${total} nodes, ${blocking.length} blocking ===\n`);
    // eslint-disable-next-line no-console
    console.log(summarise(scans).join('\n'));
    for (const scan of scans) {
      if (scan.violations.length === 0) continue;
      // eslint-disable-next-line no-console
      console.log(`\n--- #${scan.route} ${scan.theme} ${scan.width} ---`);
      // eslint-disable-next-line no-console
      console.log(formatViolations(scan.violations).join('\n'));
    }
    // eslint-disable-next-line no-console
    console.log(`\nreport written to ${file}`);
    if (unstable.length > 0) {
      // Silently scanning a half-themed page is how a real audit turns into a
      // list of findings nobody can reproduce.
      // eslint-disable-next-line no-console
      console.log(`\n!! ${unstable.length} scan(s) were not in a settled state: ${unstable.join(', ')}`);
    }

    // The report stays report-only, but an unscannable page means its numbers
    // are fiction, so the matrix still has to have been fully covered.
    expect(scans.length).toBe(ROUTES.length * THEMES.length * VIEWPORTS.length);
    expect(unstable, `these scans ran against an overlay or an unsettled theme:\n${unstable.join('\n')}`).toEqual([]);
  });
});

function totalViolationNodes(scans: AxeScan[]): number {
  return scans.reduce((sum, scan) => sum + scan.violations.reduce((count, violation) => count + violation.nodes.length, 0), 0);
}
