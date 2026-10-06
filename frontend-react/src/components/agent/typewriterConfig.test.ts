import { beforeEach, describe, expect, it, vi } from 'vitest';
import { cycleTypewriterMode, setTypewriterMode, typewriterPresetFor, useTypewriterMode } from './typewriterConfig';

import { act, renderHook } from '@testing-library/react';

beforeEach(() => {
  setTypewriterMode('off');
  localStorage.clear();
});

describe('typewriterConfig', () => {
  it('cycles off -> balanced -> realtime -> silky -> off', () => {
    expect(cycleTypewriterMode()).toBe('balanced');
    expect(cycleTypewriterMode()).toBe('realtime');
    expect(cycleTypewriterMode()).toBe('silky');
    expect(cycleTypewriterMode()).toBe('off');
  });

  it('maps only active presets to a reveal preset', () => {
    expect(typewriterPresetFor('off')).toBe('balanced');
    expect(typewriterPresetFor('realtime')).toBe('realtime');
    expect(typewriterPresetFor('silky')).toBe('silky');
  });

  it('notifies useSyncExternalStore subscribers', () => {
    const { result } = renderHook(() => useTypewriterMode());
    expect(result.current).toBe('off');
    act(() => setTypewriterMode('realtime'));
    expect(result.current).toBe('realtime');
  });

  it('persists the selection and restores it', () => {
    setTypewriterMode('silky');
    expect(localStorage.getItem('climber.anchored.typewriter-mode')).toBe('silky');
  });

  it('wraps a malformed in-memory mode back to the safe default', () => {
    const { result } = renderHook(() => useTypewriterMode());
    act(() => { setTypewriterMode('turbo' as unknown as 'off'); });
    expect(result.current).toBe('turbo');
    act(() => { cycleTypewriterMode(); });
    expect(result.current).toBe('off');
  });

  it('survives storage being unavailable', () => {
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new Error('quota');
    });
    expect(() => setTypewriterMode('balanced')).not.toThrow();
  });
});