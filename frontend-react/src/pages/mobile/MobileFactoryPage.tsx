import { lazy, Suspense } from 'react';

const FactoryModePage = lazy(() => import('../FactoryModePage').then(m => ({ default: m.FactoryModePage })));

export function MobileFactoryPage() {
  return (
    <div className="mobile-page-container mobile-touch-feedback">
      <div className="px-4 mobile-content-shift-fix">
        <Suspense fallback={null}>
          <FactoryModePage />
        </Suspense>
      </div>
    </div>
  );
}
