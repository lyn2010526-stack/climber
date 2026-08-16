import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ChatInterface } from '../ChatInterface';

vi.mock('../../../api', () => ({
  api: {
    listModels: vi.fn().mockResolvedValue([]),
    submitFeedback: vi.fn().mockResolvedValue(undefined),
    resolvePermission: vi.fn().mockResolvedValue(undefined),
  },
}));

describe('ChatInterface', () => {
  it('renders without crashing with empty messages', () => {
    render(<ChatInterface messages={[]} onSend={() => {}} onStop={() => {}} isLoading={false} />);
    expect(screen.getByText('开始新的对话')).toBeDefined();
  });

  it('renders empty state description', () => {
    render(<ChatInterface messages={[]} onSend={() => {}} onStop={() => {}} isLoading={false} />);
    expect(screen.getByText('输入任何问题或任务，Climber 将为你自主执行。')).toBeDefined();
  });

  it('renders suggestions', () => {
    render(<ChatInterface messages={[]} onSend={() => {}} onStop={() => {}} isLoading={false} />);
    expect(screen.getByText('帮我分析代码')).toBeDefined();
  });

  it('renders reasoning, tool execution, and final answer together', () => {
    render(
      <ChatInterface
        messages={[{
          id: 'assistant-1',
          role: 'assistant',
          content: '最终答案',
          reasoning: '分析过程',
          toolCalls: [{ id: 'tool-1', name: 'read_file', arguments: {}, result: 'ok', status: 'success' }],
        }]}
        onSend={() => {}}
        isLoading={false}
      />,
    );

    expect(screen.getByText(/思考完成/)).toBeDefined();
    expect(screen.getByText('read_file')).toBeDefined();
    expect(screen.getByText('最终答案')).toBeDefined();
  });

  it('renders the new composer', () => {
    render(<ChatInterface messages={[]} onSend={() => {}} isLoading={false} />);

    expect(screen.getByRole('textbox', { name: '消息输入框' })).toBeDefined();
    expect(screen.getByRole('button', { name: '添加附件' })).toBeDefined();
  });
});
