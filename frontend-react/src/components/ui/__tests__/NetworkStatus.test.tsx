import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { NetworkStatus, useNetworkStatus, OfflineIndicator } from '../NetworkStatus';

describe('NetworkStatus', () => {
  beforeEach(() => {
    Object.defineProperty(navigator, 'onLine', { value: true, writable: true });
  });

  it('returns null when online', () => {
    const { container } = render(<NetworkStatus />);
    expect(container.firstChild).toBeNull();
  });

  it('shows banner when offline', () => {
    Object.defineProperty(navigator, 'onLine', { value: false, writable: true });
    render(<NetworkStatus />);
    expect(screen.getByText(/网络连接已断开/)).toBeDefined();
  });

  it('responds to offline event', () => {
    Object.defineProperty(navigator, 'onLine', { value: true, writable: true });
    render(<NetworkStatus />);
    expect(screen.queryByText(/网络连接已断开/)).toBeNull();

    Object.defineProperty(navigator, 'onLine', { value: false, writable: true });
    fireEvent(window, new Event('offline'));
    expect(screen.getByText(/网络连接已断开/)).toBeDefined();
  });

  it('responds to online event', () => {
    Object.defineProperty(navigator, 'onLine', { value: false, writable: true });
    render(<NetworkStatus />);
    expect(screen.getByText(/网络连接已断开/)).toBeDefined();

    Object.defineProperty(navigator, 'onLine', { value: true, writable: true });
    fireEvent(window, new Event('online'));
    expect(screen.queryByText(/网络连接已断开/)).toBeNull();
  });
});

describe('useNetworkStatus', () => {
  beforeEach(() => {
    Object.defineProperty(navigator, 'onLine', { value: true, writable: true });
  });

  it('returns online status', () => {
    const { result } = renderHook(() => useNetworkStatus());
    expect(result.current.online).toBe(true);
    expect(result.current.isOffline).toBe(false);
  });

  it('returns offline status', () => {
    Object.defineProperty(navigator, 'onLine', { value: false, writable: true });
    const { result } = renderHook(() => useNetworkStatus());
    expect(result.current.online).toBe(false);
    expect(result.current.isOffline).toBe(true);
  });

  it('updates on offline event', () => {
    const { result } = renderHook(() => useNetworkStatus());
    expect(result.current.online).toBe(true);

    Object.defineProperty(navigator, 'onLine', { value: false, writable: true });
    fireEvent(window, new Event('offline'));
    expect(result.current.online).toBe(false);
    expect(result.current.isOffline).toBe(true);
  });

  it('updates on online event', () => {
    Object.defineProperty(navigator, 'onLine', { value: false, writable: true });
    const { result } = renderHook(() => useNetworkStatus());
    expect(result.current.online).toBe(false);

    Object.defineProperty(navigator, 'onLine', { value: true, writable: true });
    fireEvent(window, new Event('online'));
    expect(result.current.online).toBe(true);
  });
});

describe('OfflineIndicator', () => {
  beforeEach(() => {
    Object.defineProperty(navigator, 'onLine', { value: true, writable: true });
  });

  it('returns null when online', () => {
    const { container } = render(<OfflineIndicator />);
    expect(container.firstChild).toBeNull();
  });

  it('shows indicator when offline', () => {
    Object.defineProperty(navigator, 'onLine', { value: false, writable: true });
    render(<OfflineIndicator />);
    expect(screen.getByText('离线')).toBeDefined();
  });
});

import { renderHook } from '@testing-library/react';
