import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { act, cleanup, fireEvent, render, screen } from '@testing-library/react';
import { FactoryModePage } from '../FactoryModePage';
import { api } from '../../api';

vi.mock('../../api', () => ({
  api: {
    listAgents: vi.fn(),
    listApiKeys: vi.fn(),
    listTasks: vi.fn(),
    getArcbenchStatus: vi.fn(),
    runAutonomousSkillStream: vi.fn(),
    stopTask: vi.fn(),
  },
}));

const abortStream = vi.fn();

beforeEach(() => {
  vi.resetAllMocks();
  vi.mocked(api.listAgents).mockResolvedValue([
    { id: 'configured-agent', name: 'Configured', provider: 'anthropic', model_id: 'user-model', is_active: true },
    { id: 'disabled-agent', name: 'Disabled', provider: 'openai', model_id: 'disabled-model', is_active: false },
  ]);
  vi.mocked(api.listApiKeys).mockResolvedValue([
    { id: 'key', provider: 'stepfun', is_active: true },
    { id: 'disabled', provider: 'openai', is_active: false },
  ]);
  vi.mocked(api.listTasks).mockResolvedValue([]);
  vi.mocked(api.getArcbenchStatus).mockResolvedValue(null as never);
  vi.mocked(api.runAutonomousSkillStream).mockReturnValue(abortStream);
  vi.mocked(api.stopTask).mockResolvedValue({ task_id: 'run', cancelled: true });
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

async function mount() {
  const view = render(<FactoryModePage />);
  await screen.findByText(/已读取 1 个启用 Agent、1 个供应商凭据配置/);
  return view;
}

function start() {
  fireEvent.change(screen.getByPlaceholderText('描述你想要智能体完成的目标...'), { target: { value: 'test goal' } });
  fireEvent.click(screen.getByRole('button', { name: '开始执行' }));
  const calls = vi.mocked(api.runAutonomousSkillStream).mock.calls;
  const call = calls[calls.length - 1];
  return { payload: call[0], event: call[1], close: call[2]! };
}

describe('Factory configuration review 2 (scripted, no real LLM)', () => {
  it('shows configuration sources separately from health and links existing pages', async () => {
    await mount();
    expect(screen.getByRole('link', { name: '配置模型 API Keys' })).toHaveAttribute('href', '#apikeys');
    expect(screen.getByRole('link', { name: '配置 Agent 模型' })).toHaveAttribute('href', '#agents');
    expect(screen.getByText(/服务可达、凭据有效、模型可用均待实际调用验证/)).toBeVisible();
    expect(screen.getByText(/Ollama 免 Key 仍需服务运行/)).toBeVisible();
    expect(screen.queryByRole('option', { name: /Disabled/ })).toBeNull();
    expect(api.listAgents).toHaveBeenCalledTimes(1);
    expect(api.listApiKeys).toHaveBeenCalledTimes(1);
  });

  it('keeps the existing automatic payload without model or credential defaults', async () => {
    await mount();
    expect(start().payload).toEqual({
      goal: 'test goal', skills: ['code_executor', 'web_search'], prompt_template: 'senior-engineer',
    });
  });

  it('sends a selected existing agent through the existing stream method', async () => {
    await mount();
    fireEvent.change(screen.getByLabelText('模型配置来源'), { target: { value: 'configured-agent' } });
    expect(start().payload).toMatchObject({ agent_id: 'configured-agent' });
  });

  it('requires an explicit model with a saved non-OpenAI provider', async () => {
    await mount();
    fireEvent.change(screen.getByLabelText('模型配置来源'), { target: { value: 'provider' } });
    fireEvent.change(screen.getByLabelText('供应商'), { target: { value: 'stepfun' } });
    fireEvent.change(screen.getByPlaceholderText('描述你想要智能体完成的目标...'), { target: { value: 'test goal' } });
    expect(screen.getByLabelText('模型 ID')).toHaveValue('');
    expect(screen.getByRole('button', { name: '开始执行' })).toBeDisabled();
    expect(screen.queryByRole('option', { name: 'openai' })).toBeNull();
    fireEvent.change(screen.getByLabelText('模型 ID'), { target: { value: '  user-step-model  ' } });
    const { payload } = start();
    expect(payload).toMatchObject({ provider: 'stepfun', model: 'user-step-model' });
    expect(payload).not.toHaveProperty('api_key');
    expect(payload).not.toHaveProperty('owner_id');
  });

  it('surfaces configuration read errors and allows refresh', async () => {
    vi.mocked(api.listApiKeys).mockRejectedValueOnce(new Error('configuration storage unavailable'));
    render(<FactoryModePage />);
    await screen.findByText('配置读取失败：configuration storage unavailable');
    fireEvent.click(screen.getByRole('button', { name: '刷新配置' }));
    await screen.findByText(/已读取 1 个启用 Agent、1 个供应商凭据配置/);
    expect(screen.queryByText(/configuration storage unavailable/)).toBeNull();
  });

  it('shows the actual backend-selected model without a health assertion', async () => {
    await mount();
    const stream = start();
    act(() => stream.event({ type: 'factory_config', data: { task_id: 'run', provider: 'anthropic', model: 'owner-model' } }));
    expect(screen.getByText('本次后端选择：anthropic / owner-model')).toBeVisible();
    expect(screen.queryByText('已完成')).toBeNull();
  });

  it('keeps a real HTTP 409 detail through the existing API stream implementation', async () => {
    const actual = await vi.importActual<typeof import('../../api')>('../../api');
    vi.mocked(api.runAutonomousSkillStream).mockImplementation((...args) => actual.api.runAutonomousSkillStream(...args));
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(
      JSON.stringify({ detail: 'Configure an active owner model API key' }),
      { status: 409, headers: { 'Content-Type': 'application/json' } },
    )));
    await mount();
    start();
    await screen.findByText('Configure an active owner model API key');
    expect(screen.getByText('执行失败')).toBeVisible();
    expect(screen.getByRole('link', { name: '配置模型 API Keys' })).toBeVisible();
    expect(screen.queryByText('已完成')).toBeNull();
  }, 20000);

  it('keeps factory failure even if synthesis or close arrives later', async () => {
    await mount();
    const stream = start();
    await act(async () => {
      stream.event({ type: 'factory_failed', data: { task_id: 'run', error: 'provider rejected selected model' } });
      stream.event({ type: 'synthesize', data: { report: 'late report' } });
      stream.close();
    });
    expect(screen.getByRole('alert')).toHaveTextContent('provider rejected selected model');
    expect(screen.getByText('执行失败')).toBeVisible();
    expect(screen.queryByText('已完成')).toBeNull();
    expect(screen.queryByText('late report')).toBeNull();
  });

  it('preserves a failed step across later completion', async () => {
    await mount();
    const stream = start();
    await act(async () => {
      stream.event({ type: 'task_failed', data: { task_id: 'step', step: 1, error: 'step failed' } });
      stream.event({ type: 'factory_completed', data: { task_id: 'run' } });
      stream.close();
    });
    expect(screen.getByRole('alert')).toHaveTextContent('step failed');
    expect(screen.getByText('执行失败')).toBeVisible();
  });

  it.each(['planning', 'synthesize'])('treats close during %s as unconfirmed, not completed', async phase => {
    await mount();
    const stream = start();
    await act(async () => {
      stream.event({ type: phase, data: { report: 'partial report' } });
      stream.close();
    });
    expect(screen.getByText('执行状态待确认')).toBeVisible();
    expect(screen.getByRole('alert')).toHaveTextContent('尚未收到任务终态');
    expect(screen.queryByText('已完成')).toBeNull();
  });

  it('marks success only on explicit backend completion', async () => {
    await mount();
    const stream = start();
    await act(async () => {
      stream.event({ type: 'synthesize', data: { report: 'scripted report' } });
      stream.event({ type: 'factory_completed', data: { task_id: 'run' } });
      stream.close();
    });
    expect(screen.getByText('已完成')).toBeVisible();
    expect(screen.queryByRole('alert')).toBeNull();
  });

  it('retains server cancellation as a distinct terminal state', async () => {
    await mount();
    const stream = start();
    await act(async () => {
      stream.event({ type: 'factory_failed', data: { task_id: 'run', status: 'cancelled', error: 'cancelled by owner' } });
      stream.close();
    });
    expect(screen.getByText('已取消')).toBeVisible();
    expect(screen.getByRole('alert')).toHaveTextContent('cancelled by owner');
  });

  it('waits for cancellation acknowledgement and ignores aborted stream callbacks', async () => {
    let acknowledge!: (value: { task_id: string; cancelled: boolean }) => void;
    vi.mocked(api.stopTask).mockReturnValue(new Promise(resolve => { acknowledge = resolve; }));
    await mount();
    const stream = start();
    act(() => stream.event({ type: 'factory_config', data: { task_id: 'run', provider: 'ollama', model: 'local-model' } }));
    fireEvent.click(screen.getByRole('button', { name: '停止' }));
    expect(screen.getByText('正在请求取消')).toBeVisible();
    expect(screen.getByRole('button', { name: '停止' })).toBeDisabled();
    expect(abortStream).not.toHaveBeenCalled();
    act(() => stream.close());
    expect(screen.queryByText('已完成')).toBeNull();
    await act(async () => acknowledge({ task_id: 'run', cancelled: true }));
    expect(api.stopTask).toHaveBeenCalledWith('run');
    expect(abortStream).toHaveBeenCalledTimes(1);
    expect(screen.getByText('已取消')).toBeVisible();
    const next = start();
    act(() => { stream.event({ type: 'error', data: { detail: 'old error' } }); stream.close(); });
    expect(screen.getByText('规划中')).toBeVisible();
    expect(screen.queryByText('old error')).toBeNull();
    await act(async () => { next.event({ type: 'factory_completed', data: {} }); next.close(); });
  });

  it('preserves cancellation API errors without claiming cancellation success', async () => {
    vi.mocked(api.stopTask).mockRejectedValue(new Error('task cancellation unavailable'));
    await mount();
    const stream = start();
    act(() => stream.event({ type: 'factory_start', data: { task_id: 'run' } }));
    fireEvent.click(screen.getByRole('button', { name: '停止' }));
    await screen.findByText('task cancellation unavailable');
    expect(screen.getByText('执行状态待确认')).toBeVisible();
    expect(screen.queryByText('已取消')).toBeNull();
    expect(abortStream).toHaveBeenCalledTimes(1);
  });

  it('treats stopping before task identity arrives as unconfirmed', async () => {
    await mount();
    const stream = start();
    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: '停止' }));
      stream.close();
    });
    expect(api.stopTask).not.toHaveBeenCalled();
    expect(screen.getByText('执行状态待确认')).toBeVisible();
    expect(screen.queryByText('已取消')).toBeNull();
  });

  it('keeps cancellation unconfirmed when the API declines it', async () => {
    vi.mocked(api.stopTask).mockResolvedValue({ task_id: 'run', cancelled: false });
    await mount();
    const stream = start();
    act(() => stream.event({ type: 'factory_start', data: { task_id: 'run' } }));
    await act(async () => fireEvent.click(screen.getByRole('button', { name: '停止' })));
    expect(screen.getByText('执行状态待确认')).toBeVisible();
    expect(screen.queryByText('已取消')).toBeNull();
    expect(abortStream).toHaveBeenCalledTimes(1);
  });

  it.each([
    ['factory_completed', {}, '已完成'],
    ['factory_failed', { status: 'cancelled', error: 'cancelled by owner' }, '已取消'],
    ['factory_failed', { status: 'failed', error: 'Ollama connection refused' }, '执行失败'],
  ] as const)('decodes %s via the real existing SSE API', async (type, data, label) => {
    const actual = await vi.importActual<typeof import('../../api')>('../../api');
    vi.mocked(api.runAutonomousSkillStream).mockImplementation((...args) => actual.api.runAutonomousSkillStream(...args));
    const body = `event: ${type}\ndata: ${JSON.stringify({ type, data })}\n\ndata: [DONE]\n\n`;
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(body, { headers: { 'Content-Type': 'text/event-stream' } })));
    await mount();
    start();
    await screen.findByText(label);
    expect(screen.getByRole('button', { name: '开始执行' })).toBeVisible();
    if ('error' in data) expect(screen.getByRole('alert')).toHaveTextContent(data.error);
  }, 20000);

  it('aborts on unmount and ignores late events', async () => {
    const view = await mount();
    const stream = start();
    view.unmount();
    expect(abortStream).toHaveBeenCalledTimes(1);
    act(() => { stream.event({ type: 'error', data: { detail: 'late' } }); stream.close(); });
    expect(api.listTasks).toHaveBeenCalledTimes(1);
  });
});
