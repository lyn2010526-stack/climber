import { useState, useEffect } from 'react';
import { Plus, Trash2, Key } from 'lucide-react';
import { api } from '../api';
import { Button, Card, Dialog, DialogHeader, DialogTitle, DialogDescription, DialogFooter, EmptyState, Input, Select } from '../components/ui';

const PROVIDERS = ['openai', 'anthropic', 'google', 'ollama', 'stepfun'];

export function ApiKeysPage() {
  const [keys, setKeys] = useState<any[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ provider: 'openai', name: '', api_key: '', base_url: '' });
  const [pendingDelete, setPendingDelete] = useState<any | null>(null);


  useEffect(() => { loadKeys(); }, []);

  const loadKeys = () => {
    api.listApiKeys().then(setKeys).catch(() => {});
  };

  const addKey = async () => {
    await api.addApiKey(form);
    setShowForm(false);
    setForm({ provider: 'openai', name: '', api_key: '', base_url: '' });
    loadKeys();
  };

  const confirmDelete = async () => {
    if (!pendingDelete) return;
    await api.deleteApiKey(pendingDelete.id);
    setPendingDelete(null);
    loadKeys();
  };

  return (
    <div className="h-full overflow-y-auto p-8">
      <div className="max-w-4xl mx-auto">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h2 className="text-2xl font-bold text-[var(--color-text-primary)]">API 密钥</h2>
            <p className="text-[var(--color-text-secondary)] text-sm mt-1.5">管理模型提供商凭据</p>
          </div>
          <Button
            onClick={() => setShowForm(!showForm)}
            size="lg"
            className="rounded-2xl shadow-lg shadow-[var(--color-accent)]/20"
          >
             <Plus size={16} /> 添加密钥
          </Button>
        </div>

        {showForm && (
          <Card className="rounded-3xl p-6 mb-6" padding="none">
            <div className="grid grid-cols-2 gap-4">
              <Select
                value={form.provider}
                onChange={(v) => setForm({ ...form, provider: v })}
                options={PROVIDERS.map(p => ({ value: p, label: p }))}
                className="rounded-2xl"
              />
              <Input
                placeholder="名称（例如：个人 GPT-4）"
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                className="col-span-1 rounded-2xl px-4 py-2.5 placeholder:text-[var(--color-text-muted)]"
              />
              <Input
                placeholder="API 密钥"
                type="password"
                value={form.api_key}
                onChange={(e) => setForm({ ...form, api_key: e.target.value })}
                className="col-span-2 rounded-2xl px-4 py-2.5 placeholder:text-[var(--color-text-muted)]"
              />
              <Input
                placeholder="Base URL（可选，自托管时使用）"
                value={form.base_url}
                onChange={(e) => setForm({ ...form, base_url: e.target.value })}
                className="col-span-2 rounded-2xl px-4 py-2.5 placeholder:text-[var(--color-text-muted)]"
              />
            </div>
            <div className="flex justify-end mt-4">
              <Button
                onClick={addKey}
                disabled={!form.name || !form.api_key}
                size="lg"
                className="rounded-2xl shadow-lg shadow-[var(--color-accent)]/20 disabled:opacity-40"
              >
                 保存密钥
              </Button>
            </div>
          </Card>
        )}

        <div className="space-y-3">
          {keys.map(key => (
            <Card
              key={key.id}
              className="rounded-2xl p-5 flex items-center gap-4 hover:border-[var(--color-accent)]/30"
              padding="none"
            >
              <div className="w-10 h-10 rounded-2xl bg-[var(--color-warning)]/10 flex items-center justify-center border border-[var(--color-warning)]/20">
                <Key size={20} className="text-[var(--color-warning)]" />
              </div>
              <div className="flex-1">
                <h3 className="font-semibold text-[var(--color-text-primary)]">{key.name}</h3>
                <p className="text-sm text-[var(--color-text-muted)]">{key.provider}{key.base_url ? ` | ${key.base_url}` : ''}</p>
              </div>
              <Button
                variant="ghost"
                size="icon"
                onClick={() => setPendingDelete(key)}
                className="rounded-xl hover:bg-[var(--color-error)]/10 hover:text-[var(--color-error)]"
                aria-label="删除密钥"
              >
                <Trash2 size={16} />
              </Button>
            </Card>
          ))}
          {keys.length === 0 && (
            <EmptyState
              icon={Key}
              title="暂无 API 密钥"
              description="添加一个以连接到模型提供商。"
            />
          )}
        </div>
      </div>

      <Dialog open={!!pendingDelete} onClose={() => setPendingDelete(null)} size="sm">
        <DialogHeader>
          <DialogTitle>删除 API 密钥</DialogTitle>
          <DialogDescription>
            确定要删除「{pendingDelete?.name}」吗？此操作不可撤销。
          </DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <Button variant="secondary" onClick={() => setPendingDelete(null)}>取消</Button>
          <Button variant="destructive" onClick={confirmDelete}>删除</Button>
        </DialogFooter>
      </Dialog>
    </div>
  );
}
