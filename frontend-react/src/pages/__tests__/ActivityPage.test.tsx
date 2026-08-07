import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { ActivityPage } from '../ActivityPage';

describe('ActivityPage', () => {
  it('renders without crashing', () => {
    const { container } = render(
      <MemoryRouter>
        <ActivityPage />
      </MemoryRouter>
    );
    expect(container).toBeDefined();
  });

  it('renders page title', () => {
    render(
      <MemoryRouter>
        <ActivityPage title="Activity" />
      </MemoryRouter>
    );
    expect(screen.getByText('Activity')).toBeDefined();
  });

  it('renders search input', () => {
    render(
      <MemoryRouter>
        <ActivityPage />
      </MemoryRouter>
    );
    expect(screen.getByPlaceholderText('Search...')).toBeDefined();
  });

  it('renders refresh button', () => {
    render(
      <MemoryRouter>
        <ActivityPage />
      </MemoryRouter>
    );
    expect(screen.getByText('Refresh')).toBeDefined();
  });
});
