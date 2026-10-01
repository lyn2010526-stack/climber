import { fireEvent, render, screen, within } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import i18n from '../../i18n';
import { ChatInterface } from './ChatInterface';
import { getReadingWidthClass } from './readingWidth';
import { ThinkingIndicator } from './ThinkingIndicator';
import { ThinkingDetails } from '../chat/ThinkingDetails';
import { MessageActions, MessageContent, ToolCallCard } from '../chat/MessageContent';

vi.mock('../../api', () => ({ api: { submitFeedback: vi.fn(), resolvePermission: vi.fn() } }));

const messages = [
  { id: 'u1', role: 'user' as const, content: 'Review this repository' },
  { id: 'a1', role: 'assistant' as const, content: 'The parser is lenient.' },
];

beforeEach(async () => {
  await i18n.changeLanguage('zh-CN');
});

describe('chat state honesty', () => {
  it('renders one of loading, empty, error or transcript and never a blend', () => {
    const { container, rerender } = render(<ChatInterface messages={[]} onSend={vi.fn()} />);
    expect(screen.getByRole('heading')).toHaveTextContent('开始对话');
    expect(container.querySelectorAll('[data-transcript]')).toHaveLength(0);

    rerender(<ChatInterface messages={[]} onSend={vi.fn()} isLoading />);
    expect(screen.getByRole('status')).toBeInTheDocument();
    expect(screen.queryByRole('heading')).toBeNull();
    expect(container.querySelectorAll('[data-transcript]')).toHaveLength(0);

    rerender(<ChatInterface messages={[]} onSend={vi.fn()} error="上游连接失败" onRetry={() => {}} />);
    expect(screen.queryByRole('heading')).toBeNull();
    expect(screen.queryByRole('status')).toBeNull();
    expect(screen.getByRole('alert')).toHaveTextContent('上游连接失败');

    rerender(<ChatInterface messages={messages} onSend={vi.fn()} />);
    expect(container.querySelectorAll('[data-transcript]')).toHaveLength(1);
    expect(screen.queryByRole('alert')).toBeNull();
    expect(screen.queryByRole('status')).toBeNull();
  });

  it('offers no retry control when the caller supplies no handler', () => {
    render(<ChatInterface messages={[]} onSend={vi.fn()} error="失败" />);
    expect(screen.getByRole('alert')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: '重试' })).toBeNull();
  });

  it('invokes the supplied retry handler', () => {
    const onRetry = vi.fn();
    render(<ChatInterface messages={[]} onSend={vi.fn()} error="失败" onRetry={onRetry} />);
    fireEvent.click(screen.getByRole('button', { name: '重试' }));
    expect(onRetry).toHaveBeenCalledOnce();
  });

  it('never renders a progressbar or an invented stage', () => {
    const { container, rerender } = render(
      <ChatInterface
        messages={[{ ...messages[1], reasoning: '先看解析器' }]}
        onSend={vi.fn()}
        isLoading
      />,
    );
    expect(container.querySelectorAll('[role="progressbar"]')).toHaveLength(0);
    expect(container.querySelectorAll('[data-progress]')).toHaveLength(0);
    expect(container.textContent).not.toMatch(/第\s*\d+\s*步|阶段|Stage\s*\d/);
    // Text already arrived: the turn is live, and it says nothing more.
    expect(container.querySelectorAll('[role="status"]')).toHaveLength(0);

    const awaiting = [{ id: 'a3', role: 'assistant' as const, content: '' }];
    rerender(<ChatInterface messages={awaiting} onSend={vi.fn()} isLoading />);
    expect(screen.getByRole('status')).toHaveTextContent('思考中');

    rerender(<ChatInterface messages={awaiting} onSend={vi.fn()} />);
    expect(screen.queryByRole('status')).toBeNull();
  });
});

