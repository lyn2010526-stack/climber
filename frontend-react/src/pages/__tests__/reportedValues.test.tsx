import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, act } from '@testing-library/react';
import { EvalDashboard } from '../../components/eval/EvalDashboard';
import { FactoryModePage } from '../FactoryModePage';
import PluginPage from '../PluginPage';
import i18n from '../../i18n';

vi.mock('../../api', () => ({
  api: {
    listEvalDatasets: vi.fn(),
    listAgents: vi.fn(),
    runEvaluation: vi.fn(),
    listEvalReports: vi.fn(),
    evaluateOutput: vi.fn(),
    runAutonomousSkillStream: vi.fn(),
    stopTask: vi.fn(),
    getTask: vi.fn(),
    listTasks: vi.fn(),
    getArcbenchStatus: vi.fn(),
    listApiKeys: vi.fn(),
    listPlugins: vi.fn(),
    enablePlugin: vi.fn(),
    disablePlugin: vi.fn(),
    uninstallPlugin: vi.fn(),
    importPlugin: vi.fn(),
  },
}));

import { api } from '../../api';

const dataset = { id: 'ds-1', name: 'Suite', description: 'Cases', case_count: 4, created_at: '2026-01-01T00:00:00' };

beforeEach(async () => {
  await i18n.changeLanguage('zh-CN');
  vi.clearAllMocks();
  vi.mocked(api.listEvalDatasets).mockResolvedValue([dataset] as never);
  vi.mocked(api.listAgents).mockResolvedValue([{ id: 'agent-1', name: 'Nova' }] as never);
  vi.mocked(api.listEvalReports).mockResolvedValue([] as never);
  vi.mocked(api.runEvaluation).mockResolvedValue({
    id: 'run-abcdef01',
    dataset_id: 'ds-1',
    agent_id: 'agent-1',
    total_cases: 0,
    passed_cases: 0,
    failed_cases: 0,
    average_score: 0,
    pass_rate: 0,
    created_at: '2026-01-01T00:00:00',
  } as never);
  vi.mocked(api.listTasks).mockResolvedValue([] as never);
  vi.mocked(api.getArcbenchStatus).mockResolvedValue({
    available: false, message: 'none', phase: 'idle', phase_detail: '',
  } as never);
  vi.mocked(api.listApiKeys).mockResolvedValue([] as never);
  vi.mocked(api.runAutonomousSkillStream).mockImplementation((_data, _onEvent, _onClose) => () => {});
  vi.mocked(api.getTask).mockResolvedValue({} as never);
  vi.mocked(api.listPlugins).mockResolvedValue([] as never);
});

async function runEvaluation() {
  render(<EvalDashboard />);
  await screen.findByText('Suite');
  fireEvent.click(screen.getByText('Suite'));
  fireEvent.click(screen.getByText('运行'));
}

describe('EvalDashboard reports runs the backend never executed', () => {
  it('does not render a 0% pass rate for a run that executed no cases', async () => {
    await runEvaluation();

    expect(await screen.findByText('没有可运行的测试用例')).toBeInTheDocument();
    expect(screen.queryByText('通过率')).not.toBeInTheDocument();
    expect(screen.queryByText('0%')).not.toBeInTheDocument();
  });

  it('says the API returned no per-case detail instead of an empty list', async () => {
    await runEvaluation();

    // `POST /eval/run` stores results_json but omits it from the response, so an
    // absent `results` field is the normal case and must be stated, not implied.
    expect(await screen.findByText('暂无用例结果')).toBeInTheDocument();
  });

  it('renders the real pass rate once a run reports executed cases', async () => {
    vi.mocked(api.runEvaluation).mockResolvedValue({
      id: 'run-abcdef02',
      dataset_id: 'ds-1',
      agent_id: 'agent-1',
      total_cases: 4,
      passed_cases: 3,
      failed_cases: 1,
      average_score: 0.75,
      pass_rate: 0.75,
      results: [{ case_id: 'c1', score: 0.9, passed: true, reasoning: '' }],
      created_at: '2026-01-01T00:00:00',
    } as never);

    await runEvaluation();

    expect(await screen.findByText('75%')).toBeInTheDocument();
    expect(screen.queryByText('没有可运行的测试用例')).not.toBeInTheDocument();
  });

  it('reports a failed dataset request instead of an empty dataset list', async () => {
    vi.mocked(api.listEvalDatasets).mockRejectedValue(new Error('down') as never);

    render(<EvalDashboard />);

    expect(await screen.findByText('暂无可用数据集')).toBeInTheDocument();
    expect(screen.queryByText('未找到数据集')).not.toBeInTheDocument();
  });

  it('reports a failed agent request instead of offering an empty selector', async () => {
    vi.mocked(api.listAgents).mockRejectedValue(new Error('down') as never);

    render(<EvalDashboard />);

    expect(await screen.findByText('暂无可用智能体')).toBeInTheDocument();
    expect(screen.queryByText('请选择智能体')).not.toBeInTheDocument();
  });
});

