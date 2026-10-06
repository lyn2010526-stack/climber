import { act, renderHook } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { useSessionBatchSelection } from './sessionBatchSelection';

describe('useSessionBatchSelection', () => {
  it('初始未选中任何项', () => {
    const { result } = renderHook(() => useSessionBatchSelection(['a', 'b']));
    expect(result.current.count).toBe(0);
    expect(result.current.selectedIds).toEqual([]);
    expect(result.current.allSelected).toBe(false);
    expect(result.current.someSelected).toBe(false);
  });

  it('单项切换加入与移除', () => {
    const { result } = renderHook(() => useSessionBatchSelection(['a', 'b']));
    act(() => result.current.toggle('a'));
    expect(result.current.selectedIds).toEqual(['a']);
    expect(result.current.someSelected).toBe(true);
    expect(result.current.isSelected('a')).toBe(true);

    act(() => result.current.toggle('a'));
    expect(result.current.count).toBe(0);
  });

  it('全选与取消全选', () => {
    const { result } = renderHook(() => useSessionBatchSelection(['a', 'b']));
    act(() => result.current.toggleAll(true));
    expect(result.current.allSelected).toBe(true);
    expect(result.current.someSelected).toBe(false);

    act(() => result.current.toggleAll(false));
    expect(result.current.count).toBe(0);
  });

  it('列表收缩时被移除的 id 不再计入选择', () => {
    const { result, rerender } = renderHook(
      ({ ids }: { ids: string[] }) => useSessionBatchSelection(ids),
      { initialProps: { ids: ['a', 'b'] } },
    );
    act(() => result.current.toggleAll(true));
    expect(result.current.count).toBe(2);

    rerender({ ids: ['a'] });
    expect(result.current.selectedIds).toEqual(['a']);
    expect(result.current.count).toBe(1);
    expect(result.current.allSelected).toBe(true);
  });

  it('clear 清空选择', () => {
    const { result } = renderHook(() => useSessionBatchSelection(['a', 'b']));
    act(() => result.current.toggleAll(true));
    act(() => result.current.clear());
    expect(result.current.count).toBe(0);
  });
});
