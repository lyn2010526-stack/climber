import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import EvalPage from '../EvalPage';

vi.mock('../../components/eval/EvalDashboard', () => ({
  EvalDashboard: () => <div data-testid="eval-dashboard">EvalDashboard</div>,
}));

describe('EvalPage', () => {
  it('renders page title', () => {
    render(<EvalPage />);
    expect(screen.getByText('效果评估')).toBeDefined();
  });

  it('renders description', () => {
    render(<EvalPage />);
    expect(screen.getByText('运行自动化测试以衡量智能体质量')).toBeDefined();
  });

  it('renders EvalDashboard component', () => {
    render(<EvalPage />);
    expect(screen.getByTestId('eval-dashboard')).toBeDefined();
  });
});
