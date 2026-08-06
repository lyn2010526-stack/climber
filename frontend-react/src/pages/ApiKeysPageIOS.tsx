import { useState } from 'react';
import {
  IOSPage,
  IOSListGroup,
  IOSListItem,
  IOSCard,
  IOSFab,
  IOSConfirmDialog,
  toast,
} from '../components/ios';
import { Lock, KeyRound, Eye, EyeOff, Copy, Trash2, Plus } from 'lucide-react';
import { cn } from '../lib/utils';

interface ApiKey {
  id: number;
  name: string;
  masked: string;
  secret: string;
  createdAt: string;
}

const API_KEYS: ApiKey[] = [
  { id: 1, name: '主 API 密钥', masked: 'sk-••••4f2a', secret: 'sk-live-9d2e7b3c4f2a', createdAt: '2026-08-01' },
  { id: 2, name: '测试环境密钥', masked: 'sk-••••9c1d', secret: 'sk-test-5a8b2f1e9c1d', createdAt: '2026-07-20' },
  { id: 3, name: '生产只读密钥', masked: 'sk-••••7e3b', secret: 'sk-ro-3c6d9a4e7e3b', createdAt: '2026-07-05' },
  { id: 4, name: '数据管道密钥', masked: 'sk-••••2f88', secret: 'sk-pipe-8b1a5c3d2f88', createdAt: '2026-06-18' },
];

export default function ApiKeysPageIOS() {
  const [keys, setKeys] = useState<ApiKey[]>(API_KEYS);
  const [visibleIds, setVisibleIds] = useState<ReadonlySet<number>>(new Set());
  const [deleteTarget, setDeleteTarget] = useState<ApiKey | null>(null);

  const toggleVisible = (id: number) => {
    setVisibleIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  const handleCopy = async (key: ApiKey) => {
    try {
      await navigator.clipboard.writeText(key.secret);
      toast.success(`已复制 ${key.name}`);
    } catch {
      toast.error('复制失败，请重试');
    }
  };

  const handleDelete = () => {
    if (!deleteTarget) return;
    setKeys((prev) => prev.filter((item) => item.id !== deleteTarget.id));
    toast.success(`已删除 ${deleteTarget.name}`);
    setDeleteTarget(null);
  };

  return (
    <IOSPage className="pb-24">
      <div className="px-4 pt-6 space-y-5">
        <div>
          <h1 className="ios-title-1 text-[var(--color-text-primary)]">API 密钥</h1>
          <p className="ios-subhead text-[var(--color-text-muted)] mt-1">安全访问凭证</p>
        </div>

        <IOSCard>
          <div className="flex items-start gap-3 p-4" style={{ background: 'var(--color-warning-subtle)' }}>
            <Lock size={18} className="text-[var(--color-warning)] shrink-0 mt-0.5" />
            <div>
              <p className="ios-subhead text-[var(--color-text-primary)]">安全提示</p>
              <p className="ios-caption text-[var(--color-text-muted)] mt-1">
                API 密钥仅在创建时完整展示一次，请及时保存。切勿将密钥提交到代码仓库或分享给他人，泄露后请立即吊销。
              </p>
            </div>
          </div>
        </IOSCard>

        <IOSListGroup title="密钥管理">
          {keys.map((key) => (
            <IOSListItem
              key={key.id}
              icon={<KeyRound size={18} className="text-white" />}
              iconBg="#FF9500"
              title={key.name}
              showChevron={false}
              detail={
                <div className="flex flex-col items-end gap-1">
                  <span className="ios-footnote text-[var(--color-text-muted)]">
                    {visibleIds.has(key.id) ? key.secret : key.masked}
                  </span>
                  <span className="ios-footnote text-[var(--color-text-muted)]">创建于 {key.createdAt}</span>
                  <div className="flex items-center gap-3">
                    <button
                      type="button"
                      onClick={() => toggleVisible(key.id)}
                      className={cn(
                        'text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] transition-colors',
                        visibleIds.has(key.id) && 'text-[var(--color-accent)]'
                      )}
                      aria-label={visibleIds.has(key.id) ? '隐藏密钥' : '显示密钥'}
                    >
                      {visibleIds.has(key.id) ? <EyeOff size={16} /> : <Eye size={16} />}
                    </button>
                    <button
                      type="button"
                      onClick={() => handleCopy(key)}
                      className="text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] transition-colors"
                      aria-label="复制密钥"
                    >
                      <Copy size={16} />
                    </button>
                    <button
                      type="button"
                      onClick={() => setDeleteTarget(key)}
                      className="text-[var(--color-text-muted)] hover:text-[var(--color-error)] transition-colors"
                      aria-label="删除密钥"
                    >
                      <Trash2 size={16} />
                    </button>
                  </div>
                </div>
              }
            />
          ))}
        </IOSListGroup>

        <IOSCard>
          <button
            type="button"
            onClick={() => toast.info('创建密钥功能开发中')}
            className="flex w-full items-center justify-center gap-2 py-3.5 bg-[var(--color-accent)] text-white ios-headline active:opacity-80 transition-opacity"
          >
            <Plus size={18} />
            创建密钥
          </button>
        </IOSCard>
      </div>

      <IOSFab
        icon={<Plus size={20} />}
        label="创建密钥"
        onClick={() => toast.info('创建密钥功能开发中')}
      />

      <IOSConfirmDialog
        open={deleteTarget !== null}
        onOpenChange={(open) => {
          if (!open) setDeleteTarget(null);
        }}
        title="删除密钥"
        description={deleteTarget ? `确定要删除「${deleteTarget.name}」吗？使用该密钥的服务将立即失效。` : ''}
        onConfirm={handleDelete}
        confirmText="删除"
        danger
      />
    </IOSPage>
  );
}
