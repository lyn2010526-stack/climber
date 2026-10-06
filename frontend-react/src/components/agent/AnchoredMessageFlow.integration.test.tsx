import { act, fireEvent, render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import i18n from '../../i18n';
import { resetAnchoredStore, useAnchoredStore } from '../../store/anchored';
import type { Message, ToolCall } from '../../useChat';
import { AnchoredMessageFlow } from './AnchoredMessageFlow';

const writeText = vi.fn().mockResolvedValue(undefined);

const readCall: ToolCall = {
  id: 'read-1', name: 'read_file', arguments: { path: 'src/example.ts' },
  status: 'success', result: 'complete output',
};
const execCall: ToolCall = {
  id: 'exec-1', name: 'container_exec', arguments: { cmd: 'npm run lint' },
  status: 'success', result: 'line one\nline two',
};
const grepCall: ToolCall = {
  id: 'grep-1', name: 'grep', arguments: { pattern: 'TODO' },
  status: 'running',
};

function turn(toolCalls: ToolCall[], extra: Partial<Message> = {}): Message {
  return { id: 'turn-1', role: 'assistant', content: 'Answer', toolCalls, ...extra };
}

beforeEach(async () => {
  resetAnchoredStore();
  writeText.mockClear();
  Object.defineProperty(navigator, 'clipboard', { configurable: true, value: { writeText } });
  await i18n.changeLanguage('zh-CN');
});

afterEach(() => {
  vi.useRealTimers();
  vi.restoreAllMocks();
});

describe('AnchoredMessageFlow integration', () => {
  it('renders the public reasoning summary through ReasoningPanel behind one disclosure', async () => {
    const user = userEvent.setup();
    render(<AnchoredMessageFlow messages={[{ id: 'a', role: 'assistant', content: 'Answer', reasoning: '公开摘要正文' }]} />);

    // transcript 只有一个披露控件，ReasoningPanel 自己的触发按钮被移出无障碍树。
    const trigger = screen.getByRole('button', { name: '公开推理摘要' });
    expect(trigger).toHaveAttribute('aria-expanded', 'false');
    expect(screen.queryAllByTestId('reasoning-label')).toHaveLength(0);
    expect(screen.queryByText('公开摘要正文')).toBeNull();

    await user.click(trigger);
    expect(trigger).toHaveAttribute('aria-expanded', 'true');
    expect(screen.getByTestId('reasoning-content')).toHaveTextContent('公开摘要正文');

    await user.click(trigger);
    expect(screen.queryByTestId('reasoning-content')).toBeNull();
  });

  it('keeps the bubble testids and the active pulse while ReasoningPanel is in place', () => {
    const { rerender } = render(<AnchoredMessageFlow messages={[{ id: 'a', role: 'assistant', content: 'Answer', reasoning: '摘要' }]} activeMessageId="a" />);
    expect(screen.getByTestId('anchored-thinking-bubble')).toBeVisible();
    expect(screen.getByTestId('anchored-thinking-icon')).toHaveClass('motion-safe:animate-pulse');
    rerender(<AnchoredMessageFlow messages={[{ id: 'a', role: 'assistant', content: 'Answer', reasoning: '摘要' }]} />);
    expect(screen.getByTestId('anchored-thinking-icon')).not.toHaveClass('motion-safe:animate-pulse');
  });

  it('copies the assistant answer from the hover action row and confirms in place', () => {
    // 用 fireEvent 而不是 userEvent：后者会把自己的剪贴板 stub 装到
    // navigator.clipboard 上，这里要断言的正是组件写入的那一次调用。
    render(<AnchoredMessageFlow messages={[{ id: 'a', role: 'assistant', content: '可复制正文' }]} />);
    const actions = screen.getByTestId('anchored-message-actions');
    expect(actions).toHaveClass('group-hover/message:opacity-100');

    fireEvent.click(within(actions).getByRole('button', { name: '复制' }));
    expect(writeText).toHaveBeenCalledWith('可复制正文');
    expect(within(actions).getByTestId('message-copy-check')).toBeInTheDocument();
  });

  it('leaves edit and regenerate unwired because the transcript has no such capability', () => {
    render(<AnchoredMessageFlow messages={[{ id: 'a', role: 'assistant', content: '正文' }]} />);
    const actions = screen.getByTestId('anchored-message-actions');
    expect(within(actions).queryByRole('button', { name: '编辑' })).toBeNull();
    expect(within(actions).queryByRole('button', { name: '重新生成' })).toBeNull();
  });

  it('hides the action row when the assistant turn has no copyable content', () => {
    render(<AnchoredMessageFlow messages={[{ id: 'a', role: 'assistant', content: '' }]} activeMessageId="a" />);
    expect(screen.queryByTestId('anchored-message-actions')).toBeNull();
  });

  it('routes a permission-held tool call to AgentToolCard with its approval row', () => {
    const held: ToolCall = {
      id: 'write-1', name: 'write_file', arguments: { path: 'src/app.ts' },
      requiresApproval: true, approvalId: 'ap-1',
    };
    render(<AnchoredMessageFlow messages={[turn([held])]} />);
    expect(screen.getByTestId('agent-tool-card')).toHaveAttribute('data-status', 'awaiting-approval');
    expect(screen.getByTestId('agent-tool-approval')).toBeVisible();
    expect(screen.getByText('write_file')).toBeVisible();
    // 卡在审批上的调用不再走 Codex 工具卡，两者同一时刻只出现一个。
    expect(screen.queryByTestId('anchored-tool-card')).toBeNull();
  });

  it('returns the same call to the Codex card once the backend settles it', () => {
    const held: ToolCall = {
      id: 'write-1', name: 'write_file', arguments: { path: 'src/app.ts' },
      requiresApproval: false, status: 'success', result: 'written',
    };
    render(<AnchoredMessageFlow messages={[turn([held])]} />);
    expect(screen.queryByTestId('agent-tool-card')).toBeNull();
    expect(screen.getByTestId('anchored-tool-card')).toBeVisible();
  });

  it('leaves the Codex command summary as the only folded output for a command call', () => {
    render(<AnchoredMessageFlow messages={[turn([execCall])]} />);
    const summary = screen.getByTestId('anchored-exec-command-continuation');
    expect(summary).toHaveTextContent('line one');
    expect(screen.getByText('npm run lint')).toBeVisible();
  });

  it('keeps a non-command call from leaking its output in the folded state', () => {
    render(<AnchoredMessageFlow messages={[turn([readCall])]} />);
    expect(screen.queryByTestId('anchored-exec-command-continuation')).toBeNull();
    expect(screen.queryByText('complete output')).toBeNull();
  });

  it('chains a multi-call turn into one step per tool and hides the chain for a single call', () => {
    const { rerender } = render(<AnchoredMessageFlow messages={[turn([readCall, grepCall])]} activeMessageId="turn-1" />);
    const chain = screen.getByTestId('thought-chain');
    expect(within(chain).getByTestId('thought-step-read-1')).toHaveAttribute('data-status', 'success');
    expect(within(chain).getByTestId('thought-step-grep-1')).toHaveAttribute('data-status', 'running');
    expect(within(chain).getByText('read_file')).toBeVisible();
    expect(within(chain).getByText('grep')).toBeVisible();

    rerender(<AnchoredMessageFlow messages={[turn([readCall])]} />);
    expect(screen.queryByTestId('thought-chain')).toBeNull();
  });

  it('reports a tool the store marked failed as an error step in the chain', () => {
    render(<AnchoredMessageFlow messages={[turn([readCall, grepCall])]} />);
    act(() => useAnchoredStore.setState({ failedToolIds: ['grep-1'] }));
    expect(screen.getByTestId('thought-step-grep-1')).toHaveAttribute('data-status', 'error');
  });
});