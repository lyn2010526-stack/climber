import { AgentsPage } from '../AgentsPage';

export function MobileAgentsPage() {
  return (
    <div className="mobile-page-container">
      <div className="px-4 py-4">
        <div className="mb-4">
          <h2 className="text-lg font-bold" style={{ color: 'var(--color-text-primary)' }}>
            智能体
          </h2>
          <p className="text-xs mt-1" style={{ color: 'var(--color-text-muted)' }}>
            创建和管理自定义 AI 智能体
          </p>
        </div>
      </div>
      <div className="px-4">
        <AgentsPage />
      </div>
    </div>
  );
}
