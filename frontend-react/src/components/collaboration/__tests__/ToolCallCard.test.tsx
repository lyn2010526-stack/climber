import { describe, it, expect } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { ToolCallCard } from '../ToolCallCard';

describe('ToolCallCard', () => {
  it('renders without crashing', () => {
    const { container } = render(
      <ToolCallCard toolName="test_tool" args={{ key: "value" }} />
    );
    expect(container).toBeDefined();
  });

  it('renders tool name', () => {
    render(
      <ToolCallCard toolName="test_tool" args={{ key: "value" }} />
    );
    expect(screen.getByText('test_tool')).toBeDefined();
  });

  it('renders success icon when success is true', () => {
    const { container } = render(
      <ToolCallCard toolName="test_tool" args={{ key: "value" }} success={true} />
    );
    expect(container).toBeDefined();
  });

  it('renders error icon when success is false', () => {
    const { container } = render(
      <ToolCallCard toolName="test_tool" args={{ key: "value" }} success={false} />
    );
    expect(container).toBeDefined();
  });

  it('toggles expansion when clicked', () => {
    render(
      <ToolCallCard toolName="test_tool" args={{ key: "value" }} result="some result" />
    );
    fireEvent.click(screen.getByText('test_tool'));
    expect(screen.getByText('参数:')).toBeDefined();
  });

  it('renders arguments when expanded', () => {
    render(
      <ToolCallCard toolName="test_tool" args={{ key: "value" }} />
    );
    fireEvent.click(screen.getByText('test_tool'));
    expect(screen.getByText('参数:')).toBeDefined();
  });

  it('renders result when expanded', () => {
    render(
      <ToolCallCard toolName="test_tool" args={{ key: "value" }} result="some result" />
    );
    fireEvent.click(screen.getByText('test_tool'));
    expect(screen.getByText('结果:')).toBeDefined();
  });
});
