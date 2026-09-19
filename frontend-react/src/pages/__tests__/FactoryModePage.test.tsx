import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import { FactoryModePage } from '../FactoryModePage';

vi.mock('../../api', () => ({
  api: {
    runAutonomousSkillStream: vi.fn(),
    stopTask: vi.fn(),
    listTasks: vi.fn(),
    getArcbenchStatus: vi.fn(),
  },
}));

import { api } from '../../api';

const arcbenchSample = {
  available: true,
  message: 'ARC-Bench run artifacts detected',
  output_dir: '/workspace/climber/workspace/run-1',
  phase: 'acceptance',
  phase_detail: 'acceptance: 1 passed, 1 failed',
  trace_path: '/workspace/climber/workspace/run-1/.arc/traceability',
  trace_exists: true,
  acceptance: { ran: true, passed: 1, failed: 1, unverified: 0, note: '1 passed, 1 failed' },
  last_events: [{ type: 'runner_state', timestamp: '2026-09-18 10:05:00', data: { state: 'completed' } }],
  pack_artifact: '/workspace/climber/dist/climber-arcbench-20260918.zip',
  pack_exists: true,
  updated_at: '2026-09-18 10:05:00',
};

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(api.listTasks).mockResolvedValue([
    { task_id: 'abc123', objective: 'ship it', status: 'completed', progress: 3, total_steps: 3, created_at: '2026-09-18T00:00:00Z' },
  ]);
  vi.mocked(api.getArcbenchStatus).mockResolvedValue(arcbenchSample as any);
  vi.mocked(api.runAutonomousSkillStream).mockImplementation((_data, _onEvent, _onClose) => () => {});
});

function captureStream() {
  const call = vi.mocked(api.runAutonomousSkillStream).mock.calls[vi.mocked(api.runAutonomousSkillStream).mock.calls.length - 1];
  return { onEvent: call[1] as (e: { type: string; data: any }) => void, onClose: call[2] as () => void };
}

function startRun() {
  const textarea = screen.getByPlaceholderText('描述你想要智能体完成的目标...');
  fireEvent.change(textarea, { target: { value: 'build a demo' } });
  fireEvent.click(screen.getByText('开始执行'));
}

describe('FactoryModePage upgraded console', () => {
  it('loads recent runs and ARC-Bench delivery status on mount', async () => {
    render(<FactoryModePage />);
    await waitFor(() => expect(screen.getByText('最近运行')).toBeDefined());
    expect(screen.getByText('ship it')).toBeDefined();
    expect(screen.getByText(/abc123/)).toBeDefined();
    await waitFor(() => expect(screen.getByText('ARC-Bench 交付状态')).toBeDefined());
    expect(screen.getByText('1 通过 · 1 失败')).toBeDefined();
    expect(screen.getByText('climber-arcbench-20260918.zip')).toBeDefined();
  });

  it('renders idle empty state before any run', () => {
    render(<FactoryModePage />);
    expect(screen.getByText('等待执行')).toBeDefined();
  });

  it('starts the run through the service layer stream and renders plan tool badges', async () => {
    render(<FactoryModePage />);
    await waitFor(() => expect(screen.getByText('开始执行')).toBeDefined());
    startRun();

    expect(api.runAutonomousSkillStream).toHaveBeenCalledTimes(1);
    expect(vi.mocked(api.runAutonomousSkillStream).mock.calls[0][0]).toMatchObject({
      goal: 'build a demo',
      skills: ['code_executor', 'web_search'],
      prompt_template: 'senior-engineer',
    });

    const { onEvent } = captureStream();
    act(() => {
      onEvent({ type: 'planning', data: { message: 'Creating execution plan' } });
      onEvent({
        type: 'plan',
        data: {
          steps: [
            { step: 1, action: 'Research evidence', tool: 'web_search', status: 'pending' },
            { step: 2, action: 'Implement the change', tool: 'run_command', status: 'pending' },
          ],
        },
      });
    });

    await waitFor(() => expect(screen.getByText('Research evidence')).toBeDefined());
    expect(screen.getByText('web_search')).toBeDefined();
    expect(screen.getByText('run_command')).toBeDefined();
    expect(screen.getByText('0/2 步完成')).toBeDefined();
    expect(screen.getByText('执行')).toBeDefined();
  });

  it('renders progress lines and the auto-plan fallback banner', () => {
    render(<FactoryModePage />);
    startRun();
    const { onEvent } = captureStream();

    act(() => {
      onEvent({
        type: 'plan',
        data: { steps: [{ step: 1, action: 'Do it', tool: 'run_command', status: 'pending' }] },
      });
      onEvent({ type: 'progress', data: { task_id: 't1', step: 1, current: 1, total: 3, message: 'Running iteration 1' } });
    });
    expect(screen.getByText('Running iteration 1')).toBeDefined();

    act(() => {
      onEvent({ type: 'plan_fallback', data: { reason: 'planner output invalid' } });
    });
    expect(screen.getByText('已回退到自动计划')).toBeDefined();
  });

  it('marks plan steps done and surfaces the final report after synthesize + close', async () => {
    render(<FactoryModePage />);
    startRun();
    const { onEvent, onClose } = captureStream();

    act(() => {
      onEvent({
        type: 'plan',
        data: { steps: [{ step: 1, action: 'Do it', tool: 'run_command', status: 'pending' }] },
      });
      onEvent({ type: 'task_start', data: { task_id: 't1', step: 1, description: 'Do it' } });
      onEvent({ type: 'task_complete', data: { task_id: 't1', step: 1, result: 'ok' } });
      onEvent({ type: 'synthesize', data: { report: 'Final answer text' } });
    });

    await waitFor(() => expect(screen.getByText('Final answer text')).toBeDefined());
    expect(screen.getByText('1/1 步完成')).toBeDefined();

    act(() => onClose());
    await waitFor(() => expect(screen.getByText('开始执行')).toBeDefined());
    expect(api.listTasks).toHaveBeenCalledTimes(2);
  });

  it('cancels via stopTask and aborts the local stream', async () => {
    vi.mocked(api.stopTask).mockResolvedValue({ task_id: 'abc', cancelled: true } as any);
    render(<FactoryModePage />);
    startRun();
    const { onEvent } = captureStream();
    act(() => {
      onEvent({ type: 'factory_start', data: { task_id: 'run-9' } });
    });

    fireEvent.click(screen.getByText('停止'));
    expect(api.stopTask).toHaveBeenCalledWith('run-9');
    await waitFor(() => expect(screen.getByText('开始执行')).toBeDefined());
  });
});
