import { fireEvent, render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import i18n from '../../i18n';
import { SessionBatchToolbar } from './SessionBatchToolbar';

beforeEach(async () => {
  await i18n.changeLanguage('zh-CN');
});

const items = [
  { id: 'a', title: 'Read architecture doc' },
  { id: 'b', title: 'Fix login bug' },
  { id: 'c', title: 'Refactor store' },
];

function selectAll(): HTMLInputElement {
  return screen.getByRole('checkbox', { name: '全选' }) as HTMLInputElement;
}

describe('SessionBatchToolbar — 侧栏批量操作', () => {
  it('空列表渲染空态', () => {
    render(<SessionBatchToolbar items={[]} onArchive={vi.fn()} />);
    expect(screen.getByTestId('session-batch-toolbar')).toHaveAttribute('data-state', 'empty');
    expect(screen.getByText('没有可批量操作的会话')).toBeVisible();
  });

  it('渲染会话行，初始已选 0 项且动作禁用', () => {
    render(<SessionBatchToolbar items={items} onArchive={vi.fn()} onDelete={vi.fn()} />);
    expect(screen.getAllByTestId('session-batch-row')).toHaveLength(3);
    expect(screen.getByText('已选 0 项')).toBeVisible();
    expect(screen.getByRole('button', { name: /归档所选/ })).toBeDisabled();
    expect(screen.getByRole('button', { name: /删除所选/ })).toBeDisabled();
  });

  it('全选后计数更新、全选框勾选、动作解禁', () => {
    render(<SessionBatchToolbar items={items} onArchive={vi.fn()} onDelete={vi.fn()} />);
    fireEvent.click(selectAll());
    expect(screen.getByText('已选 3 项')).toBeVisible();
    expect(selectAll().checked).toBe(true);
    expect(screen.getByRole('button', { name: /归档所选/ })).toBeEnabled();
  });

  it('部分选择时全选框进入不确定态', () => {
    render(<SessionBatchToolbar items={items} onArchive={vi.fn()} />);
    fireEvent.click(screen.getByRole('checkbox', { name: '选择 Fix login bug' }));
    expect(selectAll().indeterminate).toBe(true);
    expect(selectAll().checked).toBe(false);
    expect(screen.getByText('已选 1 项')).toBeVisible();
  });

  it('归档提交所选 id 后清空选择', () => {
    const onArchive = vi.fn();
    render(<SessionBatchToolbar items={items} onArchive={onArchive} />);
    fireEvent.click(screen.getByRole('checkbox', { name: '选择 Read architecture doc' }));
    fireEvent.click(screen.getByRole('checkbox', { name: '选择 Refactor store' }));
    fireEvent.click(screen.getByRole('button', { name: /归档所选/ }));

    expect(onArchive).toHaveBeenCalledWith(['a', 'c']);
    expect(screen.getByText('已选 0 项')).toBeVisible();
  });

  it('删除提交所选 id', () => {
    const onDelete = vi.fn();
    render(<SessionBatchToolbar items={items} onDelete={onDelete} />);
    fireEvent.click(selectAll());
    fireEvent.click(screen.getByRole('button', { name: /删除所选/ }));
    expect(onDelete).toHaveBeenCalledWith(['a', 'b', 'c']);
  });

  it('退出按钮回调，且忙碌时全部锁定', () => {
    const onExit = vi.fn();
    const { rerender } = render(<SessionBatchToolbar items={items} onArchive={vi.fn()} onExit={onExit} />);
    fireEvent.click(screen.getByRole('button', { name: '退出批量模式' }));
    expect(onExit).toHaveBeenCalledTimes(1);

    rerender(<SessionBatchToolbar items={items} onArchive={vi.fn()} onExit={onExit} busy />);
    expect(selectAll()).toBeDisabled();
    expect(screen.getByRole('checkbox', { name: '选择 Fix login bug' })).toBeDisabled();
    expect(screen.getByRole('button', { name: /归档所选/ })).toBeDisabled();
  });
});
