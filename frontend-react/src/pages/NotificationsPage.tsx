import { useState } from 'react';
import { Bell, Send, CheckCircle, AlertCircle, BellRing } from 'lucide-react';
import { api } from '../api';
import { PageHeader } from '../components/ui/PageHeader';
import { Card, CardContent } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';

export function NotificationsPage() {
  const [title, setTitle] = useState('Climber 通知测试');
  const [message, setMessage] = useState('这是一条测试通知');
  const [result, setResult] = useState<{ ok: boolean; error?: string } | null>(null);
  const [sending, setSending] = useState(false);

  const send = async () => {
    if (sending || !title.trim() || !message.trim()) return;
    setSending(true);
    setResult(null);
    try {
      const data = await api.sendNotification(title, message);
      setResult(data);
    } catch (e) {
      setResult({ ok: false, error: e instanceof Error ? e.message : '发送失败' });
    } finally {
      setSending(false);
    }
  };

  const test = async () => {
    if (sending) return;
    setSending(true);
    setResult(null);
    try {
      const data = await api.testNotification();
      setResult(data);
    } catch (e) {
      setResult({ ok: false, error: e instanceof Error ? e.message : '测试失败' });
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="h-full overflow-y-auto page-transition">
      <div className="p-4 md:p-6 max-w-3xl mx-auto">
        <PageHeader
          title="通知中心"
          icon={<Bell size={20} />}
        />

        <div className="space-y-4">
          <Card variant="default">
            <CardContent className="p-4">
              <h3 className="text-sm font-semibold text-[var(--color-text-primary)] mb-4">
                发送自定义通知
              </h3>
              <div className="space-y-4">
                <div>
                  <label htmlFor="notification-title" className="block text-xs font-medium text-[var(--color-text-secondary)] mb-1.5">
                    标题
                  </label>
                  <Input
                    id="notification-title"
                    value={title}
                    onChange={(e) => setTitle(e.target.value)}
                    placeholder="通知标题"
                  />
                </div>
                <div>
                  <label htmlFor="notification-message" className="block text-xs font-medium text-[var(--color-text-secondary)] mb-1.5">
                    内容
                  </label>
                  <textarea
                    id="notification-message"
                    value={message}
                    onChange={(e) => setMessage(e.target.value)}
                    rows={3}
                    className="w-full rounded-lg border border-[var(--color-border-default)] bg-[var(--color-bg-surface-1)] px-3 py-2.5 text-sm text-[var(--color-text-primary)] placeholder:text-[var(--color-text-muted)] focus:outline-none focus:ring-2 focus:ring-[var(--color-accent)]/20 focus:border-[var(--color-accent)] transition-all duration-150 resize-none"
                    placeholder="通知内容"
                  />
                </div>
                <div className="flex flex-wrap gap-2">
                  <Button
                    size="sm"
                    onClick={send}
                    loading={sending}
                    disabled={!title.trim() || !message.trim()}
                    icon={<Send size={14} />}
                  >
                    发送通知
                  </Button>
                  <Button
                    size="sm"
                    variant="secondary"
                    onClick={test}
                    loading={sending}
                    icon={<BellRing size={14} />}
                  >
                    系统测试
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>

          {result && (
            <Card
              padding="none"
              role="status"
              aria-live="polite"
              className={`flex items-center gap-3 p-3 ${
                result.ok
                  ? 'border-[var(--color-success)]/30 bg-[var(--color-success)]/10'
                  : 'border-[var(--color-error)]/30 bg-[var(--color-error)]/10'
              }`}
            >
              {result.ok ? (
                <CheckCircle size={18} className="text-[var(--color-success)] shrink-0" />
              ) : (
                <AlertCircle size={18} className="text-[var(--color-error)] shrink-0" />
              )}
              <p className={`text-sm ${result.ok ? 'text-[var(--color-success)]' : 'text-[var(--color-error)]'}`}>
                {result.ok ? '通知已发送' : `发送失败: ${result.error || '未知错误'}`}
              </p>
            </Card>
          )}

          <p className="text-xs text-[var(--color-text-muted)]">通知由后端主机发送，显示结果取决于该主机的桌面通知支持。</p>
        </div>
      </div>
    </div>
  );
}
