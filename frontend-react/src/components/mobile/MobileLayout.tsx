import { MobileBottomNav } from './MobileBottomNav';
import { Sparkles } from 'lucide-react';

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
          backdropFilter: 'blur(24px) saturate(180%)',
          WebkitBackdropFilter: 'blur(24px) saturate(180%)',
        }}
      >
        <div className="flex items-center justify-between px-4 h-12">
          <div className="flex items-center gap-2">
            <div
              className="w-8 h-8 rounded-xl flex items-center justify-center"
              style={{
                backgroundColor: 'var(--color-accent)',
                boxShadow: '0 0 12px var(--color-accent-glow)',
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

      <main className="mobile-main flex-1 overflow-y-auto" style={{ overscrollBehavior: 'contain' }}>
        {children}
      </main>

      <MobileBottomNav currentPage={currentPage} onNavigate={onNavigate} />
    </div>
  );
}
