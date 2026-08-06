import { useCallback, lazy, Suspense } from 'react';

const ClusterPage = lazy(() => import('../ClusterPage').then(m => ({ default: m.ClusterPage })));

export function MobileClusterPage() {
  const handleRefresh = useCallback(async () => {
    // Implement pull-to-refresh functionality here
  }, []);

  return (
    <div className="mobile-page-container mobile-touch-feedback">
      <div className="px-4 py-4 safe-area-top">
        <div className="mb-4">
          <h2 className="text-lg font-bold" style={{ color: 'var(--color-text-primary)' }}>
            集群协作
          </h2>
          <p className="text-xs mt-1" style={{ color: 'var(--color-text-muted)' }}>
            多智能体集群协作管理
          </p>
        </div>
      </div>
      <div className="px-4 mobile-content-shift-fix">
        <Suspense fallback={null}>
          <ClusterPage />
        </Suspense>
      </div>
    </div>
  );
}
