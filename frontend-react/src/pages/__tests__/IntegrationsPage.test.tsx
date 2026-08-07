import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { IntegrationsPage } from '../IntegrationsPage';

describe('IntegrationsPage', () => {
  it('renders without crashing', () => {
    const { container } = render(
      <MemoryRouter>
        <IntegrationsPage />
      </MemoryRouter>
    );
    expect(container).toBeDefined();
  });

  it('renders page title', () => {
    render(
      <MemoryRouter>
        <IntegrationsPage title="Integrations" />
      </MemoryRouter>
    );
    expect(screen.getByText('Integrations')).toBeDefined();
  });

  it('renders search input', () => {
    render(
      <MemoryRouter>
        <IntegrationsPage />
      </MemoryRouter>
    );
    expect(screen.getByPlaceholderText('Search...')).toBeDefined();
  });
});