describe('composer layering', () => {
  it('keeps stopping and sending in a single mutually exclusive slot', () => {
    const { rerender } = render(<ChatInterface messages={messages} onSend={vi.fn()} />);
    expect(screen.getByRole('button', { name: '发送' })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: '停止生成' })).toBeNull();

    rerender(<ChatInterface messages={messages} onSend={vi.fn()} onStop={vi.fn()} isLoading />);
    expect(screen.getByRole('button', { name: '停止生成' })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: '发送' })).toBeNull();
  });

  it('disables send on a blank draft and the stop control without a handler', () => {
    const { rerender } = render(<ChatInterface messages={messages} onSend={vi.fn()} />);
    const send = screen.getByRole('button', { name: '发送' });
    expect(send).toBeDisabled();

    fireEvent.change(screen.getByRole('textbox'), { target: { value: '  ' } });
    expect(send).toBeDisabled();

    fireEvent.change(screen.getByRole('textbox'), { target: { value: 'go' } });
    expect(send).toBeEnabled();

    rerender(<ChatInterface messages={messages} onSend={vi.fn()} isLoading />);
    expect(screen.getByRole('button', { name: '停止生成' })).toBeDisabled();
  });

  it('holds Enter while an IME candidate window is open and releases it after', () => {
    const onSend = vi.fn();
    render(<ChatInterface messages={[]} onSend={onSend} />);
    const input = screen.getByRole('textbox');

    fireEvent.change(input, { target: { value: 'ni hao' } });
    fireEvent.compositionStart(input);
    fireEvent.keyDown(input, { key: 'Enter' });
    expect(onSend).not.toHaveBeenCalled();
    expect(input).toHaveValue('ni hao');

    fireEvent.compositionEnd(input);
    fireEvent.keyDown(input, { key: 'Enter' });
    expect(onSend).toHaveBeenCalledWith('ni hao');
  });

  it('ignores the Safari keyCode 229 candidate Enter', () => {
    const onSend = vi.fn();
    render(<ChatInterface messages={[]} onSend={onSend} />);
    const input = screen.getByRole('textbox');
    fireEvent.change(input, { target: { value: '你好' } });
    fireEvent.keyDown(input, { key: 'Enter', keyCode: 229 });
    expect(onSend).not.toHaveBeenCalled();
  });

  it('shares one reading column between the transcript and the composer', () => {
    const { container } = render(<ChatInterface messages={messages} onSend={vi.fn()} />);
    // Both surfaces take their width from the same decision, so a reply's
    // lines start exactly where the next prompt will.
    const width = getReadingWidthClass({ fullWidth: false });
    const row = container.querySelector('[data-transcript] > div')!;
    expect(row).toHaveClass(width);
    const form = screen.getByRole('textbox').closest('form')!;
    expect(within(form).getByRole('textbox')).toBeInTheDocument();
    expect(form.firstElementChild).toHaveClass(width);
  });
});

