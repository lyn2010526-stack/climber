import { act, renderHook } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { usePrefersReducedMotion } from './usePrefersReducedMotion';

type MediaListener = (event: { matches: boolean }) => void;

function stubMatchMedia(matches: boolean) {
  const listeners = new Set<MediaListener>();
  const addEventListener = vi.fn((_: string, listener: MediaListener) => listeners.add(listener));
  const removeEventListener = vi.fn((_: string, listener: MediaListener) => listeners.delete(listener));
  vi.spyOn(window, 'matchMedia').mockImplementation(((query: string) => ({
    matches,
    media: query,
    onchange: null,
    addListener: addEventListener,
    removeListener: () => {},
    addEventListener,
    removeEventListener,
    dispatchEvent: () => false,
  })) as unknown as typeof window.matchMedia);
  return { addEventListener, removeEventListener, listeners };
}

afterEach(() => {
  vi.restoreAllMocks();
});

describe('usePrefersReducedMotion', () => {
  it('reports false when the media query does not match', () => {
    stubMatchMedia(false);
    const { result } = renderHook(() => usePrefersReducedMotion());
    expect(result.current).toBe(false);
  });

  it('reports true and updates reactively when the media query matches later', () => {
    const stub = stubMatchMedia(false);
    const { result } = renderHook(() => usePrefersReducedMotion());
    expect(result.current).toBe(false);
    expect(stub.addEventListener).toHaveBeenCalledWith('change', expect.any(Function));
    const listener = [...stub.listeners][0];
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
    act(() => {
      listener({ matches: true });
    });
    expect(result.current).toBe(true);
  });

  it('unsubscribes from the media query on unmount', () => {
    const stub = stubMatchMedia(false);
    const { unmount } = renderHook(() => usePrefersReducedMotion());
    unmount();
    expect(stub.removeEventListener).toHaveBeenCalledWith('change', expect.any(Function));
  });
});
