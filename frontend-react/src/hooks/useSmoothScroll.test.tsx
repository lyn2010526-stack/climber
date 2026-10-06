import { render, renderHook, screen, waitFor } from '@testing-library/react';
import { useEffect, useRef } from 'react';
import type { RefObject } from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import Lenis from 'lenis';
import { useSmoothScroll } from './useSmoothScroll';
import type { SmoothScrollOptions } from './useSmoothScroll';

interface LenisInstanceStub {
  options: Record<string, unknown>;
  raf: ReturnType<typeof vi.fn>;
  scrollTo: ReturnType<typeof vi.fn>;
  stop: ReturnType<typeof vi.fn>;
  start: ReturnType<typeof vi.fn>;
  destroy: ReturnType<typeof vi.fn>;
}

type LenisCtorStub = ReturnType<typeof vi.fn> & { instances: LenisInstanceStub[] };

vi.mock('lenis', () => {
  const instances: LenisInstanceStub[] = [];
  const ctor = vi.fn(function lenisFactory(this: unknown, options: Record<string, unknown>) {
    const instance: LenisInstanceStub = {
      options,
      raf: vi.fn(),
      scrollTo: vi.fn(),
      stop: vi.fn(),
      start: vi.fn(),
      destroy: vi.fn(),
    };
    instances.push(instance);
    return instance;
  });
  (ctor as unknown as { instances: LenisInstanceStub[] }).instances = instances;
  return { default: ctor };
});

const lenisCtor = Lenis as unknown as LenisCtorStub;

function stubDocumentSurface(scrollHeight: number, clientHeight = 300) {
  vi.spyOn(document.documentElement, 'scrollHeight', 'get').mockReturnValue(scrollHeight);
  vi.spyOn(document.documentElement, 'clientHeight', 'get').mockReturnValue(clientHeight);
}

function ElementHarness({ options, toggle }: { options?: SmoothScrollOptions; toggle?: boolean }) {
  const ref = useRef<HTMLDivElement | null>(null);
  const handle = useSmoothScroll(ref, options);
  void handle;
  void toggle;
  return (
    <div ref={ref} data-testid="scroller">
      <div data-testid="scroller-content" />
    </div>
  );
}

beforeEach(() => {
  lenisCtor.instances.length = 0;
  lenisCtor.mockClear();
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe('useSmoothScroll degradation', () => {
  it('stays a no-op when the scroll surface is not measurable (jsdom)', () => {
    const { result } = renderHook(() => useSmoothScroll());
    expect(result.current.enabled).toBe(false);
    expect(lenisCtor).not.toHaveBeenCalled();
    result.current.stop();
    result.current.start();
    expect(lenisCtor).not.toHaveBeenCalled();
  });

  it('stays a no-op when the user prefers reduced motion', () => {
    stubDocumentSurface(1000);
    vi.spyOn(window, 'matchMedia').mockImplementation((() => ({
      matches: true,
      media: '(prefers-reduced-motion: reduce)',
      onchange: null,
      addListener: () => {},
      removeListener: () => {},
      addEventListener: () => {},
      removeEventListener: () => {},
      dispatchEvent: () => false,
    })) as unknown as typeof window.matchMedia);
    const { result } = renderHook(() => useSmoothScroll());
    expect(result.current.enabled).toBe(false);
    expect(lenisCtor).not.toHaveBeenCalled();
  });

  it('degrades gracefully when lenis instantiation throws', () => {
    stubDocumentSurface(1000);
    lenisCtor.mockImplementationOnce(() => {
      throw new Error('lenis unavailable');
    });
    const { result } = renderHook(() => useSmoothScroll());
    expect(result.current.enabled).toBe(false);
    expect(lenisCtor).toHaveBeenCalledTimes(1);
  });
});

describe('useSmoothScroll activation', () => {
  it('activates lenis on window with nested-scroll safety and drives the raf loop', async () => {
    stubDocumentSurface(1000);
    const { result, unmount } = renderHook(() => useSmoothScroll());
    expect(result.current.enabled).toBe(true);
    expect(lenisCtor).toHaveBeenCalledTimes(1);
    expect(lenisCtor).toHaveBeenCalledWith(
      expect.objectContaining({ wrapper: window, allowNestedScroll: true, autoRaf: false }),
    );
    const instance = lenisCtor.instances[0];
    await waitFor(() => expect(instance.raf).toHaveBeenCalled());
    expect(instance.raf.mock.calls[0][0]).toEqual(expect.any(Number));

    result.current.stop();
    expect(instance.stop).toHaveBeenCalledTimes(1);
    result.current.start();
    expect(instance.start).toHaveBeenCalledTimes(1);
    result.current.scrollTo(240, { immediate: true, duration: 0.4 });
    expect(instance.scrollTo).toHaveBeenCalledWith(240, { immediate: true, duration: 0.4 });

    const cancelSpy = vi.spyOn(window, 'cancelAnimationFrame');
    unmount();
    expect(instance.destroy).toHaveBeenCalledTimes(1);
    expect(cancelSpy).toHaveBeenCalled();
    cancelSpy.mockRestore();
  });

  it('binds an element wrapper with an explicit content element on re-run', () => {
    const { rerender } = render(<ElementHarness options={{}} />);
    const scroller = screen.getByTestId('scroller');
    expect(lenisCtor).not.toHaveBeenCalled();
    vi.spyOn(scroller, 'scrollHeight', 'get').mockReturnValue(900);
    rerender(<ElementHarness options={{ duration: 1.2 }} toggle />);
    expect(lenisCtor).toHaveBeenCalledTimes(1);
    expect(lenisCtor).toHaveBeenCalledWith(
      expect.objectContaining({
        wrapper: scroller,
        content: screen.getByTestId('scroller-content'),
        duration: 1.2,
        allowNestedScroll: true,
        autoRaf: false,
      }),
    );
  });

  it('forwards a custom easing via a stable ref across re-renders', () => {
    stubDocumentSurface(1000);
    const easing = (time: number) => time;
    const { rerender } = renderHook(({ options }: { options: SmoothScrollOptions }) => useSmoothScroll(undefined, options), {
      initialProps: { options: { easing } },
    });
    rerender({ options: { easing } });
    expect(lenisCtor).toHaveBeenCalledTimes(1);
    expect(lenisCtor).toHaveBeenCalledWith(expect.objectContaining({ easing }));
  });
});

describe('useSmoothScroll native fallback', () => {
  it('falls back to a native scrollTop jump on the bound element when disabled', () => {
    const fallbackRef: RefObject<HTMLDivElement | null> = { current: null };
    function FallbackHarness() {
      const handle = useSmoothScroll(fallbackRef);
      useEffect(() => {
        handle.scrollTo(120);
      }, [handle]);
      return <div ref={fallbackRef} data-testid="fallback" />;
    }
    render(<FallbackHarness />);
    const node = screen.getByTestId('fallback');
    expect(node.scrollTop).toBe(120);
  });

  it('resolves string and element targets through scrollIntoView when disabled', () => {
    const target = document.createElement('div');
    const scrollIntoView = vi.fn();
    (target as unknown as { scrollIntoView: unknown }).scrollIntoView = scrollIntoView;
    document.body.appendChild(target);
    const { result } = renderHook(() => useSmoothScroll());
    result.current.scrollTo('#missing');
    result.current.scrollTo(target);
    expect(scrollIntoView).toHaveBeenCalledWith({ block: 'start', behavior: 'auto' });
    target.parentElement?.removeChild(target);
  });
});
