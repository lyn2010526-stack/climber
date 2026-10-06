export type ScrollProgressVariant = 'bar' | 'segments';

const clamp01 = (value: number): number => Math.min(1, Math.max(0, value));

export function measureScrollProgress(container: HTMLElement | Window): number {
  const isWindow = container === window;
  const scrollTop = isWindow ? window.scrollY : (container as HTMLElement).scrollTop;
  const scrollHeight = isWindow ? document.documentElement.scrollHeight : (container as HTMLElement).scrollHeight;
  const clientHeight = isWindow ? document.documentElement.clientHeight : (container as HTMLElement).clientHeight;
  const max = scrollHeight - clientHeight;
  if (!(max > 0)) return 0;
  return clamp01(scrollTop / max);
}

export function resolveScrollSegment(progress: number, segments: number): number {
  const count = Math.max(1, Math.floor(segments));
  return Math.min(count - 1, Math.floor(clamp01(progress) * count));
}
