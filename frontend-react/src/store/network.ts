import { create } from 'zustand';
import { devtools } from 'zustand/middleware';

interface NetworkState {
  online: boolean;
  webSocketConnected: boolean;
  webSocketError: string | null;

  setOnline: (online: boolean) => void;
  setWebSocketConnected: (connected: boolean) => void;
  setWebSocketError: (error: string | null) => void;
}

export const useNetworkStore = create<NetworkState>()(
  devtools(
    (set) => ({
      online: typeof navigator !== 'undefined' ? navigator.onLine : true,
      webSocketConnected: false,
      webSocketError: null,

      setOnline: (online) => set({ online }),
      setWebSocketConnected: (connected) => set({ webSocketConnected: connected }),
      setWebSocketError: (error) => set({ webSocketError: error }),
    }),
    { name: 'NetworkStore' }
  )
);
