import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { SubscriptionsPage } from '../SubscriptionsPage';

describe('SubscriptionsPage', () => {
  it('renders without crashing', () => {
    const { container } = render(
      <MemoryRouter>
        <SubscriptionsPage />
      </MemoryRouter>
    );
    expect(container).toBeDefined();
  });

  it('renders page title', () => {
    render(
      <MemoryRouter>
        <SubscriptionsPage title="Subscriptions" />
      </MemoryRouter>
    );
    expect(screen.getByText('Subscriptions')).toBeDefined();
  });

  it('renders search input', () => {
    render(
      <MemoryRouter>
        <SubscriptionsPage />
      </MemoryRouter>
    );
    expect(screen.getByPlaceholderText('Search...')).toBeDefined();
  });
});
