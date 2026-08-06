import { IOSPage } from '../components/ios';
import { ShieldX, ArrowLeft } from 'lucide-react';
import { useCurrentPage } from '../store/page';

export default function ForbiddenPageIOS() {
  const setPage = useCurrentPage((s) => s.setPage);

  const goBack = () => {
    setPage('chat');
    window.location.hash = 'chat';
  };

  return (
    <IOSPage className="h-full flex flex-col items-center justify-center px-6">
      <div className="flex flex-col items-center gap-6 text-center">
        <div className="w-24 h-24 rounded-3xl flex items-center justify-center bg-[var(--color-accent-subtle)]">
          <ShieldX size={48} className="text-[var(--color-accent)]" />
        </div>
        <div>
          <h1 className="ios-title-2 text-[var(--color-text-primary)]">访问受限</h1>
          <p className="ios-body text-[var(--color-text-muted)] mt-2 max-w-xs">
            您没有权限访问此页面，请返回后联系管理员获取相应权限
          </p>
        </div>
        <button
          type="button"
          onClick={goBack}
          className="inline-flex items-center gap-2 px-6 py-3 rounded-full bg-[var(--color-accent)] text-white ios-headline active:opacity-80 transition-opacity"
        >
          <ArrowLeft size={16} />
          返回
        </button>
      </div>
      <p className="ios-footnote text-[var(--color-text-muted)] absolute bottom-8">
        需要管理员权限，请联系管理员
      </p>
    </IOSPage>
  );
}
