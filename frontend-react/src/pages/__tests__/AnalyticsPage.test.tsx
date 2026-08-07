import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { AnalyticsPage } from '../AnalyticsPage';

describe('AnalyticsPage', () => {
  it('renders without crashing', () => {
    const { container } = render(
      <MemoryRouter>
        <AnalyticsPage />
      </MemoryRouter>
    );
    expect(container).toBeDefined();
  });

  it('renders page title', () => {
    render(
      <MemoryRouter>
        <AnalyticsPage title="Analytics" />
      </MemoryRouter>
    );
    expect(screen.getByText('Analytics')).toBeDefined();
  });

  it('renders search input', () => {
    render(
      <MemoryRouter>
        <AnalyticsPage />
      </MemoryRouter>
    );
    expect(screen.getByPlaceholderText('Search...')).toBeDefined();
  });

  it('renders refresh button', () => {
    render(
      <MemoryRouter>
        <AnalyticsPage />
      </MemoryRouter>
    );
    expect(screen.getByText('Refresh')).toBeDefined();
  });
});
