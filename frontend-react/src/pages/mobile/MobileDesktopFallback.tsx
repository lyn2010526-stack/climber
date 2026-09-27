import { MessageSquare } from 'lucide-react';

interface MobileDesktopFallbackProps {
  title: string;
  description: string;
}

export function MobileDesktopFallback({ title, description }: MobileDesktopFallbackProps) {
  return (
    <section className="mobile-page-container mobile-fallback" aria-labelledby="mobile-fallback-title">
      <div className="mobile-fallback-card">
        <div className="mobile-fallback-icon" aria-hidden="true"><MessageSquare size={22} /></div>
        <h2 id="mobile-fallback-title" className="text-lg font-semibold text-[var(--color-text-primary)]">{title}</h2>
        <p className="mt-2 text-sm leading-6 text-[var(--color-text-secondary)]">{description}</p>
        <p className="mt-4 text-xs leading-5 text-[var(--color-text-muted)]">使用底部导航打开聊天，或点击“更多”访问可用的移动端入口。</p>
      </div>
    </section>
  );
}
