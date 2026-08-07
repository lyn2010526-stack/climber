import { ShieldX, Home, ArrowLeft } from 'lucide-react';
import { useCurrentPage } from '../store/page';

export function ForbiddenPage() {
  const setPage = useCurrentPage((s) => s.setPage);

  const navigate = (page: string) => {
    setPage(page as any);
    window.location.hash = page;
  };

  return (
    <div className="flex-1 flex items-center justify-center">
      <div className="flex flex-col items-center gap-8 p-8 text-center max-w-md">
        <div className="relative">
          <div
            className="w-28 h-28 rounded-4xl flex items-center justify-center"
            style={{
              backgroundColor: 'var(--color-error-subtle)',
              border: '1px solid rgba(239, 68, 68, 0.2)',
            }}
          >
            <ShieldX size={48} style={{ color: 'var(--color-error)' }} />
          </div>
        </div>

        <div>
          <h1 className="text-2xl font-bold mb-3" style={{ color: 'var(--color-text-primary)' }}>
            访问被拒绝
          </h1>
          <p className="text-sm leading-relaxed" style={{ color: 'var(--color-text-secondary)' }}>
            您没有权限访问此页面，请联系管理员获取相应权限
          </p>
        </div>

        <div className="flex flex-col sm:flex-row gap-3 w-full sm:w-auto">
          <button
            onClick={() => navigate('chat')}
            className="inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-2xl text-sm font-semibold transition-all duration-200 active:scale-[0.97]"
            style={{
              backgroundColor: 'var(--color-accent)',
              color: 'white',
              boxShadow: '0 4px 12px var(--color-accent-glow)',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.backgroundColor = 'var(--color-accent-hover)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.backgroundColor = 'var(--color-accent)';
            }}
          >
            <Home size={14} />
            返回首页
          </button>
          <button
            onClick={() => window.history.back()}
            className="inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-2xl text-sm font-medium transition-all duration-200 active:scale-[0.97]"
            style={{
              backgroundColor: 'var(--color-bg-surface-2)',
              color: 'var(--color-text-secondary)',
              border: '1px solid var(--color-border-subtle)',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.backgroundColor = 'var(--color-bg-surface-3)';
              e.currentTarget.style.borderColor = 'var(--color-border-default)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.backgroundColor = 'var(--color-bg-surface-2)';
              e.currentTarget.style.borderColor = 'var(--color-border-subtle)';
            }}
          >
            <ArrowLeft size={14} />
            返回上页
          </button>
        </div>
      </div>
    </div>
  );
}
