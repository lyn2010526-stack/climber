import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { ModelSelector, type ModelSelectorProps } from './ModelSelector';
import { ModelConfig } from './ModelConfig';

// Only HTTP is mocked: components and apiClient execute their real branches.
const fetchMock = vi.fn();
const json = (body: unknown, status = 200) => new Response(JSON.stringify(body), {
  status, headers: { 'Content-Type': 'application/json' },
});
const discovered = (credential = 'mine', model = 'model-test') => ({
  credential_id: credential, provider: 'openai', source: 'provider_api',
  status: 'ok', models: [{ provider: 'openai', model_id: model, label: model }],
});
const props = (): ModelSelectorProps => ({
  ownerKey: 'owner-a', credentialId: 'mine', provider: 'openai', value: null, onChange: vi.fn(),
});

beforeEach(() => {
  fetchMock.mockReset();
  vi.stubGlobal('fetch', fetchMock);
  localStorage.removeItem('auth_token');
});
afterEach(() => {
  cleanup();
  vi.useRealTimers();
  vi.unstubAllGlobals();
  localStorage.removeItem('auth_token');
});

describe('ModelSelector discovery', () => {
  it('makes no discovery request without a saved credential', () => {
    render(<ModelSelector {...props()} credentialId={null} />);
    expect(fetchMock).not.toHaveBeenCalled();
    expect(screen.getByRole('combobox')).toBeDisabled();
    expect(screen.getByRole('status')).toHaveTextContent('请选择已保存的模型凭据');
  });

  it('uses the existing authenticated client and returns the credential-scoped selection', async () => {
    localStorage.setItem('auth_token', 'caller-test-token');
    fetchMock.mockResolvedValue(json(discovered()));
    const options = props();
    render(<ModelSelector {...options} />);
    await screen.findByRole('option', { name: 'model-test' });
    const [url, config] = fetchMock.mock.calls[0];
    expect(url).toBe('/api/v1/models/discover?credential_id=mine');
    expect(config.headers.Authorization).toBe('Bearer caller-test-token');
    expect(config.signal).toBeInstanceOf(AbortSignal);
    expect(screen.getByRole('status')).toHaveTextContent('来源：供应商实时 API');
    expect(options.onChange).not.toHaveBeenCalled();
    fireEvent.change(screen.getByRole('combobox'), { target: { value: 'model-test' } });
    expect(options.onChange).toHaveBeenCalledWith({ credential_id: 'mine', provider: 'openai', model_id: 'model-test' });
  });

  it('shows an explicit empty list without fabricated options', async () => {
    fetchMock.mockResolvedValue(json({ ...discovered(), status: 'empty', models: [] }));
    render(<ModelSelector {...props()} />);
    await screen.findByText('供应商返回空列表，暂无可选模型');
    expect(screen.getAllByRole('option')).toHaveLength(1);
    expect(screen.getByRole('combobox')).toBeDisabled();
  });

  it('labels a previously selected unavailable model without replacing it', async () => {
    fetchMock.mockResolvedValue(json(discovered()));
    const options = { ...props(), value: { credential_id: 'mine', provider: 'openai', model_id: 'old-model' } };
    render(<ModelSelector {...options} />);
    await screen.findByRole('option', { name: 'model-test' });
    expect(screen.getByRole('option', { name: 'old-model（未在当前发现列表中）' })).toBeDisabled();
    expect(screen.getByRole('combobox')).toHaveValue('old-model');
    expect(options.onChange).not.toHaveBeenCalled();
  });

  it('shows provider errors safely and supports a successful retry', async () => {
    fetchMock.mockResolvedValueOnce(json({ detail: { code: 'provider_auth_failed', message: 'secret-upstream-body' } }, 424));
    fetchMock.mockResolvedValueOnce(json(discovered()));
    render(<ModelSelector {...props()} />);
    expect(await screen.findByRole('alert')).toHaveTextContent('供应商拒绝了已存凭据');
    expect(screen.queryByText('secret-upstream-body')).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '重试模型发现' }));
    await screen.findByRole('option', { name: 'model-test' });
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });

  it('cancels an old credential request and ignores its late response', async () => {
    let resolveOld!: (response: Response) => void;
    fetchMock.mockReturnValueOnce(new Promise<Response>((resolve) => { resolveOld = resolve; }));
    fetchMock.mockResolvedValueOnce(json(discovered('next', 'new-model')));
    const options = props();
    const view = render(<ModelSelector {...options} />);
    const oldSignal = fetchMock.mock.calls[0][1].signal as AbortSignal;
    view.rerender(<ModelSelector {...options} credentialId="next" />);
    await screen.findByRole('option', { name: 'new-model' });
    expect(oldSignal.aborted).toBe(true);
    await act(async () => { resolveOld(json(discovered('mine', 'old-model'))); });
    expect(screen.queryByRole('option', { name: 'old-model' })).not.toBeInTheDocument();
    expect(screen.getByRole('option', { name: 'new-model' })).toBeInTheDocument();
  });

  it('resets loaded models when the owner changes, even for the same credential ID', async () => {
    fetchMock.mockResolvedValueOnce(json(discovered('mine', 'owner-a-model')));
    fetchMock.mockReturnValueOnce(new Promise(() => {}));
    const options = props();
    const view = render(<ModelSelector {...options} />);
    await screen.findByRole('option', { name: 'owner-a-model' });
    view.rerender(<ModelSelector {...options} ownerKey="owner-b" />);
    expect(screen.queryByRole('option', { name: 'owner-a-model' })).not.toBeInTheDocument();
    expect(screen.getByRole('combobox')).toBeDisabled();
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it('aborts and displays timeout after fifteen seconds', async () => {
    vi.useFakeTimers();
    fetchMock.mockReturnValue(new Promise(() => {}));
    render(<ModelSelector {...props()} />);
    await act(async () => { vi.advanceTimersByTime(15000); });
    expect(screen.getByRole('alert')).toHaveTextContent('模型发现超时');
    expect(fetchMock.mock.calls[0][1].signal.aborted).toBe(true);
    expect(screen.getByRole('button', { name: '重试模型发现' })).toBeEnabled();
  });

  it.each([
    { source: 'static_fallback' }, { credential_id: 'other' }, { provider: 'google' },
    { models: [{ provider: 'openai', model_id: null, label: 'invalid' }] },
  ])('rejects mismatched or static discovery payload %j', async (override) => {
    fetchMock.mockResolvedValue(json({ ...discovered(), ...override }));
    render(<ModelSelector {...props()} />);
    expect(await screen.findByRole('alert')).toHaveTextContent('模型发现失败');
    expect(screen.getAllByRole('option')).toHaveLength(1);
  });
});

