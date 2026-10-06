import { useState, type FormEvent } from 'react';
import { Lock, User } from 'lucide-react';
import { ApiRequestError, api } from '../api';
import { ClimberMark } from '../components/brand/ClimberMark';
import { Button } from '../components/ui/Button';
import { FormField } from '../components/ui/Field';
import { Input } from '../components/ui/Input';
import { useI18n } from '../i18n';

export interface LoginPageProps {
  onSuccess?: () => void;
}

export function LoginPage({ onSuccess }: LoginPageProps) {
  const { t } = useI18n();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (submitting) return;
    const trimmedUsername = username.trim();
    if (!trimmedUsername || !password) {
      setError(t('auth.required_fields'));
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const data = await api.login(trimmedUsername, password);
      localStorage.setItem('auth_token', data.access_token);
      localStorage.setItem('refresh_token', data.refresh_token);
      localStorage.setItem('user_info', JSON.stringify(data.user ?? data));
      window.location.hash = 'chat';
      onSuccess?.();
    } catch (err) {
      setError(
        err instanceof ApiRequestError && err.status === 401
          ? t('auth.invalid_credentials')
          : t('auth.login_failed'),
      );
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label={t('auth.login_title')}
      className="fixed inset-0 z-[var(--z-modal)] flex flex-col items-center justify-center overflow-hidden px-6"
    >
      <div aria-hidden="true" className="absolute inset-0 bg-[var(--color-bg-page)]/80 backdrop-blur-2xl" />
      <div className="relative w-full max-w-sm">
        <div className="flex flex-col items-center gap-2">
          <span className="flex h-16 w-16 items-center justify-center rounded-[22px] border border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-1)]/70 shadow-[var(--shadow-panel)]">
            <ClimberMark size={30} color="var(--color-accent-foreground)" />
          </span>
          <h1 className="mt-2 text-[17px] font-semibold tracking-tight text-[var(--color-text-primary)]">
            {t('auth.login_title')}
          </h1>
          <p className="text-[13px] text-[var(--color-text-secondary)]">
            {t('auth.login_subtitle')}
          </p>
        </div>

        <form onSubmit={handleSubmit} className="mt-6 space-y-4" noValidate>
          <FormField label={t('auth.username')}>
            <Input
              type="text"
              autoComplete="username"
              value={username}
              onChange={(event) => setUsername(event.target.value)}
              placeholder={t('auth.username')}
              leftIcon={<User size={14} aria-hidden="true" />}
              disabled={submitting}
            />
          </FormField>

          <FormField label={t('auth.password')}>
            <Input
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              placeholder={t('auth.password')}
              leftIcon={<Lock size={14} aria-hidden="true" />}
              disabled={submitting}
            />
          </FormField>

          <p role="alert" className="h-5 text-center text-[length:var(--text-xs)] text-[var(--color-error)]">
            {error}
          </p>

          <Button type="submit" variant="primary" size="lg" loading={submitting} className="w-full">
            {t('auth.login_submit')}
          </Button>
        </form>
      </div>
    </div>
  );
}

export default LoginPage;