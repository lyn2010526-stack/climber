import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import TracesPage from '../TracesPage';

vi.mock('../../components/tracing/TraceViewer', () => ({
  default: () => <div data-testid="trace-viewer">TraceViewer</div>,
}));

describe('TracesPage', () => {
  it('renders page title', () => {
    render(<TracesPage />);
    expect(screen.getByText('链路追踪')).toBeDefined();
  });

  it('renders description', () => {
    render(<TracesPage />);
    expect(screen.getByText('实时观察 LLM 调用、工具执行和智能体循环')).toBeDefined();
  });

  it('renders TraceViewer component', () => {
    render(<TracesPage />);
    expect(screen.getByTestId('trace-viewer')).toBeDefined();
  });
});