describe('ModelConfig saved credentials', () => {
  it('reuses api-keys, filters inactive records and discovers only the chosen credential', async () => {
    fetchMock.mockResolvedValueOnce(json([
      { id: 'mine', provider: 'openai', name: 'Saved user key', is_active: true },
      { id: 'disabled', provider: 'openai', name: 'Disabled key', is_active: false },
    ]));
    fetchMock.mockResolvedValueOnce(json(discovered()));
    const onChange = vi.fn();
    render(<ModelConfig ownerKey="owner-a" value={null} onChange={onChange} />);
    await screen.findByRole('option', { name: 'Saved user key (openai)' });
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(fetchMock.mock.calls[0][0]).toBe('/api/v1/api-keys');
    expect(screen.queryByText('Disabled key (openai)')).not.toBeInTheDocument();
    fireEvent.change(screen.getByLabelText('已保存的模型凭据'), { target: { value: 'mine' } });
    expect(onChange).toHaveBeenCalledWith(null);
    await screen.findByRole('option', { name: 'model-test' });
    fireEvent.change(screen.getByLabelText('模型'), { target: { value: 'model-test' } });
    expect(onChange).toHaveBeenLastCalledWith({ credential_id: 'mine', provider: 'openai', model_id: 'model-test' });
  });

  it('shows missing saved credentials and makes no discovery request', async () => {
    fetchMock.mockResolvedValue(json([]));
    render(<ModelConfig ownerKey="owner-a" value={null} onChange={vi.fn()} />);
    await screen.findByText('请先保存模型供应商凭据');
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(screen.getByLabelText('模型')).toBeDisabled();
  });

  it('reports credential fetch failures and reloads on owner change', async () => {
    fetchMock.mockRejectedValueOnce(new Error('offline'));
    fetchMock.mockResolvedValueOnce(json([]));
    const view = render(<ModelConfig ownerKey="owner-a" value={null} onChange={vi.fn()} />);
    await screen.findByText('读取已存凭据失败，请重试');
    view.rerender(<ModelConfig ownerKey="owner-b" value={null} onChange={vi.fn()} />);
    await screen.findByText('请先保存模型供应商凭据');
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });

  it('aborts credential loading on unmount', async () => {
    fetchMock.mockReturnValue(new Promise(() => {}));
    const view = render(<ModelConfig ownerKey="owner-a" value={null} onChange={vi.fn()} />);
    const signal = fetchMock.mock.calls[0][1].signal as AbortSignal;
    view.unmount();
    expect(signal.aborted).toBe(true);
  });

  it('follows a saved selection supplied by the parent after mount', async () => {
    fetchMock.mockResolvedValueOnce(json([
      { id: 'mine', provider: 'openai', name: 'Saved key', is_active: true },
    ]));
    fetchMock.mockResolvedValueOnce(json(discovered()));
    const onChange = vi.fn();
    const view = render(<ModelConfig ownerKey="owner-a" value={null} onChange={onChange} />);
    await screen.findByRole('option', { name: 'Saved key (openai)' });
    view.rerender(<ModelConfig ownerKey="owner-a"
      value={{ credential_id: 'mine', provider: 'openai', model_id: 'model-test' }} onChange={onChange} />);
    await waitFor(() => expect(screen.getByLabelText('已保存的模型凭据')).toHaveValue('mine'));
    await screen.findByRole('option', { name: 'model-test' });
    expect(screen.getByLabelText('模型')).toHaveValue('model-test');
  });
});
