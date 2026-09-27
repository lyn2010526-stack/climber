/**
 * Guard against matrix drift.
 *
 * `navConfig.ts` is the source of truth for routes. When a page is added there
 * and not in `e2e/visual/matrix.ts`, the visual matrix silently stops covering
 * it — the failure mode where a new page ships with no baseline at all. This
 * script fails loudly instead.
 *
 * Run: node scripts/verify-visual-matrix.mjs
 */

import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.join(HERE, '..');
const NAV_CONFIG = path.join(ROOT, 'src', 'navigation', 'navConfig.ts');
const MATRIX = path.join(ROOT, 'e2e', 'visual', 'matrix.ts');

const navSource = readFileSync(NAV_CONFIG, 'utf8');
const matrixSource = readFileSync(MATRIX, 'utf8');

// The `Page` union is the contract: every id the app can route to.
const unionMatch = navSource.match(/export type Page\s*=\s*([\s\S]*?);/);
if (!unionMatch) {
  console.error('FAIL: could not find the `Page` union in src/navigation/navConfig.ts');
  process.exit(1);
}
const navIds = [...unionMatch[1].matchAll(/'([a-z-]+)'/g)].map(m => m[1]);

const listedMatch = matrixSource.match(/REQUIRED_PAGES\s*=\s*\[([\s\S]*?)\] as const/);
if (!listedMatch) {
  console.error('FAIL: could not find REQUIRED_PAGES in e2e/visual/matrix.ts');
  process.exit(1);
}
const covered = new Set([...listedMatch[1].matchAll(/'([a-z-]+)'/g)].map(m => m[1]));

// Excluded on purpose, with the reason recorded next to the exclusion so the
// gap is a decision rather than an oversight.
const EXCLUDED = new Map([
  ['crews', 'renders ClusterPage; cluster is covered'],
  ['plugin-manage', 'secondary editor surface of the same plugins data'],
  ['stats', 'analytics dashboard, not part of the required page list'],
  ['task-history', 'read-only archive of the tasks data'],
  ['reasoning-history', 'read-only archive of the reasoning data'],
  ['terminal', 'xterm canvas surface, not a layout-comparable page'],
]);

const missing = navIds.filter(id => !covered.has(id) && !EXCLUDED.has(id));
const unknown = [...covered].filter(id => !navIds.includes(id));

if (unknown.length > 0) {
  console.error(`FAIL: matrix lists ids that no longer exist in navConfig: ${unknown.join(', ')}`);
  process.exit(1);
}

if (missing.length > 0) {
  console.error(`FAIL: navConfig has pages with no visual matrix entry: ${missing.join(', ')}`);
  console.error('      Add them to REQUIRED_PAGES in e2e/visual/matrix.ts, or record an EXCLUDED reason.');
  process.exit(1);
}

console.log(`OK: ${covered.size} pages covered, ${EXCLUDED.size} explicitly excluded.`);
