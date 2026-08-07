import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useToast } from '../useToast';
import { useUIStore } from '../../store/ui';

describe('useToast', () => {
  beforeEach(() => {
    vi.useRealTimers();
    useUIStore.setState({ toasts: [] });
  });

  it('initializes with empty toasts', () => {
    const { result } = renderHook(() => useToast());
    expect(result.current.toasts).toEqual([]);
  });

  it('toast adds a toast to the list', () => {
    const { result } = renderHook(() => useToast());
    act(() => {
      result.current.toast({ type: 'success', title: 'Saved' });
    });
    expect(result.current.toasts).toHaveLength(1);
    expect(result.current.toasts[0].type).toBe('success');
    expect(result.current.toasts[0].title).toBe('Saved');
  });

  it('toast returns a unique id', () => {
    const { result } = renderHook(() => useToast());
    let id: string | undefined;
    act(() => {
      id = result.current.toast({ type: 'info', title: 'Hello' });
    });
    expect(typeof id).toBe('string');
    expect(id).toBeTruthy();
  });

  it('removeToast removes the toast by id', () => {
    const { result } = renderHook(() => useToast());
    let id: string | undefined;
    act(() => {
      id = result.current.toast({ type: 'warning', title: 'Careful' });
    });
    act(() => {
      result.current.removeToast(id as string);
    });
    expect(result.current.toasts).toHaveLength(0);
  });

  it('auto-removes toast after duration', () => {
    vi.useFakeTimers();
    const { result } = renderHook(() => useToast());
    act(() => {
      result.current.toast({ type: 'success', title: 'Temp', duration: 1000 });
    });
    expect(result.current.toasts).toHaveLength(1);
    act(() => {
      vi.advanceTimersByTime(1001);
    });
    expect(result.current.toasts).toHaveLength(0);
  });

  it('keeps toast when duration is 0', () => {
    const { result } = renderHook(() => useToast());
    act(() => {
      result.current.toast({ type: 'error', title: 'Stay', duration: 0 });
    });
    expect(result.current.toasts).toHaveLength(1);
  });
});
