import { describe, it, expect, vi, beforeEach } from 'vitest';
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MobileChatPage } from '../../MobileChatPage';

const state = vi.hoisted(() => ({
  sessionId: 'test-session' as string | null,
  creationError: null as string | null,
  sendMessage: vi.fn(),
  refresh: vi.fn(),
}));

vi.mock('../../../useChat', () => ({
  useChat: () => ({
    messages: [],
    isStreaming: false,
    error: null,
    sendMessage: state.sendMessage,
    stopStreaming: vi.fn(),
    refresh: state.refresh,
  }),
}));

vi.mock('../../../hooks/useDefaultSession', () => ({
  useDefaultSession: () => state,
}));
vi.mock('../../../components/mobile/LazyImage', () => ({
  cacheManager: { set: vi.fn().mockRejectedValue(new Error('Cache unavailable')) },
}));

class FakeVisualViewport extends EventTarget {
  height: number;
  offsetTop: number;
  scale = 1;
  constructor(height: number) {
    super();
    this.height = height;
    this.offsetTop = 0;
  }
}

describe('MobileChatPage', () => {
  beforeEach(() => {
    state.sessionId = 'test-session';
    state.creationError = null;
    vi.clearAllMocks();
    vi.unstubAllGlobals();
  });

  it('renders chat interface', () => {
    render(<MobileChatPage />);
    expect(screen.getByText('新对话')).toBeDefined();
  });

  it('sends through useChat even when optional caching fails', async () => {
    render(<MobileChatPage />);
    fireEvent.change(screen.getByRole('textbox'), { target: { value: '测试消息' } });
    fireEvent.click(screen.getByRole('button', { name: '发送消息' }));
    await waitFor(() => expect(state.sendMessage).toHaveBeenCalledExactlyOnceWith('测试消息'));
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });

  it('preserves text and reports session creation failure', () => {
    state.sessionId = null;
    state.creationError = '创建失败';
    render(<MobileChatPage />);
    fireEvent.change(screen.getByRole('textbox'), { target: { value: '草稿' } });
    expect(screen.getByRole('button', { name: '发送消息' })).toBeDisabled();
    expect(screen.getByRole('textbox')).toHaveValue('草稿');
    expect(screen.getByRole('alert')).toHaveTextContent('创建失败');
  });

  it('calls the existing refresh contract', () => {
    render(<MobileChatPage />);
    fireEvent.click(screen.getByRole('button', { name: '刷新消息' }));
    expect(state.refresh).toHaveBeenCalledOnce();
  });

  it('retains a draft when the default session becomes ready', () => {
    state.sessionId = null;
    const { rerender } = render(<MobileChatPage />);
    fireEvent.change(screen.getByRole('textbox'), { target: { value: '等待中的草稿' } });
    state.sessionId = 'ready';
    rerender(<MobileChatPage />);
    expect(screen.getByRole('textbox')).toHaveValue('等待中的草稿');
    expect(screen.getByRole('button', { name: '发送消息' })).toBeEnabled();
  });

  it('leaves sizing to the shell instead of pinning a pixel height', () => {
    const { container } = render(<main style={{ paddingBottom: 64 }}><MobileChatPage /></main>);
    const page = container.querySelector('main > div') as HTMLElement;
    // The shell clamps itself to the visual viewport, so the page only fills the
    // content box and never measures the viewport itself.
    expect(page.style.height).toBe('');
    expect(page.className).toContain('h-full');
    expect(page.className).toContain('min-h-0');
  });

  it('keeps the composer mounted and the draft intact while the keyboard opens and closes', async () => {
    const viewport = new FakeVisualViewport(768);
    vi.stubGlobal('visualViewport', viewport);
    const { container } = render(<MobileChatPage />);
    const input = screen.getByRole('textbox');
    fireEvent.change(input, { target: { value: '键盘弹出前写的草稿' } });

    act(() => {
      viewport.height = 420;
      viewport.dispatchEvent(new Event('resize'));
    });
    await act(async () => {
      await new Promise<void>(resolve => requestAnimationFrame(() => resolve()));
    });

    // Same node, same value: the resize must not remount the composer.
    expect(screen.getByRole('textbox')).toBe(input);
    expect(input).toHaveValue('键盘弹出前写的草稿');
    expect(container.querySelector('form')).toBeInTheDocument();

    act(() => {
      viewport.height = 768;
      viewport.dispatchEvent(new Event('resize'));
    });
    await act(async () => {
      await new Promise<void>(resolve => requestAnimationFrame(() => resolve()));
    });
    expect(input).toHaveValue('键盘弹出前写的草稿');
  });

  it('keeps the composer usable after a visual viewport scroll', async () => {
    const viewport = new FakeVisualViewport(768);
    vi.stubGlobal('visualViewport', viewport);
    render(<MobileChatPage />);
    act(() => {
      viewport.height = 380;
      viewport.offsetTop = 30;
      viewport.dispatchEvent(new Event('scroll'));
    });
    await act(async () => {
      await new Promise<void>(resolve => requestAnimationFrame(() => resolve()));
    });
    expect(screen.getByRole('textbox')).toBeEnabled();
    expect(screen.getByRole('button', { name: '发送消息' })).toBeInTheDocument();
  });
});
