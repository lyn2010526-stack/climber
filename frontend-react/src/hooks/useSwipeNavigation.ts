import { useRef, useCallback, useEffect } from 'react';

export interface SwipeConfig {
  minDistance?: number;
  maxVerticalOffset?: number;
  maxDuration?: number;
  enabled?: boolean;
}

export interface SwipeHandlers {
  onTouchStart: (e: React.TouchEvent) => void;
  onTouchMove: (e: React.TouchEvent) => void;
  onTouchEnd: () => void;
}

export interface SwipeNavigationOptions extends SwipeConfig {
  onSwipeLeft: () => void;
  onSwipeRight: () => void;
  onSwipeProgress?: (direction: 'left' | 'right', deltaX: number) => void;
}

interface SwipeState {
  startX: number;
  startY: number;
  startTime: number;
  currentX: number;
  currentY: number;
  isSwiping: boolean;
  direction: 'left' | 'right' | null;
}

const DEFAULT_CONFIG: Required<SwipeConfig> = {
  minDistance: 50,
  maxVerticalOffset: 30,
  maxDuration: 1000,
  enabled: true,
};

export function useSwipeNavigation(options: SwipeNavigationOptions): SwipeHandlers {
  const {
    onSwipeLeft,
    onSwipeRight,
    onSwipeProgress,
    minDistance = DEFAULT_CONFIG.minDistance,
    maxVerticalOffset = DEFAULT_CONFIG.maxVerticalOffset,
    maxDuration = DEFAULT_CONFIG.maxDuration,
    enabled = DEFAULT_CONFIG.enabled,
  } = options;

  const state = useRef<SwipeState>({
    startX: 0,
    startY: 0,
    startTime: 0,
    currentX: 0,
    currentY: 0,
    isSwiping: false,
    direction: null,
  });

  const handleTouchStart = useCallback((e: React.TouchEvent) => {
    if (!enabled) return;
    const touch = e.touches[0];
    if (!touch) return;
    state.current = {
      startX: touch.clientX,
      startY: touch.clientY,
      startTime: Date.now(),
      currentX: touch.clientX,
      currentY: touch.clientY,
      isSwiping: false,
      direction: null,
    };
  }, [enabled]);

  const handleTouchMove = useCallback((e: React.TouchEvent) => {
    if (!enabled) return;
    const touch = e.touches[0];
    if (!touch) return;

    const s = state.current;
    const deltaX = touch.clientX - s.startX;
    const deltaY = Math.abs(touch.clientY - s.startY);

    if (!s.isSwiping) {
      if (deltaY > maxVerticalOffset) return;
      if (Math.abs(deltaX) > 10) {
        s.isSwiping = true;
        s.direction = deltaX > 0 ? 'right' : 'left';
      }
    }

    if (s.isSwiping) {
      s.currentX = touch.clientX;
      s.currentY = touch.clientY;
      onSwipeProgress?.(s.direction!, deltaX);
    }
  }, [enabled, maxVerticalOffset, onSwipeProgress]);

  const handleTouchEnd = useCallback(() => {
    if (!enabled) return;
    const s = state.current;

    if (!s.isSwiping) return;

    const deltaX = s.currentX - s.startX;
    const absDeltaX = Math.abs(deltaX);
    const deltaY = Math.abs((s.currentY ?? s.startY) - s.startY);
    const duration = Date.now() - s.startTime;

    s.isSwiping = false;

    if (deltaY > maxVerticalOffset) return;
    if (absDeltaX < minDistance) return;
    if (duration > maxDuration) return;

    if (deltaX < 0) {
      onSwipeLeft();
    } else {
      onSwipeRight();
    }
  }, [enabled, minDistance, maxVerticalOffset, maxDuration, onSwipeLeft, onSwipeRight]);

  useEffect(() => {
    return () => {
      state.current.isSwiping = false;
    };
  }, []);

  return {
    onTouchStart: handleTouchStart,
    onTouchMove: handleTouchMove,
    onTouchEnd: handleTouchEnd,
  };
}

export type MobileNavPage = 'chat' | 'factory' | 'cluster' | 'tasks' | 'agents' | 'settings';

export const MOBILE_NAV_PAGES: MobileNavPage[] = [
  'chat',
  'factory',
  'cluster',
  'tasks',
  'agents',
  'settings',
];

export function useMobileSwipeNavigation(
  currentPage: MobileNavPage,
  onNavigate: (page: MobileNavPage) => void,
  config?: SwipeConfig,
): SwipeHandlers {
  const currentIndex = MOBILE_NAV_PAGES.indexOf(currentPage);

  const navigateTo = useCallback((index: number) => {
    const clamped = Math.max(0, Math.min(index, MOBILE_NAV_PAGES.length - 1));
    const target = MOBILE_NAV_PAGES[clamped];
    if (target && target !== currentPage) {
      onNavigate(target);
    }
  }, [currentPage, onNavigate]);

  const onSwipeLeft = useCallback(() => {
    navigateTo(currentIndex + 1);
  }, [currentIndex, navigateTo]);

  const onSwipeRight = useCallback(() => {
    navigateTo(currentIndex - 1);
  }, [currentIndex, navigateTo]);

  return useSwipeNavigation({
    onSwipeLeft,
    onSwipeRight,
    ...config,
  });
}
