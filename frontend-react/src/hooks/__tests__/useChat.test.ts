import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, act, waitFor } from '@testing-library/react';
import { useChat } from '../../hooks/useChat';

const mocks = vi.hoisted(() => ({
  onEvent: null as ((event: { event: string; data: any }) => void) | null,
  chatStream: vi.fn(),
  getSessionMessages: vi.fn().mockResolvedValue({ messages: [] }),
}));

vi.mock('../../api', () => ({
  api: {
    getSessionMessages: mocks.getSessionMessages,
    chatStream: mocks.chatStream,
  },
}));

describe('useChat', () => {
  beforeEach(() => {
    mocks.onEvent = null;
    mocks.chatStream.mockReset();
    mocks.getSessionMessages.mockClear();
    mocks.chatStream.mockImplementation((_sessionId, _content, onEvent) => {
      mocks.onEvent = onEvent;
      return vi.fn();
    });
  });

  it('initializes with empty messages', async () => {
    const { result } = renderHook(() => useChat('session-1'));
    await waitFor(() => expect(mocks.getSessionMessages).toHaveBeenCalledWith('session-1'));
    expect(result.current.messages).toEqual([]);
    expect(result.current.isStreaming).toBe(false);
  });

  it('exposes sendMessage and stopStreaming', async () => {
    const { result } = renderHook(() => useChat('session-1'));
    await waitFor(() => expect(mocks.getSessionMessages).toHaveBeenCalledWith('session-1'));
    expect(typeof result.current.sendMessage).toBe('function');
    expect(typeof result.current.stopStreaming).toBe('function');
    expect(typeof result.current.clear).toBe('function');
  });

  it('clears messages', async () => {
    const { result } = renderHook(() => useChat('session-1'));
    await waitFor(() => expect(mocks.getSessionMessages).toHaveBeenCalledWith('session-1'));
    await act(async () => {
      result.current.clear();
    });
    expect(result.current.messages).toEqual([]);
  });

  it('preserves completed and failed tool states as more events arrive', async () => {
    const { result } = renderHook(() => useChat('session-1'));
    await waitFor(() => expect(mocks.getSessionMessages).toHaveBeenCalledWith('session-1'));

    await act(async () => {
      await result.current.sendMessage('run tools');
    });
    await act(async () => {
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

  it('correlates tool results by tool_call_id', async () => {
    const { result } = renderHook(() => useChat('session-1'));
    await waitFor(() => expect(mocks.getSessionMessages).toHaveBeenCalledWith('session-1'));

    await act(async () => {
      await result.current.sendMessage('run tool');
      mocks.onEvent?.({ event: 'tool_call', data: { id: 'call-1', name: 'echo', arguments: {} } });
      mocks.onEvent?.({ event: 'tool_result', data: { tool_call_id: 'call-1', result: 'ok' } });
    });

    const toolCall = result.current.messages.find(message => message.role === 'assistant')?.toolCalls?.[0];
    expect(toolCall).toEqual(expect.objectContaining({ id: 'call-1', status: 'success', result: 'ok' }));
  });

  it('marks tool calls without a result as errors when the stream ends', async () => {
    const { result } = renderHook(() => useChat('session-1'));
    await waitFor(() => expect(mocks.getSessionMessages).toHaveBeenCalledWith('session-1'));

    await act(async () => {
      await result.current.sendMessage('run tool');
      mocks.onEvent?.({ event: 'tool_call', data: { id: 'call-1', name: 'echo', arguments: {} } });
      mocks.onEvent?.({ event: 'done', data: {} });
    });

    const toolCall = result.current.messages.find(message => message.role === 'assistant')?.toolCalls?.[0];
    expect(toolCall).toEqual(expect.objectContaining({
      id: 'call-1',
      status: 'error',
      error: 'Tool stream ended before a result was received',
    }));
  });

  it('marks running tool calls as errors when the stream reports an error', async () => {
    const { result } = renderHook(() => useChat('session-1'));
    await waitFor(() => expect(mocks.getSessionMessages).toHaveBeenCalledWith('session-1'));

    await act(async () => {
      await result.current.sendMessage('run tool');
      mocks.onEvent?.({ event: 'tool_call', data: { id: 'call-1', name: 'echo', arguments: {} } });
      mocks.onEvent?.({ event: 'error', data: { error: 'connection failed' } });
    });

    const toolCall = result.current.messages.find(message => message.role === 'assistant')?.toolCalls?.[0];
    expect(toolCall).toEqual(expect.objectContaining({
      id: 'call-1',
      status: 'error',
      error: 'connection failed',
    }));
  });

  it('marks running tool calls as errors when the stream closes unexpectedly', async () => {
    const { result } = renderHook(() => useChat('session-1'));
    await waitFor(() => expect(mocks.getSessionMessages).toHaveBeenCalledWith('session-1'));

    await act(async () => {
      await result.current.sendMessage('run tool');
      mocks.onEvent?.({ event: 'tool_call', data: { id: 'call-1', name: 'echo', arguments: {} } });
      mocks.onEvent?.({ event: 'eof', data: {} });
    });

    const toolCall = result.current.messages.find(message => message.role === 'assistant')?.toolCalls?.[0];
    expect(toolCall).toEqual(expect.objectContaining({
      id: 'call-1',
      status: 'error',
      error: 'Tool stream ended before a result was received',
    }));
  });

  it('marks running tool calls as errors when streaming is stopped', async () => {
    const { result } = renderHook(() => useChat('session-1'));
    await waitFor(() => expect(mocks.getSessionMessages).toHaveBeenCalledWith('session-1'));

    await act(async () => {
      await result.current.sendMessage('run tool');
      mocks.onEvent?.({ event: 'tool_call', data: { id: 'call-1', name: 'echo', arguments: {} } });
      result.current.stopStreaming();
    });

    const toolCall = result.current.messages.find(message => message.role === 'assistant')?.toolCalls?.[0];
    expect(toolCall).toEqual(expect.objectContaining({
      id: 'call-1',
      status: 'error',
      error: 'Tool execution was cancelled',
    }));
  });
});
