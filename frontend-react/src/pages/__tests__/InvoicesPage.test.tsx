import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { InvoicesPage } from '../InvoicesPage';

describe('InvoicesPage', () => {
  it('renders without crashing', () => {
    const { container } = render(
      <MemoryRouter>
        <InvoicesPage />
      </MemoryRouter>
    );
    expect(container).toBeDefined();
  });

  it('renders page title', () => {
    render(
      <MemoryRouter>
        <InvoicesPage title="Invoices" />
      </MemoryRouter>
    );
    expect(screen.getByText('Invoices')).toBeDefined();
  });

  it('renders search input', () => {
    render(
      <MemoryRouter>
        <InvoicesPage />
      </MemoryRouter>
    );
    expect(screen.getByPlaceholderText('Search...')).toBeDefined();
  });
});
