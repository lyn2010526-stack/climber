import { useEffect, useRef, useState, useCallback } from 'react';

export interface CollabEvent {
  type: string;
  session_id: string;
  member_id?: string;
  member_name?: string;
  data?: Record<string, unknown>;
  timestamp?: string;
}

interface UseCollaborationWebSocketOptions {
  sessionId: string;
  token?: string;
  onEvent?: (event: CollabEvent) => void;
  onConnect?: () => void;
  onDisconnect?: () => void;
  autoReconnect?: boolean;
}

export function useCollaborationWebSocket({
  sessionId,
  token,
  onEvent,
  onConnect,
  onDisconnect,
  autoReconnect = true,
}: UseCollaborationWebSocketOptions) {
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const shouldReconnectRef = useRef(autoReconnect);

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/api/v1/ws/collab/${sessionId}?token=${token || ''}`;

    try {
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        setConnected(true);
        setError(null);
        onConnect?.();
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === 'ping') {
            ws.send(JSON.stringify({ action: 'ping' }));
            return;
          }
          onEvent?.(data as CollabEvent);
        } catch {
          // ignore malformed messages
        }
      };

      ws.onclose = () => {
        setConnected(false);
        onDisconnect?.();
        if (shouldReconnectRef.current) {
          reconnectTimeoutRef.current = setTimeout(connect, 3000);
        }
      };

      ws.onerror = () => {
        setError('WebSocket connection error');
      };
    } catch (e) {
      setError('Failed to create WebSocket');
    }
  }, [sessionId, token, onEvent, onConnect, onDisconnect]);

  const disconnect = useCallback(() => {
    shouldReconnectRef.current = false;
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }
    wsRef.current?.close();
  }, []);

  const sendAction = useCallback((action: string, data?: Record<string, unknown>) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ action, ...data }));
    }
  }, []);

  const pause = useCallback(() => sendAction('pause'), [sendAction]);
  const resume = useCallback(() => sendAction('resume'), [sendAction]);
  const stop = useCallback(() => sendAction('stop'), [sendAction]);
  const getStatus = useCallback(() => sendAction('status'), [sendAction]);

  useEffect(() => {
    connect();
    return () => {
      shouldReconnectRef.current = false;
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      wsRef.current?.close();
    };
  }, [connect]);

  return {
    connected,
    error,
    pause,
    resume,
    stop,
    getStatus,
    disconnect,
    sendAction,
  };
}
