import { ArrowLeft, Home } from 'lucide-react';

export function NotFoundPage() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-[var(--color-bg-page)] p-6 text-center">
      <div className="max-w-md">
        <p className="text-7xl font-bold text-[var(--color-accent)]">404</p>
        <h1 className="mt-4 text-2xl font-semibold text-[var(--color-text-primary)]">页面未找到</h1>
        <p className="mt-2 text-sm text-[var(--color-text-muted)]">您访问的页面不存在或已被移除</p>
        <div className="mt-8 flex justify-center gap-3">
          <button className="inline-flex items-center gap-2 rounded-xl px-4 py-2" onClick={() => { window.location.hash = 'chat'; }}>
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
