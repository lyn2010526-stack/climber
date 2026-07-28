import { describe, it, expect } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useChat } from '../../useChat';

describe('useChat', () => {
  it('initializes with empty messages', () => {
    const { result } = renderHook(() => useChat('session-1'));
    expect(result.current.messages).toEqual([]);
    expect(result.current.isStreaming).toBe(false);
  });

  it('exposes sendMessage and stopStreaming', () => {
    const { result } = renderHook(() => useChat('session-1'));
    expect(typeof result.current.sendMessage).toBe('function');
    expect(typeof result.current.stopStreaming).toBe('function');
    expect(typeof result.current.clear).toBe('function');
  });

  it('clears messages', () => {
    const { result } = renderHook(() => useChat('session-1'));
    act(() => {
      result.current.clear();
    });
    expect(result.current.messages).toEqual([]);
  });
});
