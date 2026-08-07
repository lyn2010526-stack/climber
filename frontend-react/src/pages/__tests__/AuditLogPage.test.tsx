import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { AuditLogPage } from '../AuditLogPage';

describe('AuditLogPage', () => {
  it('renders without crashing', () => {
    const { container } = render(
      <MemoryRouter>
        <AuditLogPage />
      </MemoryRouter>
    );
    expect(container).toBeDefined();
  });

  it('renders page title', () => {
    render(
      <MemoryRouter>
        <AuditLogPage title="Audit Log" />
      </MemoryRouter>
    );
    expect(screen.getByText('Audit Log')).toBeDefined();
  });

  it('renders search input', () => {
    render(
      <MemoryRouter>
        <AuditLogPage />
      </MemoryRouter>
    );
    expect(screen.getByPlaceholderText('Search...')).toBeDefined();
  });
});
