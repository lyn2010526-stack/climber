import { useCallback, lazy, Suspense } from 'react';

const FactoryModePage = lazy(() => import('../FactoryModePage').then(m => ({ default: m.FactoryModePage })));

export function MobileFactoryPage() {
  const handleRefresh = useCallback(async () => {
    // Implement pull-to-refresh functionality here
  }, []);

  return (
    <div className="mobile-page-container mobile-touch-feedback">
      <div className="px-4 py-4 safe-area-top">
        <div className="mb-4">
          <h2 className="text-lg font-bold" style={{ color: 'var(--color-text-primary)' }}>
            自主执行
          </h2>
          <p className="text-xs mt-1" style={{ color: 'var(--color-text-muted)' }}>
            让 AI 自主完成复杂任务
          </p>
        </div>
      </div>
      <div className="px-4 mobile-content-shift-fix">
        <Suspense fallback={null}>
          <FactoryModePage />
        </Suspense>
      </div>
    </div>
  );
}
