import { describe, it, expect } from 'vitest';
import { useNetworkStore } from '../network';

describe('useNetworkStore', () => {
  it('has initial online state', () => {
    const state = useNetworkStore.getState();
    expect(typeof state.online).toBe('boolean');
  });

  it('has initial webSocketConnected as false', () => {
    const state = useNetworkStore.getState();
    expect(state.webSocketConnected).toBe(false);
  });

  it('has initial webSocketError as null', () => {
    const state = useNetworkStore.getState();
    expect(state.webSocketError).toBeNull();
  });

  it('setOnline updates online state', () => {
    useNetworkStore.getState().setOnline(false);
    expect(useNetworkStore.getState().online).toBe(false);
    useNetworkStore.getState().setOnline(true);
    expect(useNetworkStore.getState().online).toBe(true);
  });

  it('setWebSocketConnected updates connection state', () => {
    useNetworkStore.getState().setWebSocketConnected(true);
    expect(useNetworkStore.getState().webSocketConnected).toBe(true);
    useNetworkStore.getState().setWebSocketConnected(false);
    expect(useNetworkStore.getState().webSocketConnected).toBe(false);
  });

  it('setWebSocketError updates error state', () => {
    useNetworkStore.getState().setWebSocketError('Connection failed');
    expect(useNetworkStore.getState().webSocketError).toBe('Connection failed');
    useNetworkStore.getState().setWebSocketError(null);
    expect(useNetworkStore.getState().webSocketError).toBeNull();
  });
});
