/**
 * Numeric report.
 *
 * Assertions fail on their own; this writes down what was actually measured so
 * a later reader can tell "44px touch target" from "43.5px touch target", and
 * can see which combinations produced a readable surface versus a blank one.
 *
 * Output: `artifacts/ui-acceptance/visual-report.json` plus a Markdown digest.
 */

import { mkdirSync, readdirSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import type { Theme, ThemeProof } from './fixtures/theme';
import type { GeometryReport } from './fixtures/geometry';
import type { KnownDefectFinding } from './fixtures/defects';

export const ARTIFACT_ROOT = join(process.cwd(), 'artifacts', 'ui-acceptance');
export const REPORT_JSON = join(ARTIFACT_ROOT, 'visual-report.json');
export const REPORT_MD = join(ARTIFACT_ROOT, 'visual-report.md');
export const RECORDS_DIR = join(ARTIFACT_ROOT, 'records');

/**
 * One file per recorded combination.
 *
 * Playwright runs every worker in its own Node process, so a module-level array
 * only ever sees the combinations that worker happened to run. An earlier version
 * aggregated in memory and reported 2 of 230 results. Writing each combination to
 * its own file makes the report independent of worker count and of ordering.
 *
 * The title is slugged rather than used verbatim, because titles contain spaces,
 * parentheses, dots and slashes.
 */
function recordPath(title: string): string {
  const slug = title
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 120);
  return join(ARTIFACT_ROOT, 'records', `${slug}.json`);
}

export interface CombinationRecord {
  title: string;
  page: string;
  state: string | null;
  width: number;
  height: number;
  theme: Theme;
  themeProof: ThemeProof;
  geometry: GeometryReport;
  fixturesRequested: string[];
  fixturesUnfulfilled: string[];
  screenshot: string | null;
  pixelsCompared: boolean;
  status: 'passed' | 'failed';
  failure?: string;
  /** Ids of known product defects observed on this combination. */
  knownDefects?: string[];
}

interface Aggregator {
  /** Specs whose records should survive a `resetReport` in this process. */
  keepSpecs: string[];
}

let aggregator: Aggregator = { keepSpecs: [] };

/**
 * Drop this process's records for `spec`, leaving other specs and other workers'
 * records on disk untouched. Called at the start of a spec file so a re-run
 * replaces that spec's contribution instead of accumulating stale rows.
 */
export function resetReport(spec: string): void {
  aggregator = { keepSpecs: [spec] };
  let entries: string[] = [];
  try {
    entries = readdirSync(RECORDS_DIR);
  } catch {
    return; // first run: the directory does not exist yet
  }
  for (const name of entries) {
    if (!name.endsWith('.json')) continue;
    const full = join(RECORDS_DIR, name);
    try {
      const parsed = JSON.parse(readFileSync(full, 'utf8')) as { spec?: string };
      if (parsed.spec !== spec) continue;
    } catch {
      continue; // a partially written file from a killed run: let the next write replace it
    }
    rmSync(full, { force: true });
  }
}

function writeRecordFile(spec: string, entry: CombinationRecord): void {
  mkdirSync(RECORDS_DIR, { recursive: true });
  writeFileSync(recordPath(entry.title), JSON.stringify({ ...entry, spec }, null, 2) + '\n', 'utf8');
}

export function record(entry: Omit<CombinationRecord, 'status'>): void {
  writeRecordFile(aggregator.keepSpecs[0] ?? 'unknown', { ...entry, status: 'passed' });
}

/**
 * Record a known product defect. The combination still counts as covered: the
 * defect is a finding about the product, not a gap in the matrix, and it is
 * written into the report with its measurements so it cannot be lost.
 */
export function recordKnownDefect(finding: KnownDefectFinding): void {
  const spec = aggregator.keepSpecs[0] ?? 'unknown';
  const defects: KnownDefectFinding[] = [...readDefectsFor(finding.title), finding];
  mkdirSync(RECORDS_DIR, { recursive: true });
  writeFileSync(defectPath(finding.title), JSON.stringify(defects, null, 2) + '\n', 'utf8');

  // The record is written before the defect in the test, so it usually already
  // exists. Rewriting it here keeps the two in sync either way.
  const existing = readRecordFile(finding.title);
  if (existing) {
    writeRecordFile(spec, {
      ...existing,
      knownDefects: [...new Set([...(existing.knownDefects ?? []), finding.id])],
    });
  }
}

function defectPath(title: string): string {
  return recordPath(title).replace(/\.json$/, '.defects.json');
}

