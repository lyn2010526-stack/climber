import TaskMonitorPage from '../TaskMonitorPage';

export function MobileTasksPage() {
  return (
    <div className="mobile-page-container">
      <div className="px-4 py-4">
        <div className="mb-4">
          <h2 className="text-lg font-bold" style={{ color: 'var(--color-text-primary)' }}>
            任务监控
          </h2>
          <p className="text-xs mt-1" style={{ color: 'var(--color-text-muted)' }}>
            查看和管理你的自主执行任务
          </p>
        </div>
      </div>
      <div className="px-4">
        <TaskMonitorPage />
      </div>
    </div>
  );
}
