import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type { RefObject } from 'react';
import Lenis from 'lenis';
import { usePrefersReducedMotion } from './usePrefersReducedMotion';

export interface SmoothScrollOptions {
  duration?: number;
  lerp?: number;
  easing?: (time: number) => number;
  allowNestedScroll?: boolean;
}

export interface SmoothScrollTargetOptions {
  offset?: number;
  immediate?: boolean;
  duration?: number;
}

export interface SmoothScrollHandle {
  enabled: boolean;
  scrollTo: (target: number | string | HTMLElement, options?: SmoothScrollTargetOptions) => void;
  stop: () => void;
  start: () => void;
}

export function isSmoothScrollSurfaceReady(wrapper: HTMLElement | Window): boolean {
  if (typeof window === 'undefined' || typeof document === 'undefined') return false;
  if (typeof window.requestAnimationFrame !== 'function') return false;
  if (wrapper instanceof HTMLElement) return wrapper.scrollHeight > 0 || wrapper.clientHeight > 0;
  return document.documentElement.scrollHeight > 0;
}

function nativeScrollTo(target: number | string | HTMLElement, container: HTMLElement | null): void {
  if (typeof target === 'number') {
    if (container) container.scrollTop = target;
    else window.scrollTo(0, target);
    return;
  }
  const element = typeof target === 'string' ? document.querySelector<HTMLElement>(target) : target;
  element?.scrollIntoView({ block: 'start', behavior: 'auto' });
}

export function useSmoothScroll(
  ref?: RefObject<HTMLElement | null>,
  options: SmoothScrollOptions = {},
): SmoothScrollHandle {
  const reducedMotion = usePrefersReducedMotion();
  const instanceRef = useRef<Lenis | null>(null);
  const [enabled, setEnabled] = useState(false);
  const { duration, lerp, easing, allowNestedScroll = true } = options;
  const easingRef = useRef(easing);
  easingRef.current = easing;

  useEffect(() => {
    if (reducedMotion) {
      setEnabled(false);
      return;
    }
    const wrapper = ref?.current ?? window;
    if (!isSmoothScrollSurfaceReady(wrapper)) return;
    const content =
      wrapper instanceof HTMLElement ? ((wrapper.firstElementChild as HTMLElement | null) ?? wrapper) : undefined;
    let instance: Lenis;
    try {
      instance = new Lenis({
        wrapper,
        ...(content ? { content } : {}),
        ...(typeof duration === 'number' ? { duration } : {}),
        ...(typeof lerp === 'number' ? { lerp } : {}),
        ...(easingRef.current ? { easing: easingRef.current } : {}),
        allowNestedScroll,
        autoRaf: false,
      });
    } catch {
      return;
    }
    instanceRef.current = instance;
    setEnabled(true);
    let frame = requestAnimationFrame(function tick(time: number) {
      instance.raf(time);
      frame = requestAnimationFrame(tick);
    });
    return () => {
      cancelAnimationFrame(frame);
      instanceRef.current = null;
      setEnabled(false);
      instance.destroy();
    };
  }, [reducedMotion, ref, duration, lerp, allowNestedScroll]);

  const scrollTo = useCallback(
    (target: number | string | HTMLElement, targetOptions: SmoothScrollTargetOptions = {}) => {
      const instance = instanceRef.current;
      if (instance) {
        instance.scrollTo(target, {
          ...(typeof targetOptions.offset === 'number' ? { offset: targetOptions.offset } : {}),
          ...(targetOptions.immediate ? { immediate: true } : {}),
          ...(typeof targetOptions.duration === 'number' ? { duration: targetOptions.duration } : {}),
        });
        return;
      }
      nativeScrollTo(target, ref?.current ?? null);
    },
    [ref],
  );

  const stop = useCallback(() => {
    instanceRef.current?.stop();
  }, []);

  const start = useCallback(() => {
    instanceRef.current?.start();
  }, []);

  return useMemo(() => ({ enabled, scrollTo, stop, start }), [enabled, scrollTo, stop, start]);
}
