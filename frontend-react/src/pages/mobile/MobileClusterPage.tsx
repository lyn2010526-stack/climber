import { lazy, Suspense } from 'react';

const ClusterPage = lazy(() => import('../ClusterPage').then(m => ({ default: m.ClusterPage })));

export function MobileClusterPage() {
  return (
    <div className="mobile-page-container mobile-touch-feedback">
      <div className="px-4 mobile-content-shift-fix">
        <Suspense fallback={null}>
          <ClusterPage />
        </Suspense>
      </div>
    </div>
  );
}
