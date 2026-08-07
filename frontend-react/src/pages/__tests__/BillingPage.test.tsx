import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { BillingPage } from '../BillingPage';

describe('BillingPage', () => {
  it('renders without crashing', () => {
    const { container } = render(
      <MemoryRouter>
        <BillingPage />
      </MemoryRouter>
    );
    expect(container).toBeDefined();
  });

  it('renders page title', () => {
    render(
      <MemoryRouter>
        <BillingPage title="Billing" />
      </MemoryRouter>
    );
    expect(screen.getByText('Billing')).toBeDefined();
  });

  it('renders search input', () => {
    render(
      <MemoryRouter>
        <BillingPage />
      </MemoryRouter>
    );
    expect(screen.getByPlaceholderText('Search...')).toBeDefined();
  });
});
