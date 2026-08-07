import { describe, it, expect, vi } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useSwipeNavigation, useMobileSwipeNavigation } from '../useSwipeNavigation';

const touch = (x: number, y: number) => ({ touches: [{ clientX: x, clientY: y }] }) as any;

describe('useSwipeNavigation', () => {
  it('calls onSwipeLeft for a left swipe', () => {
    const onSwipeLeft = vi.fn();
    const onSwipeRight = vi.fn();
    const { result } = renderHook(() => useSwipeNavigation({ onSwipeLeft, onSwipeRight }));
    act(() => result.current.onTouchStart(touch(200, 100)));
    act(() => result.current.onTouchMove(touch(120, 100)));
    act(() => result.current.onTouchEnd());
    expect(onSwipeLeft).toHaveBeenCalledTimes(1);
    expect(onSwipeRight).not.toHaveBeenCalled();
  });

  it('calls onSwipeRight for a right swipe', () => {
    const onSwipeLeft = vi.fn();
    const onSwipeRight = vi.fn();
    const { result } = renderHook(() => useSwipeNavigation({ onSwipeLeft, onSwipeRight }));
    act(() => result.current.onTouchStart(touch(100, 100)));
    act(() => result.current.onTouchMove(touch(180, 100)));
    act(() => result.current.onTouchEnd());
    expect(onSwipeRight).toHaveBeenCalledTimes(1);
    expect(onSwipeLeft).not.toHaveBeenCalled();
  });

  it('ignores swipes below the minimum distance', () => {
    const onSwipeLeft = vi.fn();
    const { result } = renderHook(() =>
      useSwipeNavigation({ onSwipeLeft, onSwipeRight: vi.fn(), minDistance: 100 }),
    );
    act(() => result.current.onTouchStart(touch(200, 100)));
    act(() => result.current.onTouchMove(touch(150, 100)));
    act(() => result.current.onTouchEnd());
    expect(onSwipeLeft).not.toHaveBeenCalled();
  });

  it('ignores swipes with excessive vertical offset', () => {
    const onSwipeLeft = vi.fn();
    const { result } = renderHook(() => useSwipeNavigation({ onSwipeLeft, onSwipeRight: vi.fn() }));
    act(() => result.current.onTouchStart(touch(200, 100)));
    act(() => result.current.onTouchMove(touch(120, 200)));
    act(() => result.current.onTouchEnd());
    expect(onSwipeLeft).not.toHaveBeenCalled();
  });

  it('reports swipe progress during move', () => {
    const onSwipeProgress = vi.fn();
    const { result } = renderHook(() =>
      useSwipeNavigation({ onSwipeLeft: vi.fn(), onSwipeRight: vi.fn(), onSwipeProgress }),
    );
    act(() => result.current.onTouchStart(touch(200, 100)));
    act(() => result.current.onTouchMove(touch(150, 100)));
    expect(onSwipeProgress).toHaveBeenCalledWith('left', -50);
  });

  it('does nothing when disabled', () => {
    const onSwipeLeft = vi.fn();
    const { result } = renderHook(() =>
      useSwipeNavigation({ onSwipeLeft, onSwipeRight: vi.fn(), enabled: false }),
    );
    act(() => result.current.onTouchStart(touch(200, 100)));
    act(() => result.current.onTouchMove(touch(120, 100)));
    act(() => result.current.onTouchEnd());
    expect(onSwipeLeft).not.toHaveBeenCalled();
  });
});

describe('useMobileSwipeNavigation', () => {
  it('navigates to the next page on a left swipe', () => {
    const onNavigate = vi.fn();
    const { result } = renderHook(() => useMobileSwipeNavigation('chat', onNavigate));
    act(() => result.current.onTouchStart(touch(200, 100)));
    act(() => result.current.onTouchMove(touch(120, 100)));
    act(() => result.current.onTouchEnd());
    expect(onNavigate).toHaveBeenCalledWith('factory');
  });
});
