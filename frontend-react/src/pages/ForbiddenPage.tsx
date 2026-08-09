import { ArrowLeft, Home, ShieldAlert } from 'lucide-react';
import { useCurrentPage } from '../store/page';

export function ForbiddenPage() {
  const setPage = useCurrentPage((state) => state.setPage);

  const goHome = () => {
    setPage('chat');
    window.location.hash = 'chat';
  };

  return (
    <main className="flex min-h-screen items-center justify-center bg-[var(--color-bg-page)] p-6 text-center">
      <div className="max-w-md">
        <ShieldAlert className="mx-auto text-[var(--color-error)]" size={56} />
        <h1 className="mt-4 text-2xl font-semibold text-[var(--color-text-primary)]">访问被拒绝</h1>
        <p className="mt-2 text-sm text-[var(--color-text-muted)]">您没有权限访问此页面，请联系管理员获取相应权限</p>
        <div className="mt-8 flex justify-center gap-3">
          <button className="inline-flex items-center gap-2 rounded-xl px-4 py-2" onClick={goHome}>
            <Home size={16} />返回首页
          </button>
          <button className="inline-flex items-center gap-2 rounded-xl px-4 py-2" onClick={() => history.back()}>
            <ArrowLeft size={16} />返回上页
          </button>
        </div>
      </div>
    </main>
  );
}
