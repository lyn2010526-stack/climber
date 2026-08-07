import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { WebhooksPage } from '../WebhooksPage';

describe('WebhooksPage', () => {
  it('renders without crashing', () => {
    const { container } = render(
      <MemoryRouter>
        <WebhooksPage />
      </MemoryRouter>
    );
    expect(container).toBeDefined();
  });

  it('renders page title', () => {
    render(
      <MemoryRouter>
        <WebhooksPage title="Webhooks" />
      </MemoryRouter>
    );
    expect(screen.getByText('Webhooks')).toBeDefined();
  });

  it('renders search input', () => {
    render(
      <MemoryRouter>
        <WebhooksPage />
      </MemoryRouter>
    );
    expect(screen.getByPlaceholderText('Search...')).toBeDefined();
  });
});
