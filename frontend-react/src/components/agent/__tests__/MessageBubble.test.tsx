import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MessageBubble } from '../MessageBubble';

describe('MessageBubble', () => {
  it('renders without crashing', () => {
    const { container } = render(
      <MessageBubble role="user" content="Hello" />
    );
    expect(container).toBeDefined();
  });

  it('renders user message', () => {
    render(<MessageBubble role="user" content="Hello world" />);
    expect(screen.getByText('Hello world')).toBeDefined();
    expect(screen.getByText('You')).toBeDefined();
  });

  it('renders assistant message', () => {
    render(<MessageBubble role="assistant" content="Hi there" />);
    expect(screen.getByText('Hi there')).toBeDefined();
    expect(screen.getByText('Climber')).toBeDefined();
  });

  it('renders system message', () => {
    render(<MessageBubble role="system" content="System message" />);
    expect(screen.getByText('System message')).toBeDefined();
    expect(screen.getByText('System')).toBeDefined();
  });

  it('renders tool message', () => {
    render(<MessageBubble role="tool" content="Tool output" />);
    expect(screen.getByText('Tool output')).toBeDefined();
    expect(screen.getByText('Tool')).toBeDefined();
  });

  it('renders reasoning section when provided', () => {
    render(
      <MessageBubble role="assistant" content="Answer" reasoning="Thinking..." />
    );
    expect(screen.getByText('Reasoning')).toBeDefined();
  });

  it('renders timestamp when provided', () => {
    const timestamp = new Date('2024-01-01T12:00:00');
    render(
      <MessageBubble role="user" content="Test" timestamp={timestamp} />
    );
    expect(screen.getByText(/12:00:00/)).toBeDefined();
  });
});
