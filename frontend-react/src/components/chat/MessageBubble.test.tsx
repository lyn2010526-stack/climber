import { render } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { MessageBubble } from './MessageBubble';

describe('MessageBubble presentation', () => {
  it('marks assistant turns with the product avatar and renders markdown', () => {
    const { container } = render(
      <MessageBubble message={{ id: 'a1', role: 'assistant', content: '# 标题', timestamp: new Date(0) }} />,
    );
    expect(container.querySelector('[data-avatar]')).not.toBeNull();
    expect(container.querySelector('svg')).not.toBeNull();
    expect(container.querySelector('[data-message-body]')!.innerHTML).toContain('h1');
    expect(container.textContent).toContain('标题');
  });

  it('renders user turns as a right-aligned tinted bubble with no avatar', () => {
    const { container } = render(
      <MessageBubble message={{ id: 'u1', role: 'user', content: '帮我看看', timestamp: new Date(0) }} />,
    );
    const row = container.querySelector('[data-message-bubble]')!;
    expect(row).toHaveClass('justify-end');
    expect(container.querySelector('[data-avatar]')).toBeNull();
    const body = container.querySelector('[data-message-body]')!;
    expect(body).toHaveClass('bg-[var(--color-accent-subtle)]');
    expect(body).toHaveClass('rounded-2xl');
    expect(body.textContent).toBe('帮我看看');
  });

  it('hides the avatar but keeps its spacer for a merged consecutive turn', () => {
    const { container } = render(
      <MessageBubble
        message={{ id: 'a2', role: 'assistant', content: '接着上一条说。' }}
        showAvatar={false}
        merged
      />,
    );
    // 合并的后一条隐藏头像，但保留占位宽度，行首始终对齐。
    expect(container.querySelector('[data-avatar]')).toBeNull();
    const col = container.querySelector('[data-avatar-col]')!;
    expect(col).not.toBeNull();
    expect(col).toHaveAttribute('aria-hidden', 'true');
    expect(container.querySelector('[data-message-bubble]')).not.toBeNull();
  });

  it('reveals timestamp and actions on hover and reserves the meta height', () => {
    const { container } = render(
      <MessageBubble
        message={{ id: 'a1', role: 'assistant', content: '回答', timestamp: new Date(0) }}
        actions={<button type="button">复制</button>}
      />,
    );
    const meta = container.querySelector('[data-message-meta]')!;
    // 悬停显隐：指针设备默认隐藏，悬停或键盘聚焦后出现。
    expect(meta.className).toContain('[@media(hover:hover)]:opacity-0');
    expect(meta.className).toContain('group-hover:opacity-100');
    expect(meta.className).toContain('group-focus-within:opacity-100');
    // meta 行常驻占位高度：显隐永远不推动布局。
    expect(meta.className).toContain('min-h-[26px]');
    expect(meta.textContent).toContain('复制');
    expect(meta.querySelector('time')).not.toBeNull();
  });

  it('keeps the meta row reserved during a stream with no actions yet', () => {
    const { container } = render(
      <MessageBubble
        message={{ id: 'a1', role: 'assistant', content: '', timestamp: new Date(0), isStreaming: true }}
      />,
    );
    // 流式开始时 meta 行已经占位：首 token 到来不会推挤布局。
    expect(container.querySelector('[data-message-meta]')).not.toBeNull();
    expect(container.querySelector('[data-streaming-cursor]')).not.toBeNull();
    expect(container.querySelector('[data-cursor-bar]')).not.toBeNull();
  });

  it('carries the caller reading width on the row', () => {
    const { container } = render(
      <MessageBubble
        message={{ id: 'a1', role: 'assistant', content: '回答' }}
        className="mx-auto w-full md:max-w-3xl"
      />,
    );
    expect(container.querySelector('[data-message-bubble]')).toHaveClass('md:max-w-3xl');
  });
});
