import { useState, useRef, useEffect, useCallback } from 'react';
import { MobileBottomNav } from './MobileBottomNav';
import { Sparkles } from 'lucide-react';

interface PullToRefreshProps {
  onRefresh: () => Promise<void>;
  isRefreshing: boolean;
  children: React.ReactNode;
}

function PullToRefresh({ onRefresh, isRefreshing, children }: PullToRefreshProps) {
  const [touchStart, setTouchStart] = useState<number | null>(null);
  const [touchEnd, setTouchEnd] = useState<number | null>(null);
  const [refreshOffset, setRefreshOffset] = useState(0);
  const minSwipeDistance = 50;
  const refreshThreshold = 80;
  const refreshRef = useRef<HTMLDivElement>(null);

  const onTouchStart = useCallback((e: React.TouchEvent) => {
    setTouchEnd(null);
    setTouchStart(e.targetTouches[0]?.clientY ?? 0);
    setRefreshOffset(0);
  }, []);

  const onTouchMove = useCallback((e: React.TouchEvent) => {
    if (touchStart === null) return;

    const currentY = e.targetTouches[0]?.clientY ?? 0;
    const distance = currentY - touchStart;

    const mainElement = e.currentTarget.closest('main');
    if (mainElement && mainElement.scrollTop > 0) return;

    if (distance > 0) {
      setRefreshOffset(Math.min(distance, refreshThreshold * 2));
    }
  }, [touchStart]);

  const onTouchEnd = useCallback(() => {
    setTouchStart(null);
    setTouchEnd(null);

    if (refreshOffset > refreshThreshold) {
      onRefresh();
    }
    setRefreshOffset(0);
  }, [refreshOffset, onRefresh]);

  return (
    <div className="relative">
      {isRefreshing && (
        <div
          ref={refreshRef}
          className="flex items-center justify-center py-3"
          style={{ transform: `translateY(${refreshOffset}px)` }}
        >
          <div
            className="w-5 h-5 border-2 rounded-full animate-spin"
            style={{ borderColor: 'var(--color-accent)', borderTopColor: 'transparent' }}
          />
        </div>
      )}
      <main
        className="mobile-main flex-1 overflow-y-auto"
        style={{ overscrollBehavior: 'contain' }}
        onTouchStart={onTouchStart}
        onTouchMove={onTouchMove}
        onTouchEnd={onTouchEnd}
      >
        {children}
      </main>
    </div>
  );
}

export function MobileLayout({ children, currentPage, onNavigate }: {
  children: React.ReactNode;
  currentPage: string;
  onNavigate: (page: string) => void;
}) {
  const [refreshing, setRefreshing] = useState(false);

  const handleRefresh = useCallback(async () => {
    setRefreshing(true);
    await new Promise(resolve => setTimeout(resolve, 1000));
    setRefreshing(false);
  }, []);

  return (
    <div className="mobile-layout" style={{ height: '100vh', display: 'flex', flexDirection: 'column' }}>
      <header
        className="sticky top-0 z-40 safe-area-top"
        style={{
          backgroundColor: 'var(--color-glass-bg)',
          borderBottom: '1px solid var(--color-glass-border)',
          backdropFilter: 'blur(24px) saturate(180%)',
          WebkitBackdropFilter: 'blur(24px) saturate(180%)',
        }}
      >
        <div className="flex items-center justify-between px-4 h-12">
          <div className="flex items-center gap-2">
            <div
              className="w-8 h-8 rounded-xl flex items-center justify-center"
              style={{
                background: 'linear-gradient(135deg, #5E6AD2, #6366F1)',
                boxShadow: '0 0 12px rgba(94, 106, 210, 0.3)',
              }}
            >
              <Sparkles size={16} className="text-white" />
            </div>
            <h1
              className="text-base font-semibold"
              style={{ color: 'var(--color-text-primary)' }}
            >
              Climber
            </h1>
          </div>
        </div>
      </header>

      <PullToRefresh onRefresh={handleRefresh} isRefreshing={refreshing}>
        {children}
      </PullToRefresh>

      <MobileBottomNav currentPage={currentPage} onNavigate={onNavigate} />
    </div>
  );
}
