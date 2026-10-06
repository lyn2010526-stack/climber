import { act, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it } from 'vitest';
import i18n from '../../i18n';
import { resetAnchoredStore, useAnchoredStore } from '../../store/anchored';
import type { Message, ToolCall } from '../../useChat';
import { AnchoredMessageFlow, ToolCallCard } from './AnchoredMessageFlow';

const call: ToolCall = {
  id: 'read-1', name: 'read_file', arguments: { path: 'src/example.ts', limit: 200 },
  status: 'success', result: 'complete output',
};
const message: Message = {
  id: 'answer-1', role: 'assistant', content: 'Final answer', reasoning: 'Reported public summary',
};

beforeEach(async () => {
  resetAnchoredStore();
  await i18n.changeLanguage('zh-CN');
});

describe('AnchoredMessageFlow', () => {
  it('keeps tool progress compact and the final answer visible by default', () => {
    render(<AnchoredMessageFlow messages={[{ ...message, toolCalls: [call] }]} />);
    expect(screen.getByText('read_file')).toBeVisible();
    expect(screen.getByText('已完成')).toBeVisible();
    expect(screen.getByText('Final answer')).toBeVisible();
    expect(screen.queryByText(/src\/example.ts/)).toBeNull();
    expect(screen.queryByText('complete output')).toBeNull();
    expect(screen.queryByText('Reported public summary')).toBeNull();
    expect(screen.getByRole('button', { name: '展开详情' })).toHaveAttribute('aria-expanded', 'false');
    expect(screen.getByRole('button', { name: '公开推理摘要' })).toHaveAttribute('aria-expanded', 'false');
  });

  it('expands full arguments and logs and keeps the controlled panel addressable', async () => {
    const user = userEvent.setup();
    render(<ToolCallCard call={{ ...call, arguments: { path: 'x'.repeat(300), nested: { enabled: true } } }} active={false} defaultExpanded={false} />);
    const toggle = screen.getByRole('button', { name: '展开详情' });
    const panel = document.getElementById(toggle.getAttribute('aria-controls')!)!;
    expect(panel).not.toBeVisible();
    await user.click(toggle);
    expect(panel).toBeVisible();
    expect(screen.getByLabelText('参数')).toHaveTextContent('x'.repeat(300));
    expect(screen.getByLabelText('参数')).toHaveTextContent('"enabled": true');
    expect(screen.getByText('complete output')).toBeVisible();
    await user.click(toggle);
    expect(panel).not.toBeVisible();
    expect(screen.queryByText('complete output')).toBeNull();
  });

  it('makes running arguments available before output arrives without inventing status', async () => {
    const user = userEvent.setup();
    const { rerender } = render(<ToolCallCard call={{ ...call, status: undefined, result: undefined }} active defaultExpanded={false} />);
    expect(screen.getByText('运行中')).toBeVisible();
    await user.click(screen.getByRole('button', { name: '展开详情' }));
    expect(screen.getByLabelText('参数')).toHaveTextContent('src/example.ts');
    rerender(<ToolCallCard call={{ ...call, status: undefined, result: undefined }} active={false} defaultExpanded={false} />);
    expect(screen.getByTestId('anchored-tool-card')).toHaveAttribute('data-tool-status', 'unreported');
    expect(screen.queryByText('已完成')).toBeNull();
  });

  it('opens errors automatically and preserves both error and output when collapsed again', async () => {
    const user = userEvent.setup();
    render(<ToolCallCard call={{ ...call, error: 'Permission denied' }} active={false} defaultExpanded={false} />);
    const toggle = screen.getByRole('button', { name: '工具失败' });
    expect(screen.getByTestId('anchored-tool-card')).toHaveAttribute('data-tool-status', 'error');
    expect(toggle).toHaveAttribute('aria-expanded', 'true');
    expect(screen.getByLabelText('错误详情')).toHaveTextContent('Permission denied');
    expect(screen.getByText('complete output')).toBeVisible();
    await user.click(toggle);
    expect(screen.getByText('异常')).toBeVisible();
    expect(screen.queryByText('Permission denied')).toBeNull();
    await user.click(toggle);
    expect(screen.getByText('Permission denied')).toBeVisible();
  });

  it('handles a reported failure without logs and a later failure update', () => {
    const { rerender } = render(<ToolCallCard call={call} active={false} defaultExpanded={false} />);
    act(() => useAnchoredStore.setState({ failedToolIds: [call.id] }));
    rerender(<ToolCallCard call={{ ...call, result: undefined }} active={false} defaultExpanded={false} />);
    expect(screen.getByText('异常')).toBeVisible();
    expect(screen.getByRole('button', { name: '工具失败' })).toHaveAttribute('aria-expanded', 'true');
  });

  it('supports Enter and Space disclosure and keyboard access to payloads', async () => {
    const user = userEvent.setup();
    render(<AnchoredMessageFlow messages={[{ ...message, toolCalls: [call] }]} />);
    await user.tab();
    const toggle = screen.getByRole('button', { name: '展开详情' });
    expect(toggle).toHaveFocus();
    await user.keyboard('{Enter}');
    expect(toggle).toHaveAttribute('aria-expanded', 'true');
    await user.tab();
    expect(screen.getByLabelText('参数')).toHaveFocus();
    await user.tab();
    expect(screen.getByLabelText('工具结果')).toHaveFocus();
    await user.tab();
    const summary = screen.getByRole('button', { name: '公开推理摘要' });
    expect(summary).toHaveFocus();
    await user.keyboard(' ');
    expect(screen.getByText('Reported public summary')).toBeVisible();
    expect(summary).toHaveAttribute('aria-expanded', 'true');
    await user.keyboard('{Enter}');
    expect(screen.queryByText('Reported public summary')).toBeNull();
    toggle.focus();
    await user.keyboard(' ');
    expect(toggle).toHaveAttribute('aria-expanded', 'false');
  });

  it('shows diff output only on expansion and retains errors alongside diffs', async () => {
    const user = userEvent.setup();
    const result = 'diff --git a/file b/file\n@@ -1 +1 @@\n-old\n+new';
    const { rerender } = render(<ToolCallCard call={{ ...call, result }} active={false} defaultExpanded={false} />);
    expect(screen.queryByRole('table')).toBeNull();
    await user.click(screen.getByRole('button', { name: '展开详情' }));
    expect(screen.getByRole('table', { name: '代码差异' })).toBeVisible();
    rerender(<ToolCallCard call={{ ...call, result, error: 'Partial failure' }} active={false} defaultExpanded={false} />);
    expect(screen.getByText('Partial failure')).toBeVisible();
    expect(screen.getByRole('table')).toBeVisible();
  });

  it('shows active progress and failure feedback without revealing other reasoning fields', () => {
    const hidden = { ...message, content: '', reasoning: undefined, thinking: 'Hidden chain', reasoning_content: 'Private chain' };
    const { rerender } = render(<AnchoredMessageFlow messages={[hidden]} activeMessageId={message.id} />);
    expect(screen.queryByRole('button', { name: '公开推理摘要' })).toBeNull();
    expect(screen.queryByText(/Hidden chain|Private chain/)).toBeNull();
    expect(screen.getByTestId('anchored-thinking-bubble')).toBeVisible();
    rerender(<AnchoredMessageFlow messages={[{ ...message, failed: true }]} />);
    expect(screen.getByRole('alert')).toHaveTextContent('异常');
    expect(screen.getByText('Final answer')).toBeVisible();
  });

  it('splits the tool call card from the tool result block so the two styles never mix', () => {
    render(<ToolCallCard call={{ ...call, result: 'plain output' }} active={false} defaultExpanded={false} rawResult />);
    expect(screen.getByTestId('anchored-tool-result')).toBeVisible();
    expect(screen.queryByTestId('anchored-tool-card')).toBeNull();
    expect(screen.queryByLabelText('参数')).toBeNull();
    expect(screen.getByRole('button', { name: '展开详情' })).toHaveAttribute('aria-expanded', 'false');
  });

  it('keeps the tool result block collapsed and bounded until the reader expands it', async () => {
    const user = userEvent.setup();
    const result = Array.from({ length: 200 }, (_, i) => `line ${i}`).join('\n');
    render(<ToolCallCard call={{ ...call, result }} active={false} defaultExpanded={false} rawResult />);
    const toggle = screen.getByRole('button', { name: '展开详情' });
    const panel = document.getElementById(toggle.getAttribute('aria-controls')!)!;
    expect(panel).not.toBeVisible();
    expect(panel).toHaveClass('max-h-[var(--anchored-result-height)]');
    await user.click(toggle);
    expect(panel).toBeVisible();
    expect(screen.getByLabelText('工具结果')).toHaveTextContent('line 199');
  });

  it('renders a persisted tool role message as a collapsed result block', async () => {
    const user = userEvent.setup();
    render(<AnchoredMessageFlow messages={[{ id: 'tr-1', role: 'tool', content: 'diff --git a/f b/f\n@@ -1 +1 @@\n-old\n+new', tool_name: 'apply_patch' }]} />);
    expect(screen.getByTestId('anchored-tool-result')).toBeVisible();
    expect(screen.getByText('apply_patch')).toBeVisible();
    expect(screen.queryByRole('table')).toBeNull();
    await user.click(screen.getByRole('button', { name: '展开详情' }));
    expect(screen.getByRole('table', { name: '代码差异' })).toBeVisible();
  });

  it('renders the thinking icon with motion only while the agent is active', () => {
    const { rerender } = render(<AnchoredMessageFlow messages={[message]} activeMessageId={message.id} />);
    expect(screen.getByTestId('anchored-thinking-icon')).toHaveClass('motion-safe:animate-pulse');
    rerender(<AnchoredMessageFlow messages={[message]} />);
    expect(screen.getByTestId('anchored-thinking-icon')).not.toHaveClass('motion-safe:animate-pulse');
  });

  it('renders skeleton rows for the loading state instead of posing as an empty transcript', () => {
    render(<AnchoredMessageFlow messages={[]} loading />);
    expect(screen.getByTestId('chat-stream-skeleton')).toBeVisible();
    expect(screen.getByTestId('anchored-session-header')).toBeVisible();
  });

  it('keeps the transcript content once messages arrive, dropping the skeleton', () => {
    render(<AnchoredMessageFlow messages={[message]} loading />);
    expect(screen.queryByTestId('chat-stream-skeleton')).toBeNull();
    expect(screen.getByText('Final answer')).toBeVisible();
  });
});
