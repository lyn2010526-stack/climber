import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { ProgressHeader } from '../ProgressHeader';

describe('ProgressHeader', () => {
  it('renders without crashing', () => {
    const { container } = render(
      <ProgressHeader status="running" currentRound={1} maxRounds={5} />
    );
    expect(container).toBeDefined();
  });

  it('renders status label', () => {
    render(<ProgressHeader status="running" currentRound={1} maxRounds={5} />);
    expect(screen.getByText('执行中')).toBeDefined();
  });

  it('renders round info', () => {
    render(<ProgressHeader status="running" currentRound={2} maxRounds={5} />);
    expect(screen.getByText('轮次 2/5')).toBeDefined();
  });

  it('renders active member', () => {
    render(
      <ProgressHeader status="running" currentRound={1} maxRounds={5} activeMember="Agent 1" />
    );
    expect(screen.getByText('Agent 1 执行中...')).toBeDefined();
  });

  it('renders token usage', () => {
    render(
      <ProgressHeader status="running" currentRound={1} maxRounds={5} totalTokens={1500} />
    );
    expect(screen.getByText('1,500 tokens')).toBeDefined();
  });

  it('renders elapsed time', () => {
    render(
      <ProgressHeader status="running" currentRound={1} maxRounds={5} elapsedTime={65} />
    );
    expect(screen.getByText('1:05')).toBeDefined();
  });

  it('renders pause and stop buttons when running', () => {
    const onPause = vi.fn();
    const onStop = vi.fn();
    render(
      <ProgressHeader
        status="running"
        currentRound={1}
        maxRounds={5}
        onPause={onPause}
        onStop={onStop}
      />
    );
    fireEvent.click(screen.getByTitle('暂停'));
    expect(onPause).toHaveBeenCalled();
    fireEvent.click(screen.getByTitle('停止'));
    expect(onStop).toHaveBeenCalled();
  });

  it('renders completed status', () => {
    render(<ProgressHeader status="completed" currentRound={5} maxRounds={5} />);
    expect(screen.getByText('已完成')).toBeDefined();
  });

  it('renders failed status', () => {
    render(<ProgressHeader status="failed" currentRound={2} maxRounds={5} />);
    expect(screen.getByText('失败')).toBeDefined();
  });
});
