import { MobileBottomNav } from './MobileBottomNav';
import { Mountain } from 'lucide-react';

export function MobileLayout({ children, currentPage, onNavigate }: { 
  children: React.ReactNode; 
  currentPage: string; 
  onNavigate: (page: string) => void;
}) {
  return (
    <div className="mobile-layout">
      <header
        className="sticky top-0 z-40 safe-area-top"
        style={{
          backgroundColor: 'var(--color-glass-bg)',
          borderBottom: '1px solid var(--color-glass-border)',
          backdropFilter: 'blur(16px)',
          WebkitBackdropFilter: 'blur(16px)',
        }}
      >
        <div className="flex items-center justify-between px-4 h-12">
          <div className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-[var(--color-text-primary)] text-[var(--color-text-inverse)]">
              <Mountain size={16} strokeWidth={2.25} />
            </div>
            <h1
              className="text-sm font-semibold tracking-[-0.01em]"
              style={{ color: 'var(--color-text-primary)' }}
            >
              Climber
            </h1>
          </div>
        </div>
      </header>

      <main className="mobile-main flex-1 overflow-y-auto" style={{ overscrollBehavior: 'contain' }}>
        {children}
      </main>

      <MobileBottomNav currentPage={currentPage} onNavigate={onNavigate} />
    </div>
  );
}
