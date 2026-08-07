import { describe, it, expect } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { ToolCallVisualization, type ToolCall } from '../ToolCallVisualization';

const mockToolCalls: ToolCall[] = [
  {
    id: 'tc-1',
    name: 'file_read',
    arguments: { path: '/test.txt' },
    result: 'file content',
    status: 'success',
    duration: 150,
  },
  {
    id: 'tc-2',
    name: 'run_command',
    arguments: { cmd: 'ls -la' },
    status: 'running',
  },
  {
    id: 'tc-3',
    name: 'web_search',
    arguments: { query: 'test' },
    error: 'timeout',
    status: 'error',
  },
  {
    id: 'tc-4',
    name: 'unknown_tool',
    arguments: {},
    status: 'pending',
  },
];

describe('ToolCallVisualization', () => {
  it('returns null when no calls', () => {
    const { container } = render(<ToolCallVisualization calls={[]} />);
    expect(container.firstChild).toBeNull();
  });

  it('renders call count summary', () => {
    render(<ToolCallVisualization calls={mockToolCalls} />);
    expect(screen.getByText('4 个工具调用')).toBeDefined();
  });

  it('shows running count', () => {
    render(<ToolCallVisualization calls={mockToolCalls} />);
    expect(screen.getByText(/1 运行中/)).toBeDefined();
  });

  it('renders all tool call cards', () => {
    render(<ToolCallVisualization calls={mockToolCalls} />);
    expect(screen.getByText('file_read')).toBeDefined();
    expect(screen.getByText('run_command')).toBeDefined();
    expect(screen.getByText('web_search')).toBeDefined();
    expect(screen.getByText('unknown_tool')).toBeDefined();
  });

  it('toggles all expanded', () => {
    render(<ToolCallVisualization calls={mockToolCalls} />);
    const toggleBtn = screen.getByText('全部展开');
    fireEvent.click(toggleBtn);
    expect(screen.getByText('全部折叠')).toBeDefined();
  });

  it('shows duration for completed calls', () => {
    render(<ToolCallVisualization calls={mockToolCalls} />);
    expect(screen.getByText('150ms')).toBeDefined();
  });

  it('shows result preview for success calls', () => {
    render(<ToolCallVisualization calls={mockToolCalls} />);
    expect(screen.getByText(/file content/)).toBeDefined();
  });

  it('shows error preview for error calls', () => {
    render(<ToolCallVisualization calls={mockToolCalls} />);
    expect(screen.getByText(/timeout/)).toBeDefined();
  });

  it('expands to show args when clicked', () => {
    render(<ToolCallVisualization calls={[mockToolCalls[1]]} />);
    fireEvent.click(screen.getByText('run_command'));
    expect(screen.getByText(/参数/)).toBeDefined();
  });

  it('toggles args visibility', () => {
    render(<ToolCallVisualization calls={[mockToolCalls[1]]} />);
    fireEvent.click(screen.getByText('run_command'));
    const argsBtn = screen.getByText(/参数/);
    fireEvent.click(argsBtn);
    expect(screen.getByText(/"cmd": "ls -la"/)).toBeDefined();
  });

  it('toggles result visibility', () => {
    const calls: ToolCall[] = [{
      id: 'tc-r',
      name: 'tool_with_result',
      arguments: {},
      result: 'the result',
      status: 'running',
    }];
    render(<ToolCallVisualization calls={calls} />);
    fireEvent.click(screen.getByText('tool_with_result'));
    const resultBtn = screen.getByText('执行结果');
    fireEvent.click(resultBtn);
    expect(screen.getByText('the result')).toBeDefined();
  });

  it('shows error when expanded', () => {
    render(<ToolCallVisualization calls={[mockToolCalls[2]]} />);
    fireEvent.click(screen.getByText('web_search'));
    expect(screen.getByText('错误信息')).toBeDefined();
  });

  it('renders with className', () => {
    const { container } = render(<ToolCallVisualization calls={mockToolCalls} className="custom-class" />);
    expect(container.querySelector('.custom-class')).toBeDefined();
  });

  it('shows displayName when provided', () => {
    const calls: ToolCall[] = [{
      id: 'tc-d',
      name: 'my_tool',
      displayName: 'My Custom Tool',
      arguments: {},
      status: 'success',
    }];
    render(<ToolCallVisualization calls={calls} />);
    expect(screen.getByText('My Custom Tool')).toBeDefined();
  });

  it('formats duration correctly', () => {
    const calls: ToolCall[] = [{
      id: 'tc-dur',
      name: 'slow_tool',
      arguments: {},
      status: 'success',
      duration: 2500,
    }];
    render(<ToolCallVisualization calls={calls} />);
    expect(screen.getByText('2.5s')).toBeDefined();
  });
});
