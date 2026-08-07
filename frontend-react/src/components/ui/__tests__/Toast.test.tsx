import { describe, it, expect } from 'vitest';
import { render, screen, renderHook, act } from '@testing-library/react';
import { ToastProvider, ToastContainer, useToast } from '../Toast';

describe('ToastProvider', () => {
  it('renders children', () => {
    render(
      <ToastProvider>
        <span>App Content</span>
      </ToastProvider>
    );
    expect(screen.getByText('App Content')).toBeDefined();
  });
});

describe('ToastContainer', () => {
  it('renders nothing when there are no toasts', () => {
    const { container } = render(<ToastContainer toasts={[]} onRemove={() => {}} />);
    expect(container.firstChild).toBeNull();
  });

  it('renders toast messages', () => {
    render(
      <ToastContainer
        toasts={[{ id: '1', type: 'info', message: 'Hello toast' }]}
        onRemove={() => {}}
      />
    );
    expect(screen.getByText('Hello toast')).toBeDefined();
  });
});

describe('useToast', () => {
  it('returns toast helper api', () => {
    const { result } = renderHook(() => useToast());
    expect(typeof result.current.addToast).toBe('function');
    expect(typeof result.current.success).toBe('function');
    expect(typeof result.current.error).toBe('function');
    expect(typeof result.current.warning).toBe('function');
    expect(typeof result.current.info).toBe('function');
    expect(typeof result.current.loading).toBe('function');
    expect(result.current.toasts).toEqual([]);
  });

  it('success adds a toast', () => {
    const { result } = renderHook(() => useToast());
    act(() => {
      result.current.success('Saved!');
    });
    expect(result.current.toasts).toHaveLength(1);
    expect(result.current.toasts[0].message).toBe('Saved!');
    expect(result.current.toasts[0].type).toBe('success');
  });
});
