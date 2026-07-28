import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { usePersistentState, useSessionRecovery } from '../usePersistentState';

describe('usePersistentState', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('initializes with default value', () => {
    const { result } = renderHook(() => usePersistentState('test_key', 'default'));
    expect(result.current[0]).toBe('default');
  });

  it('persists value to localStorage', () => {
    const { result } = renderHook(() => usePersistentState<string>('test_key', 'default'));
    act(() => result.current[1]('new_value'));
    expect(localStorage.getItem('agent_engine_test_key')).toBe('"new_value"');
  });

  it('reads persisted value on next render', () => {
    localStorage.setItem('agent_engine_test_key', JSON.stringify('saved'));
    const { result } = renderHook(() => usePersistentState<string>('test_key', 'default'));
    expect(result.current[0]).toBe('saved');
  });

  it('supports functional updates', () => {
    const { result } = renderHook(() => usePersistentState<number>('counter', 0));
    act(() => result.current[1](prev => prev + 1));
    act(() => result.current[1](prev => prev + 1));
    expect(result.current[0]).toBe(2);
  });

  it('respects TTL and expires old values', () => {
    vi.useFakeTimers();
    const { result } = renderHook(() =>
      usePersistentState<string>('ttl_key', 'default', { ttl: 1000 }),
    );
    act(() => result.current[1]('expirable'));
    expect(result.current[0]).toBe('expirable');

    act(() => vi.advanceTimersByTime(1001));
    const { result: result2 } = renderHook(() =>
      usePersistentState<string>('ttl_key', 'default', { ttl: 1000 }),
    );
    expect(result2.current[0]).toBe('default');
    vi.useRealTimers();
  });
});

describe('useSessionRecovery', () => {
  beforeEach(() => {
    sessionStorage.clear();
  });

  it('returns false when no saved session', () => {
    const { result } = renderHook(() => useSessionRecovery('session'));
    expect(result.current.restore()).toBe(false);
  });

  it('restores session within 30s window', () => {
    sessionStorage.setItem('agent_engine_session_session', JSON.stringify({ timestamp: Date.now(), data: {} }));
    const { result } = renderHook(() => useSessionRecovery('session'));
    expect(result.current.restore()).toBe(true);
  });

  it('returns false when session is older than 30s', () => {
    vi.useFakeTimers();
    sessionStorage.setItem('agent_engine_session_session', JSON.stringify({ timestamp: Date.now() - 31000, data: {} }));
    const { result } = renderHook(() => useSessionRecovery('session'));
    expect(result.current.restore()).toBe(false);
    vi.useRealTimers();
  });

  it('clears saved session', () => {
    sessionStorage.setItem('agent_engine_session_session', JSON.stringify({ timestamp: Date.now(), data: {} }));
    const { result } = renderHook(() => useSessionRecovery('session'));
    act(() => result.current.clear());
    expect(sessionStorage.getItem('agent_engine_session_session')).toBeNull();
  });
});
