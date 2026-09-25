import { useEffect, useId, useState } from 'react';
import { ApiError, apiClient } from '../../lib/api-client';

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

interface DiscoveryResult {
  credential_id: string;
  provider: string;
  source: 'provider_api';
  status: 'ok' | 'empty';
  models: DiscoveredModel[];
}

export interface ModelSelectorProps {
  ownerKey: string;
  credentialId: string | null;
  provider: string;
  value: ModelSelection | null;
  onChange: (value: ModelSelection) => void;
  disabled?: boolean;
}

const TIMEOUT_ERROR = '模型发现超时，请重试';

const errors: Record<string, string> = {
  missing_key: '请先为此凭据保存 API Key',
  missing_endpoint: '请先保存公网 HTTPS 模型端点',
  credential_not_found: '凭据已删除、停用或不属于当前用户',
  credential_unreadable: '凭据无法解密，请重新保存',
  unsupported_provider: '当前 provider 暂不支持模型发现',
  discovery_unavailable: '此端点未提供模型发现接口',
  provider_auth_failed: '供应商拒绝了已存凭据，请检查 Key 或权限',
  rate_limited: '供应商限流，请稍后重试',
  timeout: TIMEOUT_ERROR,
  unsafe_endpoint: '发现仅允许公网 HTTPS 端点，私网和本机地址被禁用',
  unsafe_redirect: '发现已拒绝供应商重定向',
  invalid_response: '供应商返回的模型列表格式无效',
  pagination_limit: '模型列表超出分页上限',
  response_too_large: '模型列表超出大小上限',
  network_error: '暂时无法连接供应商',
};

function errorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.status === 401 || error.status === 403) return '当前身份无权获取模型列表';
    const data = error.data as { detail?: { code?: string } } | undefined;
    const code = data?.detail?.code;
    if (code && errors[code]) return errors[code];
  }
  return '模型发现失败，请重试';
}

function ScopedModelSelector({ credentialId, provider, value, onChange, disabled }: ModelSelectorProps) {
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
        setError(TIMEOUT_ERROR);
      }
    }, 15000);
    apiClient.get<DiscoveryResult>(
      `/models/discover?credential_id=${encodeURIComponent(credentialId)}`,
      { signal: controller.signal },
    ).then((result) => {
      if (!active || controller.signal.aborted) return;
      if (result.credential_id !== credentialId || result.provider !== provider ||
          result.source !== 'provider_api' || !['ok', 'empty'].includes(result.status) ||
          !Array.isArray(result.models) || result.models.some((model) =>
            !model || model.provider !== provider || typeof model.model_id !== 'string' ||
            !model.model_id || typeof model.label !== 'string')) {
        throw new Error('Invalid discovery response');
      }
      setModels(result.models);
      setLoaded(true);
    }).catch((reason: unknown) => {
      if (active && !controller.signal.aborted) setError(errorMessage(reason));
    }).finally(() => {
      window.clearTimeout(timer);
      if (active) setLoading(false);
    });
    return () => {
      active = false;
      window.clearTimeout(timer);
      controller.abort();
    };
  }, [credentialId, provider, revision]);

  const selected = value?.credential_id === credentialId && value.provider === provider ? value.model_id : '';
  const missing = selected && !models.some((model) => model.model_id === selected);
  return (
    <div className="space-y-2">
      <label htmlFor={id}>模型</label>
      <select
        id={id} value={selected} aria-describedby={`${id}-status`}
        disabled={disabled || loading || !credentialId || !loaded || !models.length}
        className="w-full rounded-lg border border-[var(--color-border-subtle)] bg-[var(--color-bg-secondary)] p-2"
        onChange={(event) => {
          const model = models.find((item) => item.model_id === event.target.value);
          if (credentialId && model) onChange({ credential_id: credentialId, provider, model_id: model.model_id });
        }}
      >
        <option value="">请选择模型</option>
        {missing && <option value={selected} disabled>{selected}（未在当前发现列表中）</option>}
        {models.map((model) => <option key={model.model_id} value={model.model_id}>{model.label}</option>)}
      </select>
      <p id={`${id}-status`} role="status" className="text-xs text-[var(--color-text-secondary)]">
        {!credentialId ? '请选择已保存的模型凭据' : loading ? '正在从供应商获取模型…' :
          loaded ? (models.length ? '来源：供应商实时 API' : '供应商返回空列表，暂无可选模型') : ''}
      </p>
      {error && <p role="alert" className="text-sm text-red-500">{error}</p>}
      <button type="button" disabled={disabled || loading || !credentialId} onClick={() => setRevision((n) => n + 1)}>
        {error ? '重试模型发现' : '刷新模型列表'}
      </button>
    </div>
  );
}

export function ModelSelector(props: ModelSelectorProps) {
  // Reset and cancel owner/credential-specific state before exposing a new selection.
  return <ScopedModelSelector key={JSON.stringify([props.ownerKey, props.credentialId, props.provider])} {...props} />;
}