function readDefectsFor(title: string): KnownDefectFinding[] {
  try {
    return JSON.parse(readFileSync(defectPath(title), 'utf8')) as KnownDefectFinding[];
  } catch {
    return [];
  }
}

export function recordFailure(title: string, error: string): void {
  const spec = aggregator.keepSpecs[0] ?? 'unknown';
  const existing = readRecordFile(title);
  if (existing) {
    writeRecordFile(spec, { ...existing, status: 'failed', failure: error });
    return;
  }
  // A combination can fail before it ever produces a record, for example while
  // waiting for the route to render. Keep the failure visible with a stub row.
  writeFileSync(
    join(ARTIFACT_ROOT, 'records', `${titleSlug(title)}.failure.json`),
    JSON.stringify({ spec, title, status: 'failed', failure: error }, null, 2) + '\n',
    'utf8',
  );
}

function titleSlug(title: string): string {
  return title
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 120);
}

function readRecordFile(title: string): CombinationRecord | null {
  try {
    return JSON.parse(readFileSync(recordPath(title), 'utf8')) as CombinationRecord;
  } catch {
    return null;
  }
}

/** Read back every combination and defect written by any worker. */
function readAll(): {
  records: CombinationRecord[];
  failures: Array<{ title: string; error: string }>;
  defects: KnownDefectFinding[];
} {
  const records: CombinationRecord[] = [];
  const failures: Array<{ title: string; error: string }> = [];
  const defects: KnownDefectFinding[] = [];

  let entries: string[] = [];
  try {
    entries = readdirSync(RECORDS_DIR);
  } catch {
    return { records, failures, defects };
  }

  for (const name of entries) {
    if (!name.endsWith('.json')) continue;
    let parsed: unknown;
    try {
      parsed = JSON.parse(readFileSync(join(RECORDS_DIR, name), 'utf8'));
    } catch {
      continue;
    }
    if (Array.isArray(parsed)) {
      defects.push(...(parsed as KnownDefectFinding[]));
    } else if (parsed && typeof parsed === 'object') {
      const row = parsed as Partial<CombinationRecord> & { spec?: string };
      if (row.geometry && row.themeProof) records.push(row as CombinationRecord);
      else if (row.failure) failures.push({ title: row.title ?? name, error: String(row.failure) });
    }
  }

  records.sort((a, b) => a.title.localeCompare(b.title));
  return { records, failures, defects };
}

export function getRecords(): CombinationRecord[] {
  return readAll().records;
}

/**
 * Write the report to `artifacts/ui-acceptance/`.
 *
 * Called from `afterAll`, so it runs even when combinations failed — a failed
 * run is exactly when the measured numbers matter most.
 */
export function flushReport(meta: Record<string, unknown> = {}): void {
  const { records, failures, defects } = readAll();
  const recordedTitles = new Set(records.map(r => r.title));
  const onlyInFailures = failures.filter(f => !recordedTitles.has(f.title)).length;

  const overflowDeltas = records
    .map(r => r.geometry.overflow.delta)
    .filter(d => typeof d === 'number' && Number.isFinite(d));

  const summary = {
    generatedAt: new Date().toISOString(),
    total: records.length + onlyInFailures,
    passed: records.filter(r => r.status === 'passed').length,
    failed: failures.length,
    combosWithPixelBaseline: records.filter(r => r.screenshot !== null).length,
    maxHorizontalOverflowPx: max(overflowDeltas),
    maxHorizontalOverflowCombo: worstCombo(records, r => r.geometry.overflow.delta),
    themeVerifications: records.filter(r => r.themeProof.matchesExpected).length,
    blankSurfaceCombos: records.filter(r => r.fixturesRequested.length === 0).map(r => r.title),
    knownDefects: defects.length,
    knownDefectIds: [...new Set(defects.map(d => d.id))],
    ...meta,
  };

  const payload = { summary, records, failures, knownDefects: defects };
  mkdirSync(dirname(REPORT_JSON), { recursive: true });
  writeFileSync(REPORT_JSON, JSON.stringify(payload, null, 2) + '\n', 'utf8');
  writeFileSync(REPORT_MD, renderMarkdown(payload), 'utf8');
}

function max(values: number[]): number {
  return values.length === 0 ? 0 : Math.max(...values);
}

function worstCombo(
  records: CombinationRecord[],
  metric: (record: CombinationRecord) => number,
): string | null {
  if (records.length === 0) return null;
  const sorted = [...records].sort((a, b) => metric(b) - metric(a));
  const worst = sorted[0];
  return worst ? `${worst.title} (${metric(worst)})` : null;
}