describe('transcript hierarchy', () => {
  it('fits the user turn to a right-aligned surface and leaves the answer flat', () => {
    const { container } = render(<ChatInterface messages={messages} onSend={vi.fn()} />);
    const rows = container.querySelectorAll('[data-transcript] > div');
    const userRow = rows[0]!;
    const assistantRow = rows[1]!;

    expect(userRow).toHaveClass('justify-end');
    expect(assistantRow).toHaveClass('items-start');
    expect(userRow.textContent).toContain('Review this repository');
    expect(assistantRow.textContent).toContain('The parser is lenient.');
  });

  it('marks assistant turns with the product avatar and keeps the answer flat', () => {
    const { container } = render(<ChatInterface messages={messages} onSend={vi.fn()} />);
    const [userRow, assistantRow] = Array.from(container.querySelectorAll('[data-transcript] > div'));
    // The assistant row carries the ClimberMark avatar column; the user row
    // reads as a right-aligned bubble with no avatar of its own.
    expect(assistantRow!.querySelector('[data-avatar]')).not.toBeNull();
    expect(assistantRow!.querySelector('svg')).not.toBeNull();
    expect(userRow!.querySelector('[data-avatar]')).toBeNull();

    const userSurface = userRow!.querySelector('[data-message-body]')!;
    expect(userSurface).toHaveClass('bg-[var(--color-accent-subtle)]');
    // A short question fits its content, capped so it never spans the column.
    expect(userRow!.querySelector('[data-message-column]')).toHaveClass('max-w-[85%]');

    const assistantBody = assistantRow!.querySelector('[data-message-body]')!;
    // The answer is the content: full column, no surface, no bubble rounding.
    expect(assistantRow!.querySelector('[data-message-column]')).toHaveClass('flex-1');
    expect(assistantBody).not.toHaveClass('bg-[var(--color-bg-surface-2)]');
    expect(assistantBody).not.toHaveClass('rounded-2xl');
  });

  it('merges consecutive same-role turns into one visual group', () => {
    const run = [
      ...messages,
      { id: 'a2', role: 'assistant' as const, content: 'Second paragraph of the same voice.' },
    ];
    const { container } = render(<ChatInterface messages={run} onSend={vi.fn()} />);
    const rows = Array.from(container.querySelectorAll('[data-transcript] > div'));
    expect(rows).toHaveLength(3);
    // The merged follow-up hides the avatar but keeps its spacer width, and the
    // row rhythm tightens so the two turns read as one group.
    expect(rows[1]!.querySelector('[data-avatar]')).not.toBeNull();
    expect(rows[2]!.querySelector('[data-avatar]')).toBeNull();
    expect(rows[2]!.querySelector('[data-avatar-col]')).not.toBeNull();
    expect(rows[2]!.className).toContain('pb-2');
    expect(rows[1]!.className).toContain('pb-5');
  });

  it('marks only the trailing assistant turn while a run is in flight', () => {
    const withUserTail = [...messages, { id: 'u2', role: 'user' as const, content: 'and this?' }];
    const { container, rerender } = render(
      <ChatInterface messages={messages} onSend={vi.fn()} isLoading />,
    );
    expect(container.querySelectorAll('[data-streaming-cursor]')).toHaveLength(1);

    rerender(<ChatInterface messages={withUserTail} onSend={vi.fn()} isLoading />);
    expect(container.querySelectorAll('[data-streaming-cursor]')).toHaveLength(0);

    rerender(<ChatInterface messages={messages} onSend={vi.fn()} />);
    expect(container.querySelectorAll('[data-streaming-cursor]')).toHaveLength(0);
  });

  it('keeps message actions reachable by keyboard and on touch', () => {
    render(<MessageActions onCopy={() => {}} onFeedback={() => {}} onEdit={() => {}} />);
    const reveal = document.querySelector('[data-message-actions]')!;
    expect(reveal.className).toContain('[@media(hover:hover)]:opacity-0');
    expect(reveal.className).toContain('group-focus-within:opacity-100');
  });
});

