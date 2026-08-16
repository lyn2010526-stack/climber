import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useChat } from '../../useChat';

const mocks = vi.hoisted(() => ({
  onEvent: null as ((event: { event: string; data: any }) => void) | null,
  chatStream: vi.fn(),
}));

vi.mock('../../api', () => ({
  api: {
    getSessionMessages: vi.fn().mockResolvedValue({ messages: [] }),
    chatStream: mocks.chatStream,
  },
}));

describe('useChat', () => {
  beforeEach(() => {
    mocks.onEvent = null;
    mocks.chatStream.mockReset();
    mocks.chatStream.mockImplementation((_sessionId, _content, onEvent) => {
      mocks.onEvent = onEvent;
      return vi.fn();
    });
  });

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

  it('preserves completed and failed tool states as more events arrive', async () => {
    const { result } = renderHook(() => useChat('session-1'));

    await act(async () => {
      await result.current.sendMessage('run tools');
    });
    act(() => {
      mocks.onEvent?.({ event: 'tool_call', data: { id: 'one', name: 'first', arguments: {} } });
      mocks.onEvent?.({ event: 'tool_result', data: { id: 'one', result: 'ok' } });
      mocks.onEvent?.({ event: 'tool_call', data: { id: 'two', name: 'second', arguments: {} } });
      mocks.onEvent?.({ event: 'tool_result', data: { id: 'two', error: 'failed' } });
      mocks.onEvent?.({ event: 'done', data: {} });
    });

    const toolCalls = result.current.messages.find(message => message.role === 'assistant')?.toolCalls;
    expect(toolCalls).toEqual([
      expect.objectContaining({ id: 'one', status: 'success', result: 'ok' }),
      expect.objectContaining({ id: 'two', status: 'error', error: 'failed' }),
    ]);
  });
});
