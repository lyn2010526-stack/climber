import { useEffect, useId, useState } from 'react';
import { api } from '../../api';
import { useI18n } from '../../i18n';
import { ModelSelector, type ModelSelection } from './ModelSelector';

interface SavedCredential {
  id: string;
  provider: string;
  name: string;
  is_active: boolean;
}

export interface ModelConfigProps {
  ownerKey: string;
  value: ModelSelection | null;
  onChange: (value: ModelSelection | null) => void;
  disabled?: boolean;
}

function ScopedModelConfig({ ownerKey, value, onChange, disabled }: ModelConfigProps) {
  const id = useId();
  const { t } = useI18n();
  const [credentials, setCredentials] = useState<SavedCredential[]>([]);
  const [selectedId, setSelectedId] = useState(value?.credential_id || '');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [revision, setRevision] = useState(0);

  useEffect(() => {
    if (value?.credential_id) setSelectedId(value.credential_id);
  }, [value?.credential_id]);

  useEffect(() => {
    const controller = new AbortController();
    let active = true;
    setLoading(true);
    setError('');
    setCredentials([]);
    const timer = window.setTimeout(() => {
      controller.abort();
      if (active) {
        setLoading(false);
        setError(t('model_config.credentials_timeout'));
      }
    }, 15000);
    api.listApiKeys(controller.signal).then((rows) => {
      if (!active || controller.signal.aborted) return;
      if (!Array.isArray(rows) || rows.some((row) => !row || typeof row.id !== 'string' ||
          typeof row.provider !== 'string' || typeof row.name !== 'string' || typeof row.is_active !== 'boolean')) {
        throw new Error('Invalid credential list');
      }
      setCredentials(rows.filter((row) => row.is_active));
    }).catch(() => {
      if (active && !controller.signal.aborted) setError(t('model_config.credentials_load_failed'));
    }).finally(() => {
      window.clearTimeout(timer);
      if (active) setLoading(false);
    });
    return () => {
      active = false;
      controller.abort();
      window.clearTimeout(timer);
    };
  }, [revision]);

  const credential = credentials.find((row) => row.id === selectedId);
  useEffect(() => {
    if (!loading && value && (!credential || error || credential.provider !== value.provider)) {
      onChange(null);
    }
  }, [loading, credential, error, value, onChange]);
  return (
    <fieldset disabled={disabled} className="space-y-3">
      <legend>{t('model_config.title')}</legend>
      <label htmlFor={id}>{t('model_config.saved_credentials')}</label>
      <select
        id={id} value={credential?.id || ''} disabled={loading}
        className="w-full rounded-lg border border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-2)] p-2"
        onChange={(event) => { setSelectedId(event.target.value); onChange(null); }}
      >
        <option value="">{t('model_config.select_credential_placeholder')}</option>
        {credentials.map((row) => <option key={row.id} value={row.id}>{row.name} ({row.provider})</option>)}
      </select>
      {loading && <p role="status">{t('model_config.loading_credentials')}</p>}
      {error && <p role="alert">{error}</p>}
      {!loading && !error && !credentials.length && <p role="status">{t('model_config.no_credentials')}</p>}
      <button type="button" disabled={loading} onClick={() => { onChange(null); setRevision((n) => n + 1); }}>{t('model_config.refresh')}</button>
      <ModelSelector ownerKey={ownerKey} credentialId={credential?.id || null}
        provider={credential?.provider || ''} value={value} onChange={onChange} disabled={disabled} />
    </fieldset>
  );
}

export function ModelConfig(props: ModelConfigProps) {
  return <ScopedModelConfig key={props.ownerKey} {...props} />;
}
