import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useCollaborationWebSocket } from '../useCollaborationWebSocket';

class MockWebSocket {
  static OPEN = 1;
  static CLOSED = 3;
  static instances: MockWebSocket[] = [];
  url: string;
  readyState = 0;
  sent: string[] = [];
  onopen: (() => void) | null = null;
  onmessage: ((e: { data: string }) => void) | null = null;
  onclose: (() => void) | null = null;
  onerror: (() => void) | null = null;

  constructor(url: string) {
    this.url = url;
    MockWebSocket.instances.push(this);
  }

  send(data: string) {
    this.sent.push(data);
  }

  close() {
    this.readyState = MockWebSocket.CLOSED;
    this.onclose?.();
  }
}

describe('useCollaborationWebSocket', () => {
  beforeEach(() => {
    MockWebSocket.instances = [];
    (globalThis as any).WebSocket = MockWebSocket;
  });

  const lastSocket = () => MockWebSocket.instances[MockWebSocket.instances.length - 1];

  it('connects on mount and reports connected state', () => {
    const { result } = renderHook(() => useCollaborationWebSocket({ sessionId: 's1' }));
    const ws = lastSocket();
    expect(ws).toBeDefined();
    expect(result.current.connected).toBe(false);
    act(() => ws.onopen?.());
    expect(result.current.connected).toBe(true);
  });

  it('calls onConnect when the socket opens', () => {
    const onConnect = vi.fn();
    renderHook(() => useCollaborationWebSocket({ sessionId: 's1', onConnect }));
    const ws = lastSocket();
    act(() => ws.onopen?.());
    expect(onConnect).toHaveBeenCalled();
  });

  it('invokes onEvent when a message arrives', () => {
    const onEvent = vi.fn();
    renderHook(() => useCollaborationWebSocket({ sessionId: 's1', onEvent }));
    const ws = lastSocket();
    const payload = { type: 'update', session_id: 's1', data: { cursor: 3 } };
    act(() => ws.onmessage?.({ data: JSON.stringify(payload) }));
    expect(onEvent).toHaveBeenCalledWith(payload);
  });

  it('responds to ping messages', () => {
    renderHook(() => useCollaborationWebSocket({ sessionId: 's1' }));
    const ws = lastSocket();
    act(() => ws.onmessage?.({ data: JSON.stringify({ type: 'ping' }) }));
    expect(ws.sent).toContain(JSON.stringify({ action: 'ping' }));
  });

  it('sets an error when the socket errors', () => {
    const { result } = renderHook(() => useCollaborationWebSocket({ sessionId: 's1' }));
    const ws = lastSocket();
    act(() => ws.onerror?.());
    expect(result.current.error).toBe('WebSocket connection error');
  });

  it('sendAction sends JSON when the socket is open', () => {
    const { result } = renderHook(() => useCollaborationWebSocket({ sessionId: 's1' }));
    const ws = lastSocket();
    ws.readyState = MockWebSocket.OPEN;
    act(() => result.current.sendAction('pause', { extra: 1 }));
    expect(ws.sent).toContain(JSON.stringify({ action: 'pause', extra: 1 }));
  });

  it('pause and resume helpers send actions', () => {
    const { result } = renderHook(() => useCollaborationWebSocket({ sessionId: 's1' }));
    const ws = lastSocket();
    ws.readyState = MockWebSocket.OPEN;
    act(() => result.current.pause());
    act(() => result.current.resume());
    expect(ws.sent).toEqual([JSON.stringify({ action: 'pause' }), JSON.stringify({ action: 'resume' })]);
  });

  it('disconnect closes the socket', () => {
    const { result } = renderHook(() => useCollaborationWebSocket({ sessionId: 's1' }));
    const ws = lastSocket();
    const closeSpy = vi.spyOn(ws, 'close');
    act(() => result.current.disconnect());
    expect(closeSpy).toHaveBeenCalled();
  });
});