function renderMarkdown(payload: {
  summary: Record<string, unknown>;
  records: CombinationRecord[];
  failures: Array<{ title: string; error: string }>;
  knownDefects: KnownDefectFinding[];
}): string {
  const { summary, records, failures } = payload;
  const lines: string[] = [];

  lines.push('# 双主题视觉回归实测报告');
  lines.push('');
  lines.push(`生成时间：${summary.generatedAt}`);
  lines.push('');
  lines.push('## 汇总');
  lines.push('');
  lines.push('| 指标 | 数值 |');
  lines.push('| --- | --- |');
  lines.push(`| 组合总数 | ${summary.total} |`);
  lines.push(`| 通过 | ${summary.passed} |`);
  lines.push(`| 失败 | ${summary.failed} |`);
  lines.push(`| 主题生效验证通过 | ${summary.themeVerifications} |`);
  lines.push(`| 最大水平溢出 | ${summary.maxHorizontalOverflowPx}px |`);
  lines.push(`| 溢出最严重组合 | ${summary.maxHorizontalOverflowCombo ?? 'n/a'} |`);
  lines.push(`| 已生成像素基线 | ${summary.combosWithPixelBaseline} |`);
  lines.push(`| 夹具未被消费（空页面风险） | ${(summary.blankSurfaceCombos as string[]).length} |`);
  lines.push(`| 已知产品缺陷 | ${summary.knownDefects ?? 0} |`);
  lines.push('');

  const defects = payload.knownDefects ?? [];
  if (defects.length > 0) {
    lines.push('## 已知产品缺陷（已记录，未修改产品代码）');
    lines.push('');
    for (const defect of defects) {
      lines.push(`### ${defect.id}`);
      lines.push('');
      lines.push(defect.symptom);
      lines.push('');
      lines.push(`- 缺陷位置：\`${defect.source}\``);
      lines.push(`- 复现：\`/#${defect.scope.page}\`，视口 \`${defect.width}x${defect.height}\`，主题 \`${defect.theme}\``);
      lines.push(
        `- 实测：\`${defect.evidence.targetName}\` 中心 (${defect.evidence.centerX},${defect.evidence.centerY}) 被 \`${defect.evidence.topmost}\` 覆盖`,
      );
      lines.push('');
    }
  }

  const widths = [...new Set(records.map(r => r.width))].sort((a, b) => b - a);
  const themes = [...new Set(records.map(r => r.theme))];

  lines.push('## 覆盖矩阵');
  lines.push('');
  lines.push('| 宽度 | ' + themes.map(t => `${t} 通过/总数`).join(' | ') + ' |');
  lines.push('| --- | ' + themes.map(() => '---').join(' | ') + ' |');
  for (const width of widths) {
    const cells = themes.map(theme => {
      const scoped = records.filter(r => r.width === width && r.theme === theme);
      const ok = scoped.filter(r => r.status === 'passed').length;
      return `${ok}/${scoped.length}`;
    });
    lines.push(`| ${width} | ${cells.join(' | ')} |`);
  }
  lines.push('');

  lines.push('## 主题实测值');
  lines.push('');
  lines.push('| 组合 | data-theme | 存储值 | --color-bg-page | 前景色 | 生效 |');
  lines.push('| --- | --- | --- | --- | --- | --- |');
  for (const record of records.slice(0, 400)) {
    const p = record.themeProof;
    lines.push(
      `| ${record.title} | ${p.attribute ?? 'null'} | ${p.stored ?? 'null'} | ${p.pageBackground} | ${p.textColor} | ${p.matchesExpected ? 'yes' : 'NO'} |`,
    );
  }
  lines.push('');

  lines.push('## 逐组合结构测量');
  lines.push('');
  lines.push('| 组合 | scrollWidth | clientWidth | 溢出 | 越界元素 | aria-current | 命中测试 |');
  lines.push('| --- | --- | --- | --- | --- | --- | --- |');
  for (const record of records) {
    const o = record.geometry.overflow;
    const hits = record.geometry.hitTests.map(h => `${h.selector}:${h.reachable ? 'ok' : 'BLOCKED'}`).join(' ');
    lines.push(
      `| ${record.title} | ${o.scrollWidth} | ${o.clientWidth} | ${o.delta} | ${o.offenders.length} | ${record.geometry.ariaCurrentCount} | ${hits || 'n/a'} |`,
    );
  }
  lines.push('');

  if (failures.length > 0) {
    lines.push('## 失败明细');
    lines.push('');
    for (const failure of failures) {
      lines.push(`### ${failure.title}`);
      lines.push('');
      lines.push('```');
      lines.push(failure.error);
      lines.push('```');
      lines.push('');
    }
  }

  return lines.join('\n');
}
