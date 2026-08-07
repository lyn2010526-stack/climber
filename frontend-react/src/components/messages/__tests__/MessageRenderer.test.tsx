import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { MessageRenderer } from '../MessageRenderer';

vi.mock('../../../store/workspace', () => ({
  useWorkspaceStore: (selector: any) => selector({ expertMode: true }),
}));

describe('MessageRenderer', () => {
  it('renders without crashing', () => {
    const message = { id: '1', type: 'user', content: 'Hello', timestamp: Date.now(), metadata: {} };
    const { container } = render(<MessageRenderer message={message} />);
    expect(container).toBeDefined();
  });

  it('renders user message', () => {
    const message = { id: '1', type: 'user', content: 'Hello world', timestamp: Date.now(), metadata: {} };
    render(<MessageRenderer message={message} />);
    expect(screen.getByText('Hello world')).toBeDefined();
  });

  it('renders thinking block', () => {
    const message = { id: '2', type: 'thinking', content: 'Thinking...', timestamp: Date.now(), metadata: {} };
    const { container } = render(<MessageRenderer message={message} />);
    expect(screen.getByText('Thinking')).toBeDefined();
  });

  it('renders tool call card', () => {
    const message = { id: '3', type: 'tool-call', content: 'Tool call', timestamp: Date.now(), metadata: {} };
    const { container } = render(<MessageRenderer message={message} />);
    expect(container).toBeDefined();
  });

  it('renders tool result card', () => {
    const message = { id: '4', type: 'tool-result', content: 'Tool result', timestamp: Date.now(), metadata: {} };
    const { container } = render(<MessageRenderer message={message} />);
    expect(container).toBeDefined();
  });

  it('renders system notification', () => {
    const message = { id: '5', type: 'system', content: 'System message', timestamp: Date.now(), metadata: {} };
    const { container } = render(<MessageRenderer message={message} />);
    expect(container).toBeDefined();
  });

  it('renders reflection card', () => {
    const message = { id: '6', type: 'reflection', content: 'Reflection', timestamp: Date.now(), metadata: {} };
    const { container } = render(<MessageRenderer message={message} />);
    expect(container).toBeDefined();
  });

  it('renders deep reflection', () => {
    const message = { id: '7', type: 'thinking', content: { type: 'deep_reflection', text: 'Deep' }, timestamp: Date.now(), metadata: {} };
    const { container } = render(<MessageRenderer message={message} />);
    expect(screen.getByText('Deep Reflection')).toBeDefined();
  });

  it('renders tokens in thinking block', () => {
    const message = { id: '8', type: 'thinking', content: 'Thinking...', timestamp: Date.now(), metadata: { tokens: 150 } };
    const { container } = render(<MessageRenderer message={message} />);
    expect(screen.getByText('150 tokens')).toBeDefined();
  });

  it('toggles thinking block expansion', () => {
    const message = { id: '9', type: 'thinking', content: 'Expanded content', timestamp: Date.now(), metadata: {} };
    const { container } = render(<MessageRenderer message={message} />);
    fireEvent.click(screen.getByText('Thinking'));
  });
});
