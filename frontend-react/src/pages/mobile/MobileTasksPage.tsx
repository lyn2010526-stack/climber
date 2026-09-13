import { lazy, Suspense } from 'react';

const TaskMonitorPage = lazy(() => import('../TaskMonitorPage'));

export function MobileTasksPage() {
  return (
    <div className="mobile-page-container mobile-touch-feedback">
      <div className="px-4 mobile-content-shift-fix">
        <Suspense fallback={null}>
          <TaskMonitorPage />
        </Suspense>
      </div>
    </div>
  );
}
