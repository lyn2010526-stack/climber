import { useState, useEffect, useCallback } from 'react';
import { Bell, Send, CheckCircle, AlertCircle, Trash2, Inbox } from 'lucide-react';
import { api } from '../api';
import { Button, Card, Input } from '../components/ui';

interface NotificationItem {
  id?: string;
  title: string;
  message: string;
  created_at?: string;
}

export function NotificationsPage() {
  const [title, setTitle] = useState('Climber 通知测试');
  const [message, setMessage] = useState('这是一条测试通知');
  const [result, setResult] = useState<{ ok: boolean; error?: string } | null>(null);
  const [sending, setSending] = useState(false);
  const [items, setItems] = useState<NotificationItem[]>([]);

  const fetchHistory = useCallback(async () => {
    try {
      const data = await api.listNotifications(50);
      setItems(Array.isArray(data) ? data : data?.notifications || []);
    } catch { /* skip */ }
  }, []);

  useEffect(() => {
    fetchHistory();
  }, [fetchHistory]);

  const send = async () => {
    setSending(true);
    setResult(null);
    try {
      const data = await api.sendNotification(title, message);
      setResult(data);
      fetchHistory();
    } catch (e: any) {
      setResult({ ok: false, error: e.message });
    } finally {
      setSending(false);
    }
  };

  const test = async () => {
    setSending(true);
    setResult(null);
    try {
      const data = await api.testNotification();
      setResult(data);
      fetchHistory();
    } catch (e: any) {
      setResult({ ok: false, error: e.message });
    } finally {
      setSending(false);
    }
  };

  const clearAll = async () => {
    try {
      await api.clearNotifications();
      setItems([]);
    } catch { /* skip */ }
  };

  const formatTime = (ts?: string) => {
    if (!ts) return '';
    try {
      return new Date(ts).toLocaleString();
    } catch {
      return '';
    }
  };

  return (
    <div className="h-full overflow-y-auto p-8">
      <div className="max-w-3xl mx-auto">
        <div className="mb-8">
          <h2 className="text-2xl font-bold text-[var(--color-text-primary)] flex items-center gap-3">
            <Bell size={24} className="text-[var(--color-accent)]" />
            通知中心
          </h2>
          <p className="text-[var(--color-text-secondary)] text-sm mt-1.5">
            测试桌面通知，任务完成或出错时会自动弹出提醒。
          </p>
        </div>

        <div className="space-y-6">
          <Card className="rounded-3xl p-6" padding="none">
            <h3 className="text-sm font-semibold text-[var(--color-text-primary)] mb-4">发送自定义通知</h3>
            <div className="space-y-4">
              <div>
                <label className="block text-xs text-[var(--color-text-muted)] mb-1.5">标题</label>
                <Input
                  type="text"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  className="rounded-2xl px-4 py-2.5"
                />
              </div>
              <div>
                <label className="block text-xs text-[var(--color-text-muted)] mb-1.5">内容</label>
                <textarea
                  value={message}
                  onChange={(e) => setMessage(e.target.value)}
                  rows={3}
                  className="w-full px-4 py-2.5 bg-[var(--color-bg-surface-2)] border border-[var(--color-border-subtle)] rounded-2xl text-sm text-[var(--color-text-primary)] focus:outline-none focus:border-[var(--color-accent)]/50 resize-none transition-all duration-200"
                />
              </div>
              <div className="flex gap-3">
                <Button
                  onClick={send}
                  disabled={sending || !title.trim() || !message.trim()}
                  size="lg"
                  className="rounded-2xl"
                >
                  <Send size={14} />
                  发送通知
                </Button>
                <Button
                  onClick={test}
                  disabled={sending}
                  variant="secondary"
                  size="lg"
                  className="rounded-2xl bg-white/[0.03] text-[var(--color-text-secondary)]"
                >
                  <Bell size={14} />
                  系统测试
                </Button>
              </div>
            </div>
          </Card>

          {result && (
            <div className={`rounded-2xl p-4 flex items-center gap-3 border ${result.ok ? 'bg-[var(--color-success)]/10 border-[var(--color-success)]/30' : 'bg-[var(--color-error)]/10 border-[var(--color-error)]/30'}`}>
              {result.ok ? (
                <CheckCircle size={18} className="text-[var(--color-success)] shrink-0" />
              ) : (
                <AlertCircle size={18} className="text-[var(--color-error)] shrink-0" />
              )}
              <p className={`text-sm ${result.ok ? 'text-[var(--color-success)]' : 'text-[var(--color-error)]'}`}>
                {result.ok ? '通知已发送' : `发送失败: ${result.error || '未知错误'}`}
              </p>
            </div>
          )}

          <Card className="rounded-3xl p-6" padding="none">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-semibold text-[var(--color-text-primary)]">通知历史</h3>
              {items.length > 0 && (
                <Button
                  onClick={clearAll}
                  variant="outline"
                  size="sm"
                  className="rounded-xl text-xs text-[var(--color-text-muted)] hover:text-[var(--color-error)]"
                >
                  <Trash2 size={12} />
                  清空
                </Button>
              )}
            </div>
            {items.length === 0 ? (
              <div className="py-10 flex flex-col items-center gap-2 text-[var(--color-text-muted)]">
                <Inbox size={24} />
                <span className="text-sm">暂无通知记录</span>
              </div>
            ) : (
              <ul className="space-y-2">
                {items.map((n, i) => (
                  <li key={n.id || i} className="p-3 bg-white/[0.03] border border-[var(--color-border-subtle)] rounded-2xl">
                    <div className="flex items-center justify-between gap-3">
                      <span className="text-sm font-medium text-[var(--color-text-primary)] truncate">{n.title}</span>
                      <span className="text-[10px] text-[var(--color-text-muted)] shrink-0">{formatTime(n.created_at)}</span>
                    </div>
                    <p className="text-xs text-[var(--color-text-muted)] mt-1">{n.message}</p>
                  </li>
                ))}
              </ul>
            )}
          </Card>

          <Card className="rounded-3xl p-6" padding="none">
            <h3 className="text-sm font-semibold text-[var(--color-text-primary)] mb-3">通知说明</h3>
            <ul className="text-xs text-[var(--color-text-muted)] space-y-2 list-disc list-inside">
              <li>通知通过系统原生机制发送（Linux notify-send / macOS osascript / Windows PowerShell）</li>
              <li>如果系统不支持桌面通知，会自动跳过，不会影响应用运行</li>
              <li>任务完成、失败或需要审批时，系统会自动触发通知</li>
              <li>通知服务在后台运行，不占用前端资源</li>
            </ul>
          </Card>
        </div>
      </div>
    </div>
  );
}
