import { describe, it, expect, beforeEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useNetworkStatus } from '../useNetworkStatus';
import { useNetworkStore } from '../../store/network';

describe('useNetworkStatus', () => {
  beforeEach(() => {
    useNetworkStore.setState({ online: true });
  });

  it('returns the online status from the store', () => {
    const { result } = renderHook(() => useNetworkStatus());
    expect(result.current.online).toBe(true);
    expect(result.current.isOffline).toBe(false);
  });

  it('reacts to the offline event', () => {
    const { result } = renderHook(() => useNetworkStatus());
    act(() => {
      window.dispatchEvent(new Event('offline'));
    });
    expect(result.current.online).toBe(false);
    expect(result.current.isOffline).toBe(true);
  });

  it('reacts to the online event', () => {
    const { result } = renderHook(() => useNetworkStatus());
    act(() => {
      window.dispatchEvent(new Event('offline'));
      window.dispatchEvent(new Event('online'));
    });
    expect(result.current.online).toBe(true);
    expect(result.current.isOffline).toBe(false);
  });
});
