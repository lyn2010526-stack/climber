import { useState } from 'react';
import { Bell, Send, CheckCircle, AlertCircle, BellRing } from 'lucide-react';
import { api } from '../api';
import { useI18n } from '../i18n';
import { PageHeader } from '../components/ui/PageHeader';
import { Card, CardContent } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';

export function NotificationsPage() {
  const { t } = useI18n();
  const [title, setTitle] = useState(t('notifications_page.default_title'));
  const [message, setMessage] = useState(t('notifications_page.default_message'));
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
      setResult({ ok: false, error: e instanceof Error ? e.message : t('notifications_page.send_failed_fallback') });
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
      setResult({ ok: false, error: e instanceof Error ? e.message : t('notifications_page.test_failed_fallback') });
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="h-full overflow-y-auto page-transition">
      <div className="p-4 md:p-6 max-w-3xl mx-auto">
        <PageHeader
          title={t('notifications_page.title')}
          icon={<Bell size={20} />}
          className="border-b border-[var(--color-border-subtle)] pb-[var(--space-4)] [&_h1]:text-[length:var(--text-base)] [&_h1]:md:text-[length:var(--text-base)] [&_p]:text-[var(--color-text-muted)]"
        />

        <div className="space-y-4">
          <Card variant="default">
            <CardContent className="p-4">
              <h3 className="text-sm font-semibold text-[var(--color-text-primary)] mb-4">
                {t('notifications_page.send_custom')}
              </h3>
              <div className="space-y-4">
                <div>
                  <label htmlFor="notification-title" className="block text-[length:var(--text-sm)] font-medium text-[var(--color-text-secondary)] mb-1.5">
                    {t('notifications_page.title_label')}
                  </label>
                  <Input
                    id="notification-title"
                    value={title}
                    onChange={(e) => setTitle(e.target.value)}
                    placeholder={t('notifications_page.title_placeholder')}
                  />
                </div>
                <div>
                  <label htmlFor="notification-message" className="block text-[length:var(--text-sm)] font-medium text-[var(--color-text-secondary)] mb-1.5">
                    {t('notifications_page.message_label')}
                  </label>
                  <textarea
                    id="notification-message"
                    value={message}
                    onChange={(e) => setMessage(e.target.value)}
                    rows={3}
                    className="w-full rounded-[var(--radius-md)] border border-[var(--color-border-default)] bg-[var(--color-bg-surface-1)] px-3 py-2.5 text-[length:var(--text-sm)] text-[var(--color-text-primary)] placeholder:text-[var(--color-text-muted)] focus:outline-none focus:ring-2 focus:ring-[var(--color-accent)]/20 focus:border-[var(--color-accent)] transition-all duration-150 resize-none motion-reduce:transition-none"
                    placeholder={t('notifications_page.message_placeholder')}
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
                    {t('notifications_page.send')}
                  </Button>
                  <Button
                    size="sm"
                    variant="secondary"
                    onClick={test}
                    loading={sending}
                    icon={<BellRing size={14} />}
                  >
                    {t('notifications_page.system_test')}
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
                {result.ok ? t('notifications_page.sent') : t('notifications_page.send_failed', { error: result.error || t('notifications_page.unknown_error') })}
              </p>
            </Card>
          )}

          <p className="text-xs text-[var(--color-text-muted)]">{t('notifications_page.footer_hint')}</p>
        </div>
      </div>
    </div>
  );
}
