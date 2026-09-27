/**
 * Duration rendering shared by every surface that shows an elapsed time.
 *
 * One function, one explicit unit: the backend reports elapsed time in
 * milliseconds almost everywhere, while the factory run timer counts seconds,
 * and a mm:ss clock only makes sense for the latter. The unit is a required
 * argument so a caller cannot silently render a value scaled by 1000.
 */

/** Milliseconds: `820ms` below a second, `1.4s` above it. */
export type DurationUnit = 'ms' | 'seconds';

/** Rendered whenever the source value is absent, negative or not a number. */
export const DURATION_FALLBACK = '-';

const pad2 = (value: number) => String(value).padStart(2, '0');

/**
 * @param value  Elapsed time, in `unit`.
 * @param unit   Unit `value` is expressed in.
 * @param fallback Text for values that were not reported.
 */
export function formatDuration(
  value: number | null | undefined,
  unit: DurationUnit,
  fallback: string = DURATION_FALLBACK,
): string {
  const n = Number(value);
  if (!Number.isFinite(n) || n < 0) return fallback;

  if (unit === 'seconds') {
    const total = Math.floor(n);
    return `${pad2(Math.floor(total / 60))}:${pad2(total % 60)}`;
  }
  if (n < 1000) return `${Math.round(n)}ms`;
  return `${(n / 1000).toFixed(1)}s`;
}
