import { act, fireEvent, render, screen } from '@testing-library/react';
import { useRef } from 'react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { measureScrollProgress, resolveScrollSegment } from './scrollProgressMath';
import { ScrollProgress } from './ScrollProgress';

const rafFlush = () => new Promise<void>((resolve) => requestAnimationFrame(() => resolve()));

interface ProgressHarnessProps {
  variant?: 'bar' | 'segments';
  segments?: number;
  attachContainer?: boolean;
  ariaLabel?: string;
}

function ProgressHarness({ variant, segments, attachContainer = true, ariaLabel = '阅读进度' }: ProgressHarnessProps) {
  const ref = useRef<HTMLDivElement | null>(null);
  return (
    <div>
      <div ref={attachContainer ? ref : undefined} data-testid="scroller">
        <p>content</p>
      </div>
      <ScrollProgress containerRef={attachContainer ? ref : undefined} variant={variant} segments={segments} ariaLabel={ariaLabel} />
    </div>
  );
}

function stubScrollMetrics(element: HTMLElement, scrollTop: number, scrollHeight: number, clientHeight: number) {
  vi.spyOn(element, 'scrollHeight', 'get').mockReturnValue(scrollHeight);
  vi.spyOn(element, 'clientHeight', 'get').mockReturnValue(clientHeight);
  element.scrollTop = scrollTop;
}

afterEach(() => {
  vi.restoreAllMocks();
});

describe('scrollProgressMath', () => {
  it('measures element scroll progress and clamps to [0, 1]', () => {
    const element = { scrollTop: 100, scrollHeight: 500, clientHeight: 300 } as unknown as HTMLElement;
    expect(measureScrollProgress(element)).toBe(0.5);
    const overshoot = { scrollTop: 900, scrollHeight: 500, clientHeight: 300 } as unknown as HTMLElement;
    expect(measureScrollProgress(overshoot)).toBe(1);
    const negative = { scrollTop: -50, scrollHeight: 500, clientHeight: 300 } as unknown as HTMLElement;
    expect(measureScrollProgress(negative)).toBe(0);
  });

  it('returns zero progress when the container cannot scroll', () => {
    const flat = { scrollTop: 0, scrollHeight: 300, clientHeight: 300 } as unknown as HTMLElement;
    expect(measureScrollProgress(flat)).toBe(0);
    const inverted = { scrollTop: 0, scrollHeight: 200, clientHeight: 300 } as unknown as HTMLElement;
    expect(measureScrollProgress(inverted)).toBe(0);
  });

  it('measures window scroll progress from the document element', () => {
    const scrollYSpy = vi.spyOn(window, 'scrollY', 'get').mockReturnValue(120);
    const heightSpy = vi.spyOn(document.documentElement, 'scrollHeight', 'get').mockReturnValue(1000);
    const clientSpy = vi.spyOn(document.documentElement, 'clientHeight', 'get').mockReturnValue(400);
    expect(measureScrollProgress(window)).toBe(0.2);
    scrollYSpy.mockRestore();
    heightSpy.mockRestore();
    clientSpy.mockRestore();
  });

  it('resolves the active segment index for a segmented bar', () => {
    expect(resolveScrollSegment(0, 5)).toBe(0);
    expect(resolveScrollSegment(0.5, 5)).toBe(2);
    expect(resolveScrollSegment(1, 5)).toBe(4);
    expect(resolveScrollSegment(-1, 5)).toBe(0);
    expect(resolveScrollSegment(2, 5)).toBe(4);
    expect(resolveScrollSegment(0.5, 0)).toBe(0);
  });
});

describe('ScrollProgress bar variant', () => {
  it('exposes progressbar semantics starting at zero', async () => {
    render(<ProgressHarness />);
    const bar = screen.getByRole('progressbar', { name: '阅读进度' });
    expect(bar).toHaveAttribute('aria-valuemin', '0');
    expect(bar).toHaveAttribute('aria-valuemax', '100');
    expect(bar).toHaveAttribute('aria-valuenow', '0');
    await act(async () => {
      await rafFlush();
    });
    const fill = bar.querySelector('span');
    expect(fill?.style.transform).toBe('scaleX(0)');
  });

  it('tracks container scroll progress', async () => {
    render(<ProgressHarness />);
    const bar = screen.getByRole('progressbar', { name: '阅读进度' });
    const scroller = screen.getByTestId('scroller');
    stubScrollMetrics(scroller, 100, 500, 300);
    await act(async () => {
      fireEvent.scroll(scroller);
      await rafFlush();
    });
    expect(bar).toHaveAttribute('aria-valuenow', '50');
    const fill = bar.querySelector('span');
    expect(fill?.style.transform).toBe('scaleX(0.5)');
  });

  it('tracks window scroll progress without a container', async () => {
    render(<ProgressHarness attachContainer={false} />);
    const bar = screen.getByRole('progressbar', { name: '阅读进度' });
    vi.spyOn(window, 'scrollY', 'get').mockReturnValue(200);
    vi.spyOn(document.documentElement, 'scrollHeight', 'get').mockReturnValue(1200);
    vi.spyOn(document.documentElement, 'clientHeight', 'get').mockReturnValue(400);
    await act(async () => {
      fireEvent.scroll(window);
      await rafFlush();
    });
    expect(bar).toHaveAttribute('aria-valuenow', '25');
  });
});

describe('ScrollProgress segments variant', () => {
  it('marks the first segment active before scrolling', async () => {
    render(<ProgressHarness variant="segments" segments={5} ariaLabel="信息面板阅读进度" />);
    const bar = screen.getByRole('progressbar', { name: '信息面板阅读进度' });
    await act(async () => {
      await rafFlush();
    });
    const states = [...bar.querySelectorAll('span')].map((span) => span.getAttribute('data-state'));
    expect(states).toEqual(['active', 'idle', 'idle', 'idle', 'idle']);
  });

  it('maps mid-scroll progress to passed, active, and idle segments', async () => {
    render(<ProgressHarness variant="segments" segments={5} ariaLabel="信息面板阅读进度" />);
    const bar = screen.getByRole('progressbar', { name: '信息面板阅读进度' });
    const scroller = screen.getByTestId('scroller');
    stubScrollMetrics(scroller, 100, 500, 300);
    await act(async () => {
      fireEvent.scroll(scroller);
      await rafFlush();
    });
    expect(bar).toHaveAttribute('aria-valuenow', '50');
    const states = [...bar.querySelectorAll('span')].map((span) => span.getAttribute('data-state'));
    expect(states).toEqual(['passed', 'passed', 'active', 'idle', 'idle']);
  });

  it('marks the final segment active at full progress', async () => {
    render(<ProgressHarness variant="segments" segments={5} ariaLabel="信息面板阅读进度" />);
    const bar = screen.getByRole('progressbar', { name: '信息面板阅读进度' });
    const scroller = screen.getByTestId('scroller');
    stubScrollMetrics(scroller, 300, 500, 300);
    await act(async () => {
      fireEvent.scroll(scroller);
      await rafFlush();
    });
    const states = [...bar.querySelectorAll('span')].map((span) => span.getAttribute('data-state'));
    expect(states).toEqual(['passed', 'passed', 'passed', 'passed', 'active']);
  });
});
