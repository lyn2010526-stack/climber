import { useState, useEffect, useCallback } from 'react';
import { Bell, Send, CheckCircle, AlertCircle, Trash2, Inbox } from 'lucide-react';
import { api } from '../../api';

interface NotificationItem {
  id?: string;
  title: string;
  message: string;
  created_at?: string;
}

export function MobileNotificationsPage() {
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
    <div className="mobile-page-container">
      <div className="px-4 py-4">
        <div className="mb-4">
          <h2 className="text-lg font-bold flex items-center gap-2" style={{ color: 'var(--color-text-primary)' }}>
            <Bell size={18} className="text-[var(--color-accent)]" />
            通知中心
          </h2>
          <p className="text-xs mt-1" style={{ color: 'var(--color-text-muted)' }}>
            测试桌面通知，任务完成或出错时会自动弹出提醒
          </p>
        </div>

        <div className="bg-[var(--color-bg-surface-1)] border border-[var(--color-border-subtle)] rounded-2xl p-4 mb-3">
          <h3 className="text-sm font-semibold text-[var(--color-text-primary)] mb-3">发送自定义通知</h3>
          <div className="space-y-3">
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="标题"
              className="w-full px-3 py-2.5 bg-[var(--color-bg-surface-2)] border border-[var(--color-border-subtle)] rounded-2xl text-sm text-[var(--color-text-primary)] placeholder:text-[var(--color-text-muted)] focus:outline-none focus:border-[var(--color-accent)]/50 transition-all duration-200"
            />
            <textarea
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              rows={2}
              placeholder="内容"
              className="w-full px-3 py-2.5 bg-[var(--color-bg-surface-2)] border border-[var(--color-border-subtle)] rounded-2xl text-sm text-[var(--color-text-primary)] placeholder:text-[var(--color-text-muted)] focus:outline-none focus:border-[var(--color-accent)]/50 resize-none transition-all duration-200"
            />
            <div className="flex gap-2">
              <button
                onClick={send}
                disabled={sending || !title.trim() || !message.trim()}
                className="flex items-center justify-center gap-1.5 flex-1 py-2.5 bg-[var(--color-accent)] text-white rounded-2xl text-sm font-semibold hover:bg-[var(--color-accent-hover)] disabled:opacity-50 transition-all duration-200 active:scale-[0.97]"
              >
                <Send size={14} />
                发送
              </button>
              <button
                onClick={test}
                disabled={sending}
                className="flex items-center justify-center gap-1.5 flex-1 py-2.5 bg-[var(--color-bg-surface-2)] border border-[var(--color-border-subtle)] text-[var(--color-text-secondary)] rounded-2xl text-sm font-semibold hover:bg-[var(--color-bg-surface-3)] disabled:opacity-50 transition-all duration-200"
              >
                <Bell size={14} />
                系统测试
              </button>
            </div>
          </div>
        </div>

        {result && (
          <div className={`rounded-2xl p-3 flex items-center gap-2.5 border mb-3 ${result.ok ? 'bg-[var(--color-success)]/10 border-[var(--color-success)]/30' : 'bg-[var(--color-error)]/10 border-[var(--color-error)]/30'}`}>
            {result.ok ? (
              <CheckCircle size={16} className="text-[var(--color-success)] shrink-0" />
            ) : (
              <AlertCircle size={16} className="text-[var(--color-error)] shrink-0" />
            )}
            <p className={`text-xs ${result.ok ? 'text-[var(--color-success)]' : 'text-[var(--color-error)]'}`}>
              {result.ok ? '通知已发送' : `发送失败: ${result.error || '未知错误'}`}
            </p>
          </div>
        )}

        <div className="bg-[var(--color-bg-surface-1)] border border-[var(--color-border-subtle)] rounded-2xl p-4">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-semibold text-[var(--color-text-primary)]">通知历史</h3>
            {items.length > 0 && (
              <button
                onClick={clearAll}
                className="flex items-center gap-1 px-2.5 py-1.5 text-[11px] text-[var(--color-text-muted)] hover:text-[var(--color-error)] border border-[var(--color-border-subtle)] rounded-xl transition-colors"
              >
                <Trash2 size={12} />
                清空
              </button>
            )}
          </div>
          {items.length === 0 ? (
            <div className="py-8 flex flex-col items-center gap-2 text-[var(--color-text-muted)]">
              <Inbox size={22} />
              <span className="text-xs">暂无通知记录</span>
            </div>
          ) : (
            <ul className="space-y-2">
              {items.map((n, i) => (
                <li key={n.id || i} className="p-3 bg-[var(--color-bg-surface-2)] border border-[var(--color-border-subtle)] rounded-xl">
                  <div className="flex items-center justify-between gap-3">
                    <span className="text-xs font-medium text-[var(--color-text-primary)] truncate">{n.title}</span>
                    <span className="text-[10px] text-[var(--color-text-muted)] shrink-0">{formatTime(n.created_at)}</span>
                  </div>
                  <p className="text-[11px] text-[var(--color-text-muted)] mt-1 leading-snug">{n.message}</p>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}
