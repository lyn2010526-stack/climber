import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import CostPage from '../CostPage';

vi.mock('../../api', () => ({
  api: {
    getCostUsage: vi.fn().mockResolvedValue({ total_cost: 0, total_tokens: 0, total_calls: 0, by_model: [], by_day: [] }),
    getCostBudget: vi.fn().mockResolvedValue({ daily_limit: 0, weekly_limit: 0, monthly_limit: 0, current_daily: 0, current_weekly: 0, current_monthly: 0 }),
  },
}));

describe('CostPage', () => {
  it('renders without crashing', () => {
    const { container } = render(<CostPage />);
    expect(container).toBeDefined();
  });

  it('renders page header while loading', () => {
    render(<CostPage />);
    expect(screen.getByText('成本概览')).toBeDefined();
  });
});