describe('tool call labelling', () => {
  it('states a status only when the caller supplied one', () => {
    const { rerender, container } = render(
      <ToolCallCard name="read_file" arguments={{}} result={undefined} error={undefined} isRunning={false} />,
    );
    expect(screen.getByText('read_file')).toBeInTheDocument();
    expect(screen.queryByText('执行中')).toBeNull();
    expect(screen.queryByText('完成')).toBeNull();
    expect(container.textContent).not.toMatch(/等待中/);

    rerender(
      <ToolCallCard name="read_file" arguments={{}} result={undefined} error={undefined} isRunning />,
    );
    expect(screen.getByText('执行中')).toBeInTheDocument();

    rerender(
      <ToolCallCard name="read_file" arguments={{}} result="ok" error={undefined} isRunning={false} />,
    );
    expect(screen.getByText('完成')).toBeInTheDocument();

    rerender(
      <ToolCallCard name="read_file" arguments={{}} result={undefined} error="boom" isRunning={false} />,
    );
    expect(screen.getByText('失败')).toBeInTheDocument();
  });

  it('spans the full column instead of capping at a bubble width', () => {
    const { container } = render(
      <ToolCallCard name="read_file" arguments={{}} result={undefined} error={undefined} isRunning={false} />,
    );
    const card = container.querySelector('[data-tool-call]')!;
    expect(card).toHaveClass('w-full');
    expect(card.className).not.toMatch(/max-w-\[8/);
  });

  it('labels the sections from the translation table', () => {
    render(
      <ToolCallCard name="read_file" arguments={{ path: 'a.ts' }} result="ok" error={undefined} isRunning={false} />,
    );
    const toggle = screen.getByRole('button', { name: /read_file/ });
    expect(toggle).toHaveAttribute('aria-expanded', 'false');
    fireEvent.click(toggle);
    expect(screen.getByText('参数')).toBeInTheDocument();
    expect(screen.getByText('执行结果')).toBeInTheDocument();
  });
});

describe('reasoning disclosure', () => {
  it('stays collapsible after the stream ends and keeps the text mounted', () => {
    const { container, rerender } = render(<ThinkingDetails isComplete={false}>先看解析器</ThinkingDetails>);
    const trigger = container.querySelector('button')!;
    const panel = container.querySelector('[data-reasoning-panel]') as HTMLElement;
    expect(trigger).toHaveAttribute('aria-expanded', 'false');
    expect(panel).toHaveAttribute('hidden');

    fireEvent.click(trigger);
    expect(trigger).toHaveAttribute('aria-expanded', 'true');
    expect(panel).not.toHaveAttribute('hidden');

    fireEvent.click(trigger);
    expect(panel).toHaveAttribute('hidden');

    rerender(<ThinkingDetails isComplete>先看解析器</ThinkingDetails>);
    expect(container.querySelector('button')).toHaveAttribute('aria-expanded', 'false');
    fireEvent.click(container.querySelector('button')!);
    expect(container.querySelector('button')).toHaveAttribute('aria-expanded', 'true');
    expect(screen.getByText('先看解析器')).toBeInTheDocument();
  });

  it('states the kind of content and no duration it was not given', () => {
    const { container } = render(<ThinkingDetails>内容</ThinkingDetails>);
    expect(container.textContent).toContain('思考中');
    expect(container.textContent).not.toMatch(/\d+\.\d+s/);
  });
});

describe('working indicator', () => {
  it('pairs a single dot with a label and honours an explicit stage', () => {
    const { container, rerender } = render(<ThinkingIndicator />);
    expect(screen.getByRole('status')).toHaveTextContent('思考中');
    expect(container.querySelectorAll('svg')).toHaveLength(0);
    expect(container.querySelectorAll('[class*="animate-pulse"]')).toHaveLength(1);

    rerender(<ThinkingIndicator stage="Waiting for tool" />);
    expect(screen.getByRole('status')).toHaveTextContent('Waiting for tool');
    expect(container.querySelectorAll('[class*="animate-pulse"]')).toHaveLength(1);
  });
});

describe('standalone transcript row', () => {
  it('renders a user turn as a surface and an assistant turn as plain text', () => {
    const { container, rerender } = render(
      <MessageContent content="提问" role="user" timestamp={new Date(0)} />,
    );
    expect(container.firstElementChild).toHaveClass('justify-end');
    const userSurface = container.querySelector('.bg-\\[var\\(--color-bg-surface-2\\)\\]');
    expect(userSurface).not.toBeNull();

    rerender(<MessageContent content="回答" role="assistant" timestamp={undefined} />);
    expect(container.firstElementChild).toHaveClass('items-start');
    expect(container.querySelector('.bg-\\[var\\(--color-bg-surface-2\\)\\]')).toBeNull();
  });
});
