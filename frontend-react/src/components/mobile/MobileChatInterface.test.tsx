import { describe, it, expect, vi, afterEach } from 'vitest';
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MobileChatInterface } from './MobileChatInterface';

const SAFARI_UA = 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1';
const CHROME_UA = 'Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36';

function stubUserAgent(userAgent: string) {
  Object.defineProperty(window.navigator, 'userAgent', { value: userAgent, configurable: true });
}

function setMetrics(element: HTMLElement, { scrollHeight, clientHeight }: { scrollHeight: number; clientHeight: number }) {
  Object.defineProperty(element, 'scrollHeight', { value: scrollHeight, configurable: true });
  Object.defineProperty(element, 'clientHeight', { value: clientHeight, configurable: true });
}

afterEach(() => {
  vi.restoreAllMocks();
});

describe('MobileChatInterface', () => {
  it('keeps the composer in flow and omits promotional empty content', () => {
    render(<MobileChatInterface messages={[]} onSend={vi.fn()} />);
    const input = screen.getByRole('textbox', { name: '输入消息' });
    expect(input.closest('form')).not.toHaveClass('fixed');
    expect(screen.getByRole('heading', { name: '新对话' })).toBeInTheDocument();
    expect(screen.queryByText('帮我分析代码')).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: '发送消息' })).toBeDisabled();
  });

  it('renders a title-only empty state without a duplicate header label', () => {
    render(<MobileChatInterface messages={[]} onSend={vi.fn()} />);
    const empty = screen.getByRole('heading', { name: '新对话' }).parentElement as HTMLElement;
    expect(empty.textContent).toBe('新对话');
    expect(screen.queryByText('对话')).not.toBeInTheDocument();
    expect(screen.queryByRole('status')).not.toBeInTheDocument();
  });

  it('keeps a single safe-area reserve on the composer', () => {
    render(<MobileChatInterface messages={[]} onSend={vi.fn()} />);
    const form = screen.getByRole('textbox').closest('form') as HTMLElement;
    // The shell already reserves the navigation strip and the bottom inset, so
    // the composer must not stack a second bottom inset on top of it.
    expect(form.style.paddingBottom).toBe('12px');
    expect(form.getAttribute('style')).not.toContain('safe-area-inset-bottom');
  });

  it('holds the composer at the minimum touch height when the draft is empty', () => {
    render(<MobileChatInterface messages={[]} onSend={vi.fn()} />);
    const input = screen.getByRole('textbox');
    fireEvent.change(input, { target: { value: '草稿' } });
    expect(parseInt(input.style.height, 10)).toBeGreaterThanOrEqual(44);
  });

  it('guards IME, Shift+Enter and blank input; sends trimmed text', async () => {
    const onSend = vi.fn().mockResolvedValue(undefined);
    render(<MobileChatInterface messages={[]} onSend={onSend} />);
    const input = screen.getByRole('textbox');
    fireEvent.change(input, { target: { value: '  问题  ' } });
    fireEvent.compositionStart(input);
    fireEvent.keyDown(input, { key: 'Enter' });
    expect(onSend).not.toHaveBeenCalled();
    fireEvent.compositionEnd(input);
    fireEvent.keyDown(input, { key: 'Enter', shiftKey: true });
    expect(onSend).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole('button', { name: '发送消息' }));
    await waitFor(() => expect(onSend).toHaveBeenCalledExactlyOnceWith('问题'));
    expect(input).toHaveValue('');
  });

  it('keeps drafts editable during streaming and exposes only stop', () => {
    const onStop = vi.fn();
    render(<MobileChatInterface messages={[]} onSend={vi.fn()} isLoading onStop={onStop} />);
    fireEvent.change(screen.getByRole('textbox'), { target: { value: '下一条' } });
    expect(screen.getByRole('textbox')).toHaveValue('下一条');
    expect(screen.queryByRole('button', { name: '发送消息' })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '停止生成' }));
    expect(onStop).toHaveBeenCalledOnce();
  });

  it('restores a rejected draft and displays the error', async () => {
    render(<MobileChatInterface messages={[]} onSend={vi.fn().mockRejectedValue(new Error('连接失败'))} />);
    fireEvent.change(screen.getByRole('textbox'), { target: { value: '保留内容' } });
    fireEvent.click(screen.getByRole('button', { name: '发送消息' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('连接失败');
    expect(screen.getByRole('textbox')).toHaveValue('保留内容');
  });

  it('prevents duplicate sends while the callback is pending', async () => {
    let resolve!: () => void;
    const onSend = vi.fn(() => new Promise<void>(done => { resolve = done; }));
    render(<MobileChatInterface messages={[]} onSend={onSend} />);
    const input = screen.getByRole('textbox');
    fireEvent.change(input, { target: { value: '第一条' } });
    fireEvent.click(screen.getByRole('button', { name: '发送消息' }));
    fireEvent.change(input, { target: { value: '第二条' } });
    fireEvent.click(screen.getByRole('button', { name: '发送消息' }));
    expect(onSend).toHaveBeenCalledTimes(1);
    resolve();
    await waitFor(() => expect(input).toHaveValue('第二条'));
  });

  it('preserves a scrolled-up position during streaming and can return to latest', () => {
    const message = { id: '1', role: 'assistant' as const, content: '第一段' };
    const { rerender } = render(<MobileChatInterface messages={[message]} onSend={vi.fn()} />);
    const list = screen.getByRole('region', { name: '消息列表' });
    Object.defineProperties(list, { scrollHeight: { value: 1000, configurable: true }, clientHeight: { value: 300 } });
    list.scrollTop = 100;
    fireEvent.scroll(list);
    rerender(<MobileChatInterface messages={[{ ...message, content: '第一段，第二段' }]} onSend={vi.fn()} isLoading />);
    expect(list.scrollTop).toBe(100);
    fireEvent.click(screen.getByRole('button', { name: '回到最新' }));
    expect(list.scrollTop).toBe(1000);
    Object.defineProperty(list, 'scrollHeight', { value: 1200 });
    rerender(<MobileChatInterface messages={[{ ...message, content: '第三段' }]} onSend={vi.fn()} isLoading />);
    expect(list.scrollTop).toBe(1200);
  });

  it('retains tool and reasoning data and disables refresh during streaming', () => {
    render(<MobileChatInterface messages={[{ id: '1', role: 'assistant', content: '结果', reasoning: '分析', toolCalls: [{ id: 't1', name: 'read_file', arguments: { path: 'test.ts' }, status: 'error', error: '读取失败' }] }]} onSend={vi.fn()} onRefresh={vi.fn()} isLoading />);
    expect(screen.getByText('分析')).toBeInTheDocument();
    expect(screen.getByText('read_file · 失败')).toBeInTheDocument();
    expect(screen.getByText('读取失败')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '刷新消息' })).toBeDisabled();
  });

  it('announces streaming without repeating the page title', () => {
    render(<MobileChatInterface messages={[]} onSend={vi.fn()} isLoading />);
    expect(screen.getByRole('status')).toHaveTextContent('正在生成');
    expect(screen.queryByText('对话')).not.toBeInTheDocument();
  });

  it('follows the tail while the reader stays near the bottom', () => {
    const message = { id: '1', role: 'assistant' as const, content: '第一段' };
    const { rerender } = render(<MobileChatInterface messages={[message]} onSend={vi.fn()} isLoading />);
    const list = screen.getByRole('region', { name: '消息列表' });
    setMetrics(list, { scrollHeight: 1000, clientHeight: 300 });
    // 40px from the tail is still within the follow threshold.
    list.scrollTop = 660;
    fireEvent.scroll(list);
    expect(screen.queryByRole('button', { name: /回到最新/ })).not.toBeInTheDocument();
    rerender(<MobileChatInterface messages={[message, { id: '2', role: 'assistant', content: '第二段' }]} onSend={vi.fn()} isLoading />);
    expect(list.scrollTop).toBe(1000);
  });

  it('counts messages that arrive while the reader is scrolled up', () => {
    const message = { id: '1', role: 'assistant' as const, content: '第一段' };
    const { rerender } = render(<MobileChatInterface messages={[message]} onSend={vi.fn()} isLoading />);
    const list = screen.getByRole('region', { name: '消息列表' });
    setMetrics(list, { scrollHeight: 1000, clientHeight: 300 });
    list.scrollTop = 0;
    fireEvent.scroll(list);
    rerender(<MobileChatInterface messages={[message, { id: '2', role: 'assistant', content: '第二段' }]} onSend={vi.fn()} isLoading />);
    rerender(<MobileChatInterface messages={[message, { id: '2', role: 'assistant', content: '第二段' }, { id: '3', role: 'assistant', content: '第三段' }]} onSend={vi.fn()} isLoading />);
    const entry = screen.getByRole('button', { name: /回到最新/ });
    expect(entry).toHaveTextContent('2');
    fireEvent.click(entry);
    expect(list.scrollTop).toBe(1000);
    expect(screen.queryByRole('button', { name: /回到最新/ })).not.toBeInTheDocument();
  });

  it('treats a list shorter than its viewport as the tail', () => {
    const message = { id: '1', role: 'assistant' as const, content: '很短的一条' };
    const { rerender } = render(<MobileChatInterface messages={[message]} onSend={vi.fn()} isLoading />);
    const list = screen.getByRole('region', { name: '消息列表' });
    setMetrics(list, { scrollHeight: 200, clientHeight: 600 });
    list.scrollTop = 0;
    fireEvent.scroll(list);
    expect(screen.queryByRole('button', { name: /回到最新/ })).not.toBeInTheDocument();
    Object.defineProperty(list, 'scrollHeight', { value: 400, configurable: true });
    rerender(<MobileChatInterface messages={[message, { id: '2', role: 'assistant', content: '第二段' }]} onSend={vi.fn()} isLoading />);
    expect(list.scrollTop).toBe(400);
  });

  it('follows the growing transcript through a resize observer', () => {
    const observed: Element[] = [];
    let trigger: (() => void) | null = null;
    class FakeResizeObserver {
      constructor(callback: () => void) { trigger = callback; }
      observe(element: Element) { observed.push(element); }
      disconnect() {}
    }
    vi.stubGlobal('ResizeObserver', FakeResizeObserver);
    try {
      const message = { id: '1', role: 'assistant' as const, content: '第一段' };
      render(<MobileChatInterface messages={[message]} onSend={vi.fn()} isLoading />);
      const list = screen.getByRole('region', { name: '消息列表' });
      setMetrics(list, { scrollHeight: 1000, clientHeight: 300 });
      // The observed node is the transcript, not the fixed-height scroller:
      // streaming growth has to re-pin the tail.
      expect(observed).toHaveLength(1);
      expect(observed[0]).not.toBe(list);
      expect(observed[0]).toContainElement(screen.getByText('第一段'));

      list.scrollTop = 700;
      fireEvent.scroll(list);
      Object.defineProperty(list, 'scrollHeight', { value: 1500, configurable: true });
      expect(trigger).not.toBeNull();
      act(() => { trigger?.(); });
      expect(list.scrollTop).toBe(1500);
    } finally {
      vi.unstubAllGlobals();
    }
  });

  it('swallows the single confirming Enter that Safari emits after compositionend', async () => {
    stubUserAgent(SAFARI_UA);
    const onSend = vi.fn().mockResolvedValue(undefined);
    render(<MobileChatInterface messages={[]} onSend={onSend} />);
    const input = screen.getByRole('textbox');
    fireEvent.change(input, { target: { value: '你好' } });
    fireEvent.compositionEnd(input, { data: '你好' });
    fireEvent.keyDown(input, { key: 'Enter' });
    expect(onSend).not.toHaveBeenCalled();
    // The guard is consumed once, so the next Enter sends.
    fireEvent.keyDown(input, { key: 'Enter' });
    await waitFor(() => expect(onSend).toHaveBeenCalledExactlyOnceWith('你好'));
  });

  it('sends straight away on Chromium IMEs that already report composition', async () => {
    stubUserAgent(CHROME_UA);
    const onSend = vi.fn().mockResolvedValue(undefined);
    render(<MobileChatInterface messages={[]} onSend={onSend} />);
    const input = screen.getByRole('textbox');
    fireEvent.change(input, { target: { value: '你好' } });
    fireEvent.compositionEnd(input, { data: '你好' });
    fireEvent.keyDown(input, { key: 'Enter' });
    await waitFor(() => expect(onSend).toHaveBeenCalledExactlyOnceWith('你好'));
  });

  it('still blocks Enter while a composition is open and while keyCode 229 is reported', () => {
    const onSend = vi.fn().mockResolvedValue(undefined);
    render(<MobileChatInterface messages={[]} onSend={onSend} />);
    const input = screen.getByRole('textbox');
    fireEvent.change(input, { target: { value: 'にほん' } });
    fireEvent.compositionStart(input);
    fireEvent.keyDown(input, { key: 'Enter', keyCode: 13 });
    expect(onSend).not.toHaveBeenCalled();
    fireEvent.compositionEnd(input, { data: '日本' });
    fireEvent.keyDown(input, { key: 'Enter', keyCode: 229 });
    expect(onSend).not.toHaveBeenCalled();
  });
});
