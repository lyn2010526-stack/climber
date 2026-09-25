import { useEffect, useId, useState } from 'react';
import { apiClient } from '../../lib/api-client';
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
        setError('读取凭据超时，请重试');
      }
    }, 15000);
    apiClient.get<SavedCredential[]>('/api-keys', { signal: controller.signal }).then((rows) => {
      if (!active || controller.signal.aborted) return;
      if (!Array.isArray(rows) || rows.some((row) => !row || typeof row.id !== 'string' ||
          typeof row.provider !== 'string' || typeof row.name !== 'string' || typeof row.is_active !== 'boolean')) {
        throw new Error('Invalid credential list');
      }
      setCredentials(rows.filter((row) => row.is_active));
    }).catch(() => {
      if (active && !controller.signal.aborted) setError('读取已存凭据失败，请重试');
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
      <legend>模型配置</legend>
      <label htmlFor={id}>已保存的模型凭据</label>
      <select
        id={id} value={credential?.id || ''} disabled={loading}
        className="w-full rounded-lg border border-[var(--color-border-subtle)] bg-[var(--color-bg-secondary)] p-2"
        onChange={(event) => { setSelectedId(event.target.value); onChange(null); }}
      >
        <option value="">请选择凭据</option>
        {credentials.map((row) => <option key={row.id} value={row.id}>{row.name} ({row.provider})</option>)}
      </select>
      {loading && <p role="status">正在读取已存凭据…</p>}
      {error && <p role="alert">{error}</p>}
      {!loading && !error && !credentials.length && <p role="status">请先保存模型供应商凭据</p>}
      <button type="button" disabled={loading} onClick={() => { onChange(null); setRevision((n) => n + 1); }}>刷新凭据</button>
      <ModelSelector ownerKey={ownerKey} credentialId={credential?.id || null}
        provider={credential?.provider || ''} value={value} onChange={onChange} disabled={disabled} />
    </fieldset>
  );
}

export function ModelConfig(props: ModelConfigProps) {
  return <ScopedModelConfig key={props.ownerKey} {...props} />;
}
