import { describe, it, expect, beforeAll } from 'vitest';
import { render, screen } from '@testing-library/react';
import i18n from '../../i18n';
import { ClimberMark } from '../brand/ClimberMark';
import { MobileMessageBubble } from './MobileMessageBubble';
import type { Message } from '../../useChat';

beforeAll(async () => {
  await i18n.changeLanguage('zh-CN');
});

const base: Message = { id: 'm1', content: '' };

describe('MobileMessageBubble', () => {
  it('hangs the assistant turn left under the ClimberMark avatar', () => {
    render(<MobileMessageBubble message={{ ...base, id: 'a1', role: 'assistant', content: '你好' }} showThinking showToolCalls />);
    const row = screen.getByText('你好').closest('article') as HTMLElement;
    expect(row).toHaveAttribute('data-role', 'assistant');
    expect(row).toHaveClass('items-start');
    expect(row.querySelector('svg polyline')).not.toBeNull();
  });

  it('right-aligns the user turn inside an accent bubble', () => {
    const { container } = render(<MobileMessageBubble message={{ ...base, id: 'u1', role: 'user', content: '问题' }} showThinking={false} showToolCalls={false} />);
    const row = container.querySelector('article')!;
    expect(row).toHaveAttribute('data-role', 'user');
    expect(row).toHaveClass('justify-end');
    expect(row.querySelector('svg')).toBeNull();
    const bubble = screen.getByText('问题') as HTMLElement;
    expect(bubble.className).toContain('bg-[var(--color-accent)]');
    expect(bubble.textContent).toBe('问题');
  });

  it('renders the assistant body through the markdown pipeline', () => {
    render(<MobileMessageBubble message={{ ...base, id: 'a1', role: 'assistant', content: '- 一\n- 二' }} showThinking={false} showToolCalls={false} />);
    expect(screen.getByRole('list')).toBeInTheDocument();
    expect(screen.getAllByRole('listitem')).toHaveLength(2);
  });

  it('shows the cursor on the streaming assistant turn only', () => {
    const { container, rerender } = render(
      <MobileMessageBubble message={{ ...base, id: 'a1', role: 'assistant', content: '生成中' }} isStreaming showThinking={false} showToolCalls={false} />,
    );
    expect(container.querySelector('span[class*="w-[2px]"]')).not.toBeNull();
    rerender(
      <MobileMessageBubble message={{ ...base, id: 'a1', role: 'assistant', content: '生成中' }} showThinking={false} showToolCalls={false} />,
    );
    expect(container.querySelector('span[class*="w-[2px]"]')).toBeNull();
  });

  it('shows the typing dots bubble while the first assistant token is pending', () => {
    const { container } = render(
      <MobileMessageBubble message={{ ...base, id: 'a1', role: 'assistant' }} isStreaming showThinking={false} showToolCalls={false} />,
    );
    expect(container.querySelectorAll('span.size-1\\.5')).toHaveLength(3);
  });

  it('keeps reasoning and tool calls inside the assistant row', () => {
    render(
      <MobileMessageBubble
        message={{
          ...base,
          id: 'a1',
          role: 'assistant',
          content: '答案',
          reasoning: '推理',
          toolCalls: [{ id: 't1', name: 'grep', arguments: {}, status: 'success', result: 'ok' }],
        }}
        showThinking
        showToolCalls
      />,
    );
    const row = screen.getByText('答案').closest('article')!;
    expect(row.querySelector('[data-thinking-block]')).not.toBeNull();
    expect(row.querySelector('[data-tool-call]')).not.toBeNull();
  });

  it('reads a tool role row as a quiet note labelled by its tool name', () => {
    render(<MobileMessageBubble message={{ ...base, id: 'x1', role: 'tool', content: 'raw', tool_name: 'shell' }} showThinking={false} showToolCalls={false} />);
    const row = screen.getByText('raw').closest('article') as HTMLElement;
    expect(row).toHaveAttribute('data-role', 'tool');
    expect(row.textContent).toContain('shell');
  });

  it('always draws the assistant avatar with the product mark geometry', () => {
    render(<MobileMessageBubble message={{ ...base, id: 'a1', role: 'assistant', content: 'x' }} showThinking={false} showToolCalls={false} />);
    const mark = screen.getByText('x').closest('article')!.querySelector('svg')!;
    expect(mark.querySelector('polyline')!.getAttribute('points')).toBe('4.6 19.9 9.9 13.9 7.2 10.2 11.7 7.1');
    expect(mark.getAttribute('stroke')).toBe('var(--color-accent-foreground)');
  });

  it('reuses the exact ClimberMark drawing', () => {
    const { container: markContainer } = render(<ClimberMark size={15} color="var(--color-accent-foreground)" />);
    const reference = markContainer.querySelector('svg')!.outerHTML;
    const { container } = render(<MobileMessageBubble message={{ ...base, id: 'a1', role: 'assistant', content: 'x' }} showThinking={false} showToolCalls={false} />);
    const bubbleMark = container.querySelector('article svg')!.outerHTML;
    expect(bubbleMark).toBe(reference);
  });
});
