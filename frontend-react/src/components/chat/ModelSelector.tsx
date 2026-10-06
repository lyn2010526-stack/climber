import { useEffect, useId, useState } from 'react';
import { ApiRequestError, api } from '../../api';
import { useI18n } from '../../i18n';

export interface ModelSelection {
  credential_id: string;
  provider: string;
  model_id: string;
}

interface DiscoveredModel {
  provider: string;
  model_id: string;
  label: string;
}

export interface ModelSelectorProps {
  ownerKey: string;
  credentialId: string | null;
  provider: string;
  value: ModelSelection | null;
  onChange: (value: ModelSelection) => void;
  disabled?: boolean;
}

const ERROR_KEY_BY_CODE: Record<string, string> = {
  missing_key: 'chat.model_selector.missing_key',
  missing_endpoint: 'chat.model_selector.missing_endpoint',
  credential_not_found: 'chat.model_selector.credential_not_found',
  credential_unreadable: 'chat.model_selector.credential_unreadable',
  unsupported_provider: 'chat.model_selector.unsupported_provider',
  discovery_unavailable: 'chat.model_selector.discovery_unavailable',
  provider_auth_failed: 'chat.model_selector.provider_auth_failed',
  rate_limited: 'chat.model_selector.rate_limited',
  timeout: 'chat.model_selector.timeout',
  unsafe_endpoint: 'chat.model_selector.unsafe_endpoint',
  unsafe_redirect: 'chat.model_selector.unsafe_redirect',
  invalid_response: 'chat.model_selector.invalid_response',
  pagination_limit: 'chat.model_selector.pagination_limit',
  response_too_large: 'chat.model_selector.response_too_large',
  network_error: 'chat.model_selector.network_error',
};

function errorMessage(error: unknown, t: (key: string) => string): string {
  if (error instanceof ApiRequestError) {
    if (error.status === 401 || error.status === 403) return t('chat.model_selector.unauthorized');
    const data = error.data as { detail?: { code?: string } } | undefined;
    const code = data?.detail?.code;
    if (code && ERROR_KEY_BY_CODE[code]) return t(ERROR_KEY_BY_CODE[code]);
  }
  return t('chat.model_selector.generic_failed');
}

function ScopedModelSelector({ credentialId, provider, value, onChange, disabled }: ModelSelectorProps) {
  const { t } = useI18n();
  const id = useId();
  const [models, setModels] = useState<DiscoveredModel[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [loaded, setLoaded] = useState(false);
  const [revision, setRevision] = useState(0);

  useEffect(() => {
    if (!credentialId) return;
    const controller = new AbortController();
    let active = true;
    setLoading(true);
    setLoaded(false);
    setError('');
    setModels([]);
    const timer = window.setTimeout(() => {
      controller.abort();
      if (active) {
        setLoading(false);
        setError(t('chat.model_selector.timeout'));
      }
    }, 15000);
    api.discoverModels(credentialId, controller.signal).then((result) => {
      if (!active || controller.signal.aborted) return;
      if (result.credential_id !== credentialId || result.provider !== provider ||
          result.source !== 'provider_api' || !['ok', 'empty'].includes(result.status) ||
          !Array.isArray(result.models) || result.models.some((model) =>
            !model || model.provider !== provider || typeof model.model_id !== 'string' ||
            !model.model_id || typeof model.label !== 'string')) {
        throw new Error(t('chat.model_selector.invalid_payload'));
      }
      setModels(result.models);
      setLoaded(true);
    }).catch((reason: unknown) => {
      if (active && !controller.signal.aborted) setError(errorMessage(reason, t));
    }).finally(() => {
      window.clearTimeout(timer);
      if (active) setLoading(false);
    });
    return () => {
      active = false;
      window.clearTimeout(timer);
      controller.abort();
    };
  }, [credentialId, provider, revision, t]);

  const selected = value?.credential_id === credentialId && value.provider === provider ? value.model_id : '';
  const missing = selected && !models.some((model) => model.model_id === selected);
  return (
    <div className="space-y-2">
      <label htmlFor={id}>{t('chat.model_selector.label')}</label>
      <select
        id={id} value={selected} aria-describedby={`${id}-status`}
        disabled={disabled || loading || !credentialId || !loaded || !models.length}
        className="w-full rounded-lg border border-[var(--color-border-subtle)] bg-[var(--color-bg-surface-2)] p-2"
        onChange={(event) => {
          const model = models.find((item) => item.model_id === event.target.value);
          if (credentialId && model) onChange({ credential_id: credentialId, provider, model_id: model.model_id });
        }}
      >
        <option value="">{t('chat.model_selector.empty_choice')}</option>
        {missing && <option value={selected} disabled>{t('chat.model_selector.not_in_list', { name: selected })}</option>}
        {models.map((model) => <option key={model.model_id} value={model.model_id}>{model.label}</option>)}
      </select>
      <p id={`${id}-status`} role="status" className="text-xs text-[var(--color-text-secondary)]">
        {!credentialId ? t('chat.model_selector.no_credential') : loading ? t('chat.model_selector.loading_models') :
          loaded ? (models.length ? t('chat.model_selector.source_live') : t('chat.model_selector.empty_list')) : ''}
      </p>
      {error && <p role="alert" className="text-sm text-[var(--color-error)]">{error}</p>}
      <button type="button" disabled={disabled || loading || !credentialId} onClick={() => setRevision((n) => n + 1)}>
        {error ? t('chat.model_selector.retry') : t('chat.model_selector.refresh')}
      </button>
    </div>
  );
}

export function ModelSelector(props: ModelSelectorProps) {
  // Reset and cancel owner/credential-specific state before exposing a new selection.
  return <ScopedModelSelector key={JSON.stringify([props.ownerKey, props.credentialId, props.provider])} {...props} />;
}
