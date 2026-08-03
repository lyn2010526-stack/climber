import { useState } from 'react';
import { Bell, Send, CheckCircle, AlertCircle } from 'lucide-react';
import { api } from '../api';

export function NotificationsPage() {
  const [title, setTitle] = useState('Climber 通知测试');
  const [message, setMessage] = useState('这是一条测试通知');
  const [result, setResult] = useState<{ ok: boolean; error?: string } | null>(null);
  const [sending, setSending] = useState(false);

  const send = async () => {
    setSending(true);
    setResult(null);
    try {
      const data = await api.sendNotification(title, message);
      setResult(data);
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
    } catch (e: any) {
      setResult({ ok: false, error: e.message });
    } finally {
      setSending(false);
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
          <div className="bg-[var(--color-bg-surface-1)] border border-[var(--color-border-subtle)] rounded-3xl p-6">
            <h3 className="text-sm font-semibold text-[var(--color-text-primary)] mb-4">发送自定义通知</h3>
            <div className="space-y-4">
              <div>
                <label className="block text-xs text-[var(--color-text-muted)] mb-1.5">标题</label>
                <input
                  type="text"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  className="w-full px-4 py-2.5 bg-[var(--color-bg-surface-2)] border border-[var(--color-border-subtle)] rounded-2xl text-sm text-[var(--color-text-primary)] focus:outline-none focus:border-[var(--color-accent)]/50 transition-all duration-200"
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
                <button
                  onClick={send}
                  disabled={sending || !title.trim() || !message.trim()}
                  className="flex items-center gap-2 px-5 py-2.5 bg-[var(--color-accent)] text-white rounded-2xl text-sm font-semibold hover:bg-[var(--color-accent-hover)] disabled:opacity-50 transition-all duration-200 active:scale-[0.97]"
                >
                  <Send size={14} />
                  发送通知
                </button>
                <button
                  onClick={test}
                  disabled={sending}
                  className="flex items-center gap-2 px-5 py-2.5 bg-white/[0.03] border border-[var(--color-border-subtle)] text-[var(--color-text-secondary)] rounded-2xl text-sm font-semibold hover:bg-white/[0.06] disabled:opacity-50 transition-all duration-200"
                >
                  <Bell size={14} />
                  系统测试
                </button>
              </div>
            </div>
          </div>

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

          <div className="bg-[var(--color-bg-surface-1)] border border-[var(--color-border-subtle)] rounded-3xl p-6">
            <h3 className="text-sm font-semibold text-[var(--color-text-primary)] mb-3">通知说明</h3>
            <ul className="text-xs text-[var(--color-text-muted)] space-y-2 list-disc list-inside">
              <li>通知通过系统原生机制发送（Linux notify-send / macOS osascript / Windows PowerShell）</li>
              <li>如果系统不支持桌面通知，会自动跳过，不会影响应用运行</li>
              <li>任务完成、失败或需要审批时，系统会自动触发通知</li>
              <li>通知服务在后台运行，不占用前端资源</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}
