import { fireEvent, render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import i18n from '../../i18n';
import { ChatInterface } from './ChatInterface';
import { ThinkingIndicator } from './ThinkingIndicator';
import { ChatEmptyState } from './ChatEmptyState';

vi.mock('../../api', () => ({ api: { submitFeedback: vi.fn() } }));

describe('Task 03 chat stage', () => {
  beforeEach(async () => { await i18n.changeLanguage('zh-CN'); });
  it('protects IME input and submits trimmed text with Enter', () => {
    const onSend = vi.fn();
    render(<ChatInterface messages={[]} onSend={onSend} />);
    const input = screen.getByRole('textbox');
    fireEvent.change(input, { target: { value: '  task  ' } });
    fireEvent.keyDown(input, { key: 'Enter', isComposing: true });
    fireEvent.keyDown(input, { key: 'Enter', shiftKey: true });
    expect(onSend).not.toHaveBeenCalled();
    fireEvent.keyDown(input, { key: 'Enter' });
    expect(onSend).toHaveBeenCalledWith('task');
    expect(input).toHaveValue('');
  });

  it('fills and focuses the composer from a suggestion', () => {
    const onSend = vi.fn();
    render(<ChatInterface messages={[]} onSend={onSend} suggestions={['Review code']} />);
    fireEvent.click(screen.getByRole('button', { name: 'Review code' }));
    expect(screen.getByRole('textbox')).toHaveValue('Review code');
    expect(screen.getByRole('textbox')).toHaveFocus();
    expect(onSend).not.toHaveBeenCalled();
  });

  it('renders reasoning, tools and text together and only marks the active response', () => {
    const onStop = vi.fn();
    const messages = [
      { id: 'old', role: 'assistant' as const, content: 'Previous answer' },
      { id: 'current', role: 'assistant' as const, content: 'Current answer', reasoning: 'Reasoning detail',
        toolCalls: [{ id: 'tool', name: 'read_file', arguments: {}, status: 'running' as const }] },
    ];
    const { container, rerender } = render(<ChatInterface messages={messages} onSend={vi.fn()} onStop={onStop} isLoading />);
    expect(screen.getByText('Current answer')).toBeInTheDocument();
    expect(screen.getByText('read_file')).toBeInTheDocument();
    expect(screen.getByText('Reasoning detail')).toBeInTheDocument();
    expect(container.querySelectorAll('[data-streaming-cursor]')).toHaveLength(1);
    fireEvent.click(screen.getByRole('button', { name: '停止生成' }));
    expect(onStop).toHaveBeenCalledOnce();
    rerender(<ChatInterface messages={messages} onSend={vi.fn()} onStop={onStop} isLoading={false} />);
    expect(container.querySelector('[data-streaming-cursor]')).toBeNull();
    expect(screen.queryByRole('status')).toBeNull();
    expect(screen.queryByText('执行中')).toBeNull();
  });

  it('uses the result-first tool disclosure in the live chat row', () => {
    render(<ChatInterface messages={[{
      id: 'tool-turn', role: 'assistant', content: '',
      toolCalls: [{ id: 'tool-1', name: 'run_command', arguments: { command: 'npm test' }, result: 'all passed', status: 'success' }],
    }]} onSend={vi.fn()} />);

    const tool = screen.getByRole('button', { name: /run_command/ });
    expect(tool).toHaveAttribute('aria-expanded', 'false');
    fireEvent.click(tool);
    expect(screen.getByLabelText(i18n.t('tool_call.result'))).toHaveTextContent('all passed');
    expect(screen.getByRole('button', { name: `${i18n.t('tool_call.arguments')} (1)` })).toHaveAttribute('aria-expanded', 'false');
  });

  it('keeps drafts while loading and disables unavailable stop', () => {
    const onSend = vi.fn();
    render(<ChatInterface messages={[]} onSend={onSend} isLoading />);
    fireEvent.change(screen.getByRole('textbox'), { target: { value: 'next task' } });
    fireEvent.keyDown(screen.getByRole('textbox'), { key: 'Enter' });
    expect(onSend).not.toHaveBeenCalled();
    expect(screen.getByRole('textbox')).toHaveValue('next task');
    expect(screen.getByRole('button', { name: '停止生成' })).toBeDisabled();
  });

  it('uses explicit stage text without synthetic progress', () => {
    const { rerender } = render(<ThinkingIndicator stage="Waiting for tool" />);
    expect(screen.getByRole('status')).toHaveTextContent('Waiting for tool');
    expect(screen.queryByRole('progressbar')).toBeNull();
    rerender(<ThinkingIndicator isActive={false} />);
    expect(screen.queryByRole('status')).toBeNull();
  });

  it('preserves edit submission and rejects blank edits', () => {
    const onSend = vi.fn();
    render(<ChatInterface messages={[{ id: 'a', role: 'assistant', content: 'Answer' }]} onSend={onSend} />);
    fireEvent.click(screen.getByRole('button', { name: '编辑' }));
    const editor = screen.getByRole('textbox', { name: '编辑消息' });
    fireEvent.change(editor, { target: { value: '   ' } });
    expect(screen.getByRole('button', { name: /保存/ })).toBeDisabled();
    fireEvent.change(editor, { target: { value: ' revised ' } });
    fireEvent.click(screen.getByRole('button', { name: /保存/ }));
    expect(onSend).toHaveBeenCalledWith('revised');
  });

  it('allows reading history during streaming and resumes following on demand', () => {
    const messages = [{ id: 'a', role: 'assistant' as const, content: 'Answer' }];
    const { container, rerender } = render(<ChatInterface messages={messages} onSend={vi.fn()} isLoading />);
    const viewport = container.querySelector('.overflow-y-auto') as HTMLDivElement;
    Object.defineProperties(viewport, { scrollHeight: { value: 1200 }, clientHeight: { value: 400 } });
    viewport.scrollTop = 100;
    fireEvent.scroll(viewport);
    rerender(<ChatInterface messages={[{ ...messages[0], content: 'More content' }]} onSend={vi.fn()} isLoading />);
    expect(viewport.scrollTop).toBe(100);
    fireEvent.click(screen.getByRole('button', { name: '滚动到底部' }));
    expect(viewport.scrollTop).toBe(1200);
  });

  it('renders a minimal empty state and preserves custom content', () => {
    const { rerender } = render(<ChatEmptyState />);
    expect(screen.getByRole('heading')).toBeInTheDocument();
    expect(screen.queryByText(/自主执行/)).toBeNull();
    rerender(<ChatEmptyState title="Title" description="Description" actions={<button>Action</button>} />);
    expect(screen.getByText('Description')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Action' })).toBeInTheDocument();
  });
});
