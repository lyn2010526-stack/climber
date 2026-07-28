import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ChatInterface } from '../ChatInterface';

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
});
