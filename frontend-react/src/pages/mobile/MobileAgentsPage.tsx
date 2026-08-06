import { useCallback, lazy, Suspense } from 'react';

const AgentsPage = lazy(() => import('../AgentsPage').then(m => ({ default: m.AgentsPage })));

export function MobileAgentsPage() {
  const handleRefresh = useCallback(async () => {
    // Implement pull-to-refresh functionality here
  }, []);

  return (
    <div className="mobile-page-container mobile-touch-feedback">
      <div className="px-4 py-4 safe-area-top">
        <div className="mb-4">
          <h2 className="text-lg font-bold" style={{ color: 'var(--color-text-primary)' }}>
            智能体
          </h2>
          <p className="text-xs mt-1" style={{ color: 'var(--color-text-muted)' }}>
            创建和管理自定义 AI 智能体
          </p>
        </div>
      </div>
      <div className="px-4 mobile-content-shift-fix">
        <Suspense fallback={null}>
          <AgentsPage />
        </Suspense>
      </div>
    </div>
  );
}
