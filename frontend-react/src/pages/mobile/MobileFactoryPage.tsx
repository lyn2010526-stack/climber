import { FactoryModePage } from '../FactoryModePage';

export function MobileFactoryPage() {
  return (
    <div className="mobile-page-container">
      <div className="px-4 py-4">
        <div className="mb-4">
          <h2 className="text-lg font-bold" style={{ color: 'var(--color-text-primary)' }}>
            自主执行
          </h2>
          <p className="text-xs mt-1" style={{ color: 'var(--color-text-muted)' }}>
            让 AI 自主完成复杂任务
          </p>
        </div>
      </div>
      <div className="px-4">
        <FactoryModePage />
      </div>
    </div>
  );
}
