import { describe, it, expect, beforeEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useAppTheme } from '../useAppTheme';
import { useUIStore } from '../../store/ui';

describe('useAppTheme', () => {
  beforeEach(() => {
    localStorage.clear();
    useUIStore.setState({ theme: 'dark' });
    document.documentElement.removeAttribute('data-theme');
  });

  it('returns the current theme', () => {
    const { result } = renderHook(() => useAppTheme());
    expect(result.current.theme).toBe('dark');
  });

  it('toggles between dark and light', () => {
    const { result } = renderHook(() => useAppTheme());
    act(() => result.current.toggleTheme());
    expect(result.current.theme).toBe('light');
    act(() => result.current.toggleTheme());
    expect(result.current.theme).toBe('dark');
  });

  it('setTheme updates the theme', () => {
    const { result } = renderHook(() => useAppTheme());
    act(() => result.current.setTheme('light'));
    expect(result.current.theme).toBe('light');
  });

  it('syncs theme to the data-theme attribute and localStorage', () => {
    const { result } = renderHook(() => useAppTheme());
    act(() => result.current.setTheme('light'));
    expect(document.documentElement.getAttribute('data-theme')).toBe('light');
    expect(localStorage.getItem('climber-theme')).toBe('light');
  });
});
