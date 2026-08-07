import { describe, it, expect, vi } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useClipboardPaste } from '../useClipboardPaste';

function createPasteEvent(items?: any[]) {
  const event = new Event('paste');
  Object.defineProperty(event, 'clipboardData', { value: { items } });
  return event;
}

describe('useClipboardPaste', () => {
  it('calls onPaste with image files', () => {
    const onPaste = vi.fn();
    renderHook(() => useClipboardPaste(onPaste));
    const file = new File(['data'], 'photo.png', { type: 'image/png' });
    const event = createPasteEvent([
      { type: 'image/png', getAsFile: () => file },
      { type: 'text/plain', getAsFile: () => new File(['hi'], 'a.txt', { type: 'text/plain' }) },
    ]);
    act(() => {
      document.dispatchEvent(event);
    });
    expect(onPaste).toHaveBeenCalledWith([file]);
  });

  it('ignores paste events without image files', () => {
    const onPaste = vi.fn();
    renderHook(() => useClipboardPaste(onPaste));
    const event = createPasteEvent([
      { type: 'text/plain', getAsFile: () => new File(['hi'], 'a.txt', { type: 'text/plain' }) },
    ]);
    act(() => {
      document.dispatchEvent(event);
    });
    expect(onPaste).not.toHaveBeenCalled();
  });

  it('ignores paste events without clipboard items', () => {
    const onPaste = vi.fn();
    renderHook(() => useClipboardPaste(onPaste));
    act(() => {
      document.dispatchEvent(createPasteEvent(undefined));
    });
    expect(onPaste).not.toHaveBeenCalled();
  });

  it('removes the listener on unmount', () => {
    const onPaste = vi.fn();
    const { unmount } = renderHook(() => useClipboardPaste(onPaste));
    unmount();
    act(() => {
      document.dispatchEvent(
        createPasteEvent([
          { type: 'image/png', getAsFile: () => new File(['d'], 'x.png', { type: 'image/png' }) },
        ]),
      );
    });
    expect(onPaste).not.toHaveBeenCalled();
  });
});
