import { useState } from 'react';
import { Bell, Send, CheckCircle, AlertCircle, BellRing, Info } from 'lucide-react';
import { api } from '../api';
import { PageHeader } from '../components/ui/PageHeader';
import { Card, CardContent } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { Badge } from '../components/ui/Badge';

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
    <div className="h-full overflow-y-auto page-transition">
      <div className="p-4 md:p-6 lg:p-8 max-w-3xl mx-auto">
        <PageHeader
          title="通知中心"
          description="测试桌面通知，任务完成或出错时会自动弹出提醒"
          icon={<Bell size={20} />}
        />

        <div className="space-y-6">
          <Card variant="default">
            <CardContent className="p-6">
              <h3 className="text-sm font-semibold text-[var(--color-text-primary)] mb-4">
                发送自定义通知
              </h3>
              <div className="space-y-4">
                <div>
                  <label className="block text-xs font-medium text-[var(--color-text-secondary)] mb-1.5">
                    标题
                  </label>
                  <Input
                    value={title}
                    onChange={(e) => setTitle(e.target.value)}
                    placeholder="通知标题"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-[var(--color-text-secondary)] mb-1.5">
                    内容
                  </label>
                  <textarea
                    value={message}
                    onChange={(e) => setMessage(e.target.value)}
                    rows={3}
                    className="w-full rounded-lg border border-[var(--color-border-default)] bg-[var(--color-bg-surface-1)] px-3 py-2.5 text-sm text-[var(--color-text-primary)] placeholder:text-[var(--color-text-muted)] focus:outline-none focus:ring-2 focus:ring-[var(--color-accent)]/20 focus:border-[var(--color-accent)] transition-all duration-150 resize-none"
                    placeholder="通知内容"
                  />
                </div>
                <div className="flex gap-3">
                  <Button
                    onClick={send}
                    loading={sending}
                    disabled={!title.trim() || !message.trim()}
                    icon={<Send size={14} />}
                  >
                    发送通知
                  </Button>
                  <Button
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
            <div className={`rounded-xl p-4 flex items-center gap-3 border ${
              result.ok
                ? 'bg-[var(--color-success)]/10 border-[var(--color-success)]/30'
                : 'bg-[var(--color-error)]/10 border-[var(--color-error)]/30'
            }`}>
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

          <Card variant="default">
            <CardContent className="p-6">
              <h3 className="text-sm font-semibold text-[var(--color-text-primary)] mb-3">
                通知说明
              </h3>
              <ul className="space-y-2">
                {[
                  '通知通过系统原生机制发送（Linux notify-send / macOS osascript / Windows PowerShell）',
                  '如果系统不支持桌面通知，会自动跳过，不会影响应用运行',
                  '任务完成、失败或需要审批时，系统会自动触发通知',
                  '通知服务在后台运行，不占用前端资源',
                ].map((tip, i) => (
                  <li key={i} className="flex items-start gap-2 text-xs text-[var(--color-text-muted)]">
                    <Info size={12} className="text-[var(--color-text-muted)] shrink-0 mt-0.5" />
                    <span>{tip}</span>
                  </li>
                ))}
              </ul>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
