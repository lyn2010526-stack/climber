import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ReasoningPage } from '../ReasoningPage';

vi.mock('../../components/workspace/ReasoningPanel', () => ({
  ReasoningPanel: () => <div data-testid="reasoning-panel">ReasoningPanel</div>,
}));

describe('ReasoningPage', () => {
  it('renders page title', () => {
    render(<ReasoningPage />);
    expect(screen.getByText('推理引擎')).toBeDefined();
  });

  it('renders description', () => {
    render(<ReasoningPage />);
    expect(screen.getByText('多策略推理：思维树、深度反思、辩论')).toBeDefined();
  });

  it('renders ReasoningPanel component', () => {
    render(<ReasoningPage />);
    expect(screen.getByTestId('reasoning-panel')).toBeDefined();
  });
});
