import { useCallback, lazy, Suspense } from 'react';

const TaskMonitorPage = lazy(() => import('../TaskMonitorPage'));

export function MobileTasksPage() {
  const handleRefresh = useCallback(async () => {
    // Implement pull-to-refresh functionality here
  }, []);

  return (
    <div className="mobile-page-container mobile-touch-feedback">
      <div className="px-4 py-4 safe-area-top">
        <div className="mb-4">
          <h2 className="text-lg font-bold" style={{ color: 'var(--color-text-primary)' }}>
            任务监控
          </h2>
          <p className="text-xs mt-1" style={{ color: 'var(--color-text-muted)' }}>
            查看和管理你的自主执行任务
          </p>
        </div>
      </div>
      <div className="px-4 mobile-content-shift-fix">
        <Suspense fallback={null}>
          <TaskMonitorPage />
        </Suspense>
      </div>
    </div>
  );
}
