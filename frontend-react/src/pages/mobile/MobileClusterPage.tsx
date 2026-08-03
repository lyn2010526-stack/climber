import { ClusterPage } from '../ClusterPage';

export function MobileClusterPage() {
  return (
    <div className="mobile-page-container">
      <div className="px-4 py-4">
        <div className="mb-4">
          <h2 className="text-lg font-bold" style={{ color: 'var(--color-text-primary)' }}>
            集群协作
          </h2>
          <p className="text-xs mt-1" style={{ color: 'var(--color-text-muted)' }}>
            多智能体集群协作管理
          </p>
        </div>
      </div>
      <div className="px-4">
        <ClusterPage />
      </div>
    </div>
  );
}
