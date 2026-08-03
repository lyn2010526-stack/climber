import { useEffect, useState } from 'react';
import { WifiOff } from 'lucide-react';

export function NetworkStatus() {
  const [online, setOnline] = useState(navigator.onLine);

  useEffect(() => {
    const handleOnline = () => setOnline(true);
    const handleOffline = () => setOnline(false);
    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);
    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);

  if (online) return null;

  return (
    <div className="fixed top-0 left-0 right-0 z-50 bg-amber-500/90 backdrop-blur-sm text-black px-4 py-2 flex items-center justify-center gap-2 text-xs font-medium">
      <WifiOff size={14} />
      <span>网络连接已断开。部分功能可能不可用。</span>
    </div>
  );
}

export function useNetworkStatus() {
  const [online, setOnline] = useState(navigator.onLine);

  useEffect(() => {
    const handleOnline = () => setOnline(true);
    const handleOffline = () => setOnline(false);
    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);
    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);

  return { online, isOffline: !online };
}

export function OfflineIndicator() {
  const { isOffline } = useNetworkStatus();

  if (!isOffline) return null;

  return (
    <div className="flex items-center gap-1.5 px-2 py-1 bg-amber-500/10 text-amber-400 rounded-lg text-[10px] font-medium border border-amber-500/20">
      <WifiOff size={10} />
      离线
    </div>
  );
}
