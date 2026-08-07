import { useEffect } from 'react';
import { useNetworkStore } from '../store/network';

export function useNetworkStatus() {
  const online = useNetworkStore((s) => s.online);
  const setOnline = useNetworkStore((s) => s.setOnline);

  useEffect(() => {
    const handleOnline = () => setOnline(true);
    const handleOffline = () => setOnline(false);
    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);
    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, [setOnline]);

  return { online, isOffline: !online };
}
