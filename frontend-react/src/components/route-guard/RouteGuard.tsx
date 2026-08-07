import { useEffect } from 'react';
import { LogIn } from 'lucide-react';
import { useAuthStore } from '../../store/auth';
import { useCurrentPage } from '../../store/page';

interface RouteGuardProps {
  children: React.ReactNode;
  requireAuth?: boolean;
}

export function RouteGuard({ children, requireAuth = false }: RouteGuardProps) {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const setPage = useCurrentPage((s) => s.setPage);

  useEffect(() => {
    if (requireAuth && !isAuthenticated) {
      setPage('chat');
      window.location.hash = 'chat';
    }
  }, [requireAuth, isAuthenticated, setPage]);

  if (requireAuth && !isAuthenticated) {
    return <LoginRedirect />;
  }

  return <>{children}</>;
}

function LoginRedirect() {
  const setPage = useCurrentPage((s) => s.setPage);

  return (
    <div className="flex-1 flex items-center justify-center">
      <div className="flex flex-col items-center gap-6 p-8 text-center max-w-sm">
        <div
          className="w-20 h-20 rounded-3xl flex items-center justify-center"
          style={{
            backgroundColor: 'var(--color-accent-subtle)',
            border: '1px solid var(--color-border-accent)',
          }}
        >
          <LogIn size={36} style={{ color: 'var(--color-accent)' }} />
        </div>
        <div>
          <h2 className="text-xl font-semibold mb-2" style={{ color: 'var(--color-text-primary)' }}>
            需要登录
          </h2>
          <p className="text-sm leading-relaxed" style={{ color: 'var(--color-text-secondary)' }}>
            请先登录后再访问此页面
          </p>
        </div>
        <button
          onClick={() => {
            setPage('chat');
            window.location.hash = 'chat';
          }}
          className="inline-flex items-center gap-2 px-6 py-3 rounded-2xl text-sm font-semibold transition-all duration-200 active:scale-[0.97]"
          style={{
            backgroundColor: 'var(--color-accent)',
            color: 'white',
            boxShadow: '0 4px 16px var(--color-accent-glow)',
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.backgroundColor = 'var(--color-accent-hover)';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.backgroundColor = 'var(--color-accent)';
          }}
        >
          返回首页
        </button>
      </div>
    </div>
  );
}
