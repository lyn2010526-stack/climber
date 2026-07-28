import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { Dashboard, StatCard } from '../Dashboard';

describe('StatCard', () => {
  it('renders title and value', () => {
    render(<StatCard title="Users" value={1234} />);
    expect(screen.getByText('Users')).toBeDefined();
    expect(screen.getByText('1234')).toBeDefined();
  });

  it('renders trend indicator', () => {
    render(<StatCard title="Revenue" value={5000} change={{ value: 12, trend: 'up' }} />);
    expect(screen.getByText('12%')).toBeDefined();
  });

  it('renders bordered variant', () => {
    const { container } = render(<StatCard title="Test" value={1} variant="bordered" />);
    expect(container.querySelector('.border-white\\/10')).not.toBeNull();
  });
});

describe('Dashboard', () => {
  it('renders stats array', () => {
    render(
      <Dashboard
        stats={[
          { title: 'Active', value: 42, change: { value: 5, trend: 'up' } },
          { title: 'Errors', value: 3, change: { value: 2, trend: 'down' } },
        ]}
      />
    );
    expect(screen.getByText('Active')).toBeDefined();
    expect(screen.getByText('Errors')).toBeDefined();
  });

  it('renders default stats when none provided', () => {
    render(<Dashboard />);
    expect(screen.getByText('活跃会话')).toBeDefined();
    expect(screen.getByText('Token 消耗')).toBeDefined();
  });

  it('applies staggered animation classes', () => {
    const { container } = render(<Dashboard stats={[{ title: 'Test', value: 1 }]} />);
    const animatedDiv = container.querySelector('.animate-in');
    expect(animatedDiv).not.toBeNull();
  });
});
