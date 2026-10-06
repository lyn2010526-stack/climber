import { useEffect, useState } from 'react';
import { profileApi, type ProfileSettings } from '../../lib/profileApi';
import { useI18n } from '../../i18n';
import { Button } from '../ui/Button';
import { Card } from '../ui/Card';

export function ProfileLearningSettings() {
  const { t } = useI18n();
  const [settings, setSettings] = useState<ProfileSettings | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [agreed, setAgreed] = useState(false);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [reload, setReload] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError('');
    setSettings(null);
    setConfirming(false);
    setAgreed(false);
    profileApi.getSettings(controller.signal).then((data) => {
      if (!controller.signal.aborted) setSettings(data);
    }).catch(() => {
      if (!controller.signal.aborted) setError(t('privacy_profile_learning.load_error'));
    }).finally(() => {
      if (!controller.signal.aborted) setLoading(false);
    });
    return () => controller.abort();
  }, [reload]);

  const save = async (enabled: boolean) => {
    if (!settings || busy || (enabled && settings.consent_required && !agreed)) return;
    setBusy(true);
    setError('');
    setMessage('');
    try {
      const updated = await profileApi.updateSettings({
        enabled,
        show_raw_profile: false,
        ...(enabled && settings.consent_required ? { consent_version: settings.notice_version } : {}),
      });
      setSettings(updated);
      setConfirming(false);
      setAgreed(false);
      setMessage(t(updated.enabled ? 'privacy_profile_learning.message_enabled' : 'privacy_profile_learning.message_disabled'));
    } catch {
      setError(t('privacy_profile_learning.save_error'));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Card className="mb-4">
      <section aria-labelledby="profile-learning-title" className="space-y-3">
        <h3 id="profile-learning-title" className="text-sm font-semibold">{t('privacy_profile_learning.title')}</h3>
        <p className="text-sm text-[var(--color-text-secondary)]">{t('privacy_profile_learning.description')}</p>
        {loading && <p role="status">{t('privacy_profile_learning.loading')}</p>}
        {settings && <>
          <p className="text-sm">{t('privacy_profile_learning.current_status', { state: settings.enabled ? t('privacy_profile_learning.status_enabled') : t('privacy_profile_learning.status_disabled') })}</p>
          <p id="profile-learning-notice" className="text-sm text-[var(--color-text-secondary)] whitespace-pre-wrap break-words">{settings.notice}</p>
          <p className="text-xs text-[var(--color-text-muted)]">{t('privacy_profile_learning.closing_note')}</p>
          {confirming ? (
            <form onSubmit={(event) => { event.preventDefault(); void save(true); }}>
              <fieldset disabled={busy} className="space-y-3">
                <label className="flex items-start gap-2 text-sm">
                  <input type="checkbox" checked={agreed} onChange={(event) => setAgreed(event.target.checked)} aria-describedby="profile-learning-notice" />
                  <span>{t('privacy_profile_learning.agree_label')}</span>
                </label>
                <div className="flex flex-wrap gap-2">
                  <Button type="submit" size="sm" disabled={!agreed || busy} loading={busy}>{t('privacy_profile_learning.agree_submit')}</Button>
                  <Button type="button" size="sm" variant="ghost" onClick={() => { setConfirming(false); setAgreed(false); setError(''); }}>{t('privacy_profile_learning.cancel')}</Button>
                </div>
              </fieldset>
            </form>
          ) : (
            <Button size="sm" variant="outline" disabled={busy} loading={busy} onClick={() => {
              setError('');
              setMessage('');
              if (!settings.enabled && settings.consent_required) {
                setAgreed(false);
                setConfirming(true);
              } else {
                void save(!settings.enabled);
              }
            }}>{settings.enabled ? t('privacy_profile_learning.disable_button') : t('privacy_profile_learning.enable_button')}</Button>
          )}
        </>}
        {error && <p role="alert" className="text-sm text-[var(--color-error)]">{error}</p>}
        {!loading && !settings && <Button size="sm" variant="outline" onClick={() => setReload((value) => value + 1)}>{t('privacy_profile_learning.reload_button')}</Button>}
        {message && <p role="status" className="text-sm">{message}</p>}
      </section>
    </Card>
  );
}
