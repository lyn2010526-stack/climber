import { useState } from 'react';
import { PIN_LENGTH, useAppLock } from '../../hooks/useAppLock';
import { icons, iconSizes } from '../../lib/icons';
import { useI18n } from '../../i18n';
import { Button } from '../ui/Button';
import { Input } from '../ui/Input';

export function LocalPinSettings() {
  const { t } = useI18n();
  const lock = useAppLock();
  const [editing, setEditing] = useState(false);
  const [pin, setPin] = useState('');
  const [confirmation, setConfirmation] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const LockIcon = icons.privacyLock;

  const reset = () => {
    setEditing(false);
    setPin('');
    setConfirmation('');
    setError('');
  };

  const submit = async () => {
    if (busy) return;
    setError('');
    setMessage('');
    if (!/^\d{6}$/.test(pin)) {
      setError(t('privacy_local_pin.error_invalid'));
      return;
    }
    if (!lock.hasPin && pin !== confirmation) {
      setError(t('privacy_local_pin.error_mismatch'));
      return;
    }
    const disabling = lock.hasPin;
    setBusy(true);
    try {
      const ok = disabling ? await lock.disableLock(pin) : await lock.setupPin(pin);
      setPin('');
      setConfirmation('');
      if (ok) {
        setEditing(false);
        setMessage(t(disabling ? 'privacy_local_pin.message_disabled' : 'privacy_local_pin.message_enabled'));
      } else {
        setError(t(disabling ? 'privacy_local_pin.error_disable_failed' : 'privacy_local_pin.error_enable_failed'));
      }
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="local-pin-settings" aria-labelledby="local-pin-title">
      <div className="local-pin-heading">
        <LockIcon size={iconSizes.md} aria-hidden="true" />
        <h3 id="local-pin-title">{t('privacy_local_pin.title')}</h3>
        <span className="local-pin-state" data-enabled={lock.hasPin}>{lock.hasPin ? t('privacy_local_pin.enabled') : t('privacy_local_pin.disabled')}</span>
      </div>
      <p>{t('privacy_local_pin.intro')}</p>
      <p>
        {lock.autoLockMs > 0
          ? t('privacy_local_pin.auto_lock_seconds', { seconds: lock.autoLockMs / 1000 })
          : t('privacy_local_pin.auto_lock_off')}
        {' '}
        {t('privacy_local_pin.relock_hint')}
      </p>
      {editing ? (
        <form onSubmit={(event) => { event.preventDefault(); void submit(); }}>
          <fieldset disabled={busy} className="local-pin-form">
            <label htmlFor="local-pin">{lock.hasPin ? t('privacy_local_pin.label_current') : t('privacy_local_pin.label_set')}</label>
            <Input id="local-pin" type="password" inputMode="numeric" autoComplete="off" maxLength={PIN_LENGTH} value={pin} onChange={(event) => setPin(event.target.value)} />
            {!lock.hasPin && <>
              <label htmlFor="local-pin-confirm">{t('privacy_local_pin.label_confirm')}</label>
              <Input id="local-pin-confirm" type="password" inputMode="numeric" autoComplete="off" maxLength={PIN_LENGTH} value={confirmation} onChange={(event) => setConfirmation(event.target.value)} />
            </>}
            <div className="local-pin-actions">
              <Button type="submit" size="sm" loading={busy}>{lock.hasPin ? t('privacy_local_pin.submit_disable') : t('privacy_local_pin.submit_enable')}</Button>
              <Button type="button" size="sm" variant="ghost" onClick={reset}>{t('privacy_local_pin.cancel')}</Button>
            </div>
          </fieldset>
        </form>
      ) : (
        <div className="local-pin-actions">
          <Button size="sm" variant="outline" onClick={() => { setEditing(true); setMessage(''); }}>{lock.hasPin ? t('privacy_local_pin.action_disable') : t('privacy_local_pin.action_enable')}</Button>
          {lock.hasPin && <Button size="sm" variant="ghost" onClick={lock.lock}>{t('privacy_local_pin.lock_now')}</Button>}
        </div>
      )}
      {error && <p role="alert">{error}</p>}
      {message && <p role="status">{message}</p>}
    </section>
  );
}
