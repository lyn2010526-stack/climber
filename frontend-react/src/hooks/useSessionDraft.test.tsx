import { StrictMode } from 'react';
import { act, cleanup, renderHook } from '@testing-library/react';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { useSessionDraft } from './useSessionDraft';

beforeEach(() => localStorage.clear());
afterEach(() => { cleanup(); vi.restoreAllMocks(); });

it('isolates session text and restores it across switching and keyed remounts', () => {
  const hook = renderHook(({ id }) => useSessionDraft(id), { initialProps: { id: 'A' }, wrapper: StrictMode });
  act(() => hook.result.current.setText(' A\n草稿 '));
  hook.rerender({ id: 'B' });
  expect(hook.result.current.text).toBe('');
  act(() => hook.result.current.setText('B draft'));
  hook.rerender({ id: 'A' });
  expect(hook.result.current.text).toBe(' A\n草稿 ');
  hook.unmount();
  expect(renderHook(() => useSessionDraft('B')).result.current.text).toBe('B draft');
});

it('persists cleared text and keeps a missing session separate', () => {
  const hook = renderHook(({ id }) => useSessionDraft(id), { initialProps: { id: null as string | null } });
  act(() => hook.result.current.setText('unbound'));
  expect(localStorage.length).toBe(0);
  hook.rerender({ id: 'A' });
  expect(hook.result.current.text).toBe('');
  act(() => hook.result.current.setText('saved'));
  act(() => hook.result.current.setText(''));
  hook.unmount();
  expect(renderHook(() => useSessionDraft('A')).result.current.text).toBe('');
});

it('retains editable text when storage is unavailable and reports the limitation', () => {
  vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => { throw new Error('blocked'); });
  vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => { throw new Error('quota'); });
  const hook = renderHook(() => useSessionDraft('A'));
  act(() => hook.result.current.setText('still editable'));
  expect(hook.result.current.text).toBe('still editable');
  expect(hook.result.current.storageError).toContain('草稿暂存失败');
});
