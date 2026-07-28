import { describe, it, expect } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { MessageContent } from '../MessageContent';
import { ToolCallCard } from '../MessageContent';

describe('MessageContent', () => {
  it('renders user message with correct alignment', () => {
    render(<MessageContent content="Hello" role="user" timestamp={new Date('2024-01-01T12:00:00')} actions={undefined} />);
    expect(screen.getByText('Hello')).toBeDefined();
  });

  it('renders assistant message', () => {
    render(<MessageContent content="Hi there" role="assistant" timestamp={new Date('2024-01-01T12:00:00')} actions={undefined} />);
    expect(screen.getByText('Hi there')).toBeDefined();
  });

  it('renders system message', () => {
    render(<MessageContent content="System notice" role="system" timestamp={new Date('2024-01-01T12:00:00')} actions={undefined} />);
    expect(screen.getByText('System notice')).toBeDefined();
  });

  it('renders timestamp', () => {
    render(<MessageContent content="Test" role="user" timestamp={new Date('2024-01-01T12:00:00')} actions={undefined} />);
    const timeElements = screen.getAllByText(/12:00/);
    expect(timeElements.length).toBeGreaterThan(0);
  });

  it('renders actions when provided', () => {
    render(
      <MessageContent content="Test" role="assistant" timestamp={new Date('2024-01-01T12:00:00')} actions={<button>Action</button>} />
    );
    expect(screen.getByText('Action')).toBeDefined();
  });
});

describe('ToolCallCard', () => {
  it('renders tool name', () => {
    render(<ToolCallCard name="search" arguments={{ query: "test" }} result="found results" error={undefined} isRunning={false} />);
    expect(screen.getByText('search')).toBeDefined();
  });

  it('shows loading state', () => {
    render(<ToolCallCard name="search" arguments={{}} result={undefined} error={undefined} isRunning />);
    expect(screen.getByText('search')).toBeDefined();
  });

  it('shows error badge', () => {
    render(<ToolCallCard name="search" arguments={{}} result={undefined} error="Something went wrong" isRunning={false} />);
    expect(screen.getByText('error')).toBeDefined();
  });

  it('expands on click', () => {
    render(<ToolCallCard name="search" arguments={{ query: "test" }} result="found" error={undefined} isRunning={false} />);
    const button = screen.getByText('search').closest('button');
    fireEvent.click(button!);
    expect(screen.getByText('Output')).toBeDefined();
  });
});
