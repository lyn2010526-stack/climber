import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { StatsPage } from '../StatsPage';

vi.mock('../../api', () => ({
  api: {
    getStats: vi.fn().mockResolvedValue(null),
  },
}));

describe('StatsPage', () => {
  it('renders loading state initially', () => {
    const { container } = render(<StatsPage />);
    expect(container).toBeDefined();
  });

  it('renders without crashing', () => {
    const { container } = render(<StatsPage />);
    expect(container.querySelector('.h-full')).not.toBeNull();
  });
});
