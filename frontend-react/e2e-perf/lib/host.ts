/**
 * Host + page-side metric sampling for the performance baseline.
 *
 * Every number this project reports must carry a `host` block (machine
 * capacity + load before/after the run) and a `raw` block (the untouched
 * sample arrays). A metric without both is an anecdote, not a baseline, so the
 * collectors below always return them as a pair.
 */
import { execFileSync } from 'node:child_process';
import os from 'node:os';
import fs from 'node:fs';

export interface HostSnapshot {
  /** Host CPU model, for reading numbers collected on different machines. */
  model: string;
  logicalCpus: number;
  /** Total RAM in bytes. */
  memTotalBytes: number;
  /** 1/5/15 minute load averages. */
  loadAverage: [number, number, number];
  /** Since-boot /proc/stat counters, kept raw so windowed utilisation can be derived. */
  cpuJiffies: { idle: number; iowait: number; total: number } | null;
  /**
   * Percent of all logical CPUs busy between the previous snapshot and this
   * one. Null on the first snapshot, where no previous counters exist.
   */
  cpuUtilizationPct: number | null;
  capturedAt: string;
}

/**
 * Raw jiffy counters from the aggregate /proc/stat line.
 *
 * Kept raw so a later reading can subtract this one, which is the only way to
 * get CPU use over a measurement window. Dividing by the since-boot total
 * would report the machine's whole history, not this run.
 */
function readCpuJiffies(): { idle: number; iowait: number; total: number } | null {
  try {
    const text = fs.readFileSync('/proc/stat', 'utf8');
    const line = text.split('\n').find((l) => l.startsWith('cpu '));
    if (!line) return null;
    const parts = line.trim().split(/\s+/).slice(1).map(Number);
    const idle = parts[3] ?? 0;
    const iowait = parts[4] ?? 0;
    const total = parts.reduce((acc, value) => acc + value, 0);
    return { idle, iowait, total };
  } catch {
    return null;
  }
}

/**
 * CPU utilisation across the measurement window, in percent of all logical
 * CPUs. Returns null when the counters did not advance, which happens on a
 * freshly booted host sampled too soon after the previous read.
 */
export function cpuUtilizationSincePct(previous: HostSnapshot | null | undefined): number | null {
  const now = readCpuJiffies();
  const then = previous?.cpuJiffies;
  if (!now || !then) return null;
  const totalDelta = now.total - then.total;
  if (totalDelta <= 0) return null;
  const idleDelta = now.idle - then.idle + (now.iowait - then.iowait);
  return Number((((totalDelta - idleDelta) / totalDelta) * 100).toFixed(2));
}

export function captureHost(): HostSnapshot {
  const cpus = os.cpus();
  return {
    model: cpus[0]?.model?.trim() ?? 'unknown',
    logicalCpus: cpus.length,
    memTotalBytes: os.totalmem(),
    loadAverage: [os.loadavg()[0], os.loadavg()[1], os.loadavg()[2]],
    cpuJiffies: readCpuJiffies(),
    cpuUtilizationPct: null,
    capturedAt: new Date().toISOString(),
  };
}

/** A host block pairing the run-start and run-end load with machine capacity. */
export function buildHostBlock(before: HostSnapshot, after: HostSnapshot) {
  return {
    before,
    after,
    logicalCpus: before.logicalCpus,
    cpuModel: before.model,
    memTotalBytes: before.memTotalBytes,
    memTotalGiB: Number((before.memTotalBytes / 1024 ** 3).toFixed(2)),
    loadAverageBefore: before.loadAverage,
    loadAverageAfter: after.loadAverage,
    loadAverage1mDelta: Number((after.loadAverage[0] - before.loadAverage[0]).toFixed(2)),
    /**
     * The headline figure: CPU busy across this run's own window, in percent of
     * all logical CPUs. High values mean the numbers below are contended.
     */
    cpuUtilizationPctOverRun: cpuUtilizationSincePct(before),
    /**
     * Kept for readers comparing against a since-boot average; it does not
     * describe the measurement window.
     */
    cpuUtilizationPctSinceBootMean:
      before.cpuJiffies && after.cpuJiffies
        ? Number((((after.cpuJiffies.total - after.cpuJiffies.idle - after.cpuJiffies.iowait) /
            after.cpuJiffies.total) * 100).toFixed(2))
        : null,
    cpuJiffiesRaw: { before: before.cpuJiffies, after: after.cpuJiffies },
    platform: `${os.platform()} ${os.release()} ${os.arch()}`,
  };
}

/** Chromium build under test; part of the environment a baseline is tied to. */
export function captureBrowserVersion(executablePath?: string): string {
  try {
    return execFileSync(executablePath ?? 'chromium', ['--version'], { encoding: 'utf8' }).trim();
  } catch {
    return 'unknown';
  }
}

/** Node runtime that drove the measurement. */
export function captureRuntime(): Record<string, string> {
  return {
    node: process.version,
    platform: `${os.platform()} ${os.arch()}`,
  };
}

/**
 * Statistical summary alongside the raw samples.
 *
 * `percentiles` uses the nearest-rank method so a reported p95 always names a
 * real measured sample rather than an interpolation between two.
 */
export function summarize(values: number[]) {
  if (values.length === 0) {
    return { count: 0, min: null, max: null, mean: null, p50: null, p95: null, p99: null, stdev: null };
  }
  const sorted = [...values].sort((a, b) => a - b);
  const rank = (p: number) => sorted[Math.min(sorted.length - 1, Math.max(0, Math.ceil((p / 100) * sorted.length) - 1))];
  const mean = values.reduce((a, b) => a + b, 0) / values.length;
  const variance = values.reduce((acc, v) => acc + (v - mean) ** 2, 0) / values.length;
  const round = (n: number | null) => (n === null ? null : Number(n.toFixed(2)));
  return {
    count: values.length,
    min: round(sorted[0] as number),
    max: round(sorted[sorted.length - 1] as number),
    mean: round(mean),
    p50: round(rank(50)),
    p95: round(rank(95)),
    p99: round(rank(99)),
    stdev: round(Math.sqrt(variance)),
  };
}
