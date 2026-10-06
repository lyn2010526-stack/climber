import { fireEvent, render, screen, within } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import i18n from '../../i18n';
import { ApprovalQueueRail } from './ApprovalQueueRail';
import type { ApprovalQueueItem } from './ApprovalQueueRail';

beforeEach(async () => {
  await i18n.changeLanguage('zh-CN');
});

const items: ApprovalQueueItem[] = [
  { id: 'a', title: 'Run command', subject: 'echo hello', severity: 'low' },
  { id: 'b', title: 'Edit file', subject: '/tmp/target.md', severity: 'high' },
];

function itemRow(title: string): HTMLElement {
  const row = screen.getAllByTestId('approval-queue-item').find((node) =>
    node.textContent?.includes(title),
  );
  if (!row) throw new Error(`no approval row for ${title}`);
  return row;
}

describe('ApprovalQueueRail — 审批队列总览', () => {
  it('空队列渲染无待审批状态', () => {
    render(<ApprovalQueueRail items={[]} onDecision={vi.fn()} />);
    const rail = screen.getByTestId('approval-queue-rail');
    expect(rail).toHaveAttribute('data-state', 'empty');
    expect(rail).toHaveTextContent('当前没有待审批的请求');
  });

  it('渲染队列数量与每一项的标题、目标与严重度', () => {
    render(<ApprovalQueueRail items={items} onDecision={vi.fn()} />);
    const rail = screen.getByTestId('approval-queue-rail');
    expect(rail).toHaveAttribute('data-state', 'populated');
    expect(rail).toHaveTextContent('2 项待审批');
    expect(itemRow('Run command')).toHaveTextContent('echo hello');
    expect(itemRow('Edit file')).toHaveTextContent('/tmp/target.md');
    expect(screen.getAllByTestId('approval-queue-item')).toHaveLength(2);
  });

  it('单项批准 / 拒绝各自回调对应 id', () => {
    const onDecision = vi.fn();
    render(<ApprovalQueueRail items={items} onDecision={onDecision} />);

    fireEvent.click(within(itemRow('Run command')).getByRole('button', { name: '批准：Run command' }));
    expect(onDecision).toHaveBeenCalledWith('a', 'allow');

    fireEvent.click(within(itemRow('Edit file')).getByRole('button', { name: '拒绝：Edit file' }));
    expect(onDecision).toHaveBeenCalledWith('b', 'deny');
  });

  it('批量按钮对所有可提交项一次性投递决策', () => {
    const onBatchDecision = vi.fn();
    render(<ApprovalQueueRail items={items} onDecision={vi.fn()} onBatchDecision={onBatchDecision} />);

    fireEvent.click(screen.getByRole('button', { name: '全部批准' }));
    expect(onBatchDecision).toHaveBeenCalledWith(['a', 'b'], 'allow');

    fireEvent.click(screen.getByRole('button', { name: '全部拒绝' }));
    expect(onBatchDecision).toHaveBeenCalledWith(['a', 'b'], 'deny');
  });

  it('缺少可提交标识的项被锁住并排除出批量决策', () => {
    const onDecision = vi.fn();
    const onBatchDecision = vi.fn();
    render(
      <ApprovalQueueRail
        items={[{ id: 'a', title: 'Run command' }, { id: 'c', title: 'Unknown request', resolvable: false }]}
        onDecision={onDecision}
        onBatchDecision={onBatchDecision}
      />,
    );

    const locked = itemRow('Unknown request');
    expect(within(locked).getByRole('button', { name: '批准：Unknown request' })).toBeDisabled();
    expect(locked).toHaveTextContent('仅能关闭');

    fireEvent.click(screen.getByRole('button', { name: '全部批准' }));
    expect(onBatchDecision).toHaveBeenCalledWith(['a'], 'allow');
  });

  it('提交中的项锁定控件并显示进度', () => {
    render(<ApprovalQueueRail items={items} onDecision={vi.fn()} pendingIds={['a']} />);
    const pendingRow = itemRow('Run command');
    expect(pendingRow).toHaveAttribute('data-pending', 'true');
    expect(within(pendingRow).getByText('提交中…')).toBeVisible();
    expect(within(pendingRow).getByRole('button', { name: '批准：Run command' })).toBeDisabled();
  });

  it('未接入批量回调时不渲染批量按钮', () => {
    render(<ApprovalQueueRail items={items} onDecision={vi.fn()} />);
    expect(screen.queryByRole('button', { name: '全部批准' })).toBeNull();
  });
});