describe('FactoryModePage measures nothing the backend did not report', () => {
  it('shows the run duration as unreported while the task record has no stamps', async () => {
    vi.mocked(api.getTask).mockResolvedValue({ task_id: 't1', status: 'completed' } as never);

    render(<FactoryModePage />);
    const textarea = screen.getByPlaceholderText('描述您希望智能体完成的目标...');
    fireEvent.change(textarea, { target: { value: 'build a demo' } });
    fireEvent.click(screen.getByText('开始运行'));

    expect(await screen.findByText('暂无运行时长')).toBeInTheDocument();
    // No locally ticking clock: a browser-side counter never appears.
    expect(screen.queryByText(/已运行 00:/)).not.toBeInTheDocument();
  });

  it('shows the duration the backend recorded from its own start and finish stamps', async () => {
    vi.mocked(api.runAutonomousSkillStream).mockImplementation((_data, onEvent, _onClose) => {
      onEvent({ type: 'factory_config', data: { task_id: 't1', provider: 'openai', model: 'gpt-4o' } });
      return () => {};
    });
    vi.mocked(api.getTask).mockResolvedValue({
      task_id: 't1',
      status: 'completed',
      created_at: '2026-01-01T00:00:00Z',
      finished_at: '2026-01-01T00:02:30Z',
    } as never);

    render(<FactoryModePage />);
    const textarea = screen.getByPlaceholderText('描述您希望智能体完成的目标...');
    fireEvent.change(textarea, { target: { value: 'build a demo' } });
    fireEvent.click(screen.getByText('开始运行'));

    const call = vi.mocked(api.runAutonomousSkillStream).mock.calls[0];
    await act(async () => { (call[2] as () => void)(); });

    expect(await screen.findByText(/已运行 02:30/)).toBeInTheDocument();
  });

  it('does not mark every stage complete just because the run ended', async () => {
    vi.mocked(api.runAutonomousSkillStream).mockImplementation((_data, onEvent, _onClose) => {
      onEvent({ type: 'factory_config', data: { task_id: 't1', provider: 'openai', model: 'gpt-4o' } });
      onEvent({ type: 'plan', data: { steps: [{ step: 1, description: 'step one' }] } });
      return () => {};
    });

    render(<FactoryModePage />);
    const textarea = screen.getByPlaceholderText('描述您希望智能体完成的目标...');
    fireEvent.change(textarea, { target: { value: 'build a demo' } });
    fireEvent.click(screen.getByText('开始运行'));

    const call = vi.mocked(api.runAutonomousSkillStream).mock.calls[0];
    await act(async () => {
      (call[1] as (e: { type: string; data: unknown }) => void)({ type: 'factory_completed', data: { task_id: 't1' } });
      (call[2] as () => void)();
    });

    // The synthesis badge exists; the run reported no synthesize event, so it
    // must not carry the success styling that a completed stage gets.
    const synthesis = await screen.findByText('综合');
    const badge = synthesis.closest('span');
    expect(badge?.className).not.toContain('--color-success');
    // The two stages the stream did report past stay marked done.
    const planning = screen.getByText('规划');
    expect(planning.closest('span')?.className).toContain('--color-success');
  });
});

describe('PluginPage reports statuses the backend never declared', () => {
  it('labels an unrecognised status as not reported', async () => {
    vi.mocked(api.listPlugins).mockResolvedValue([
      { id: 'p1', name: 'Mystery', type: 'mcp', source: 'builtin', status: 'quarantined', description: '', icon: '', category: '', version: '1.0.0', config: {}, error: null },
    ] as never);

    render(<PluginPage />);

    expect(await screen.findByText('状态未上报', { selector: '[role="status"]' })).toBeInTheDocument();
    expect(screen.queryByText('已安装')).not.toBeInTheDocument();
  });
});
