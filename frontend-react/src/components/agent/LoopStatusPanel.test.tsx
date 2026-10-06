import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it } from 'vitest';
import { resetAnchoredStore, useAnchoredStore } from '../../store/anchored';
import { LoopStatusPanel } from './LoopStatusPanel';

beforeEach(() => resetAnchoredStore());

describe('LoopStatusPanel — 外层循环快照', () => {
  it('无快照时显示等待态', () => {
    render(<LoopStatusPanel />);
    expect(screen.getByTestId('loop-status')).toBeInTheDocument();
  });

  it('有快照时渲染当前子任务，队列明细默认折叠可展开', async () => {
    const user = userEvent.setup();
    useAnchoredStore.setState({
      loopStatus: {
        outerRound: 2,
        currentInput: 'fix the login bug',
        completed: ['scan'],
        followupQueue: ['retry deploy'],
        steeringQueue: ['use manual mode'],
        noProgressCount: 0,
      },
    });
    render(<LoopStatusPanel />);
    const section = screen.getByTestId('loop-status');
    expect(section.textContent).toContain('fix the login bug');
    const queues = screen.getByTestId('loop-status-queues');
    expect(queues.textContent).not.toContain('retry deploy');
    await user.click(screen.getByRole('button', { name: /队列明细|Queue/ }));
    expect(section.textContent).toContain('retry deploy');
    expect(section.textContent).toContain('use manual mode');
    await user.click(screen.getByRole('button', { name: /已完成|Completed/ }));
    expect(section.textContent).toContain('scan');
  });

  it('无进展 > 0 时徽标优先显示无进展并渲染 amber 警告条带', () => {
    useAnchoredStore.setState({
      loopStatus: {
        outerRound: 4,
        currentInput: 'stuck task',
        completed: [],
        followupQueue: ['q'],
        steeringQueue: [],
        noProgressCount: 3,
      },
    });
    render(<LoopStatusPanel />);
    expect(screen.getByTestId('loop-status-badge').textContent).toMatch(/无进展|No progress/);
    expect(screen.getByTestId('loop-status-warning')).toBeInTheDocument();
    expect(screen.getByTestId('loop-status')).toHaveAttribute('data-tone', 'warning');
  });

  it('队列为空且无进展时徽标显示轮数', () => {
    useAnchoredStore.setState({
      loopStatus: {
        outerRound: 7,
        currentInput: 'simple task',
        completed: [],
        followupQueue: [],
        steeringQueue: [],
        noProgressCount: 0,
      },
    });
    render(<LoopStatusPanel />);
    expect(screen.getByTestId('loop-status-badge').textContent).toMatch(/round|轮/i);
    expect(screen.getByTestId('loop-status').textContent).toContain('R07');
  });

  it('运行中快照带 running 色点，徽标显示待处理计数', () => {
    useAnchoredStore.setState({
      loopStatus: {
        outerRound: 1,
        currentInput: 'running task',
        completed: [],
        followupQueue: ['a'],
        steeringQueue: ['b'],
        noProgressCount: 0,
      },
    });
    render(<LoopStatusPanel />);
    expect(screen.getByTestId('loop-status-dot')).toHaveAttribute('data-tone', 'running');
    expect(screen.getByTestId('loop-status-badge').textContent).toMatch(/2|待处理|queued/i);
    expect(screen.getByTestId('loop-status')).toHaveAttribute('data-tone', 'running');
  });
});